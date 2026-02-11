# utils.py
import re
from typing import List

def clean_text(text: str) -> str:
    if not text:
        return ""
    # Remove extra whitespace
    text = re.sub(r"\s+", " ", text)
    # Remove strange control characters
    text = re.sub(r"[^\x00-\x7F]+", " ", text)
    return text.strip()

def chunk_list(data: List[str], chunk_size: int = 25) -> List[List[str]]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")
    return [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]