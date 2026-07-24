"""
Pydantic schemas for Document.

storage_path is never included in DocumentRead — exposing the server's
internal filesystem layout to API consumers is an information-disclosure
risk with no legitimate client use. Retrieval goes through the document
ID via the download endpoint, not a client-supplied path.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import DocumentProcessingStatus


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    uploaded_by: uuid.UUID
    document_type: str
    file_name: str
    upload_time: datetime
    version: int
    processing_status: DocumentProcessingStatus
