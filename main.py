import os
import re
import fitz  # PyMuPDF
import subprocess
import tempfile
from pathlib import Path
from ebooklib import epub
from bs4 import BeautifulSoup
from openai import OpenAI
from langdetect import detect
from dotenv import load_dotenv
load_dotenv()

# === Config ===

API_KEY_ACCESS = os.getenv("API_KEY_ACCESS")
PDF_DIR = Path(os.getenv("PDF_DIR"))

client = OpenAI(
    api_key=API_KEY_ACCESS,
    base_url="https://api.siliconflow.cn/v1"
)

# === Extraction Functions ===

def extract_first_pages_text(pdf_path, max_pages=10):
    try:
        with fitz.open(pdf_path) as doc:
            for i in range(min(max_pages, len(doc))):
                text = doc[i].get_text().strip()
                if text:
                    return text
            print("[-] No meaningful text found in first", max_pages, "pages.")
            return ""
    except Exception as e:
        print(f"[!] Error reading {pdf_path.name}: {e}")
        return ""

def extract_text_from_epub(epub_path):
    try:
        book = epub.read_epub(str(epub_path))
        all_text = ''

        for item in book.items:
            if hasattr(item, 'get_type') and item.get_type() == 9:  # type 9 = document
                try:
                    content = item.get_body_content() if hasattr(item, 'get_body_content') else item.get_content()
                    soup = BeautifulSoup(content, 'html.parser')
                    all_text += soup.get_text(separator='\n')
                except Exception as parse_err:
                    print(f"[!] Error parsing {item.file_name} in {epub_path.name}: {parse_err}")
        return all_text
    except Exception as e:
        print(f"[!] Error reading EPUB {epub_path.name}: {e}")
        return ""

def extract_text_from_mobi_or_azw3(file_path):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as temp_file:
            temp_output = temp_file.name

        subprocess.run(
            ["ebook-convert", str(file_path), temp_output],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        with open(temp_output, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read()

        os.remove(temp_output)
        return text
    except Exception as e:
        print(f"[!] Error converting {file_path.name}: {e}")
        return ""

# === LLM Interaction ===

def get_title_and_author(text, original_filename):
    lang = "en"
    try:
        lang = detect(text[:500])
    except:
        pass

    prompt = (
        f"You are a metadata assistant. File name: `{original_filename}`. Language: `{lang}`.\n\n"

        f"Output exactly one line in this format:\n"
        f"`Title - AuthorFullName`\n\n"

        f"If the file name already contains a usable title and author, clean it by removing brackets, site names, extra symbols (e.g. (), 《》, 【】), and fix spacing/capitalization.\n"
        f"If not usable, extract a short (5–15 word) title and full author name from the text.\n\n"

        f"Strict rules:\n"
    f"- One line only, no explanation or markdown.\n"
    f"- Use only ASCII characters.\n"
    f"- Do NOT say anything like 'cleaned up result is...'\n\n"

    f"Text (up to 3000 chars):\n{text[:3000]}"
    )

    try:
        response = client.chat.completions.create(
            model="deepseek-ai/DeepSeek-R1-Distill-Qwen-32B",
            messages=[{"role": "user", "content": prompt}]
        )
        reply = response.choices[0].message.content.strip()
        token_count = response.usage.total_tokens if hasattr(response, "usage") else 0
        return sanitize_filename(reply), token_count
    except Exception as e:
        print(f"[!] LLM request failed: {e}")
        return None, 0

def sanitize_filename(name):
    name = re.sub(r'[<>:"/\\|?*]', '', name)  # Remove illegal characters
    name = re.sub(r'\s+', ' ', name).strip()  # Trim spaces
    return name

# === Rename and Check ===

def rename_file(file_path, new_name):
    new_path = file_path.with_name(f"{new_name}{file_path.suffix}")
    try:
        file_path.rename(new_path)
        print(f"[✓] Renamed to: {new_path.name}")
    except Exception as e:
        print(f"[!] Failed to rename {file_path.name}: {e}")

def test_llm_connection():
    try:
        response = client.chat.completions.create(
            model="deepseek-ai/DeepSeek-R1-Distill-Qwen-32B",
            messages=[{"role": "user", "content": "Say OK"}]
        )
        reply = response.choices[0].message.content.strip()
        if "OK" in reply:
            print("[✓] LLM API connection successful.")
        else:
            print(f"[!] Unexpected LLM reply: {reply}")
    except Exception as e:
        print(f"[X] LLM API test failed: {e}")
        raise SystemExit(1)

# === Main Processing ===

def process_all_files(directory):
    global counter
    test_llm_connection()
    supported_exts = [".pdf", ".epub", ".mobi", ".azw3"]
    all_files= [f for f in directory.iterdir() if f.suffix.lower() in supported_exts]
    counter = len(all_files)
    print(f"Found {len(all_files)} supported files.")

    for file in all_files:
        global token_sum
        print(f"\n[~] Processing: {file.name}")

        if file.suffix.lower() == ".pdf":
            text = text = extract_first_pages_text(file)
        elif file.suffix.lower() == ".epub":
            text = extract_text_from_epub(file)
        elif file.suffix.lower() in [".mobi", ".azw3"]:
            text = extract_text_from_mobi_or_azw3(file)
        else:
            print(f"[-] Unsupported format: {file.name}")
            continue

        if not text.strip():
            print("[-] No text found.")
            continue

        new_filename, token_expenditure = get_title_and_author(text, file.stem)
        token_sum += token_expenditure
        if new_filename:
            rename_file(file, new_filename)
        else:
            print("[-] No new name generated.")

# === Entry Point ===
token_sum = 0
if __name__ == "__main__":
    process_all_files(PDF_DIR)
    print(f"Total token used {token_sum}, per book: {token_sum/counter}")
