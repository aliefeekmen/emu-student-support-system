# Verification Report

Date: 2026-08-18

## Delivered Build

- Application version: 1.1.0
- SQLite schema version: 2
- Privacy-clean knowledge records: 744
- Turkish/English distribution: 603 / 141
- CSV-to-database content comparison: 744 / 744 exact matches

## Automated API Tests

Command:

```text
python -m pytest -v
```

Result:

```text
31 passed, 1 warning in 10.36s
```

The warning is a third-party FastAPI/Starlette test-client deprecation notice. No application test failed.

The AI endpoint test replaces the external model call with a controlled test
response. It verifies authentication, retrieval context, API response shape,
and storage in the `ai_suggestions` table without consuming Groq quota.

## Database Checks

`scripts/validate_database.py` reported:

```text
Schema version: 2
Integrity check: ok
Foreign key errors: 0
Knowledge entries: 744
Language distribution: {'en': 141, 'tr': 603}
Required tables present: True
Database validation passed.
```

The version-2 migration was also run twice on a database copy. The second run added no columns or duplicate assignment rows, confirming idempotence.

## Fresh-Build Check

A blank database was created with `create_database.py`, populated with `import_data.py`, and checked with `validate_database.py`.

Result:

```text
Languages: 2
Categories: 31
Knowledge entries: 744
Integrity check: ok
Foreign key errors: 0
```

## SQL Restore Check

`database/emu_chatbot.sql` was restored into a blank SQLite file.

```text
Schema version: 2
Knowledge entries: 744
Integrity check: ok
Foreign key errors: 0
```

## Static Checks

- Modified Python files compiled successfully.
- Staff, student, and administrator JavaScript files passed `node --check`.
- Dashboard templates rendered successfully during the automated page tests.
