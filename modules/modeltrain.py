import torch
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
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
# 2️⃣ Model & Tokenizer (TINY BERT)
# ===============================
MODEL_NAME = "prajjwal1/bert-tiny"

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

model = AutoModelForSequenceClassification.from_pretrained(
    MODEL_NAME,
    num_labels=3  # 0=Negative, 1=Neutral, 2=Positive
)

model.to(device)

# ===============================
# 3️⃣ Training Arguments
# ===============================
training_args = TrainingArguments(
    output_dir="results",
    num_train_epochs=6,                 # Slightly more epochs for tiny model
    per_device_train_batch_size=16,     # Can increase because model is small
    per_device_eval_batch_size=32,
    learning_rate=3e-5,                 # Slightly higher LR works well for tiny
    eval_strategy="epoch",
    save_strategy="epoch",
    fp16=torch.cuda.is_available(),
    gradient_accumulation_steps=1,
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
    train_dataset=train_dataset,
    eval_dataset=test_dataset,
    compute_metrics=compute_metrics
)

# ===============================
# 6️⃣ Train
# ===============================
trainer.train()

# ===============================
# 7️⃣ Save Model
# ===============================
SAVE_DIR = "student_feedback_tinybert"

model.save_pretrained(SAVE_DIR)
tokenizer.save_pretrained(SAVE_DIR)

print("✅ TinyBERT training complete")
print(f"✅ Model saved to '{SAVE_DIR}'")