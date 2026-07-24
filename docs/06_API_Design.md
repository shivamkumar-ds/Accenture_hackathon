# BidOps AI
# API Design Document

Version: 1.0

---

# Overview

This document defines the REST API architecture of BidOps AI.

The API layer serves as the communication bridge between the frontend application, backend services, AI processing engine, and enterprise data layer.

The APIs are designed using RESTful principles with stateless communication, JWT-based authentication, structured JSON payloads, and standardized response formats.

The design prioritizes consistency, security, scalability, and future extensibility.

---

# API Design Principles

The API architecture follows several guiding principles.

• RESTful design

• Stateless communication

• JSON request/response format

• Versioned endpoints

• Secure authentication

• Consistent error handling

• Modular service boundaries

• Enterprise scalability

---

# API Architecture

```
Flutter App

↓

REST API Gateway

↓

Authentication Middleware

↓

Business Services

↓

AI Processing Layer

↓

Database

↓

Object Storage
```

Every client request enters through the API Gateway before being routed to the appropriate backend service.

---

# Authentication

Authentication is required for all protected endpoints.

The MVP uses JWT (JSON Web Tokens).

Authentication Flow:

Login

↓

Credentials Verified

↓

JWT Generated

↓

JWT Sent to Client

↓

Client Includes Token in Every Request

---

# Authorization

Role-Based Access Control (RBAC) determines which endpoints a user may access.

Supported roles include:

- Administrator
- Executive
- Bid Manager
- Reviewer
- Auditor

Future versions may support organization-specific permission policies.

---

# Standard Request Format

Example:

```json
{
  "company_id": "uuid",
  "mission_type": "tender_evaluation"
}
```

---

# Standard Success Response

```json
{
  "success": true,
  "message": "Mission created successfully",
  "data": {}
}
```

---

# Standard Error Response

```json
{
  "success": false,
  "error": {
    "code": "MISSION_NOT_FOUND",
    "message": "Requested mission does not exist."
  }
}
```

---

# Authentication APIs

## POST /api/v1/auth/login

Authenticates a user.

Request

```json
{
  "email": "user@company.com",
  "password": "********"
}
```

Response

```json
{
  "token": "jwt_token",
  "user": {}
}
```

---

## POST /api/v1/auth/logout

Terminates user session.

---

## GET /api/v1/auth/profile

Returns authenticated user information.

---

# Company APIs

## POST /api/v1/company

Create a company.

---

## GET /api/v1/company/{id}

Retrieve company details.

---

## PUT /api/v1/company/{id}

Update company profile.

---

# User APIs

## POST /api/v1/users

Create user.

---

## GET /api/v1/users

Retrieve organization users.

---

## PUT /api/v1/users/{id}

Update user.

---

## DELETE /api/v1/users/{id}

Deactivate user.

---

# Document APIs

## POST /api/v1/documents/upload

Upload enterprise documents.

Supported:

- PDF
- DOCX
- Images

Response

```json
{
  "document_id": "uuid",
  "status": "uploaded"
}
```

---

## GET /api/v1/documents

Retrieve uploaded documents.

---

## DELETE /api/v1/documents/{id}

Archive document.

---

# Capability APIs

## POST /api/v1/capabilities/build

Trigger Capability Builder Agent.

Input

Uploaded documents.

Output

Structured Company Capability Graph.

---

## GET /api/v1/capabilities

Retrieve organizational capability.

---

## GET /api/v1/capabilities/{id}

Retrieve specific capability.

---

# Mission APIs

## POST /api/v1/missions

Create new mission.

Example:

Tender Evaluation

Response

Mission ID

Workflow Status

---

## GET /api/v1/missions

Retrieve all missions.

---

## GET /api/v1/missions/{id}

Retrieve mission details.

---

## DELETE /api/v1/missions/{id}

Archive mission.

---

# Tender APIs

## POST /api/v1/tenders/upload

Upload Tender PDF.

Response

Tender ID

Mission ID

---

## GET /api/v1/tenders/{id}

Retrieve tender information.

---

# AI Processing APIs

## POST /api/v1/analysis/run

Trigger Tender Analysis Agent.

Returns

Requirement Model.

---

## POST /api/v1/evaluation/run

Trigger Decision Intelligence Agent.

Returns

Compliance Matrix

Recommendation

Gap Analysis

---

## GET /api/v1/evaluation/{mission_id}

Retrieve evaluation.

---

# Recommendation APIs

## GET /api/v1/recommendations/{mission_id}

Retrieve executive recommendation.

Response includes:

- Compliance Matrix
- Recommendation
- Risk Summary
- Executive Notes

---

# Human Approval APIs

## POST /api/v1/approval

Submit executive decision.

Request

```json
{
  "mission_id":"uuid",
  "decision":"GO"
}
```

Possible Decisions

- GO

- CONDITIONAL_GO

- REVIEW

- NO_GO

---

## GET /api/v1/approval/{mission_id}

Retrieve approval history.

---

# Audit APIs

## GET /api/v1/audit

Retrieve audit logs.

---

## GET /api/v1/audit/{mission_id}

Retrieve workflow audit history.

---

# Notification APIs

## GET /api/v1/notifications

Retrieve notifications.

---

## PUT /api/v1/notifications/{id}

Mark notification as read.

---

# Dashboard APIs

## GET /api/v1/dashboard

Returns dashboard metrics.

Example

```json
{
  "active_missions": 12,
  "completed": 38,
  "pending": 5,
  "compliance_saves": 14
}
```

---

# API Status Codes

| Code | Meaning |
|-------|----------|
| 200 | Success |
| 201 | Created |
| 400 | Invalid Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 409 | Conflict |
| 422 | Validation Error |
| 500 | Internal Server Error |

---

# Rate Limiting

To prevent abuse:

Authenticated users:

100 requests/minute

Anonymous users:

Authentication endpoints only

Future versions may support enterprise-specific quotas.

---

# Security

The API implements:

- HTTPS
- JWT Authentication
- Role-Based Access Control
- Input Validation
- File Type Validation
- Request Logging
- Audit Logging
- Secure Error Handling

Sensitive information is never exposed through API responses.

---

# Versioning Strategy

The API uses URL versioning.

Example

```
/api/v1/
/api/v2/
```

Future versions maintain backward compatibility whenever possible.

---

# Future APIs

The architecture supports additional endpoints for future modules.

Examples:

Vendor Qualification

```
/api/v1/vendors
```

Contract Intelligence

```
/api/v1/contracts
```

Marketplace

```
/api/v1/marketplace
```

ERP Integration

```
/api/v1/integrations
```

Analytics

```
/api/v1/analytics
```

---

# API Design Summary

The BidOps AI API layer provides a secure, modular, and scalable interface between enterprise users, backend services, and AI components. By standardizing request formats, authentication, workflow management, and AI execution, the API establishes a reliable communication foundation that supports both the current MVP and future enterprise-scale expansion.