# studfeedload.py
import pandas as pd
import re
import torch
from sklearn.model_selection import train_test_split
from transformers import BertTokenizer

# ===============================
# 1️⃣ Load Dataset
# ===============================
from pathlib import Path

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "..", "data", "student_feedback_2000.csv")
CSV_PATH = os.path.abspath(CSV_PATH)
df = pd.read_csv(CSV_PATH)

# Basic validation
required_cols = {"feedback", "sentiment"}
if not required_cols.issubset(df.columns):
    raise ValueError("CSV must contain 'feedback' and 'sentiment' columns")

print(f"Dataset size: {len(df)}")

# ===============================
# 2️⃣ Text Cleaning
# ===============================
def clean_text(text):
    if pd.isna(text):
        return ""
    text = str(text).lower()
    text = re.sub(r"[^a-z0-9\s.,!?]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

df["feedback_clean"] = df["feedback"].apply(clean_text)

# ===============================
# 3️⃣ Encode Labels
# ===============================
label_map = {
    "Negative": 0,
    "Neutral": 1,
    "Positive": 2
}

df["label"] = df["sentiment"].map(label_map)

if df["label"].isnull().any():
    raise ValueError("Sentiment column contains invalid labels")

# ===============================
# 4️⃣ Train / Test Split
# ===============================
train_texts, test_texts, train_labels, test_labels = train_test_split(
    df["feedback_clean"].tolist(),
    df["label"].tolist(),
    test_size=0.2,
    random_state=42,
    stratify=df["label"]
)

# ===============================
# 5️⃣ Tokenization
# ===============================
tokenizer = BertTokenizer.from_pretrained("bert-base-uncased")

train_encodings = tokenizer(
    train_texts,
    truncation=True,
    padding=True,
    max_length=128
)

test_encodings = tokenizer(
    test_texts,
    truncation=True,
    padding=True,
    max_length=128
)

# ===============================
# 6️⃣ PyTorch Dataset Class
# ===============================
class FeedbackDataset(torch.utils.data.Dataset):
    def __init__(self, encodings, labels):
        self.encodings = encodings
        self.labels = labels

    def __getitem__(self, idx):
        item = {key: torch.tensor(val[idx]) for key, val in self.encodings.items()}
        item["labels"] = torch.tensor(self.labels[idx])
        return item

    def __len__(self):
        return len(self.labels)

# ===============================
# 7️⃣ Create Dataset Objects
# ===============================
train_dataset = FeedbackDataset(train_encodings, train_labels)
test_dataset = FeedbackDataset(test_encodings, test_labels)

# ===============================
# 8️⃣ Save Datasets (Optional)
# ===============================
torch.save(train_dataset, "train_dataset.pt")
torch.save(test_dataset, "test_dataset.pt")

print("✅ Dataset preparation completed")
print(f"Train size: {len(train_dataset)}")
print(f"Test size: {len(test_dataset)}")