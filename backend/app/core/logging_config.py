"""
Application-wide logging configuration.

RC-1 audit finding B2: before this, exactly one file in the entire backend
(`app/agents/llm_client.py`) used the `logging` module at all -- no request
logging, no error logging in any service or router. The first real incident
during external beta would have been effectively undiagnosable.

Deliberately minimal for a beta, not a full observability stack: structured
stdout logging via the standard library's `logging` module, configured once
at process startup. No external log aggregation service, no JSON formatter,
no correlation IDs -- none of that is justified yet by real production usage
(same "don't build ahead of evidence" principle used everywhere else in this
project). This is meant to make a production incident diagnosable, not to be
a finished observability platform.

Call `configure_logging()` exactly once, from app.main, before anything else
in the application logs. Every other module gets its own logger via
`logging.getLogger(__name__)`, following the pattern already established in
llm_client.py -- this file only sets the root handler/format/level once.
"""

import logging

from app.core.config import get_settings


def configure_logging() -> None:
    settings = get_settings()
    # DEBUG locally (app_env defaults to "development"), INFO everywhere
    # else -- consistent with the project's existing "development is more
    # permissive, everything else is treated as real" posture (see
    # Settings._validate_secret_key for the same pattern applied to the
    # JWT secret).
    level = logging.DEBUG if settings.app_env == "development" else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    # uvicorn's own loggers are configured separately by uvicorn itself;
    # left alone here rather than silenced or reconfigured, so its access
    # log (request method/path/status/latency) keeps working unmodified.
