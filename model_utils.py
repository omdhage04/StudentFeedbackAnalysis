import torch
from transformers import BertTokenizer, BertForSequenceClassification

# Load model ONCE when server starts
try:
    # Point to the folder where modeltrain.py saved the model
    MODEL_PATH = "student_feedback_bert" 
    tokenizer = BertTokenizer.from_pretrained(MODEL_PATH)
    model = BertForSequenceClassification.from_pretrained(MODEL_PATH, num_labels=3)
    model.eval()
    print("✅ Custom Model Loaded Successfully")
except:
    print("⚠️ Custom Model not found, loading base BERT (Predictions will be random)")
    tokenizer = BertTokenizer.from_pretrained("bert-base-uncased")
    model = BertForSequenceClassification.from_pretrained("bert-base-uncased", num_labels=3)

def predict_sentiment(text):
    inputs = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        padding=True,
        max_length=128
    )
    with torch.no_grad():
        outputs = model(**inputs)

    labels = ["Negative", "Neutral", "Positive"]
    return labels[torch.argmax(outputs.logits).item()]