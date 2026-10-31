# Software Requirements Specification (SRS)
## Sugar Bloom Bakery — Inventory Management System

**Version:** 1.0  
**Status:** Coursework draft

## 1. Purpose
This document specifies the functional and non-functional requirements for the Sugar Bloom Bakery Inventory Management System. It is intended to guide implementation and testing.

## 2. System Scope
The system manages a small bakery's inventory of ingredients and supplies. Users can maintain item records, record incoming and outgoing stock, and identify low-stock items. Authentication, role-based authorization, user dashboard, and deployment are planned for Beta.

## 3. Users and Permissions
| Role | Planned permissions | Release |
|---|---|---|
| Admin/Owner | View and manage inventory; view activity; manage users and roles | Core inventory in MVP; user/role management in Beta |
| Manager | View/create/update inventory; record stock-in and stock-out; view low-stock items | Core inventory in MVP; role enforcement in Beta |
| Staff | View inventory; record permitted stock-out/usage | Basic inventory workflow in MVP; role enforcement in Beta |

The MVP may use a local development configuration. The Beta backend must enforce roles and permissions for protected operations.

## 4. Functional Requirements
### 4.1 Inventory Items
- **SRS-FR-01 (MVP):** The system shall list inventory items.
- **SRS-FR-02 (MVP):** The system shall create an item with a unique identifier, name, unit, quantity, and low-stock threshold.
- **SRS-FR-03 (MVP):** The system shall display the details of a selected item.
- **SRS-FR-04 (MVP):** The system shall update an item's editable fields.
- **SRS-FR-05 (MVP):** The system shall delete an item after the user confirms the action.
- **SRS-FR-06 (MVP):** The system shall reject missing required fields and invalid or negative quantities.

### 4.2 Stock Movements
- **SRS-FR-07 (MVP):** The system shall record stock-in movements.
- **SRS-FR-08 (MVP):** The system shall record stock-out movements.
- **SRS-FR-09 (MVP):** A stock-out operation shall not reduce an item's quantity below zero.
- **SRS-FR-10 (MVP):** The system shall display a low-stock status when quantity is less than or equal to the configured threshold.

### 4.3 Authentication and Authorization
- **SRS-FR-11 (Beta):** The system shall allow a registered user to log in and log out.
- **SRS-FR-12 (Beta):** The backend shall associate an authenticated request with a user and role.
- **SRS-FR-13 (Beta):** The backend shall deny a request when the user's role or security scope does not permit the operation.
- **SRS-FR-14 (Beta):** The system shall provide a profile/dashboard for the signed-in user.
- **SRS-FR-15 (Beta):** The system shall record inventory activity with a timestamp and user where feasible.

## 5. External Interface Requirements
### 5.1 User Interface
- React + TypeScript single-page web interface.
- Inventory list with item name, unit, current quantity, threshold, and low-stock status.
- Forms for creating/editing items and recording stock movements.
- Loading, success, empty, and error states.

### 5.2 Software Interfaces
- Frontend communicates with FastAPI backend using REST endpoints.
- Request and response bodies use JSON.
- The backend returns standard HTTP status codes for success, validation failures, missing resources, authentication failures, and authorization failures.

## 6. Proposed API Requirements
Exact route names may be adjusted during implementation while preserving these capabilities.

| Method | Endpoint | Purpose | Release |
|---|---|---|---|
| GET | `/api/items` | List inventory items | MVP |
| POST | `/api/items` | Create an item | MVP |
| GET | `/api/items/{item_id}` | Retrieve one item | MVP |
| PUT | `/api/items/{item_id}` | Update an item | MVP |
| DELETE | `/api/items/{item_id}` | Delete an item | MVP |
| POST | `/api/items/{item_id}/stock-in` | Add stock | MVP |
| POST | `/api/items/{item_id}/stock-out` | Record stock usage | MVP |
| POST | `/api/auth/login` | Authenticate a user | Beta |
| GET | `/api/users/me` | Get current user's profile | Beta |
| GET | `/api/activity` | View permitted inventory activity | Beta |

## 7. Data Requirements
### InventoryItem
- `id`: unique identifier
- `name`: required item name
- `unit`: unit such as kg, g, litre, pack, or piece
- `quantity`: current quantity; must be non-negative
- `low_stock_threshold`: non-negative threshold
- `created_at`, `updated_at`: timestamps where supported

### User (Beta)
- `id`: unique identifier
- `name`: display name
- `email`: unique login identifier
- `password_hash`: securely hashed password, never plain text
- `role`: Admin, Manager, or Staff

### StockMovement
- `id`: unique identifier
- `item_id`: related inventory item
- `movement_type`: stock-in or stock-out
- `quantity`: positive movement quantity
- `created_at`: timestamp
- `created_by`: user identifier in Beta

## 8. Non-Functional Requirements
- **SRS-NFR-01 (MVP):** The system shall validate input on the backend.
- **SRS-NFR-02 (MVP):** The interface shall provide understandable feedback for errors and successful operations.
- **SRS-NFR-03 (MVP):** The application shall separate frontend code from backend API code.
- **SRS-NFR-04 (Beta):** Passwords shall be securely hashed.
- **SRS-NFR-05 (Beta):** Authorization shall be checked by the backend for every protected operation.
- **SRS-NFR-06 (Beta):** Secrets shall be provided through environment configuration and excluded from version control.
- **SRS-NFR-07 (Beta):** The application shall be configured for deployment and tested using a production-like configuration.

## 9. Acceptance Criteria
1. A valid inventory item can be created and appears in the inventory list.
2. An item can be updated and deleted.
3. Stock-in increases quantity by the submitted amount.
4. Stock-out decreases quantity only when sufficient stock exists.
5. An item is marked low-stock when its quantity is at or below its threshold.
6. Invalid values are rejected with a useful error response.
7. In Beta, unauthenticated users cannot access protected operations.
8. In Beta, users cannot perform actions outside their assigned role and permissions.


## Use Cases

### UC-1: Product Management (Admin / Staff)
- **Actor:** Admin, Staff
- **Description:** Allows authorized users to add new bakery products, view the product list, inspect individual product details, update pricing/inventory, or remove discontinued items.
- **Preconditions:** User must be authenticated and possess Admin or Staff privileges.
- **Postconditions:** The product database is updated and reflected in the frontend application instantly.

### UC-2: Product Browsing & Ordering (Customer)
- **Actor:** Customer
- **Description:** Allows visitors and registered customers to view available bakery products and submit orders.
- **Preconditions:** None for browsing; user account required for order placement.
- **Postconditions:** An order record is generated in the system.