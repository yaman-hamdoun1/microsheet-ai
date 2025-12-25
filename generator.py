from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY

def create_cheat_sheet(data, filename="cheatsheet.pdf"):
    print(f"Generating PDF: {filename}...")
    
    # 1. Document Setup
    doc = BaseDocTemplate(filename, pagesize=A4)
    
    # 2. Define Margins and Column Layout
    page_width, page_height = A4
    margin = 5 * mm
    column_gap = 2 * mm
    column_count = 3
    
    # Calculate column width
    effective_width = page_width - (2 * margin)
    col_width = (effective_width - ((column_count - 1) * column_gap)) / column_count
    
    # 3. Create Frames (The containers for text)
    frames = []
    for i in range(column_count):
        left_pos = margin + (i * (col_width + column_gap))
        # Frame(x, y, width, height) - y is from bottom up
        frame = Frame(left_pos, margin, col_width, page_height - (2 * margin), showBoundary=0)
        frames.append(frame)
    
    # 4. Create Page Template
    template = PageTemplate(id='3Column', frames=frames)
    doc.addPageTemplates([template])
    
    # 5. Define Styles (High Density)
    styles = []
    
    # Header Style (Bold, Tiny)
    header_style = ParagraphStyle(
        'Header',
        fontName='Helvetica-Bold',
        fontSize=7,
        leading=8, # Line spacing
        spaceAfter=2,
        textColor='black'
    )
    
    # Body Style (Regular, Micro)
    body_style = ParagraphStyle(
        'Body',
        fontName='Helvetica',
        fontSize=6,
        leading=7,
        alignment=TA_JUSTIFY, # Makes it look like a newspaper column
        spaceAfter=4
    )
    
    # 6. Build the Content Flow
    story = []
    
    for section in data:
        # Add Title
        story.append(Paragraph(section['title'].upper(), header_style))
        # Add Content (Convert newlines to <br/> for HTML-like rendering in ReportLab)
        formatted_content = section['content'].replace('\n', '<br/>')
        story.append(Paragraph(formatted_content, body_style))
        story.append(Spacer(1, 2)) # Tiny gap between sections

    # 7. Build
    doc.build(story)
    print("Success! PDF generated.")