# POS System

A Flask-based Point of Sale (POS) and Inventory Management system with role-based access.

## Features

- User authentication with roles: `admin`, `manager`, `cashier`
- Product and inventory management
- POS checkout workflow
- Sales history and analytics endpoints
- Cashier activity monitoring (login/logout/sales logs)
- SQLite database with auto-initialization and seed data

## Tech Stack

- Python 3.11+
- Flask
- Flask-SQLAlchemy
- SQLite

## Project Structure

```text
pos_system/
|-- app.py
|-- pyproject.toml
|-- README.md
|-- instance/
|   `-- pos_system.db
`-- Templates/
    |-- login.html
    |-- dashboard.html
    |-- manager.html
    |-- manageUsers.html
    |-- pos.html
    `-- static/
        |-- style.css
        `-- login_background.jpg
```

## Setup

1. Create and activate virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

2. Install dependencies:

```powershell
pip install flask flask-sqlalchemy
```

3. Run the application:

```powershell
python app.py
```

Application runs at:

- `http://127.0.0.1:5555`

## Default Login Credentials

- Admin: `admin` / `admin123`
- Manager: `manager` / `manager123`
- Cashier: `cashier` / `cashier123`

## Core Routes

- `/login` - Login page
- `/logout` - Logout current user
- `/dashboard` - Admin/manager dashboard
- `/manager` - Manager dashboard
- `/manage-users` - User management page
- `/pos` - POS screen (cashier/admin/manager)

## Main API Endpoints

### User Management

- `GET /api/users`
- `POST /api/users`
- `PUT /api/users/<user_id>`
- `PUT /api/users/<user_id>/change-password`
- `DELETE /api/users/<user_id>`

### Product Management

- `GET /api/products`
- `POST /api/products`
- `GET /api/products/<product_id>`
- `PUT /api/products/<product_id>`
- `DELETE /api/products/<product_id>`
- `GET /api/products/search/<query>`

### POS

- `GET /api/pos/products`
- `GET /api/pos/search/<query>`
- `POST /api/transactions/checkout`

### Sales and Reports

- `GET /api/sales/history`
- `GET /api/sales/stats`
- `GET /api/sales/monthly-summary`

### Monitoring

- `GET /api/monitor/summary`
- `GET /api/monitor/cashiers`
- `GET /api/monitor/cashier/<cashier_id>/sales`
- `GET /api/monitor/cashier/<cashier_id>/logs`

## Database Models

- `User`
  - Authentication and role control
  - Fields include username, password hash, role, full name, active state
- `Product`
  - Product catalog with barcode, price, quantity, category
- `Transaction`
  - Sale records with total amount, item count, and line items (JSON)
- `ActivityLog`
  - User action tracking (`LOGIN`, `LOGOUT`, `SALE`)

## Notes

- DB file path: `instance/pos_system.db`
- `init_db()` in `app.py` creates tables and seed users/products if missing.
- `.editorconfig` is optional for runtime; it only helps with consistent code formatting in editors.
