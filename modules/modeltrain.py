import torch
from transformers import (
    BertForSequenceClassification,
    BertTokenizer,
    Trainer,
    TrainingArguments
)
from studfeedload import train_dataset, test_dataset
from sklearn.metrics import accuracy_score, precision_recall_fscore_support

# ===============================
# 1️⃣ Device Selection
# ===============================
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"🚀 Training on device: {device}")

# ===============================
# 2️⃣ Model & Tokenizer
# ===============================
MODEL_NAME = "bert-base-uncased"

tokenizer = BertTokenizer.from_pretrained(MODEL_NAME)

model = BertForSequenceClassification.from_pretrained(
    MODEL_NAME,
    num_labels=3  # Negative, Neutral, Positive
)
model.to(device)

# ===============================
# 3️⃣ Training Arguments
# ===============================
training_args = TrainingArguments(
    output_dir="results",
    num_train_epochs=5,                 # 🔥 REAL TRAINING
    per_device_train_batch_size=8,
    per_device_eval_batch_size=16,
    learning_rate=2e-5,
    eval_strategy="epoch",
    save_strategy="epoch",
    fp16=torch.cuda.is_available(),
    gradient_accumulation_steps=2,
    load_best_model_at_end=True,
    metric_for_best_model="eval_loss",
    logging_steps=50,
    report_to="none"
)

# ===============================
# 4️⃣ Metrics
# ===============================
def compute_metrics(pred):
    labels = pred.label_ids
    preds = pred.predictions.argmax(axis=-1)

    precision, recall, f1, _ = precision_recall_fscore_support(
        labels, preds, average="weighted"
    )
    acc = accuracy_score(labels, preds)

    return {
        "accuracy": acc,
        "precision": precision,
        "recall": recall,
        "f1": f1
    }

# ===============================
# 5️⃣ Trainer
# ===============================
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,   # ✅ from studfeedload.py
    eval_dataset=test_dataset,     # ✅ from studfeedload.py
    compute_metrics=compute_metrics
)

# ===============================
# 6️⃣ Train
# ===============================
trainer.train()

# ===============================
# 7️⃣ Save Model
# ===============================
SAVE_DIR = "student_feedback_bert"

model.save_pretrained(SAVE_DIR)
tokenizer.save_pretrained(SAVE_DIR)

print("✅ Model training complete")
print(f"✅ Model saved to '{SAVE_DIR}'")