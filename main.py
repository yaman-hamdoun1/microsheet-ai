import sys
import os
from generator_latex import create_cheat_sheet 
from extractor import extract_text_from_pdf
from compressor import compress_text, mock_compress

CACHE_FILE = "combined_text_cache.txt"

def main():
    # 1. Check for Cache First
    if os.path.exists(CACHE_FILE):
        print(f"Found cached text file ({CACHE_FILE}). Using it to skip PDF reading...")
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            combined_text = f.read()
    else:
        # No cache? Read the PDFs (The slow part)
        if len(sys.argv) < 2:
            print("Usage: python main.py <file1.pdf> ...")
            return

        input_files = sys.argv[1:]
        combined_text = ""
        print(f"Found {len(input_files)} PDF(s). Processing...")

        for pdf_path in input_files:
            if pdf_path.endswith(".pdf"):
                text = extract_text_from_pdf(pdf_path)
                if text:
                    combined_text += f"\n--- SOURCE: {os.path.basename(pdf_path)} ---\n"
                    combined_text += text
        
        # SAVE THE CACHE so you never wait again
        if combined_text:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                f.write(combined_text)
            print("Cache saved! Next run will be instant.")

    if not combined_text:
        print("No text found.")
        return

    # 3. Compress
    data = compress_text(combined_text)

    # 4. Generate
    if data:
        create_cheat_sheet(data, "cheatsheet.pdf")
    else:
        print("Generation skipped due to AI error.")

if __name__ == "__main__":
    main()