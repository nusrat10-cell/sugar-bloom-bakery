# Technical Design Document (TDD)
## Sugar Bloom Bakery — Inventory Management System

**Version:** 1.0  
**Status:** Proposed design; implementation details may be refined

## 1. Purpose
This document describes the proposed architecture, components, data model, API design, and security approach for the Sugar Bloom Bakery Inventory Management System.

## 2. Technology Stack
- **Frontend:** React + TypeScript
- **Backend:** Python + FastAPI
- **Communication:** REST API with JSON
- **Persistence:** Use the database/configuration supported by the starter template for the MVP; keep data access isolated so the storage layer can be changed if necessary.
- **Version control:** Git and GitHub
- **Beta deployment:** deployment configuration suitable for the chosen hosting environment

## 3. Architecture
The application follows a client-server structure:

1. The React frontend renders inventory pages and forms.
2. The frontend sends HTTP requests to the FastAPI REST API.
3. FastAPI validates requests and runs business rules.
4. The backend data-access layer reads or updates inventory records.
5. The API returns JSON responses, and the frontend updates the visible state.

The backend is the source of truth for validation and authorization. Hiding a button in the frontend is not sufficient security.

## 4. Proposed Component Structure
### Frontend
- `pages/` — inventory list and item form/detail views
- `components/` — reusable forms, navigation, status labels, and feedback messages
- `services/` — API request functions
- `types/` — TypeScript interfaces for inventory items and API responses

Names should be adapted to the starter template's existing structure rather than duplicating folders unnecessarily.

### Backend
- `main.py` — FastAPI application and router registration
- `routers/` — inventory and, in Beta, authentication/user routes
- `schemas/` — Pydantic request and response schemas
- `models/` — persistence models if used by the selected database layer
- `services/` — inventory business logic
- `dependencies/` or equivalent — authentication and permission dependencies in Beta

These are logical responsibilities; use the template's actual conventions when implementing.

## 5. Data Model
### InventoryItem
| Field | Type (proposed) | Rules |
|---|---|---|
| id | Integer or UUID | Primary identifier |
| name | String | Required, trimmed |
| unit | String | Required |
| quantity | Decimal or numeric | Must be >= 0 |
| low_stock_threshold | Decimal or numeric | Must be >= 0 |
| created_at | Date/time | Set by backend if supported |
| updated_at | Date/time | Updated by backend if supported |

### StockMovement
| Field | Type (proposed) | Rules |
|---|---|---|
| id | Integer or UUID | Primary identifier |
| item_id | Item identifier | References InventoryItem |
| movement_type | Enum/string | `stock_in` or `stock_out` |
| quantity | Decimal or numeric | Must be > 0 |
| created_at | Date/time | Set by backend |
| created_by | User identifier | Beta; associated with authenticated user |

### User (Beta)
| Field | Type (proposed) | Rules |
|---|---|---|
| id | Integer or UUID | Primary identifier |
| name | String | Required |
| email | String | Unique login identifier |
| password_hash | String | Never store plain-text passwords |
| role | Enum/string | Admin, Manager, or Staff |

## 6. REST API Design
The following endpoints are proposed and may be adjusted to match the existing template.

| Method | Endpoint | Purpose | Release |
|---|---|---|---|
| GET | `/api/items` | Return item list | MVP |
| POST | `/api/items` | Create item | MVP |
| GET | `/api/items/{item_id}` | Return item details | MVP |
| PUT | `/api/items/{item_id}` | Update item | MVP |
| DELETE | `/api/items/{item_id}` | Delete item | MVP |
| POST | `/api/items/{item_id}/stock-in` | Add stock | MVP |
| POST | `/api/items/{item_id}/stock-out` | Record usage | MVP |
| POST | `/api/auth/login` | Authenticate user | Beta |
| GET | `/api/users/me` | Return signed-in user's profile | Beta |
| GET | `/api/activity` | Return permitted activity history | Beta |

### API behavior
- Use `200`/`201` for successful retrieval/creation as appropriate.
- Use `400` or `422` for invalid input, `404` for a missing item, `401` for missing/invalid authentication, and `403` for insufficient permissions.
- Never allow stock-out to make quantity negative.
- Validate data in FastAPI/Pydantic schemas and business logic.

## 7. Business Logic
### Stock-in
1. Confirm the item exists.
2. Validate that movement quantity is greater than zero.
3. Increase the item's quantity.
4. Save the item and stock movement.
5. Return the updated item.

### Stock-out
1. Confirm the item exists.
2. Validate that movement quantity is greater than zero.
3. Confirm sufficient stock is available.
4. Decrease the item's quantity.
5. Save the item and stock movement.
6. Return the updated item.

### Low-stock status
An item is low-stock when:
`quantity <= low_stock_threshold`

## 8. Authentication and Authorization (Beta)
- Authenticate users through a login endpoint.
- Use a secure token/session approach compatible with the starter template.
- Hash passwords with a suitable password-hashing library.
- Define role permissions on the backend:
  - **Admin:** all inventory permissions plus user/role administration.
  - **Manager:** create/update items and record stock movements; no user/role administration.
  - **Staff:** view items and perform only explicitly permitted stock-usage actions.
- Add security scopes/permission checks to protected endpoints.
- Return `401 Unauthorized` for unauthenticated requests and `403 Forbidden` for authenticated users without permission.
- Do not commit secrets, token keys, or passwords to GitHub.

## 9. Validation and Error Handling
- Trim item names and reject empty names.
- Reject missing required fields and negative quantities/thresholds.
- Require stock movement quantity to be positive.
- Prevent stock-out when insufficient quantity is available.
- Return clear error messages while keeping internal stack traces and secrets out of API responses.

## 10. Testing Plan
### MVP
- Test creating, listing, viewing, updating, and deleting items.
- Test stock-in quantity calculation.
- Test stock-out quantity calculation and insufficient-stock rejection.
- Test low-stock boundary (`quantity == threshold`).
- Test missing item and invalid input responses.
- Verify frontend operations call the API and display updated data.

### Beta
- Test successful and unsuccessful login.
- Test that each role can access only permitted operations.
- Test that direct API calls cannot bypass role restrictions.
- Test that secrets are not exposed in responses or committed configuration.
- Test the deployed application end-to-end.

## 11. Release Plan
- **MVP:** inventory CRUD, stock movements, low-stock status, REST API, and local end-to-end operation.
- **Beta:** authentication, Admin/Manager/Staff RBAC, profile dashboard, security scopes/permissions, activity history, and deployment.

## 12. Risks and Mitigations
- **Scope creep:** limit MVP to inventory CRUD and stock movements.
- **Incorrect stock values:** validate all quantities on the backend and test movement logic.
- **Unauthorized access in Beta:** enforce permissions in FastAPI, not only in the UI.
- **Environment differences:** document local setup and use environment variables for configuration.


## Project Structure
sugar-bloom-bakery/
├── frontend/             # React + Vite + TypeScript application
│   ├── src/              # Components, pages, services, and routing
│   └── package.json      # Frontend dependencies
├── backend/              # FastAPI + Python application
│   ├── app/              # Routers, models, schemas, database config
│   └── requirements.txt  # Python dependencies
├── docs/                 # Project documentation (PRD, SRS, TDD)
└── vercel.json           # Vercel deployment configuration

## Deployment & Configuration
- **Frontend Hosting:** Deployed on Vercel utilizing static build configurations.
- **Backend Hosting:** Deployed as serverless functions or containerized web service via Vercel/FastAPI integrations.
- **Database:** Supabase PostgreSQL connected via environment variables (`DATABASE_URL`).
- **Environment Variables:** Managed securely via `.env` files locally and Vercel project settings in production.