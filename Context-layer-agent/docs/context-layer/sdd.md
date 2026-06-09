# SDD.md - System Design Document

## 1. Objective
Build a company context layer that bridges enterprise data and the AI layer without dumping the full knowledge base into the model context window. The system should dynamically assemble only the relevant business context, user context, access constraints, and data-source hints per query.

## 2. Core Design Principles
- **Dynamic context assembly, not full-context stuffing**
- **Structured rules + AI reasoning together**
- **Access-aware by design**
- **Provenance for every answer**
- **Adapter-based integration for external systems**
- **Incremental rollout: Customer → Case → Employee / Internal Service Customer**

## 3. System Components
### 3.1 Term Registry
Holds business term cards, such as:
- Customer
- Case
- Employee
- Shipment
- Policy

Each term card stores:
- scope
- formal definition
- source authority rules
- lifecycle / status rules
- non-examples
- cross-domain notes

### 3.2 User Context Registry
Holds user-specific context:
- department
- role
- access scope
- preferred response style
- preferred metric lens

### 3.3 Resolver Heuristics
A lightweight rule layer that decides which context pieces must be included for a given query. It reduces LLM randomness and keeps behavior auditable.

### 3.4 Context Package Builder
Produces a compact package:
- query context
- domain context
- user context
- access context
- warnings
- data source hints

### 3.5 Adapter Layer
Adapters provide normalized access to:
- CRM
- ERP
- Case system
- future HR / policy / documents

### 3.6 Prompt Builder
Builds a deterministic prompt from:
- user query
- context package
- merged adapter result
- warnings / limitations

### 3.7 Provenance Layer
Every result should preserve:
- source system
- adapter name
- signals used
- constraint warnings

## 4. Primary Data Flow
1. User submits query
2. Parser identifies terms and intent
3. Resolver selects applicable term cards, user context, and heuristics
4. Access filter removes restricted domains
5. Context package is generated
6. Data planner calls adapters
7. Results are normalized and merged
8. Prompt builder creates the model prompt
9. Model returns answer draft / final answer
10. Provenance is retained for inspection

## 5. Current PoC Scope
### Implemented
- Customer term support
- Case term support
- Sales manager demo user
- Resolver heuristics
- CRM / ERP / Case mock adapters
- End-to-end prompt builder
- Provenance output

### Not Yet Implemented
- Real CRM / ERP connectors
- vector document retrieval
- policy adapter
- Employee domain
- Internal Service Customer domain
- runtime action guardrails
- feedback loop for answer quality

## 6. Key Architectural Decisions
### Why not send all context to AI?
Because it is expensive, unstable, and scales poorly. The model should receive only the minimal relevant context package.

### Why not rely only on AI to choose context?
Because company semantics, permissions, and source authority must be stable and auditable.

### Why use adapters?
They isolate external systems from the AI orchestration layer and support progressive replacement of mock sources with real ones.

## 7. Target Future Architecture
- Registry backend: DB or managed metadata store
- Document retriever: vector + keyword hybrid search
- Resolver: rule engine + model-assisted disambiguation
- Adapters: real service connectors
- Prompt builder: per-intent templates
- Governance: review workflow + versioned term definitions

## 8. Success Criteria
- Same query gives stable context selection
- User role affects permitted context and answer style
- Multiple domains can be combined safely
- Every answer carries provenance
- Replacing a mock adapter with a real adapter requires minimal pipeline changes
