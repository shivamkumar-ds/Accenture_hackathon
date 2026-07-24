# BidOps AI
# MVP Roadmap

Version: 1.0

---

# Overview

This document defines the Minimum Viable Product (MVP) roadmap for BidOps AI.

The MVP is being developed for the Global AI Hackathon using Qwen Cloud under Track 4 – Autopilot Agent.

Rather than attempting to build a complete enterprise platform, the MVP focuses on validating the core concept of autonomous enterprise decision intelligence through a real-world Tender Evaluation workflow.

The roadmap intentionally prioritizes depth over breadth by implementing a small number of production-quality features instead of a large number of incomplete ones.

---

# MVP Objective

Demonstrate an Enterprise Autopilot capable of:

- Understanding organizational capability
- Understanding tender requirements
- Comparing both autonomously
- Producing evidence-backed recommendations
- Keeping humans in control of final decisions

---

# MVP Scope

The MVP consists of five core modules.

```
Company Onboarding

↓

Capability Builder

↓

Tender Analysis

↓

Decision Intelligence

↓

Human Approval
```

Everything else is intentionally deferred.

---

# MVP Features

## 1. Authentication

Users can:

- Login
- Logout
- Access dashboard

---

## 2. Company Workspace

Users can:

- Create company
- Upload company documents
- View company profile

---

## 3. Capability Builder

Users upload:

- ISO Certificates
- Employee CVs
- Project Certificates

AI extracts:

- Certifications
- Employees
- Experience
- Projects

Output:

Company Capability Graph

---

## 4. Tender Upload

Users upload:

Tender PDF

The system creates a new Mission automatically.

---

## 5. Tender Analysis

AI extracts:

- Eligibility Criteria
- Technical Requirements
- Certifications
- Deadlines
- Evaluation Criteria

Output:

Requirement Model

---

## 6. Decision Intelligence

AI compares:

Requirement Model

↓

Capability Graph

↓

Compliance Matrix

↓

Recommendation

Outputs:

- Compliance Matrix
- Executive Summary
- Gap Analysis
- Recommendation

---

## 7. Human Approval

Executive reviews:

- Recommendation
- Evidence
- Risks

Possible outcomes:

- GO
- CONDITIONAL GO
- REVIEW
- NO GO

---

## 8. Dashboard

Displays:

- Active Missions
- Completed Missions
- Recommendations
- Compliance Saves
- Notifications

---

# MVP Architecture

```
Flutter

↓

FastAPI Backend

↓

Mission Orchestrator

↓

Capability Builder

↓

Tender Analysis

↓

Decision Intelligence

↓

SQLite / PostgreSQL

↓

Object Storage
```

---

# Technology Stack

## Frontend

Flutter

---

## Backend

FastAPI

Python

---

## AI

Qwen Cloud APIs

---

## Database

SQLite (Development)

PostgreSQL (Production)

---

## Storage

Local Storage

Cloud Storage (Future)

---

## Authentication

JWT

---

## Deployment

Docker (Future)

Local deployment for MVP

---

# Deliverables

The MVP must demonstrate:

✓ Company onboarding

✓ Capability Graph generation

✓ Tender upload

✓ AI analysis

✓ Compliance Matrix

✓ Recommendation

✓ Human approval

✓ Dashboard

---

# User Journey

```
Login

↓

Upload Company Documents

↓

Build Capability Graph

↓

Upload Tender

↓

AI Evaluation

↓

Recommendation

↓

Executive Approval

↓

Mission Completed
```

---

# Demo Flow

The hackathon demonstration follows this sequence.

### Step 1

Login to BidOps AI.

---

### Step 2

Upload organizational documents.

AI builds the Company Capability Graph.

---

### Step 3

Upload a Tender PDF.

---

### Step 4

Mission Orchestrator starts automatically.

---

### Step 5

Tender Analysis Agent extracts requirements.

---

### Step 6

Decision Intelligence evaluates organizational capability.

---

### Step 7

Dashboard displays:

- Compliance Matrix
- Risks
- Gap Analysis
- Executive Recommendation

---

### Step 8

Executive approves the recommendation.

Mission completes.

---

### Step 9 (Demo Highlight)

Upload a mock tender addendum.

The system automatically:

- Detects changes
- Updates requirements
- Re-runs evaluation
- Refreshes recommendation

without restarting the workflow.

This demonstrates autonomous event-driven behavior.

---

# Success Criteria

The MVP is considered successful if it demonstrates:

- Autonomous workflow orchestration
- Structured document understanding
- Company Capability Graph generation
- Evidence-backed recommendations
- Human-in-the-loop governance
- Event-driven revalidation

---

# Explicit Non-Goals

The MVP intentionally excludes:

- Live government portal scraping
- Autonomous tender submission
- ERP integration
- SAP integration
- Salesforce integration
- Vendor marketplace
- Pricing optimization
- Competitor intelligence
- Predictive win probability
- Multi-company collaboration

These capabilities belong to future platform releases.

---

# Risks During MVP

Potential implementation risks include:

- Complex PDF layouts
- OCR inconsistencies
- Limited hackathon time
- AI latency
- Large document processing
- Integration complexity

Mitigation strategy:

Prioritize reliability over feature count.

---

# Expected Outcome

At the conclusion of the hackathon, BidOps AI should function as a working Enterprise Autopilot prototype capable of assisting organizations in evaluating tender opportunities through autonomous document understanding, capability assessment, structured compliance analysis, and evidence-backed executive recommendations.

The MVP validates the architectural foundation upon which future enterprise modules—including Vendor Qualification, Compliance Monitoring, Contract Intelligence, and Enterprise Decision Intelligence—can be built.