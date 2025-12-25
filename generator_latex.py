import os
import subprocess
import shutil
import stat
import re

def escape_latex(text):
    """
    Robustly escapes special LaTeX characters while preserving Math Mode ($...$).
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
    
    parts = text.split('$')
    escaped_parts = []
    
    for i, part in enumerate(parts):
        if i % 2 == 0: 
            # Normal Text -> Escape
            for char, escaped in chars.items():
                part = part.replace(char, escaped)
            escaped_parts.append(part)
        else:
            # Math Mode -> Keep raw
            escaped_parts.append(f"${part}$")
            
    return "".join(escaped_parts)

def get_smart_template(total_chars):
    """
    Selects the perfect layout based on content density.
    """
    print(f"Analyzing layout for {total_chars} chars...")
    
    # TIER 1: LIGHT (< 2500 chars) -> Large Font, 2 Cols
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
\usepackage{microtype}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{hyperref}

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
    # TIER 2: MEDIUM (< 5000 chars) -> Medium Font, 3 Cols
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
\usepackage{microtype}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{hyperref}

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
    # TIER 3: HEAVY (> 5000 chars) -> Tiny Font, 3 Cols (High Density)
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
\usepackage{microtype}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{hyperref}

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

    # 2. Build LaTeX Body using Smart Layouts
    try:
        # Calculate density
        total_chars = sum(len(s.get('content', '')) for s in data)
        latex_template = get_smart_template(total_chars)
        
        latex_body = ""
        for section in data:
            # Use robust sanitizer
            title = escape_latex(section.get('title', 'Section'))
            content = escape_latex(section.get('content', ''))
            latex_body += f"\\section*{{{title}}}\n{content}\n\n"
        
        full_latex = latex_template.replace("% CONTENT_PLACEHOLDER", latex_body)
        
        # 3. Save .tex File
        tex_filename = "cheatsheet.tex"
        with open(tex_filename, "w", encoding="utf-8") as f:
            f.write(full_latex)
            
        # 4. Compile with Tectonic
        print(f"Compiling with Tectonic (Size: {total_chars} chars)...")
        
        result = subprocess.run(
            [tectonic_path, tex_filename], 
            capture_output=True, 
            text=True
        )
        
        if result.returncode == 0 and os.path.exists("cheatsheet.pdf"):
            shutil.move("cheatsheet.pdf", output_filename)
            print(f"Success! Saved to {output_filename}")
        else:
            # If failed, log the error to the PDF so we can read it
            error_log = result.stderr[-1000:] if result.stderr else "Unknown Error"
            print(f"Tectonic Error Log: {error_log}")
            raise Exception(f"LaTeX Error: {error_log}")

    except Exception as e:
        print(f"Generation Error: {e}")
        create_error_pdf(output_filename, str(e))

def create_error_pdf(filename, error_msg):
    from reportlab.pdfgen import canvas
    c = canvas.Canvas(filename)
    c.drawString(50, 800, "PDF Generation Failed")
    c.drawString(50, 780, "Error details:")
    
    text = c.beginText(50, 760)
    text.setFont("Helvetica", 8)
    # Simple wrap
    for line in error_msg.split('\n'):
        while len(line) > 100:
            text.textLine(line[:100])
            line = line[100:]
        text.textLine(line)
    c.drawText(text)
    c.save()