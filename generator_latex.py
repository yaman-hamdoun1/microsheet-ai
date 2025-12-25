import os
import subprocess
import re

def sanitize_latex(text):
    if not text: return ""
    text = re.sub(r'(?<!\\)%', r'\%', text)
    text = re.sub(r'(?<!\\)&', r'\&', text)
    return text

def get_smart_template(total_chars):
    print(f"Analyzing layout for {total_chars} chars...")
    
    # TIER 1: LIGHT (< 2500 chars)
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
    # TIER 2: MEDIUM (< 5000 chars)
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
    # TIER 3: HEAVY (> 5000 chars)
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

def create_cheat_sheet(data, filename="cheatsheet.pdf"):
    print(f"Generating LaTeX PDF: {filename}...")
    total_chars = sum(len(s.get('content', '')) for s in data)
    latex_template = get_smart_template(total_chars)
    
    latex_body = ""
    for section in data:
        title = sanitize_latex(section.get('title', ''))
        content = sanitize_latex(section.get('content', ''))
        latex_body += f"\\section*{{{title}}}\n{content}\n\n"
        
    full_latex = latex_template.replace("% CONTENT_PLACEHOLDER", latex_body)
    
    tex_filename = filename.replace(".pdf", ".tex")
    with open(tex_filename, "w", encoding="utf-8") as f:
        f.write(full_latex)
        
    # --- THE FIX IS HERE ---
    output_dir = os.path.dirname(filename)
    if not output_dir: output_dir = "." 
    
    try:
        subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", f"-output-directory={output_dir}", tex_filename], 
            check=True,
            stdout=subprocess.DEVNULL
        )
        print("Success! LaTeX compiled.")
        
    except subprocess.CalledProcessError:
        print("Error: LaTeX compilation failed.")
        log_file = tex_filename.replace(".tex", ".log")
        if os.path.exists(log_file):
            os.system(f'tail -n 20 {log_file}')