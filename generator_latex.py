import requests
import re

def escape_latex(text):
    """
    Escapes special LaTeX characters to prevent compilation crashes.
    """
    if not text:
        return ""
    
    # 1. Escape basic special characters
    # Note: We do NOT escape backslashes yet because they might be part of math
    chars = {
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',  # We handle math dollars separately below
        '#': r'\#',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\textasciicircum{}'
    }
    
    # 2. Heuristic to detect Math Mode vs Normal Text
    # If the text looks like a formula (surrounded by $...$), we leave it alone.
    # Otherwise, we escape the characters.
    
    # Split by '$' to separate text from math
    parts = text.split('$')
    escaped_parts = []
    
    for i, part in enumerate(parts):
        if i % 2 == 0: 
            # This is NORMAL TEXT (even index) -> Escape it
            for char, escaped in chars.items():
                # Don't escape $ here, we split by it
                if char != '$': 
                    part = part.replace(char, escaped)
            escaped_parts.append(part)
        else:
            # This is MATH MODE (odd index) -> Keep it raw
            # But we might need to fix common AI math errors here if needed
            escaped_parts.append(f"${part}$")
            
    return "".join(escaped_parts)

def create_cheat_sheet(data, output_filename):
    print("Generating LaTeX code with Sanitization...")

    latex_content = r"""
    \documentclass[10pt]{article}
    \usepackage[utf8]{inputenc}
    \usepackage[landscape, margin=0.5in]{geometry}
    \usepackage{multicol}
    \usepackage{amsmath}
    \usepackage{amssymb}
    \usepackage{enumitem}
    \usepackage{titlesec}
    \usepackage{hyperref}

    % Tighten spacing
    \setlength{\parindent}{0pt}
    \setlength{\parskip}{0pt}
    \titlespacing*{\section}{0pt}{2pt}{2pt}
    \setlist[itemize]{noitemsep, topsep=0pt, leftmargin=*}

    \begin{document}
    \begin{multicols*}{3}
    \begin{center}
        \textbf{\LARGE MicroSheet AI Summary}
    \end{center}
    \vspace{0.2cm}
    """

    for section in data:
        title = section.get('title', 'Section').replace('_', ' ')
        content = section.get('content', '')
        
        # SANITIZE INPUTS (The Critical Fix)
        safe_title = escape_latex(title)
        safe_content = escape_latex(content)
        
        latex_content += f"\\section*{{{safe_title}}}\n"
        latex_content += f"{safe_content}\n\n"

    latex_content += r"""
    \end{multicols*}
    \end{document}
    """

    # Send to LaTeXOnline API
    url = "https://latexonline.cc/compile"
    
    try:
        payload = {'text': latex_content}
        response = requests.post(url, data=payload, timeout=45)

        if response.status_code == 200:
            with open(output_filename, 'wb') as f:
                f.write(response.content)
            print(f"Success! PDF saved to {output_filename}")
        else:
            print(f"API Error {response.status_code}")
            create_error_pdf(output_filename, "Syntax Error: " + response.text[:200])

    except Exception as e:
        print(f"Connection Error: {e}")
        create_error_pdf(output_filename, str(e))

def create_error_pdf(filename, error_msg):
    # Minimal fallback using ReportLab just to show the error
    from reportlab.pdfgen import canvas
    c = canvas.Canvas(filename)
    c.drawString(50, 800, "PDF Generation Failed")
    c.drawString(50, 780, "Error details:")
    c.drawString(50, 760, str(error_msg)[:100])
    c.save()