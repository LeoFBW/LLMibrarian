# 📚 LLM-Powered Book & Journal Renamer
Have you ever spent hours organizing your digital library, only to be thwarted by chaotic filenames that make your collection look like a digital wasteland?

Academic journals, eBooks, and scanned PDFs often come with filenames that are a nightmare to decipher. Picture this:

- `545.epub` – A meaningless number that tells you nothing
- `82年生的金智英【abcdef.com】.epub` – Cluttered with irrelevant branding and brackets
- `www.xxxyyyzzz.best+-+门口的野蛮人.mobi` – Filled with website cruft and inconsistent formatting

This isn't just an inconvenience—it's a productivity killer. Searching, sorting, and managing files becomes a tedious chore. Just as Qin Shi Huang standardized weights and measures in ancient China, we urgently need a modern solution to tame this chaos. Imagine a world where your files are clean, readable, and consistent—no more guessing games or wasted time.

---

## ✨ What This Project Does

This Python script uses a Language Model (LLM) API to:
- 📖 **Read the first page or main content** of PDF, EPUB, MOBI, and AZW3 files.
- 🧠 **Detect the language** automatically.
- 🤖 **Generate a meaningful title and full author name**, using LLM.
- ✍️ **Rename the file to:**  
  ```
  Title - AuthorFullName.ext
  ```
  (Only ASCII characters are kept to ensure compatibility)

It’s a force multiplier. In the age of LLMs, why should we still spend time renaming our books manually?
Life is already busy enough finding where to download them. Let AI do the cleanup.

---

## 💡 Motivation

This project was born out of practical pain points:
- No uniform naming standards across download sites.
- Mixed use of punctuation and languages in filenames.
- Some authors are listed inconsistently—by first name, last name, or just a transliterated guess.

Even worse: Some filenames (especially for journals) consist only of numbers and the author’s last name, which isn’t helpful for file storage unless you're in the middle of citing the text.
This project fixes that—by using AI to read and rename files based on their actual content, not arbitrary site logic.

Originally designed only for `.pdf` files, it has since grown to support various formats including book-reading formats like `.mobi`, `.azw3`, and `.epub`. More formats will be added soon—let’s make the best use of it!---

## 🛠️ Technologies Used

- `PyMuPDF` – extract text from PDFs
- `ebooklib` + `BeautifulSoup4` – parse EPUBs
- `Calibre CLI (ebook-convert)` – convert MOBI/AZW3 to text
- `langdetect` – auto-detect language
- `OpenAI SDK` – interface with any OpenAI-compatible LLM
- Your preferred LLM (I tested three models—including a free one—already configured in the code using SiliconFlow, so you can use them if you don’t already have an API key)

## ⚠️ Known Limitations

- If the first few pages of a PDF are empty (e.g., table of contents or cover), the script will **scan up to 10 pages**. It will stop at the **first page with non-empty text**.
- If that page contains a title but no clear author, the LLM may return a title **without an author name**. This will be addressed in a future update, but is currently rare.
- Some books might not return a meaningful result (e.g., obscure or poorly formatted content).
- Image-only PDFs require OCR (not currently implemented).
- A few library-related warnings (e.g., from `ebooklib`) may appear — but they do **not affect functionality**.
- Accuracy depends on model and input quality — this tool is a **productivity booster**, not a 100% solution.
- The current implementation includes **multiple plugins and dependencies**, resulting in a relatively large project footprint. Due to the high degree of LLM integration and broad format support, the filesize and complexity are on the heavier side. A **lighter, plugin-optional version is in the roadmap** for future releases.

---


## ✅ Usage

1. Place all your `.pdf`, `.epub`, `.mobi`, and `.azw3` files into a folder.
2. Update the folder path in a new `.env` file (as shown in the default configuration), directly in the script, or wherever you prefer.
3. Provide your LLM API key and base URL in `main.py` or within the `.env` file.
4. Run the script. It will rename files in-place. (Additional features may be introduced in the future.)
5. The script typically uses 160-200 tokens on average across the three models, with a runtime of 2.5-3 seconds per file without async. With async, the average runtime drops below 1 second for sample sizes above 15 (based on testing). Edge cases may exist.
> **Note:** Only ASCII characters are retained in the new filename for universal compatibility.

---

## 🔐 Optional: Hide Your API Key with `.env`

To avoid hardcoding your API key in the script, you can use a `.env` file:

1. Create a file named `.env` in your project root.
2. Add this line to it:
   ```
   API_KEY_ACCESS=your-api-key-here
   ```
3. Install `python-dotenv`:
   ```bash
   pip install python-dotenv
   ```
4. Add this to the top of your script:
   ```python
   from dotenv import load_dotenv
   load_dotenv()
   API_KEY_ACCESS = os.getenv("API_KEY_ACCESS")
   ```
5. Add `.env` to your `.gitignore` file to keep it secret.

---

## 📦 Setup

Install dependencies:
```bash
pip install openai pymupdf ebooklib beautifulsoup4 langdetect python-dotenv
```

Also, install **Calibre** from https://calibre-ebook.com/
Ensure `ebook-convert` is added to your system PATH.

---

## 📜 License

MIT — because knowledge (and cleaner filenames) should be free.

---

## 🤝 Acknowledgements

This README (and most of the program) was written with the help of AI.
I just had the problem and a vision — the AI handled the rest.

Special thanks to **SiliconFlow**, and their choice of **华为云昇腾云服务 (Huawei Cloud Ascend AI Cloud)** as a partner, which made this use of the `deepseek` `qwen` model possible.
It is the **first no-restriction platform** I’ve encountered that allows real flexibility in usage — and I **strongly recommend** it to anyone who wants to build LLM-powered tools without worrying about platform constraints or commercial roadblocks.

Happy renaming.
