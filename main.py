import os
import re
import asyncio
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime, timezone

import fitz  # PyMuPDF
import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from ebooklib import epub
from langdetect import detect

load_dotenv()

API_KEY = os.getenv("API_KEY_ACCESS")
PDF_DIR = Path(os.getenv("PDF_DIR"))
BASE_URL = "https://api.siliconflow.cn/v1"

# === Config ===
FT_MODEL = "deepseek-ai/DeepSeek-V2.5"
FALLBACK_MODEL = "deepseek-ai/DeepSeek-V2.5"
MAX_CONCURRENT = 5
semaphore = asyncio.Semaphore(MAX_CONCURRENT)

# === Utility ===

def sanitize_filename(name):
    name = re.sub(r'[<>:"/\\|?*]', '', name)  # remove invalid
    name = re.sub(r'\s+', ' ', name).strip()  # trim whitespace

    # Validate pattern: 'Title - Author'
    if len(name) > 150 or "-" not in name or len(name.split("-")) < 2:
        print("[!] Invalid format detected, skipping rename.")
        print(f"[DEBUG] Raw model reply: {name}")
        return None

    return name

def rename_file(file_path, new_name):
    new_path = file_path.with_name(f"{new_name}{file_path.suffix}")
    try:
        file_path.rename(new_path)
        print(f"[✓] Renamed to: {new_path.name}")
    except Exception as e:
        print(f"[!] Failed to rename {file_path.name}: {e}")

# === File Text Extraction ===

def extract_first_pages_text(pdf_path, max_pages=10):
    try:
        with fitz.open(pdf_path) as doc:
            for i in range(min(max_pages, len(doc))):
                text = doc[i].get_text().strip()
                if text:
                    return text
    except Exception as e:
        print(f"[!] PDF read error {pdf_path.name}: {e}")
    return ""

def extract_text_from_epub(epub_path):
    try:
        book = epub.read_epub(str(epub_path))
        all_text = ''
        for item in book.items:
            if hasattr(item, 'get_type') and item.get_type() == 9:
                content = item.get_content()
                soup = BeautifulSoup(content, 'html.parser')
                all_text += soup.get_text(separator='\n')
        return all_text
    except Exception as e:
        print(f"[!] EPUB read error {epub_path.name}: {e}")
        return ""

def extract_text_from_mobi_or_azw3(file_path):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
            tmp_out = tmp.name
        subprocess.run(["ebook-convert", str(file_path), tmp_out], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        with open(tmp_out, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read()
        os.remove(tmp_out)
        return text
    except Exception as e:
        print(f"[!] Conversion error {file_path.name}: {e}")
        return ""

# === Async LLM Calls ===

async def phase2_fallback(client, text, original_filename, lang):
    prompt = (
        f"Extract clean metadata.\n"
        f"Input: `{original_filename}`\n\n"
        f"From the text, extract a short and proper book title (max 15 words) and full author name.\n"
        f"Return ONLY in this strict format:\n"
        f"`Title - AuthorFullName`\n\n"
        f"- No extra commentary\n"
        f"- No markdown or quotation marks\n"
        f"- Use ASCII characters only\n"
        f"- Must include both title and full author name\n\n"
        f"Text:\n{text[:1000]}"
    )

    body = {
        "model": FALLBACK_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 512
    }

    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

    async with semaphore:
        r = await client.post(f"{BASE_URL}/chat/completions", headers=headers, json=body)
        data = r.json()
        return sanitize_filename(data["choices"][0]["message"]["content"].strip()), data.get("usage", {}).get("total_tokens", 0)

async def get_title_and_author(client, text, original_filename):
    try:
        lang = detect(text[:500])
    except:
        lang = "en"

    phase1_prompt = (
        f"You are a metadata assistant. File name: `{original_filename}`. Language: `{lang}`.\n\n"
        f"If the file name clearly contains a clean, usable title and full author name, return it in this format:\n"
        f"`Title - AuthorFullName`\n"
        f"Clean it by removing brackets, site names, extra symbols, and fix spacing/capitalization.\n"
        f"Remove anything like 'Z-Library' – it's not an author, just site garbage.\n\n"
        f"If the filename is too vague, noisy, or lacks usable info, reply with ONLY this word:\n"
        f"`MORE`\n\n"
        f"No markdown, no extra words, only the formatted result or the keyword `MORE`."
    )

    body = {
        "model": FT_MODEL,
        "messages": [{"role": "user", "content": phase1_prompt}],
        "max_tokens": 512
    }

    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

    async with semaphore:
        try:
            r = await client.post(f"{BASE_URL}/chat/completions", headers=headers, json=body)
            data = r.json()
            reply = data["choices"][0]["message"]["content"].strip()
            token_use = data.get("usage", {}).get("total_tokens", 0)

            if reply.upper() == "MORE":
                return await phase2_fallback(client, text, original_filename, lang)
            return sanitize_filename(reply), token_use
        except Exception as e:
            print(f"[!] LLM error on {original_filename}: {e}")
            return None, 0

# === File Processing ===

async def process_file(client, file_path):
    if file_path.suffix.lower() == ".pdf":
        text = extract_first_pages_text(file_path)
    elif file_path.suffix.lower() == ".epub":
        text = extract_text_from_epub(file_path)
    elif file_path.suffix.lower() in [".mobi", ".azw3"]:
        text = extract_text_from_mobi_or_azw3(file_path)
    else:
        return 0

    if not text.strip():
        print(f"[-] No usable text in {file_path.name}")
        return 0

    new_name, tokens = await get_title_and_author(client, text, file_path.stem)
    if new_name:
        rename_file(file_path, new_name)
    else:
        print("[-] Skipped:", file_path.name)
    return tokens

async def main():
    utc_start = datetime.now(timezone.utc)
    print("Start (UTC):", utc_start.strftime("%H:%MZ"))

    all_files = [f for f in PDF_DIR.iterdir() if f.suffix.lower() in [".pdf", ".epub", ".mobi", ".azw3"]]
    print(f"Found {len(all_files)} files to process.")

    token_sum = 0
    async with httpx.AsyncClient(timeout=60) as client:
        tasks = [process_file(client, f) for f in all_files]
        results = await asyncio.gather(*tasks)
        token_sum = sum(results)

    utc_end = datetime.now(timezone.utc)
    duration = utc_end - utc_start
    avg_time = duration.total_seconds() / max(len(all_files), 1)

    print(f"""
    === Async Renaming Complete ===
    Files processed: {len(all_files)}, 
    Total tokens: {token_sum}, Avg tokens: {token_sum / len(all_files):.2f}
    Total time: {duration.total_seconds():.2f}s, Avg time: {avg_time:.2f}s
    End (UTC): {utc_end.strftime("%H:%MZ")}
    """)

if __name__ == "__main__":
    asyncio.run(main())
