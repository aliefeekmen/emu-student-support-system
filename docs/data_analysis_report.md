# Privacy-Clean Dataset Analysis and Import Report

## 1. Scope

The active knowledge base was rebuilt from the approved privacy-clean master dataset. The earlier 769-record exploratory dataset is a legacy input and is not used or distributed in the final package.

The application dataset contains 744 institutional question-answer records prepared for relational storage, search, and later AI evaluation. Model training and the official train/test split are outside this phase.

## 2. Delivered Dataset

File:

`data/EMU_QA_Master_Privacy_Cleaned_744.csv`

Encoding: UTF-8 with BOM for reliable Windows/Excel compatibility.

| Column | Description |
|---|---|
| `id` | New stable database ID, 1–744 |
| `record_id` | Privacy-clean master record identifier |
| `source_record_id` | Source lineage identifier supplied by the master dataset |
| `question` | Institutional question text |
| `answer` | Official answer text |
| `category_tr` | Turkish category name |
| `category_en` | English category name |
| `language` | `tr` or `en` |
| `duplicate_count` | Size of the matching-question group in the approved master |

Only the fields needed for the institutional Q&A workflow are imported into SQLite. Lineage and duplicate-count fields remain in the CSV for review.

## 3. Validated Results

| Check | Result |
|---|---:|
| Total records | 744 |
| Turkish records | 603 |
| English records | 141 |
| Bilingual category pairs | 31 |
| Required-field missing values | 0 |
| Duplicate `id` values | 0 |
| Duplicate `record_id` values | 0 |
| Duplicate `source_record_id` values | 0 |
| Records in a repeated-question group | 117 |
| Repeated-question groups | 45 |

Repeated questions are retained because a repeated question may still have a distinct approved answer, language, category, or institutional context. The `duplicate_count` field makes those groups reviewable without silently deleting records.

## 4. Data Preparation

The import artifact was created from the privacy-clean master with the following controls:

1. The approved row order was retained.
2. Stable application IDs from 1 through 744 were assigned.
3. Questions, answers, bilingual categories, and language codes were preserved from the approved master.
4. Required fields were checked for missing values.
5. IDs and lineage identifiers were checked for uniqueness.
6. The final CSV was written in a Windows-friendly UTF-8 format.
7. The importer rejects any file that does not contain exactly 744 valid rows.

The migration deliberately does not copy knowledge records from the legacy 769-record backup.

## 5. Relational Normalization

Repeated values are separated into normalized tables:

- `languages` stores `tr` and `en` once.
- `categories` stores the 31 bilingual category pairs.
- `knowledge_entries` stores each approved question and answer with category and language foreign keys.

The live support workflow uses separate `users`, `questions`, `question_assignments`, `answers`, `attachments`, `subcategories`, `ai_suggestions`, and `audit_logs` tables. This keeps the curated institutional knowledge base separate from new student support requests.

## 6. Safe Import Procedure

For a new database:

```bat
python scripts\create_database.py
python scripts\import_data.py
python scripts\seed_demo_users.py
python scripts\validate_database.py
```

`import_data.py` performs these checks before writing:

- Required columns exist.
- The dataset contains exactly 744 rows.
- Required values are complete.
- Languages and categories resolve to foreign keys.

It then enables SQLite secure deletion, replaces only `knowledge_entries`, commits the validated rows, and runs `VACUUM` so deleted legacy content is not retained in unused database pages.

## 7. Database Validation

The delivered database passed:

- `PRAGMA integrity_check` → `ok`
- `PRAGMA foreign_key_check` → 0 violations
- Schema version → 2
- Knowledge entries → 744
- Language distribution → 603 Turkish, 141 English
- Required schema-v2 tables and columns → present
- Active assignment uniqueness check → passed
- Answered/status timestamp consistency check → passed

The same checks can be repeated with:

```bat
python scripts\validate_database.py
```

## 8. Privacy and Delivery Controls

The final release excludes:

- The legacy raw and intermediate datasets
- The legacy 769-record database backup
- The real `.env` file and session secret
- Git history and editor metadata
- Python caches and test caches
- User-uploaded files

Only the privacy-clean CSV, migrated 744-record database, generated SQL schema/data dump, application code, tests, and documentation are included.

## 9. System Verification

The automated suite contains 30 tests covering the database counts and schema version, authentication, role permissions, category/subcategory creation, student question submission, assignment history, answered timestamps, attachment metadata, audit-log access, knowledge search, administrator user management, dashboards, and static files.

Result:

```text
30 passed, 1 third-party deprecation warning
```

The warning comes from the current FastAPI/Starlette test-client compatibility layer and does not indicate an application failure.

## 10. Conclusion

The active application now uses one privacy-clean, validated source of truth containing 744 records. The normalized schema and migration tooling support the required student, staff, administrator, attachment, assignment, AI-metadata, and audit workflows while keeping the legacy dataset out of the final delivery.
