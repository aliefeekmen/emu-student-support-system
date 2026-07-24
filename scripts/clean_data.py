from pathlib import Path

import pandas as pd


project_folder = Path(__file__).resolve().parent.parent
input_path = project_folder / "data" / "Dau_chatbot_Raw_dataset.csv"
output_path = project_folder / "data" / "Dau_chatbot_Cleaned_dataset.csv"

df = pd.read_csv(input_path, encoding="utf-8-sig")

print("Original record count:", len(df))

text_columns = [
    "Soru",
    "Cevap",
    "Kategori (TR)",
    "Kategori (EN)",
    "Dil",
]

for column in text_columns:
    df[column] = df[column].astype("string")
    df[column] = df[column].str.strip()
    df[column] = df[column].str.replace(r"[ \t]+", " ", regex=True)
    df[column] = df[column].str.replace(r"\r\n?", "\n", regex=True)

df["Dil"] = df["Dil"].str.lower()

missing_record = df["ID"] == 5552

df.loc[
    missing_record,
    "Kategori (TR)",
] = "Bilgi Yönetimi ve Hizmetleri Şubesi"

df.loc[
    missing_record,
    "Kategori (EN)",
] = "Information Management and Services Branch"

course_issue_mask = (
    df["Kategori (TR)"]
    == "Ders Sorunları (Access Açılması)"
)

df.loc[
    course_issue_mask,
    "Kategori (EN)",
] = "Course Issues (Access Opening)"

df["Kategori (TR)"] = df["Kategori (TR)"].replace(
    {
        "Burs İşleri (Blgi)": "Burs İşleri (Bilgi)",
    }
)

df["Kategori (EN)"] = df["Kategori (EN)"].replace(
    {
        "Information Management and Services Branch Öneri":
            "Information Management and Services Branch Suggestion",

        "Graduation Procedures Otomatik E-posta":
            "Graduation Procedures Automatic Email",

        "Mezuniyet İşlemleri (İlişki Kesme, Diploma Onay)":
            "Graduation Procedures "
            "(Disenrollment, Diploma Approval)",

        "Student Affairs Öneri":
            "Student Affairs Suggestion",
    }
)

df.to_csv(
    output_path,
    index=False,
    encoding="utf-8-sig",
)

print("Cleaned record count:", len(df))
print("Cleaned dataset saved to:")
print(output_path)