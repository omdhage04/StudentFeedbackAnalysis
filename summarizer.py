# summarizer.py
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from utils import chunk_list, clean_text

# Loading the model
MODEL_NAME = "Qwen/Qwen2.5-1.5B-Instruct"

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
    device_map="auto"
)
model.eval()

def summarize_chunk(feedback_text: str) -> str:
    # 1. First, we define the prompt string
    prompt_content = f"""
You are an AI assistant summarizing student feedback for college administration.
Summarize the following feedbacks into 4–5 concise lines.
Focus on common opinions, major concerns, and overall experience.
Do NOT mention individual students.

Feedbacks:
{feedback_text}
"""
    # 2. Format it for the Qwen Chat Template
    messages = [{"role": "user", "content": prompt_content}]
    formatted_text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    
    # 3. Now we tokenize the formatted text
    inputs = tokenizer(formatted_text, return_tensors="pt").to(model.device)

    with torch.no_grad():
        output = model.generate(
            **inputs,
            max_new_tokens=200,
            temperature=0.3,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id
        )

    # 4. Decode only the new generated tokens (the summary)
    response = tokenizer.decode(output[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
    return response.strip()

def generate_final_summary(feedback_list: list) -> str:
    if not feedback_list:
        return "No feedback available for summarization."

    # Clean feedback text
    cleaned_list = [clean_text(fb) for fb in feedback_list if fb.strip()]
    
    if not cleaned_list:
        return "No valid text signals detected."

    # Hierarchical Summarization: Split into manageable chunks
    chunks = chunk_list(cleaned_list, chunk_size=20)
    chunk_summaries = []

    print(f"--- AI is processing {len(chunks)} chunk(s) ---")

    for i, chunk in enumerate(chunks):
        joined_text = "\n".join(chunk)
        summary = summarize_chunk(joined_text)
        chunk_summaries.append(summary)
        print(f"Processed chunk {i+1}/{len(chunks)}")

    # If there was only one chunk, we are done
    if len(chunk_summaries) == 1:
        return chunk_summaries[0]

    # If multiple chunks, summarize the summaries into one final result
    final_input = "\n".join(chunk_summaries)
    return summarize_chunk(final_input)