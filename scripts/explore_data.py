from pathlib import Path

import pandas as pd


project_folder = Path(__file__).resolve().parent.parent
dataset_path = project_folder / "data" / "EMU_chatbot_Raw_dataset.csv"

df = pd.read_csv(dataset_path, encoding="utf-8-sig")

print("=== DATASET SUMMARY ===")
print("Number of rows:", df.shape[0])
print("Number of columns:", df.shape[1])
print("Columns:", df.columns.tolist())

print("\n=== MISSING VALUES ===")
print(df.isnull().sum())

print("\n=== DUPLICATES ===")
print("Completely duplicated rows:", df.duplicated().sum())
print("Duplicated IDs:", df.duplicated(subset=["ID"]).sum())
print("Duplicated questions:", df.duplicated(subset=["Soru"]).sum())

print("\n=== LANGUAGE DISTRIBUTION ===")
print(df["Dil"].value_counts(dropna=False))

print("\n=== CATEGORY INFORMATION ===")
print("Unique Turkish categories:", df["Kategori (TR)"].nunique())
print("Unique English categories:", df["Kategori (EN)"].nunique())

print("\n=== UNNECESSARY SPACES ===")

text_columns = [
    "Soru",
    "Cevap",
    "Kategori (TR)",
    "Kategori (EN)",
    "Dil",
]

for column in text_columns:
    values = df[column].dropna().astype(str)
    space_count = (values != values.str.strip()).sum()
    print(column, ":", space_count)