# Data Analysis and Normalization Report

## 1. Purpose

The purpose of this phase was to explore, clean, and normalize the raw DAU student question-answer dataset.

The cleaned data was prepared for database storage and future AI integration.

The train/test split and AI model training were not completed in this phase. The official train/test split will be provided at a later stage.

## 2. Dataset Information

Dataset file:

`Dau_chatbot_Raw_dataset.csv`

The dataset uses UTF-8 encoding and contains both Turkish and English question-answer records.

### Dataset Columns

| Column | Description |
|---|---|
| ID | Unique record number |
| Soru | Student question |
| Cevap | Official answer |
| Kategori (TR) | Turkish category name |
| Kategori (EN) | English category name |
| Dil | Language code (`tr` or `en`) |

## 3. Initial Exploration Results

The following results were found during the first data exploration:

| Check | Result |
|---|---:|
| Total records | 769 |
| Total columns | 6 |
| Turkish records | 654 |
| English records | 115 |
| Fully duplicated rows | 0 |
| Duplicated questions | 120 |
| Duplicated IDs | 0 |
| Missing Turkish categories | 1 |
| Missing English categories | 1 |
| Questions with unnecessary outer spaces | 48 |
| Answers with unnecessary outer spaces | 609 |

## 4. Data Cleaning Operations

The following cleaning operations were applied:

1. Unnecessary spaces at the beginning and end of text values were removed.
2. Repeated horizontal spaces were changed to single spaces.
3. Line-ending characters were standardized.
4. Language codes were changed to lowercase.
5. The missing category was completed by checking similar records.
6. Inconsistent category translations were standardized.
7. Identified spelling mistakes in category names were corrected.
8. The cleaned data was saved as a separate CSV file.

The original raw dataset was not changed.

Cleaned dataset file:

`Dau_chatbot_Cleaned_dataset.csv`

## 5. Missing Category Correction

The record with ID `5552` had no Turkish or English category information.

The question was about Microsoft Authenticator, changing a telephone, and being unable to receive a verification code.

Similar records in the dataset were examined. These records were assigned to the following category:

- Turkish: `Bilgi Yönetimi ve Hizmetleri Şubesi`
- English: `Information Management and Services Branch`

The missing category was completed with these values.

## 6. Category Standardization

One Turkish category had two different English translations:

- `Course Issues (Access Opening)`
- `Course Issues (Access Activation)`

The dataset README used `Course Issues (Access Opening)`. Therefore, this value was selected as the standard translation.

The following category spelling and translation problems were also corrected:

| Previous Value | Standardized Value |
|---|---|
| Burs İşleri (Blgi) | Burs İşleri (Bilgi) |
| Information Management and Services Branch Öneri | Information Management and Services Branch Suggestion |
| Graduation Procedures Otomatik E-posta | Graduation Procedures Automatic Email |
| Mezuniyet İşlemleri (İlişki Kesme, Diploma Onay) | Graduation Procedures (Disenrollment, Diploma Approval) |
| Student Affairs Öneri | Student Affairs Suggestion |

## 7. Duplicated Questions

Before cleaning, 120 duplicated questions were found.

After space normalization, the number increased to 121. This happened because two questions that were different only because of unnecessary spaces became equal after cleaning.

Duplicated questions were not automatically deleted. The same question may have been asked at different times or may have received different answers.

Deleting these records could cause information loss. Therefore, all 769 records were preserved.

## 8. Validation After Cleaning

The cleaned dataset was checked again.

| Check | Result |
|---|---:|
| Total records | 769 |
| Preserved IDs | 769 |
| Missing values | 0 |
| Unnecessary outer spaces | 0 |
| Duplicated IDs | 0 |
| Fully duplicated rows | 0 |

The ID values in the raw and cleaned datasets were compared. All original IDs were preserved.

## 9. Database Normalization

Language and category values were repeated in many CSV records.

To reduce repeated data, the dataset was divided into relational database tables:

- `languages`
- `categories`
- `knowledge_entries`

The `knowledge_entries` table does not store the full language and category names in every row. It uses foreign keys to connect to the `languages` and `categories` tables.

After normalization, the database contained:

- 2 languages
- 31 categories
- 769 institutional question-answer records

## 10. Database Validation

The following database checks were completed:

- No foreign key errors were found.
- 654 Turkish records were verified.
- 115 English records were verified.
- 769 question-answer records were verified.
- Category and language relationships were successfully retrieved through the API.

## 11. Initial System Setup

A basic backend system was developed with FastAPI.

The initial system supports:

- API and database health checking
- Database statistics
- Category listing
- Knowledge-base searching
- Language filtering
- Category filtering
- Pagination
- Retrieving one knowledge entry by ID
- Student question submission
- Question assignment to staff
- Staff answers
- Viewing question and answer details

Six automated API tests were created, and all tests passed.

## 12. Conclusion

The raw dataset was successfully explored, cleaned, and normalized.

All 769 records were preserved and transferred to a relational database. The database and initial API provide a suitable foundation for the institutional question-answer memory.

The official train/test split and AI model integration will be completed in the next project phase.