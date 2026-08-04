"""
Regression coverage for Bug #003 (docs/BUG_BUCKET.md): mission_service.execute_mission()
used to guard against double-execution with a plain read-then-write
(check mission.status, then separately set it to RUNNING) -- a classic
check-then-act race. Two concurrent execute requests for the same mission
(double-click, two tabs, a client retry) could both read the pre-RUNNING
status before either committed, both pass the guard, and both proceed.

The fix replaces the guard with a single atomic `UPDATE ... WHERE
status = :expected_status`, exposed here as
mission_service._try_transition_to_running(). This test proves the
compare-and-swap itself: it simulates the exact interleaving that used to
be unsafe -- session A reads the mission while it's still CREATED, then
(before A's transition), session B independently moves the mission to
RUNNING and commits. When A's transition is finally attempted with the
status it originally observed, it must fail (rowcount 0), not silently
overwrite session B's change.
"""

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models import Company, Mission, User
from app.models.enums import MissionStatus, UserRole, UserStatus
from app.services import mission_service


@pytest.fixture()
def engine():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine, tables=[Company.__table__, User.__table__, Mission.__table__])
    return engine


def _make_company_user_mission(session):
    company = Company(id=uuid.uuid4(), name="Acme", registration_number=str(uuid.uuid4()))
    session.add(company)
    session.flush()
    user = User(
        id=uuid.uuid4(), company_id=company.id, name="Admin", email=f"{uuid.uuid4()}@example.com",
        password_hash="x", role=UserRole.ADMINISTRATOR, status=UserStatus.ACTIVE,
    )
    session.add(user)
    session.flush()
    mission = Mission(
        id=uuid.uuid4(), company_id=company.id, user_id=user.id,
        mission_type="tender_evaluation", status=MissionStatus.CREATED,
    )
    session.add(mission)
    session.commit()
    return company, user, mission


def test_concurrent_transition_to_running_only_succeeds_once(engine):
    Session = sessionmaker(bind=engine)
    session_a = Session()
    session_b = Session()

    _company, _user, mission = _make_company_user_mission(session_a)
    mission_id = mission.id
    session_a.close()
    session_b.close()

    # Two independent sessions, each reading the mission as it currently
    # stands (CREATED) -- exactly what two concurrent HTTP requests would
    # each do at the top of execute_mission().
    session_a = Session()
    session_b = Session()
    mission_a = session_a.get(Mission, mission_id)
    mission_b = session_b.get(Mission, mission_id)
    assert mission_a.status == MissionStatus.CREATED
    assert mission_b.status == MissionStatus.CREATED

    # Session B "wins the race": its transition commits first.
    won = mission_service._try_transition_to_running(session_b, mission_b, MissionStatus.CREATED)
    assert won is True
    assert mission_b.status == MissionStatus.RUNNING

    # Session A attempts the same transition based on the status it
    # observed before B's commit -- this must now fail, not silently
    # flip the mission to RUNNING a second time and let A's caller
    # proceed to run analysis/evaluation concurrently with B's.
    lost = mission_service._try_transition_to_running(session_a, mission_a, MissionStatus.CREATED)
    assert lost is False

    session_a.close()
    session_b.close()

    verify = Session()
    final = verify.get(Mission, mission_id)
    assert final.status == MissionStatus.RUNNING  # only B's transition ever applied
    verify.close()
