import os
import subprocess
import shutil
import stat
import re

def escape_latex(text):
    """
    Simpler, more robust sanitizer based on your original local code.
    It escapes key characters everywhere to prevent crashes.
    """
    if not text:
        return ""
    
    # 1. Escape the "Crashers" (Characters that break compilation immediately)
    # We use Regex negative lookbehind (?<!\\) to ensure we don't double-escape
    text = re.sub(r'(?<!\\)&', r'\&', text)  # Fixes the "alignment tab" error
    text = re.sub(r'(?<!\\)%', r'\%', text)  # Fixes comments disappearing
    text = re.sub(r'(?<!\\)#', r'\#', text)  # Fixes macro errors
    
    # 2. Fix common AI markdown issues
    # Convert bold **text** to \textbf{text}
    text = re.sub(r'\*\*(.*?)\*\*', r'\\textbf{\1}', text)
    
    return text

def get_smart_template(total_chars):
    """
    Returns the appropriate LaTeX header based on text length.
    """
    print(f"Selecting template for {total_chars} chars...")
    
    # TIER 1: Light Content -> Readable Font, 2 Columns
    if total_chars < 2500:
        return r"""
\documentclass[10pt, landscape]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\usepackage[margin=1.2cm]{geometry}
\usepackage{multicol}
\usepackage{titlesec}
\usepackage{enumitem}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{microtype}

\setlength{\parindent}{0pt}
\setlist{nosep}
\newcommand{\mysep}{\vspace{4pt}\hrule height 0.5pt \vspace{6pt}}
\titleformat{\section}{\Large\bfseries\sffamily}{}{0em}{}[\mysep]

\begin{document}
\begin{multicols*}{2}
% CONTENT_PLACEHOLDER
\end{multicols*}
\end{document}
"""
    # TIER 2: Medium Content -> Standard Font, 3 Columns
    elif total_chars < 5000:
        return r"""
\documentclass[8pt, landscape]{extarticle}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\usepackage[margin=0.8cm]{geometry}
\usepackage{multicol}
\usepackage{titlesec}
\usepackage{enumitem}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{microtype}

\setlength{\parindent}{0pt}
\setlist{nosep}
\newcommand{\mysep}{\vspace{2pt}\hrule height 0.3pt \vspace{4pt}}
\titleformat{\section}{\large\bfseries\sffamily}{}{0em}{}[\mysep]

\begin{document}
\begin{multicols*}{3}
% CONTENT_PLACEHOLDER
\end{multicols*}
\end{document}
"""
    # TIER 3: Heavy Content -> Small Font, High Density
    else:
        return r"""
\documentclass[6pt, landscape]{extarticle}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\usepackage[margin=0.4cm]{geometry}
\usepackage{multicol}
\usepackage{titlesec}
\usepackage{enumitem}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{microtype}

\setlength{\parindent}{0pt}
\setlist{nosep}
\newcommand{\mysep}{\vspace{1pt}\hrule height 0.1pt \vspace{2pt}}
\titleformat{\section}{\bfseries\scriptsize\uppercase}{}{0em}{}[\mysep]

\begin{document}
\tiny 
\begin{multicols*}{3}
% CONTENT_PLACEHOLDER
\end{multicols*}
\end{document}
"""

def create_cheat_sheet(data, output_filename):
    # 1. Setup Tectonic Engine
    tectonic_path = os.path.abspath("tectonic")
    
    if not os.path.exists(tectonic_path):
        print("Downloading Tectonic engine...")
        try:
            url = "https://github.com/tectonic-typesetting/tectonic/releases/download/tectonic%400.15.0/tectonic-0.15.0-x86_64-unknown-linux-musl.tar.gz"
            subprocess.run(f"curl -L {url} | tar -xz", shell=True, check=True)
            st = os.stat(tectonic_path)
            os.chmod(tectonic_path, st.st_mode | stat.S_IEXEC)
        except Exception as e:
            create_error_pdf(output_filename, f"Engine Download Failed: {e}")
            return

    # 2. Build LaTeX Body
    try:
        total_chars = sum(len(s.get('content', '')) for s in data)
        latex_template = get_smart_template(total_chars)
        
        latex_body = ""
        for section in data:
            # Use the safer Regex sanitizer
            title = escape_latex(section.get('title', 'Section'))
            content = escape_latex(section.get('content', ''))
            latex_body += f"\\section*{{{title}}}\n{content}\n\n"
        
        full_latex = latex_template.replace("% CONTENT_PLACEHOLDER", latex_body)
        
        # 3. Save .tex File
        tex_filename = "cheatsheet.tex"
        with open(tex_filename, "w", encoding="utf-8") as f:
            f.write(full_latex)
            
        # 4. Compile with Tectonic
        # We add 'pass-tex-errors' to help debug if it fails, but Tectonic is generally robust
        print(f"Compiling... ({total_chars} chars)")
        
        result = subprocess.run(
            [tectonic_path, tex_filename], 
            capture_output=True, 
            text=True
        )
        
        if result.returncode == 0 and os.path.exists("cheatsheet.pdf"):
            shutil.move("cheatsheet.pdf", output_filename)
            print(f"Success! Saved to {output_filename}")
        else:
            # Log the error clearly
            error_log = result.stderr[-1000:] if result.stderr else "Unknown Error"
            print(f"Tectonic Error: {error_log}")
            raise Exception(f"LaTeX Error: {error_log}")

    except Exception as e:
        print(f"Generation Error: {e}")
        # Create a simple fallback PDF with the error message
        create_error_pdf(output_filename, str(e))

def create_error_pdf(filename, error_msg):
    from reportlab.pdfgen import canvas
    c = canvas.Canvas(filename)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, 800, "PDF Generation Failed")
    c.setFont("Helvetica", 10)
    c.drawString(50, 780, "Error details:")
    
    text_obj = c.beginText(50, 760)
    text_obj.setFont("Helvetica", 8)
    
    # Wrap text roughly
    lines = error_msg.split('\n')
    for line in lines:
        while len(line) > 100:
            text_obj.textLine(line[:100])
            line = line[100:]
        text_obj.textLine(line)
        
    c.drawText(text_obj)
    c.save()