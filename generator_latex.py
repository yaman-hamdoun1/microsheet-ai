import os
import subprocess
import shutil
import stat

def create_cheat_sheet(data, output_filename):
    """
    Generates PDF using local Tectonic engine on Render.
    """
    # 1. Setup Tectonic Path
    # We store it in the current directory so we have permission to execute it
    tectonic_path = os.path.abspath("tectonic")
    
    # 2. Check if engine is missing (It will be missing every time server wakes up)
    if not os.path.exists(tectonic_path):
        print("Tectonic not found. Downloading engine (this takes ~30s)...")
        try:
            # Download the Linux binary directly
            # This is the official static binary for Linux (Render uses Linux)
            url = "https://github.com/tectonic-typesetting/tectonic/releases/download/tectonic%400.15.0/tectonic-0.15.0-x86_64-unknown-linux-musl.tar.gz"
            subprocess.run(f"curl -L {url} | tar -xz", shell=True, check=True)
            
            # Make sure it is executable
            st = os.stat(tectonic_path)
            os.chmod(tectonic_path, st.st_mode | stat.S_IEXEC)
            
            print("Tectonic downloaded successfully.")
        except Exception as e:
            print(f"Failed to download Tectonic: {e}")
            create_error_pdf(output_filename, f"Could not install LaTeX engine: {str(e)}")
            return

    # 3. Construct the LaTeX Content (SANITIZED)
    # We still sanitize to be safe, even with local compilation
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

    % Compact spacing
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
        
        # Basic cleanup for LaTeX special chars
        # We replace # with \#, & with \&, etc.
        for char in ['#', '&', '%']:
            title = title.replace(char, f"\\{char}")
            content = content.replace(char, f"\\{char}")
        
        latex_content += f"\\section*{{{title}}}\n"
        latex_content += f"{content}\n\n"

    latex_content += r"\end{multicols*} \end{document}"

    # 4. Save .tex file
    tex_filename = "temp.tex"
    with open(tex_filename, "w") as f:
        f.write(latex_content)

    # 5. Compile
    try:
        print("Compiling PDF...")
        # Run Tectonic
        subprocess.run([tectonic_path, tex_filename], check=True)
        
        # Tectonic creates 'temp.pdf'. Rename it.
        if os.path.exists("temp.pdf"):
            shutil.move("temp.pdf", output_filename)
            print(f"Success! PDF saved to {output_filename}")
        else:
            raise Exception("PDF file was not created.")
            
    except Exception as e:
        print(f"Compilation Error: {e}")
        # Try to read the log if available
        error_detail = str(e)
        create_error_pdf(output_filename, f"LaTeX Compilation Failed: {error_detail}")

def create_error_pdf(filename, error_msg):
    from reportlab.pdfgen import canvas
    c = canvas.Canvas(filename)
    c.drawString(50, 800, "Error Generating PDF")
    c.drawString(50, 780, str(error_msg)[:100]) # Truncate long errors
    c.save()