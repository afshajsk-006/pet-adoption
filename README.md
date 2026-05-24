# 🐾 PawsHome — Pet Adoption Management System

A complete, professional web application for managing pet adoptions, built with **Python (Flask)** and **MySQL**.

---

## Features

- **Admin Login** with secure password hashing (werkzeug)
- **Dashboard** with live stats, recent requests, species breakdown, and notices
- **Pets Management** — add, edit, delete, search, filter by status
- **Adopters Management** — full CRUD with adoption history
- **Adoption Requests** — approve/reject with automatic pet status update
- **Notices Board** — post and manage announcements
- **Settings** — change password, update organization name
- **Responsive UI** — Bootstrap 5, Bootstrap Icons, mobile sidebar

---

## Quick Start

### 1. Clone / Download

```bash
cd "DBMS 4"
```

### 2. Create virtual environment

```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

Copy `.env.example` to `.env` and fill in your MySQL credentials:

```
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=yourpassword
DB_NAME=pet_adoption
SECRET_KEY=change-this-to-a-random-string
```

### 5. Set up the database

Open MySQL and run:

```sql
source schema.sql
```

Or via command line:

```bash
mysql -u root -p < schema.sql
```

### 6. Run the app

```bash
python app.py
```

Visit **http://127.0.0.1:5000**

---

## Default Login

| Field    | Value                |
|----------|----------------------|
| Email    | admin@petadopt.com   |
| Password | admin123             |

---

## File Structure

```
DBMS 4/
├── app.py                  # Main Flask application
├── schema.sql              # Database schema + seed data
├── requirements.txt
├── .env.example
├── .gitignore
├── Procfile
├── README.md
├── static/
│   ├── css/custom.css
│   └── js/main.js
└── templates/
    ├── base.html
    ├── login.html
    ├── dashboard.html
    ├── pets.html
    ├── pet_detail.html
    ├── add_pet.html
    ├── adopters.html
    ├── adopter_detail.html
    ├── add_adopter.html
    ├── adoption_requests.html
    ├── notices.html
    └── settings.html
```

---

## Database Tables

| Table               | Description                          |
|---------------------|--------------------------------------|
| `admins`            | Admin accounts                       |
| `pets`              | Pet records                          |
| `adopters`          | Adopter profiles                     |
| `adoption_requests` | Requests linking pets and adopters   |
| `notices`           | Announcements posted by admins       |
| `settings`          | Key-value app configuration          |

---

## Security

- Passwords hashed with `werkzeug.security`
- All routes protected with `@login_required`
- Parameterized SQL queries (no SQL injection)
- Secrets stored in `.env` (never committed)
