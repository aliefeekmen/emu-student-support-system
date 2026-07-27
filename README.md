# EMU Student Support and Institutional Q&A System

This project is developed for the Eastern Mediterranean University summer internship project.

The system stores student questions and official staff answers in a central database. It provides role-based web dashboards and a FastAPI backend for managing student questions.

The system is also prepared for future AI-supported answer suggestions.

## Project Goals

- Explore and clean the provided Q&A dataset
- Normalize category and language information
- Design a relational database
- Create an institutional question-answer memory
- Allow students to submit and track questions
- Allow questions to be assigned to staff members
- Allow staff members to answer questions
- Provide separate student, staff, and administrator dashboards
- Protect system operations with authentication and authorization
- Prepare the system for future AI integration

## Current Phase

The following work has been completed:

- Dataset exploration
- Text cleaning and normalization
- Missing category correction
- Category name standardization
- Relational database design
- CSV data import
- Database validation
- FastAPI backend setup
- Knowledge-base searching and filtering
- Student question and staff answer workflow
- Session-based authentication
- Role-based authorization
- Student dashboard
- Expert dashboard
- Administrator dashboard
- Frontend and backend integration
- Automated API and interface tests
- Technical documentation

The official train/test split and AI model testing will be added in a later phase.

## Dataset Summary

- Total records: 769
- Turkish records: 654
- English records: 115
- Normalized categories: 31
- Missing values after cleaning: 0
- Fully duplicated rows: 0
- Duplicated questions after text normalization: 121

Dataset columns:

- `ID`
- `Soru`
- `Cevap`
- `Kategori (TR)`
- `Kategori (EN)`
- `Dil`

Duplicate questions are preserved because different records may contain useful category, language, or answer information. They can be reviewed again when the official train/test split is provided.

## Technologies

- Python
- Pandas
- FastAPI
- SQLite
- Uvicorn
- bcrypt
- Jinja2
- HTML
- CSS
- JavaScript
- Pytest
- HTTPX
- python-dotenv
- itsdangerous

## Project Structure

```text
EMU-chatbot/
|-- app/
|   `-- main.py
|-- data/
|   |-- EMU_chatbot_Raw_dataset.csv
|   `-- EMU_chatbot_Cleaned_dataset.csv
|-- database/
|   `-- EMU_chatbot.db
|-- docs/
|   |-- data_analysis_report.md
|   `-- database_schema.md
|-- scripts/
|   |-- clean_data.py
|   |-- create_database.py
|   |-- explore_data.py
|   |-- import_data.py
|   |-- inspect_database.py
|   |-- inspect_issues.py
|   |-- normalize_database_categories.py
|   |-- seed_demo_users.py
|   |-- validate_data.py
|   `-- validate_database.py
|-- static/
|   |-- css/
|   |   `-- dashboard.css
|   `-- js/
|       |-- admin_dashboard.js
|       |-- dashboard.js
|       `-- student_dashboard.js
|-- templates/
|   |-- admin_dashboard.html
|   |-- dashboard.html
|   |-- login.html
|   `-- student_dashboard.html
|-- tests/
|   `-- test_api.py
|-- .env.example
|-- .gitignore
|-- README.md
`-- requirements.txt
```

The dataset files, generated database, virtual environment, and real `.env` file are excluded from Git.

## Database Tables

The relational database contains the following tables:

- `languages`
- `categories`
- `knowledge_entries`
- `roles`
- `users`
- `questions`
- `answers`
- `attachments`
- `ai_suggestions`

The `knowledge_entries` table stores the cleaned institutional Q&A dataset.

The `questions` and `answers` tables support the live student and staff workflow.

The `ai_suggestions` table is prepared for future AI-supported answer generation.

## Installation

### 1. Clone the repository

```bat
git clone https://github.com/aliefeekmen/EMU-student-support-system.git
cd EMU-student-support-system
```

### 2. Create a virtual environment

```bat
python -m venv venv
```

### 3. Activate the virtual environment on Windows

```bat
venv\Scripts\activate
```

### 4. Install the required packages

```bat
python -m pip install -r requirements.txt
```

### 5. Create the environment file

Copy the example file:

```bat
copy .env.example .env
```

Open the new file:

```bat
notepad .env
```

Replace the example value with a long and private random value:

```env
SESSION_SECRET=replace-with-your-own-long-random-secret
```

The real `.env` file must not be uploaded to GitHub.

## Dataset and Database Setup

Place the raw dataset inside the `data` directory with the following name:

```text
EMU_chatbot_Raw_dataset.csv
```

Explore the raw dataset:

```bat
python scripts\explore_data.py
```

Clean and normalize the dataset:

```bat
python scripts\clean_data.py
```

Validate the cleaned dataset:

```bat
python scripts\validate_data.py
```

Create the database:

```bat
python scripts\create_database.py
```

Import the cleaned dataset:

```bat
python scripts\import_data.py
```

Validate the database:

```bat
python scripts\validate_database.py
```

Create the development-only demo users:

```bat
python scripts\seed_demo_users.py
```

## Running the System

Start the FastAPI development server:

```bat
python -m uvicorn app.main:app --reload
```

Open the login page:

```text
http://127.0.0.1:8000/login
```

Swagger API documentation:

```text
http://127.0.0.1:8000/docs
```

The server must remain running while the website or API is being used.

## User Roles

### Student

A student can:

- Log in to the student dashboard
- Submit a new question
- Select a question category and language
- View their own questions
- Search their own questions
- View question status
- View official staff answers

### Staff

A staff member can:

- Log in to the expert dashboard
- View incoming student questions
- Search and filter questions
- View question and student information
- Search similar institutional Q&A records
- Assign a question to themselves
- Answer assigned questions
- View answered questions

### Administrator

An administrator can:

- Log in to the administrator dashboard
- View system statistics
- View user information
- View question status counts
- View the number of answers
- View category and knowledge-base statistics

Users cannot access dashboards or operations that do not belong to their roles.

## Main Pages

- `GET /login` - Open the login page
- `GET /student-dashboard` - Open the student dashboard
- `GET /dashboard` - Open the expert dashboard
- `GET /admin-dashboard` - Open the administrator dashboard
- `GET /docs` - Open the Swagger API documentation

## Main API Endpoints

### Authentication

- `POST /login` - Authenticate a user
- `POST /logout` - End the current session
- `GET /me` - View the authenticated user

### Knowledge Base

- `GET /health` - Check the API and database connection
- `GET /stats` - View database statistics
- `GET /categories` - List categories
- `GET /knowledge` - Search and filter institutional Q&A records
- `GET /knowledge/{entry_id}` - View one institutional Q&A record

### Question Management

- `POST /questions` - Submit a student question
- `GET /questions` - List student questions for staff
- `GET /questions/{question_id}` - View question details
- `PATCH /questions/{question_id}/assign` - Assign a question
- `POST /questions/{question_id}/answers` - Answer a question
- `GET /students/{student_id}/questions` - List one student's questions

### Administration

- `GET /admin/overview` - View administrator statistics
- `GET /admin/users` - List system users

Protected endpoints require a valid session and the correct user role.

## Demo Accounts

The project contains the following development-only accounts:

| Role | Email | Password |
|---|---|---|
| Student | `student@demo.local` | `Student123!` |
| Staff | `staff@demo.local` | `Staff123!` |
| Admin | `admin@demo.local` | `Admin123!` |

These accounts are provided only for local development and demonstration. They must not be used in a production environment.

## Automated Tests

Run the complete test suite:

```bat
python -m pytest -v
```

Current result:

```text
16 passed
```

The tests cover:

- API health and database connection
- Database statistics
- Categories
- Knowledge-base searching
- Existing and missing knowledge records
- Authentication
- Role-based authorization
- Student dashboard
- Expert dashboard
- Administrator dashboard
- Administrator API endpoints
- Static file delivery
- Unauthorized access restrictions

## Security Notes

- Passwords are stored as hashes, not plain text.
- Session data is protected with `SESSION_SECRET`.
- Role checks protect student, staff, and administrator operations.
- The real `.env` file is excluded from Git.
- Demo accounts are for local development only.
- HTTPS and secure cookies must be enabled before production deployment.

## Future Work

- Receive the official train/test split
- Integrate the selected AI model
- Generate AI-supported answer suggestions
- Compare model performance
- Add file attachment upload
- Complete Turkish and English interface switching
- Add automatic question category classification
- Add password reset and account management
- Add audit logs
- Improve production security settings
- Move from SQLite to PostgreSQL if required
- Deploy the system to a production server

## Repository

GitHub repository:

https://github.com/aliefeekmen/EMU-student-support-system