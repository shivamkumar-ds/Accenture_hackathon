# BidOps AI
# Database Design Document

Version: 1.1

---

# Overview

This document defines the database architecture for BidOps AI.

The platform manages enterprise knowledge, AI-generated insights, workflow execution, uploaded documents, and organizational capability. The database is designed to support transactional consistency, auditability, scalability, and future expansion while maintaining a clear separation between operational data and AI knowledge.

The MVP adopts a relational database as the primary system of record, complemented by object storage for documents. The Company Capability Graph is represented using relational structures with extensible relationships, allowing migration to a graph database in future versions if required.

---

# Design Goals

The database is designed around the following principles:

- Normalized relational schema
- Strong data integrity
- Clear entity relationships
- High auditability
- Efficient querying
- Extensible capability model
- Secure enterprise storage

---

# Storage Strategy

The platform separates information into three storage categories.

### Relational Database

Stores structured enterprise data.

Examples:

- Users
- Companies
- Missions
- Capabilities
- Recommendations
- Audit Logs

---

### Object Storage

Stores uploaded files.

Examples:

- Tender PDFs
- ISO Certificates
- Employee CVs
- Financial Reports
- Images

Only metadata is stored inside the database.

---

### Knowledge Layer

Stores structured organizational capability.

Examples:

- Certifications
- Employees
- Projects
- Equipment
- Financial Capacity

This forms the Company Capability Graph.

---

# Core Database Entities

The MVP consists of the following primary entities.

```
Company

│

├── Users

├── Documents

├── Employees

├── Certifications

├── Projects

├── Equipment

├── Financial Records

├── Missions

│      ├── Capability Snapshot

│      ├── Tender

│      ├── Requirement

│      ├── Recommendation

│      ├── Compliance Matrix

│      └── Audit Log
```

---

# Company Table

Represents an organization using BidOps AI.

Fields:

- Company ID
- Company Name
- Industry
- Registration Number
- Country
- Created Date
- Updated Date

Relationships:

One Company

↓

Many Users

Many Documents

Many Missions

Many Capability Records

---

# User Table

Represents authenticated platform users.

Fields:

- User ID
- Company ID
- Name
- Email
- Password Hash
- Role
- Status
- Created At

Roles include:

- Administrator
- Executive
- Bid Manager
- Reviewer
- Auditor

---

# Document Table

Stores metadata for uploaded files.

Fields:

- Document ID
- Company ID
- Document Type
- File Name
- Storage Path
- Upload Time
- Version
- Processing Status

Actual file contents remain in object storage.

### Additional Fields (Confidence Pipeline)

| Field | Type |
|------|------|
| extraction_confidence | Decimal |
| processed_at | Timestamp |

Document confidence becomes the first stage of the confidence propagation pipeline.

---

# Common Metadata

Every capability entity — Certification, Employee, Project, Equipment, and Financial Record — maintains common metadata to support enterprise governance.

| Field | Type | Description |
|------|------|-------------|
| created_at | Timestamp | Record creation time |
| updated_at | Timestamp | Last modification |
| last_verified_at | Timestamp | Last time the information was verified |
| verification_status | Enum | Pending / Verified / Expired / Review Required |
| confidence_score | Decimal | Confidence of extracted information |
| source_document_id | UUID | Original supporting document |

This immediately makes the Capability Graph freshness-aware. Each of the five capability entity tables below includes these fields in addition to its own.

---

# Certification Table

Represents organizational certifications.

Fields:

- Certification ID
- Company ID
- Certification Name
- Issuing Authority
- Issue Date
- Expiry Date
- Status
- Source Document

Also includes Common Metadata (created_at, updated_at, last_verified_at, verification_status, confidence_score, source_document_id — see Common Metadata above).

---

# Employee Table

Represents organizational personnel.

Fields:

- Employee ID
- Company ID
- Name
- Position
- Qualification
- Experience
- Availability
- Skills
- Source Document

Also includes Common Metadata (created_at, updated_at, last_verified_at, verification_status, confidence_score, source_document_id — see Common Metadata above).

---

# Project Table

Represents historical organizational experience.

Fields:

- Project ID
- Company ID
- Client
- Industry
- Contract Value
- Duration
- Completion Status
- Similarity Tags

Also includes Common Metadata (created_at, updated_at, last_verified_at, verification_status, confidence_score, source_document_id — see Common Metadata above).

---

# Equipment Table

Represents organizational assets.

Fields:

- Equipment ID
- Company ID
- Equipment Name
- Category
- Quantity
- Availability
- Specifications

Also includes Common Metadata (created_at, updated_at, last_verified_at, verification_status, confidence_score, source_document_id — see Common Metadata above).

---

# Financial Record Table

Stores summarized financial capability.

Fields:

- Financial Record ID
- Company ID
- Financial Year
- Revenue
- Net Worth
- Working Capital
- Credit Rating

Also includes Common Metadata (created_at, updated_at, last_verified_at, verification_status, confidence_score, source_document_id — see Common Metadata above).

---

# Mission Table

| actual_outcome | Enum | Won / Lost / Disqualified / Cancelled / Withdrawn |
| outcome_notes | Text | Final outcome remarks |

Represents an AI workflow execution.

Fields:

- Mission ID
- Company ID
- User ID
- Mission Type
- Status
- Created At
- Completed At

Mission States:

- Created
- Running
- Awaiting Approval
- Completed
- Archived

### Additional Fields (Snapshot & Recommendation Linkage)

| Field | Type |
|------|------|
| capability_snapshot_id | UUID |
| recommendation_id | UUID |

The Mission now permanently knows exactly which snapshot generated its recommendation.

---

# Capability Snapshot Table

The Capability Snapshot captures the complete organizational capability state used during mission evaluation.

Unlike the live Company Capability Graph, snapshots are immutable and preserve historical evidence for auditing and recommendation reproducibility.

Fields:

| Field | Type |
|------|------|
| snapshot_id | UUID |
| mission_id | UUID |
| created_at | Timestamp |
| snapshot_version | Integer |
| snapshot_data | JSONB |
| generated_by | String |

Purpose:

Stores the exact capability information used when a recommendation was generated.

Snapshots guarantee:

- Recommendation reproducibility
- Enterprise auditing
- Governance
- Historical investigation

---

# Tender Table

Stores uploaded tender information.

Fields:

- Tender ID
- Mission ID
- Tender Name
- Organization
- Closing Date
- Uploaded Document
- Processing Status

---

# Requirement Table

Stores extracted tender requirements.

Fields:

- Requirement ID
- Tender ID
- Requirement Type
- Description
- Mandatory
- Source Page
- Confidence

---

# Capability Mapping Table

Links organizational capability with tender requirements.

Fields:

- Mapping ID
- Requirement ID
- Capability Entity
- Match Status
- Evidence
- Confidence

Possible Status:

- Met
- Not Met
- Review Required
- Conditional

---

# Recommendation Table

Stores AI recommendations.

Fields:

- Recommendation ID
- Mission ID
- Recommendation Type
- Executive Summary
- Risk Level
- Generated At

The single `Confidence` field has been replaced by the following confidence breakdown, each stored independently:

| Field | Type |
|------|------|
| document_confidence | Decimal |
| entity_confidence | Decimal |
| matching_confidence | Decimal |
| recommendation_confidence | Decimal |
| overall_confidence | Decimal |
| snapshot_id | UUID |

The Recommendation table now references its Capability Snapshot.

Possible Recommendations:

- Go
- Conditional Go
- Review
- No Go

---

# Compliance Matrix Table

| Field | Type | Description |
|------|------|-------------|
| requires_verification | Boolean | Indicates whether mandatory human verification is required |
| verification_reason | Text | Reason for mandatory verification |
| risk_level | Enum | Low / Medium / High / Critical |
| verification_status | Enum | Pending / Verified / Rejected |
| verified_by | UUID | Authorized reviewer who completed verification |
| verified_at | Timestamp | Time of verification |
| matching_confidence | Decimal | Confidence of capability matching |
| evidence_reference | UUID | Supporting capability entity |

### Additional Fields (Verification & Confidence)

| Field | Type | Description |
|------|------|-------------|
| requires_verification | Boolean | Mandatory human verification required |
| verification_reason | Text | Why verification is required |
| matching_confidence | Decimal | Confidence of capability matching |
| evidence_reference | UUID | Supporting capability entity |

---

# Audit Log Table

Maintains complete execution history.

Fields:

- Audit ID
- Mission ID
- User
- Agent
- Timestamp
- Event
- Result

Every significant system action generates an audit record.

---

# Entity Relationships

```
Company

│

├── Users

├── Documents

├── Certifications

├── Employees

├── Projects

├── Equipment

├── Financial Records

└── Missions

        │

        ├── Tender

        │

        ├── Requirements

        │

        ├── Capability Mapping

        │

        ├── Recommendation

        │

        ├── Compliance Matrix

        │

        └── Audit Logs
```

---

# Capability Snapshot Relationships

```
Mission
    │
    │ 1
    │
    ▼
Capability Snapshot
    │
    │
    ▼
Recommendation
```

```
Recommendation
    │
    ▼
Compliance Matrix
```

```
Compliance Matrix
    │
    ▼
Capability Graph
```

This explains how everything connects.

---

# Confidence Propagation Model

BidOps AI stores confidence throughout the complete reasoning pipeline.

```
Document
↓
Entity
↓
Requirement
↓
Matching
↓
Recommendation
```

Each confidence value is stored independently to improve explainability, auditing, and enterprise analytics.

The final recommendation confidence is derived from the complete propagation chain rather than a single confidence calculation.

---

# Database Constraints

Primary keys are UUIDs.

Foreign key constraints enforce referential integrity.

Unique constraints apply to:

- Email
- Company Registration Number
- Document Version

Cascade delete is avoided for audit-critical records.

Historical data remains immutable.

---

# Indexing Strategy

Indexes are created on frequently queried fields.

Examples:

- Company ID
- User ID
- Mission ID
- Tender ID
- Requirement Type
- Expiry Date
- Status
- Created At

Composite indexes are used for common enterprise queries.

---

# Soft Delete Strategy

Business records are never permanently deleted.

Instead:

- Active
- Archived
- Deleted

This preserves audit history.

---

# Versioning

Uploaded documents support version control.

Each upload creates:

- Version Number
- Upload Timestamp
- Previous Version Reference

Historical versions remain accessible.

---

# Auditability

Every important business event is recorded.

Examples include:

- Login
- Document Upload
- AI Evaluation
- Recommendation Generation
- Human Approval
- Workflow Completion

This supports enterprise governance and regulatory requirements.

---

# Security Considerations

Sensitive information is protected using:

- Encrypted passwords
- Encrypted storage paths
- Role-Based Access Control
- Foreign key integrity
- Audit logging
- Principle of Least Privilege

Personally identifiable information is stored separately from workflow execution data where appropriate.

---

# Scalability

The schema supports future expansion.

Additional entities can be introduced without redesigning the core structure.

Examples include:

- Vendor Management
- Contract Lifecycle
- Procurement
- ERP Integration
- Marketplace

The relational design provides a stable foundation while allowing migration toward specialized graph databases if organizational knowledge becomes significantly more interconnected.

---

# Database Design Principles

The database is designed according to five principles.

- Every recommendation must be reproducible.
- Every recommendation must reference supporting evidence.
- Organizational capability is treated as structured knowledge rather than documents.
- Confidence is propagated across the complete reasoning pipeline.
- Historical data is immutable once used for enterprise decision making.

---

# Database Design Summary

The BidOps AI database is designed to provide a reliable and extensible foundation for enterprise decision intelligence. It separates structured operational data, persistent organizational knowledge, and unstructured documents into appropriate storage layers while maintaining strong integrity, auditability, and security.

The schema emphasizes clarity, modularity, and future scalability, ensuring that the Company Capability Graph, mission workflows, and AI-generated recommendations remain consistent and traceable throughout the lifecycle of the platform.