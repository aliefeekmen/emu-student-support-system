# DAU Student Support and Institutional Q&A System

This project is developed for the Eastern Mediterranean University summer internship project.

The system stores student questions and official staff answers in a central database. It also provides a basic backend API for question management and prepares the infrastructure for future AI-supported answer suggestions.

## Project Goals

- Explore and clean the provided Q&A dataset
- Normalize category and language information
- Design a relational database schema
- Create an institutional question-answer memory
- Allow students to submit questions
- Allow questions to be assigned to staff
- Allow staff members to answer questions
- Prepare the system for future AI integration

## Current Phase

The first project phase is completed.

Completed work:

- Dataset exploration
- Text cleaning and normalization
- Missing category correction
- Category name standardization
- Relational database design
- CSV data import
- Database validation
- FastAPI backend setup
- Knowledge base search and filtering
- Basic student question and staff answer flow

The train/test split and AI model testing will be added in a later phase.

## Dataset Summary

- Total records: 769
- Turkish records: 654
- English records: 115
- Languages: Turkish and English
- Normalized categories: 31
- Missing values after cleaning: 0
- Completely duplicated rows: 0

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
|-- .gitignore
|-- README.md
`-- requirements.txt