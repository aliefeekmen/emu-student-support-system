from pathlib import Path

import pandas as pd


project_folder = Path(__file__).resolve().parent.parent
dataset_path = project_folder / "data" / "EMU_chatbot_Cleaned_dataset.csv"

df = pd.read_csv(dataset_path, encoding="utf-8-sig")

missing_categories = df[
    df["Kategori (TR)"].isna()
    | df["Kategori (EN)"].isna()
]

print("=== RECORDS WITH MISSING CATEGORIES ===")

for _, row in missing_categories.iterrows():
    print("\nID:", row["ID"])
    print("Question:", row["Soru"])
    print("Answer:", row["Cevap"])
    print("Turkish category:", row["Kategori (TR)"])
    print("English category:", row["Kategori (EN)"])
    print("Language:", row["Dil"])

keywords = (
    "authenticator|dogrulama|doğrulama|"
    "giris|giriş|sistem yoneticisi|sistem yöneticisi"
)

similar_records = df[
    df["Soru"].str.contains(
        keywords,
        case=False,
        na=False,
        regex=True,
    )
]

print("\n=== SIMILAR RECORDS ===")

for _, row in similar_records.iterrows():
    print("\nID:", row["ID"])
    print("Question:", row["Soru"])
    print("Turkish category:", row["Kategori (TR)"])
    print("English category:", row["Kategori (EN)"])