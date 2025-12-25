import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

def compress_text(raw_text):
    """
    ROBUST MODE: Uses Raw Text parsing instead of JSON.
    This prevents 'Invalid \escape' errors caused by LaTeX backslashes.
    """
    # Check for either variable name to be safe
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    
    if not api_key:
        print("Error: API_KEY not found.")
        return mock_compress()

    client = genai.Client(api_key=api_key.strip())
    
    # Start with 1.5-flash as it is the most reliable standard model.
    # If you specifically want 2.0-flash, you can change this string.
    model_name = "gemini-2.5-flash"

    # Send a safe amount of text
    safe_text = raw_text[:35000]
    
    print(f"Compressing text with {model_name} (Raw Mode)...")

    max_retries = 3
    for attempt in range(max_retries):
        try:
            # We ask for a CUSTOM FORMAT that is easy to split in Python
            # Format: ===TITLE=== \n content \n ===END===
            response = client.models.generate_content(
                model=model_name,
                contents=f"Summarize this into a cheat sheet.\n\n{safe_text}",
                config=types.GenerateContentConfig(
                    system_instruction=(
                        "You are an expert Engineering Tutor creating a High-Density Cheat Sheet. "
                        "Your goal is to compress knowledge into the smallest possible space while retaining 100% of the mathematical and logical rigor.\n"
                        "STRICT RULES:\n"
                        "1. **No Fluff**: Remove words like 'The formula is...', 'basically', 'introduction'. Start directly with facts.\n"
                        "2. **Structure**: Use LaTeX lists (`\\begin{itemize} \\item ... \\end{itemize}`) for multiple points. Never write long paragraphs.\n"
                        "3. **Formatting**: Use `\\textbf{KEYWORD}:` for definitions. Use LaTeX math mode `$E=mc^2$` for ALL formulas and variables.\n"
                        "4. **Symbols over Words**: Replace 'implies' with $\\rightarrow$, 'equivalent' with $\\leftrightarrow$, 'sum' with $\\Sigma$.\n"
                        "5. **Output Format**: Use the following separator structure EXACTLY:\n"
                        "===SECTION===\n"
                        "Title of Section\n"
                        "===CONTENT===\n"
                        "LaTeX content here\n"
                        "===END===\n\n"
                        "Do not use JSON. Do not use Markdown blocks."
                    ),
                    response_mime_type="text/plain" # Plain text avoids JSON validation errors
                )
            )
            
            # Manual Parsing (Invincible against JSON errors)
            sections = []
            
            if not response.text:
                print("AI returned empty text.")
                continue

            raw_response = response.text
            
            # Split by the section separator
            raw_sections = raw_response.split("===SECTION===")
            
            for chunk in raw_sections:
                if "===CONTENT===" not in chunk:
                    continue
                
                try:
                    # Extract Title and Content using the markers
                    parts = chunk.split("===CONTENT===")
                    title = parts[0].strip()
                    
                    # Remove the ===END=== marker from content
                    content_part = parts[1].split("===END===")[0].strip()
                    
                    if title and content_part:
                        sections.append({"title": title, "content": content_part})
                except:
                    continue

            if sections:
                print(f"Success! Extracted {len(sections)} sections.")
                return sections
            else:
                print("AI returned empty sections. Retrying...")
                continue

        except Exception as e:
            error_msg = str(e)
            print(f"AI Error (Attempt {attempt+1}): {error_msg}")
            
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                wait_time = 20 
                print(f"Rate limit hit. Waiting {wait_time}s...")
                time.sleep(wait_time)
                continue 
            elif "404" in error_msg:
                # Fallback if the specific model version isn't found
                print(f"Model {model_name} not found. Trying 'gemini-2.5-pro'...")
                model_name = "gemini-2.5-pro"
                continue
            else:
                break

    print(">>> AI failed. Using Backup. <<<")
    return mock_compress()

def mock_compress(raw_text=None):
    return [
        {"title": "AI ERROR", "content": r"Could not parse AI output."},
        {"title": "Calculus", "content": r"Derivatives: \\ $\frac{d}{dx}x^n = nx^{n-1}$"}
    ]