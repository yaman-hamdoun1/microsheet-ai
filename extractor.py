import pdfplumber

def extract_text_from_pdf(pdf_path):
    """
    Opens a PDF and extracts text page by page.
    """
    print(f"Reading {pdf_path}...")
    full_text = ""
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return None
        
    return full_text