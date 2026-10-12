# Product Requirements Document (PRD)
## Sugar Bloom Bakery — Inventory Management System

**Version:** 1.0  
**Status:** Coursework draft  
**Release plan:** MVP (mid-term demo) and Beta (final demo)

## 1. Product Overview
Sugar Bloom Bakery Inventory Management System is a small web application that helps a bakery track products and ingredients, monitor stock, and record stock movements. It replaces informal paper or spreadsheet tracking with a single, organized inventory record.

## 2. Problem Statement
A small bakery may lose track of ingredient quantities, forget to record incoming supplies, or discover shortages too late. The system will make stock information easier to update and review.

## 3. Goals
- Maintain a clear list of inventory items and their quantities.
- Record stock received and stock used or removed.
- Identify items that have reached their low-stock threshold.
- Provide a simple interface that is practical for a small bakery.
- Add authentication and role-based access in the Beta release.

## 4. Target Users and Roles
- **Owner/Admin:** manages users and inventory; can view all inventory activity.
- **Manager:** creates and updates inventory items and records stock movements.
- **Staff:** views inventory and records permitted stock usage, but cannot manage users or change role permissions.

Role enforcement is planned for Beta. During the MVP, the app may run locally with a limited development setup.

## 5. Scope by Release

### 5.1 MVP — Mid-term Demo (local)
- View a list of inventory items.
- Create an inventory item.
- View an item's details.
- Update item name, unit, quantity, and low-stock threshold.
- Delete an item when appropriate.
- Record stock-in and stock-out movements.
- Display a low-stock indicator.
- Provide REST API endpoints through FastAPI and a React + TypeScript interface.
- Run locally; no production deployment required.

### 5.2 Beta — Final Demo
- User login and logout.
- Role-based access control (Admin, Manager, Staff).
- User profile/dashboard.
- Permission and security-scope checks on protected API endpoints.
- Inventory activity history with user and timestamp where feasible.
- Input validation and clear error handling.
- Deployment and environment-based configuration.

## 6. Functional Requirements
| ID | Requirement | Release |
|---|---|---|
| FR-01 | The system shall display inventory items. | MVP |
| FR-02 | An authorized user shall be able to create an inventory item with a name, unit, quantity, and low-stock threshold. | MVP |
| FR-03 | An authorized user shall be able to view and update an inventory item. | MVP |
| FR-04 | An authorized user shall be able to delete an inventory item. | MVP |
| FR-05 | The system shall record stock-in and stock-out quantities. | MVP |
| FR-06 | The system shall flag items whose quantity is at or below the low-stock threshold. | MVP |
| FR-07 | The system shall authenticate registered users. | Beta |
| FR-08 | The system shall restrict actions according to Admin, Manager, and Staff roles. | Beta |
| FR-09 | The system shall check permissions/scopes on protected API endpoints. | Beta |
| FR-10 | The system shall provide a user profile/dashboard. | Beta |
| FR-11 | The system shall preserve an activity history for inventory changes. | Beta |
| FR-12 | The system shall be configured for deployment. | Beta |

## 7. Non-Functional Requirements
| ID | Requirement | Release |
|---|---|---|
| NFR-01 | The interface should be simple and usable on common desktop and mobile screen sizes. | MVP |
| NFR-02 | API requests and responses should use JSON over HTTP. | MVP |
| NFR-03 | Inputs must be validated, including non-negative quantities and required item names. | MVP |
| NFR-04 | Errors should be presented clearly without exposing internal server details. | MVP |
| NFR-05 | Passwords must not be stored as plain text. | Beta |
| NFR-06 | Protected operations must be authorized on the backend, not only hidden in the UI. | Beta |
| NFR-07 | Secrets and environment-specific settings must not be committed to the repository. | Beta |
| NFR-08 | The code should be organized so the frontend and backend can be maintained separately. | MVP |

## 8. Assumptions and Constraints
- The project is intended for one small bakery and a coursework demonstration.
- The required stack is React with TypeScript for the frontend and FastAPI with Python for the backend.
- The frontend communicates with the backend through REST APIs.
- Advanced accounting, supplier payments, sales forecasting, barcode scanning, and multi-branch support are out of scope.
- The MVP is expected to run locally; deployment is planned for Beta.

## 9. Success Criteria
- A user can create, view, update, and delete inventory items through the UI and API.
- Stock-in and stock-out operations update quantities correctly.
- Low-stock items are clearly identifiable.
- In Beta, users can log in and backend permissions prevent unauthorized actions.
- The application can be demonstrated end-to-end using the planned technology stack.
