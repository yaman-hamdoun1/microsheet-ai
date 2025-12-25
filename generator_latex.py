import os
import subprocess
import shutil
import stat
import re

def escape_latex(text):
    """
    Robustly escapes special LaTeX characters while trying to preserve Math.
    """
    if not text:
        return ""
    
    # Map of special chars to their escaped versions
    chars = {
        '&': r'\&',
        '%': r'\%',
        '#': r'\#',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\textasciicircum{}',
        '\\': r'\textbackslash{}'
    }
    
    # Heuristic: Split by '$' to separate text from math.
    # We only escape characters inside the TEXT parts, not the MATH parts.
    parts = text.split('$')
    escaped_parts = []
    
    for i, part in enumerate(parts):
        if i % 2 == 0: 
            # Even index = Normal Text -> Escape it
            for char, escaped in chars.items():
                part = part.replace(char, escaped)
            escaped_parts.append(part)
        else:
            # Odd index = Math Mode ($...$) -> Keep it raw
            escaped_parts.append(f"${part}$")
            
    return "".join(escaped_parts)

def create_cheat_sheet(data, output_filename):
    """
    Generates PDF using local Tectonic engine with robust error handling.
    """
    # 1. Setup Tectonic
    tectonic_path = os.path.abspath("tectonic")
    
    if not os.path.exists(tectonic_path):
        print("Tectonic not found. Downloading engine...")
        try:
            url = "https://github.com/tectonic-typesetting/tectonic/releases/download/tectonic%400.15.0/tectonic-0.15.0-x86_64-unknown-linux-musl.tar.gz"
            subprocess.run(f"curl -L {url} | tar -xz", shell=True, check=True)
            st = os.stat(tectonic_path)
            os.chmod(tectonic_path, st.st_mode | stat.S_IEXEC)
            print("Tectonic downloaded.")
        except Exception as e:
            create_error_pdf(output_filename, f"Engine Download Failed: {str(e)}")
            return

    # 2. Build LaTeX Content
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
    
    % Compact layout
    \setlength{\parindent}{0pt}
    \setlength{\parskip}{0pt}
    \titlespacing*{\section}{0pt}{2pt}{2pt}
    \setlist[itemize]{noitemsep, topsep=0pt, leftmargin=*}

    \begin{document}
    \begin{multicols*}{3}
    \begin{center}
        \textbf{\LARGE MicroSheet AI}
    \end{center}
    \vspace{0.2cm}
    """

    for section in data:
        title = section.get('title', 'Section')
        content = section.get('content', '')
        
        # Apply Robust Sanitization
        safe_title = escape_latex(title)
        safe_content = escape_latex(content)
        
        latex_content += f"\\section*{{{safe_title}}}\n"
        latex_content += f"{safe_content}\n\n"

    latex_content += r"\end{multicols*} \end{document}"

    # 3. Save .tex file
    tex_filename = "temp.tex"
    with open(tex_filename, "w") as f:
        f.write(latex_content)

    # 4. Compile with Detailed Error Capture
    try:
        print("Compiling PDF...")
        # Capture stdout and stderr to see WHY it fails
        result = subprocess.run(
            [tectonic_path, tex_filename], 
            capture_output=True, 
            text=True
        )
        
        if result.returncode == 0 and os.path.exists("temp.pdf"):
            shutil.move("temp.pdf", output_filename)
            print(f"Success! PDF saved to {output_filename}")
        else:
            # If it fails, print the actual LaTeX error log
            print(f"Tectonic Failed. Log:\n{result.stderr}")
            # Send the last 500 characters of the error log to the PDF
            error_log = result.stderr[-800:] if result.stderr else "Unknown Error"
            raise Exception(f"LaTeX Error: {error_log}")
            
    except Exception as e:
        print(f"Compilation Exception: {e}")
        create_error_pdf(output_filename, str(e))

def create_error_pdf(filename, error_msg):
    from reportlab.pdfgen import canvas
    from reportlab.lib import colors
    c = canvas.Canvas(filename)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, 800, "PDF Generation Failed")
    c.setFont("Helvetica", 8)
    
    # Wrap text manually for the error log
    y = 780
    for line in error_msg.split('\n'):
        # Split long lines
        while len(line) > 90:
            c.drawString(50, y, line[:90])
            line = line[90:]
            y -= 12
        c.drawString(50, y, line)
        y -= 12
        if y < 50: break
        
    c.save()