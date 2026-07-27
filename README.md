# DAU Student Support and Institutional Q&A System

This project is developed for the Eastern Mediterranean University summer internship project.

The system stores student questions and official staff answers in a central database. It also provides a web interface and backend API for question management.

The system is prepared for future AI-supported answer suggestions.

## Project Goals

- Explore and clean the provided Q&A dataset
- Normalize category and language information
- Design a relational database
- Create an institutional question-answer memory
- Allow students to submit questions
- Allow questions to be assigned to staff
- Allow staff members to answer questions
- Develop student and expert dashboards
- Prepare the system for future AI integration

## Current Phase

Completed work:

- Dataset exploration
- Text cleaning and normalization
- Missing category correction
- Category name standardization
- Relational database design
- CSV data import
- Database validation
- FastAPI backend setup
- Knowledge-base searching and filtering
- Student question and staff answer flow
- Expert dashboard
- Student dashboard
- Frontend and backend integration
- Automated backend and frontend tests
- Technical documentation

The official train/test split and AI model testing will be added in a later phase.

## Dataset Summary

- Total records: 769
- Turkish records: 654
- English records: 115
- Normalized categories: 31
- Missing values after cleaning: 0
- Fully duplicated rows: 0

Dataset columns:

- ID
- Soru
- Cevap
- Kategori (TR)
- Kategori (EN)
- Dil

## Technologies

- Python
- Pandas
- FastAPI
- SQLite
- SQLAlchemy
- Uvicorn
- bcrypt
- HTML
- CSS
- JavaScript
- Jinja2
- Pytest
- HTTPX

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
|       |-- dashboard.js
|       `-- student_dashboard.js
|-- templates/
|   |-- dashboard.html
|   `-- student_dashboard.html
|-- tests/
|   `-- test_api.py
|-- .gitignore
|-- README.md
`-- requirements.txt
```

## Database Tables

- languages
- categories
- knowledge_entries
- roles
- users
- questions
- answers
- attachments
- ai_suggestions

## Installation

Create a virtual environment:

```bat
python -m venv venv
```

Activate it on Windows:

```bat
venv\Scripts\activate
```

Install the required packages:

```bat
python -m pip install -r requirements.txt
```

Place the raw dataset in the `data` directory with this name:

```text
Dau_chatbot_Raw_dataset.csv
```

Clean the dataset:

```bat
python scripts\clean_data.py
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

Swagger API documentation:

```text
http://127.0.0.1:8000/docs
```

Expert dashboard:

```text
http://127.0.0.1:8000/dashboard
```

Student dashboard:

```text
http://127.0.0.1:8000/student-dashboard
```

## Expert Dashboard

The expert dashboard supports:

- Viewing incoming questions
- Searching and filtering questions
- Viewing question details
- Viewing student information
- Searching similar institutional records
- Assigning open questions to staff
- Sending staff answers
- Viewing answered questions
- Switching to the student dashboard

## Student Dashboard

The student dashboard supports:

- Viewing personal questions
- Viewing question status
- Viewing staff answers
- Searching personal questions
- Viewing question statistics
- Selecting real database categories
- Submitting new questions
- Switching to the expert dashboard

## Main API Endpoints

- `GET /health` - Check API and database connection
- `GET /stats` - View database statistics
- `GET /categories` - List categories
- `GET /knowledge` - Search and filter Q&A records
- `GET /knowledge/{entry_id}` - Get one Q&A record
- `POST /questions` - Submit a student question
- `GET /questions` - List student questions
- `GET /questions/{question_id}` - View question details
- `PATCH /questions/{question_id}/assign` - Assign a question
- `POST /questions/{question_id}/answers` - Answer a question
- `GET /students/{student_id}/questions` - List one student's questions
- `GET /dashboard` - Open the expert dashboard
- `GET /student-dashboard` - Open the student dashboard

## Automated Tests

Run the tests:

```bat
python -m pytest -v
```

Current result:

```text
9 passed
```

The tests cover:

- API health
- Database statistics
- Categories
- Knowledge-base searching
- Existing and missing knowledge records
- Expert dashboard page
- Student dashboard page
- Static CSS delivery

## Demo Accounts

The project contains development-only demo accounts:

- Demo Student
- Demo Staff
- Demo Admin

These accounts and their passwords must not be used in a production environment.

## Future Work

- Receive the official train/test split
- Integrate the selected AI model
- Generate AI answer suggestions
- Compare model performance
- Add secure login and authorization
- Add the administrator dashboard
- Add file attachment upload
- Complete Turkish and English interface switching
- Add automatic category classification
- Move from SQLite to PostgreSQL if required

## Authentication and User Roles

The system includes session-based authentication with three user roles:

- Student: creates questions and views their own questions.
- Staff: views, assigns, and answers student questions.
- Admin: views the administration dashboard and system statistics.

## Local Environment Setup

Create a `.env` file in the project root and add:

```env
SESSION_SECRET=your-long-random-secret-key

Install the dependencies and start the application:

python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload

Open the application at:

http://127.0.0.1:8000/login

Demo Accounts
Role	Email	Password
Student	student@demo.local	Student123!
Staff	staff@demo.local	Staff123!
Admin	admin@demo.local	Admin123!

These accounts are provided only for local development and demonstration.

Testing

Run the automated tests with:

python -m pytest -v

The current test suite contains 16 tests for the API, authentication, role permissions, and dashboard pages.