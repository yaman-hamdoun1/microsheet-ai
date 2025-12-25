import requests
import os

def create_cheat_sheet(data, output_filename):
    """
    Generates a PDF by sending LaTeX code to the LaTeXOnline API.
    """
    print("Generating LaTeX code...")

    # 1. Build the LaTeX String
    # We use a 2-column layout with tiny margins to maximize space
    latex_content = r"""
    \documentclass[10pt]{article}
    \usepackage[utf8]{inputenc}
    \usepackage[landscape, margin=0.5in]{geometry}
    \usepackage{multicol}
    \usepackage{amsmath}
    \usepackage{amssymb}
    \usepackage{enumitem}
    \usepackage{titlesec}

    % Tighten spacing
    \setlength{\parindent}{0pt}
    \setlength{\parskip}{0pt}
    \titlespacing*{\section}{0pt}{2pt}{2pt}

    \begin{document}
    \begin{multicols*}{3} % 3 Columns for maximum density
    \begin{center}
        \textbf{\LARGE MicroSheet AI Summary}
    \end{center}
    \vspace{0.2cm}
    """

    for section in data:
        title = section.get('title', 'Section').replace('_', ' ')
        content = section.get('content', '')
        
        # Add Section Title
        latex_content += f"\\section*{{{title}}}\n"
        
        # Add Content (Ensure line breaks are handled)
        latex_content += f"{content}\n\n"

    # Close document
    latex_content += r"""
    \end{multicols*}
    \end{document}
    """

    # 2. Send to LaTeXOnline API
    print("Sending to API for compilation...")
    url = "https://latexonline.cc/compile"
    
    try:
        # We send the LaTeX string as a file named 'main.tex'
        payload = {
            'text': latex_content
        }
        
        # Set a timeout of 30 seconds
        response = requests.post(url, data=payload, timeout=30)

        if response.status_code == 200:
            # 3. Save the PDF
            with open(output_filename, 'wb') as f:
                f.write(response.content)
            print(f"Success! PDF saved to {output_filename}")
        else:
            print(f"API Error: {response.status_code}")
            print(response.text)
            # Create a dummy file so the server doesn't crash on download
            create_error_pdf(output_filename, "API Compilation Failed")

    except Exception as e:
        print(f"Connection Error: {e}")
        create_error_pdf(output_filename, str(e))

def create_error_pdf(filename, error_msg):
    """Fallback: Creates a simple text file if API fails, so user gets SOMETHING."""
    from reportlab.pdfgen import canvas
    c = canvas.Canvas(filename)
    c.drawString(100, 800, "PDF Generation Error")
    c.drawString(100, 780, "The LaTeX API could not compile your document.")
    c.drawString(100, 760, f"Error: {error_msg}")
    c.save()