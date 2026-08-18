# EMU Student Support and Institutional Q&A System

This FastAPI application provides role-based student support workflows for Eastern Mediterranean University. Students submit questions and attachments, staff members assign and answer questions, and administrators manage users, categories, subcategories, and audit records.

The included database uses schema version 2 and the approved privacy-clean institutional Q&A master dataset.

## Current Status

- 744 privacy-clean knowledge-base records
- 603 Turkish and 141 English records
- 31 dataset categories
- Student, staff, and administrator dashboards
- Session authentication and role-based authorization
- Question assignment history and answered timestamps
- Attachment metadata and secure download checks
- Administrator-only category and subcategory creation
- Audit logging for authentication and important write operations
- GPT-OSS answer suggestions grounded in similar knowledge records
- Staff review and use tracking for AI-generated suggestions

The AI workflow uses retrieval-augmented generation (RAG). It finds
similar approved records in the 744-record knowledge base and sends only
those records to the OpenAI GPT-OSS 20B model through Groq. Staff members
review every suggestion before using it as an answer.

## Main Technologies

- Python, FastAPI, Uvicorn, Pydantic
- SQLite and Pandas
- OpenAI GPT-OSS 20B through the Groq API
- Jinja2, HTML, CSS, JavaScript
- bcrypt and signed sessions
- Pytest and HTTPX

## Project Structure

```text
emu-chatbot/
|-- app/
|   |-- database.py
|   `-- main.py
|-- data/
|   `-- EMU_QA_Master_Privacy_Cleaned_744.csv
|-- database/
|   |-- emu_chatbot.db
|   `-- emu_chatbot.sql
|-- docs/
|   |-- data_analysis_report.md
|   |-- database_schema.md
|   `-- verification_report.md
|-- scripts/
|   |-- create_database.py
|   |-- import_data.py
|   |-- migrate_database.py
|   |-- seed_demo_users.py
|   `-- validate_database.py
|-- static/
|-- templates/
|-- tests/
|   `-- test_api.py
|-- uploads/
|-- .env.example
|-- .gitignore
|-- README.md
`-- requirements.txt
```

The delivery archive does not contain the real `.env`, Git metadata, caches, legacy datasets, or the legacy database backup.

## Quick Start on Windows

From the project directory:

```bat
python -m venv venv
venv\Scripts\activate
python -m pip install -r requirements.txt
copy .env.example .env
notepad .env
```

Replace the example values in `.env` with private values:

```env
SESSION_SECRET=replace-with-a-long-random-secret
GROQ_API_KEY=gsk_your_private_groq_key
GROQ_MODEL=openai/gpt-oss-20b
```

The delivered `database\emu_chatbot.db` is already imported and migrated. Validate it:

```bat
python scripts\validate_database.py
```

Start the application:

```bat
python -m uvicorn app.main:app --reload
```

Open:

- Login: `http://127.0.0.1:8000/login`
- API documentation: `http://127.0.0.1:8000/docs`

## Rebuilding a Fresh Database

The privacy-clean CSV is the only dataset used by the import script:

```bat
python scripts\create_database.py
python scripts\import_data.py
python scripts\seed_demo_users.py
python scripts\validate_database.py
```

`import_data.py` requires exactly 744 complete records and validates its required columns before importing.

## Migrating an Older Project Database

For an existing schema-v1 database, run:

```bat
python scripts\migrate_database.py
python scripts\validate_database.py
```

The migration creates a timestamped backup by default, is safe to rerun, sets `PRAGMA user_version = 2`, and checks database integrity and foreign keys. Use `--skip-backup` only when a separate verified backup already exists.

## Roles and Permissions

### Student

- Submit a question for their own account
- Select a category and optional subcategory
- Upload an allowed attachment up to 5 MB
- View their own questions, attachments, statuses, and answers

### Staff

- View and search incoming questions
- View student attachments and similar knowledge entries
- Assign a question to themselves
- Update a question to an existing category
- Answer an assigned question

### Administrator

- View system statistics and audit logs
- Create users and update roles
- Create bilingual categories with description and responsible unit
- Create bilingual subcategories
- Assign existing categories to questions

Category and subcategory creation is administrator-only. Every protected endpoint also verifies the active session and role on the server; hiding a dashboard button is not treated as authorization.

## Database Tables

Schema version 2 contains:

- `roles`, `users`
- `languages`, `categories`, `subcategories`
- `knowledge_entries`
- `questions`, `question_assignments`, `answers`, `attachments`
- `ai_suggestions`, `audit_logs`

See [docs/database_schema.md](docs/database_schema.md) for fields, relationships, indexes, triggers, and validation results.

## Main Endpoints

| Area | Endpoint | Permission |
|---|---|---|
| Authentication | `POST /login`, `POST /logout`, `GET /me` | Session based |
| Knowledge | `GET /knowledge`, `GET /knowledge/{id}` | Staff, admin |
| Categories | `GET /categories`, `GET /subcategories` | Authenticated users |
| Category admin | `POST /categories`, `POST /subcategories` | Admin |
| Questions | `POST /questions` | Student |
| Questions | `GET /questions`, `PATCH /questions/{id}/assign` | Staff, admin |
| Questions | `PATCH /questions/{id}/category` | Staff, admin |
| Answers | `POST /questions/{id}/answers` | Staff, admin |
| Attachments | Upload/list/download routes | Ownership and role checks |
| Administration | `/admin/overview`, `/admin/users`, `/admin/audit-logs` | Admin |

## Demo Accounts

These accounts are for local development only:

| Role | Email | Password |
|---|---|---|
| Student | `student@demo.local` | `Student123!` |
| Staff | `staff@demo.local` | `Staff123!` |
| Admin | `admin@demo.local` | `Admin123!` |

Never reuse these credentials in production.

## Tests

Run:

```bat
python -m pytest -v
```

Current result:

```text
31 passed, 1 third-party deprecation warning
```

Coverage includes authentication, role restrictions, the 744-record knowledge base, schema-v2 installation, category and subcategory workflows, assignment history, answered timestamps, attachments, audit-log access, administrator user management, pages, and static files.

## Security Notes

- Passwords are stored as bcrypt hashes.
- The session secret is read from `.env`; the real file must not be committed or shared.
- Students can only create and view resources belonging to their own account.
- Upload extensions, MIME types, size, storage names, and download paths are checked.
- SQLite foreign keys, integrity validation, and cross-category subcategory triggers are enabled.
- Production deployment should enable HTTPS, secure cookies, secret rotation, backups, and a production database service.

## Future Work

- Add a formal evaluation set for retrieval and answer quality
- Add automated category classification
- Complete Turkish/English interface switching
- Add password reset and account activation controls
- Move to PostgreSQL and production hosting if required

## Repository

[GitHub repository](https://github.com/aliefeekmen/emu-student-support-system)
