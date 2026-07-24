from pathlib import Path

import pandas as pd


project_folder = Path(__file__).resolve().parent.parent
raw_path = project_folder / "data" / "Dau_chatbot_Raw_dataset.csv"
cleaned_path = project_folder / "data" / "Dau_chatbot_Cleaned_dataset.csv"

raw_df = pd.read_csv(raw_path, encoding="utf-8-sig")
cleaned_df = pd.read_csv(cleaned_path, encoding="utf-8-sig")

print("=== VALIDATION RESULTS ===")

print("Raw record count:", len(raw_df))
print("Cleaned record count:", len(cleaned_df))
print("Record count preserved:", len(raw_df) == len(cleaned_df))

print(
    "IDs preserved:",
    set(raw_df["ID"]) == set(cleaned_df["ID"]),
)

print("\n=== MISSING VALUES AFTER CLEANING ===")
print(cleaned_df.isnull().sum())

print("\n=== SPACES AFTER CLEANING ===")

text_columns = [
    "Soru",
    "Cevap",
    "Kategori (TR)",
    "Kategori (EN)",
    "Dil",
]

for column in text_columns:
    values = cleaned_df[column].dropna().astype(str)
    space_count = (values != values.str.strip()).sum()
    print(column, ":", space_count)

print("\n=== DUPLICATES AFTER CLEANING ===")
print(
    "Duplicated questions:",
    cleaned_df.duplicated(subset=["Soru"]).sum(),
)