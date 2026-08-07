# EMU Student Support and Institutional Q&A System

This project was developed for the Eastern Mediterranean University summer internship project.

The system stores student questions and official staff answers in a central database. It provides role-based web dashboards and a FastAPI backend for managing student questions, institutional Q&A records, categories, answers, and attachments.

The system is also prepared for future AI-supported answer suggestions.

## Project Goals

- Explore and clean the provided Q&A dataset
- Normalize category and language information
- Design a relational database
- Create an institutional question-answer memory
- Allow students to submit and track questions
- Allow students to upload attachments with their questions
- Allow questions to be assigned to staff members
- Allow staff members to answer questions
- Allow staff and administrators to create categories
- Allow staff and administrators to update question categories
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
- Secure question attachment upload and download
- Session-based authentication
- Role-based authorization
- Student dashboard
- Expert dashboard
- Administrator dashboard
- Independent category creation for staff and administrators
- Question category assignment by staff and administrators
- Administrator user creation and role management
- Frontend and backend integration
- Automated API and interface tests
- Technical documentation

The official train/test split and AI model testing will be added in a later phase.

## Dataset Summary

- Total records: 769
- Turkish records: 654
- English records: 115
- Original normalized categories: 31
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

The application can contain more than 31 categories because authorized staff and administrators can create new categories.

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
- python-multipart

## Project Structure

```text
dau-chatbot/
|-- app/
|   `-- main.py
|-- data/
|   |-- Dau_chatbot_Raw_dataset.csv
|   `-- Dau_chatbot_Cleaned_dataset.csv
|-- database/
|   `-- dau_chatbot.db
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
|-- uploads/
|-- .env.example
|-- .gitignore
|-- README.md
`-- requirements.txt
```

The dataset files, generated database, uploaded files, virtual environment, and real `.env` file are excluded from Git.

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

The `questions`, `answers`, and `attachments` tables support the live student and staff workflow.

The `ai_suggestions` table is prepared for future AI-supported answer generation.

## Installation

### 1. Clone the repository

```bat
git clone https://github.com/aliefeekmen/dau-student-support-system.git
cd dau-student-support-system
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
Dau_chatbot_Raw_dataset.csv
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
- Upload an allowed attachment of up to 5 MB
- View and download their own question attachments
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
- View and download student attachments
- Search similar institutional Q&A records
- Assign a question to themselves
- Answer assigned questions
- View answered questions
- Create bilingual categories independently
- Update the category of a selected question

### Administrator

An administrator can:

- Log in to the administrator dashboard
- View system statistics
- View user information
- Create new student, staff, and administrator accounts
- Change the role of an existing user
- View question status counts
- View the number of answers
- View category and knowledge-base statistics
- Create bilingual categories independently
- Update the category of a selected question

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

### Knowledge Base and Categories

- `GET /health` - Check the API and database connection
- `GET /stats` - View database statistics
- `GET /categories` - List categories
- `POST /categories` - Create a bilingual category as staff or admin
- `GET /knowledge` - Search and filter institutional Q&A records
- `GET /knowledge/{entry_id}` - View one institutional Q&A record

### Question Management

- `POST /questions` - Submit a student question
- `GET /questions` - List student questions for staff and administrators
- `GET /questions/{question_id}` - View question details
- `PATCH /questions/{question_id}/assign` - Assign a question
- `PATCH /questions/{question_id}/category` - Update a question category
- `POST /questions/{question_id}/answers` - Answer a question
- `GET /students/{student_id}/questions` - List one student's questions

### Attachments

- `POST /questions/{question_id}/attachments` - Upload a question attachment
- `GET /questions/{question_id}/attachments` - List question attachments
- `GET /attachments/{attachment_id}/download` - Download an authorized attachment

### Administration

- `GET /admin/overview` - View administrator statistics
- `GET /admin/users` - List system users
- `POST /admin/users` - Create a new user
- `PATCH /admin/users/{user_id}/role` - Change a user's role

Protected endpoints require a valid session and the correct user role.

## Attachment Security

- Only the owner student can upload an attachment to their question.
- Students can only access attachments belonging to their own questions.
- Staff and administrators can access attachments for support operations.
- File extensions and MIME types are validated.
- The maximum file size is 5 MB.
- Stored filenames are generated securely instead of trusting the original filename.
- Uploaded files are excluded from Git.

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
24 passed
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
- Administrator user creation
- User role updates
- Unauthorized user management restrictions
- Secure attachment upload and access restrictions
- Category creation by staff and administrators
- Question category assignment
- Unauthorized category operations
- Static file delivery

## Security Notes

- Passwords are stored as hashes, not plain text.
- Session data is protected with `SESSION_SECRET`.
- Role checks protect student, staff, and administrator operations.
- The real `.env` file is excluded from Git.
- Uploaded files are excluded from Git.
- Demo accounts are for local development only.
- HTTPS and secure cookies must be enabled before production deployment.

## Future Work

- Receive the official train/test split
- Integrate the selected AI model
- Generate AI-supported answer suggestions
- Compare model performance
- Complete Turkish and English interface switching
- Add automatic question category classification
- Add password reset and active/inactive account controls
- Add audit logs
- Improve production security settings
- Move from SQLite to PostgreSQL if required
- Deploy the system to a production server

## Repository

GitHub repository:

https://github.com/aliefeekmen/dau-student-support-system