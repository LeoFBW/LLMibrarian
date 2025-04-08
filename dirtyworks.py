from pathlib import Path
import os
import random
from dotenv import load_dotenv

# Get the PDF_DIR environment variable and convert it to a Path object
load_dotenv()
PDF_DIR = Path(os.getenv("PDF_DIR"))

# Define allowed extensions
ALLOWED_EXTENSIONS = {".pdf", ".azw3", ".mobi", ".epub"}

# Function to generate a random 8-digit name
def generate_random_name(existing_names):
    while True:
        random_name = f"{random.randint(10000000, 99999999)}"
        if random_name not in existing_names:
            return random_name

# Keep track of used random names to avoid duplicates
used_names = set()

# Iterate over files in the directory
for file in PDF_DIR.iterdir():
    if file.is_file() and file.suffix.lower() in ALLOWED_EXTENSIONS:
        new_name = generate_random_name(used_names)
        new_file_path = file.with_name(f"{new_name}{file.suffix}")
        file.rename(new_file_path)
        used_names.add(new_name)
        print(f"Renamed '{file.name}' to '{new_file_path.name}'")
