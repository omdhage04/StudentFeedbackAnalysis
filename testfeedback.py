from transformers import BertTokenizer, BertForSequenceClassification
import torch

# Load saved model and tokenizer
model_path = r"D:\Projects\StudentFeedbackAnalysis\student_feedback_bert"
tokenizer = BertTokenizer.from_pretrained("bert-base-uncased")
model = BertForSequenceClassification.from_pretrained(model_path)
model.eval()

# Example feedback
text = "The teacher explained concepts very clearly and was supportive."
inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True)
with torch.no_grad():
    outputs = model(**inputs)
    pred = torch.argmax(outputs.logits, dim=1).item()

labels = ["Negative", "Neutral", "Positive"]
print(f"Predicted sentiment: {labels[pred]}")
