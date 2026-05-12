import re
import json

def extract_texts(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        html = f.read()
    
    # Simple regex to find text containing Cyrillic characters outside tags
    # Remove scripts and styles first
    html = re.sub(r'<script.*?>.*?</script>', '', html, flags=re.DOTALL)
    html = re.sub(r'<style.*?>.*?</style>', '', html, flags=re.DOTALL)
    
    # Find texts outside tags
    texts = set()
    for text_block in re.split(r'<[^>]+>', html):
        text = text_block.strip()
        if text and re.search(r'[а-яА-ЯёЁ]', text):
            texts.add(text)
    
    print(json.dumps(sorted(texts), ensure_ascii=False, indent=2))

extract_texts("bxm_complete.html")
