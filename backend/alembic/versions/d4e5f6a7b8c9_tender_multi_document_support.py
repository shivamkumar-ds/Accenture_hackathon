"""tender multi-document support (real-CPPP-tender validation gap)

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-08-15 00:00:00.000000

Local customer-journey validation with a real CPPP tender (tender.pdf +
tech.xls + BOQ_969057.xls) surfaced a genuine, pre-existing product
limitation: a Tender could only ever have one source document, and only
PDF was accepted. This migration adds the minimum schema needed for a
Tender to have multiple attached Documents (main/technical/financial/
annexure) and for a Requirement to record exactly which attached
document (and where in it) it was extracted from.

Documents.tender_id / documents.document_role: additive, nullable
columns on the existing, already-generic `documents` table -- no new
table needed. NULL tender_id (the default for every existing row) means
"not a tender document" exactly as before this migration; nothing about
capability documents or the storage abstraction changes.

requirements.source_document_id / requirements.source_location:
additive, nullable columns. requirements.source_page is UNCHANGED in
both column definition and meaning -- for a tender with a single PDF
document (every tender created before this feature, and every tender
that still only attaches one PDF going forward), source_page continues
to mean exactly what it always has.

Backfill: every existing Tender's Document (found via the pre-existing
tenders.uploaded_document column, which is NOT removed or changed by
this migration) is retroactively linked via the new columns
(tender_id = tenders.id, document_role = 'main'), so
tender_service.run_analysis()'s new "query all documents attached to
this tender" logic finds it without any special-case fallback code path
for pre-existing data. Deterministic, safe to run against any real
database state (WHERE tender_id IS NULL guards against ever
double-applying it), and required by this migration's own backward-
compatibility contract, not incidental cleanup.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('documents', sa.Column('tender_id', UUID(as_uuid=True), sa.ForeignKey('tenders.id'), nullable=True))
    op.add_column('documents', sa.Column('document_role', sa.String(), nullable=True))
    op.create_index('ix_documents_tender_id', 'documents', ['tender_id'])

    op.add_column('requirements', sa.Column('source_document_id', UUID(as_uuid=True), sa.ForeignKey('documents.id'), nullable=True))
    op.add_column('requirements', sa.Column('source_location', sa.String(), nullable=True))

    # Backfill: link every existing Tender's already-referenced main
    # document via the new general relationship. Idempotent (guarded by
    # `documents.tender_id IS NULL`) and safe against Tenders whose
    # uploaded_document has since gone missing (LEFT the join effectively
    # a no-op for that row via the WHERE, since documents.id must match).
    op.execute(
        """
        UPDATE documents
        SET tender_id = tenders.id, document_role = 'main'
        FROM tenders
        WHERE tenders.uploaded_document = documents.id
          AND documents.tender_id IS NULL
        """
    )


def downgrade() -> None:
    op.drop_column('requirements', 'source_location')
    op.drop_column('requirements', 'source_document_id')
    op.drop_index('ix_documents_tender_id', table_name='documents')
    op.drop_column('documents', 'document_role')
    op.drop_column('documents', 'tender_id')
