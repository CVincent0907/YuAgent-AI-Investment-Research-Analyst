import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from langsmith import traceable

@traceable(name="Tool: Export Findings to PDF", run_type="tool")
def export_findings_to_pdf(
    ticker: str,
    title: str,
    explanation: str,
    tables_data: dict,
    output_filename: str = ""
) -> str:
    """
    Generates a professional financial analysis report and saves it in the 'output_pdf' folder.
    """
    # 1. Directory Handling: Ensure 'output_pdf' exists in project root
    target_dir = "output_pdf"
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    if not output_filename:
        output_filename = f"{ticker.upper()}_financial_analysis_report.pdf"
        
    output_path = os.path.abspath(os.path.join(target_dir, output_filename))
    
    try:
        # 2. Setup Document Template
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=inch*0.75,
            leftMargin=inch*0.75,
            topMargin=inch*0.75,
            bottomMargin=inch*0.75
        )
        
        story = []
        styles = getSampleStyleSheet()
        
        # --- 3. Professional Financial Color Palette ---
        PRIMARY_NAVY = colors.HexColor("#1A365D")   # Deep professional navy
        SECONDARY_SLATE = colors.HexColor("#4A5568") # Subtle slate for subtitles
        ACCENT_BLUE = colors.HexColor("#3182CE")    # Bright blue for borders/accents
        BG_LIGHT = colors.HexColor("#F7FAFC")       # Light grey for zebra-striping
        TEXT_DARK = colors.HexColor("#2D3748")      # Soft black for readability
        
        # --- 4. Custom Paragraph Styles ---
        title_style = ParagraphStyle(
            'ReportTitle', parent=styles['Heading1'],
            fontName='Helvetica-Bold', fontSize=24, textColor=PRIMARY_NAVY,
            spaceAfter=12
        )
        
        subtitle_style = ParagraphStyle(
            'ReportSubtitle', parent=styles['Normal'],
            fontName='Helvetica-Oblique', fontSize=10, textColor=SECONDARY_SLATE,
            spaceAfter=30
        )
        
        section_style = ParagraphStyle(
            'SectionHeading', parent=styles['Heading2'],
            fontName='Helvetica-Bold', fontSize=14, textColor=PRIMARY_NAVY,
            spaceBefore=20, spaceAfter=10, borderPadding=5,
            borderWidth=0, borderBottomWidth=1, borderColor=ACCENT_BLUE
        )
        
        body_style = ParagraphStyle(
            'ReportBody', parent=styles['Normal'],
            fontName='Helvetica', fontSize=10, leading=14,
            textColor=TEXT_DARK, spaceAfter=10
        )

        table_header_style = ParagraphStyle(
            'TableHeader', parent=styles['Normal'],
            fontName='Helvetica-Bold', fontSize=9, textColor=colors.white,
            alignment=1 # Centered
        )

        table_cell_style = ParagraphStyle(
            'TableCell', parent=styles['Normal'],
            fontName='Helvetica', fontSize=9, textColor=TEXT_DARK
        )

        # --- 5. Add Content to Story ---
        # Title Block
        story.append(Paragraph(title, title_style))
        story.append(Paragraph(
            f"Ticker: {ticker.upper()} | Model Generated via Agentic RAG | Date: 2024 Analysis", 
            subtitle_style
        ))
        
        # Executive Summary Section
        story.append(Paragraph("Executive Summary & Analysis Narrative", section_style))
        
        # Correct Paragraph Splitting: Handle double newlines as distinct paragraph blocks
        paragraphs = [p.strip() for p in explanation.split('\n') if p.strip()]
        for p_text in paragraphs:
            story.append(Paragraph(p_text, body_style))
            
        story.append(Spacer(1, 20))
        
        # Financial Data Tables Section
        if tables_data:
            story.append(Paragraph("Quantitative Modeling and Historical Data", section_style))
            
            for table_title, rows in tables_data.items():
                story.append(Paragraph(table_title, ParagraphStyle(
                    'TableTitle', parent=styles['Normal'], fontName='Helvetica-Bold', 
                    fontSize=11, textColor=SECONDARY_SLATE, spaceBefore=10, spaceAfter=5
                )))
                
                # Format table cells (Wrapping text in Paragraphs ensures columns don't overflow)
                formatted_rows = []
                for r_idx, row in enumerate(rows):
                    formatted_row = []
                    for cell in row:
                        style = table_header_style if r_idx == 0 else table_cell_style
                        formatted_row.append(Paragraph(str(cell), style))
                    formatted_rows.append(formatted_row)
                
                # Auto-calculate colWidths (Proportional to page width)
                available_width = doc.width
                num_cols = len(rows[0]) if rows else 1
                col_widths = [available_width / num_cols] * num_cols
                
                t = Table(formatted_rows, colWidths=col_widths, repeatRows=1)
                
                # Professional Table Styling
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_NAVY),      # Header Background
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),       # Header Text
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('BOX', (0, 0), (-1, -1), 0.75, PRIMARY_NAVY),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, BG_LIGHT]) # Zebra stripes
                ]))
                
                story.append(t)
                story.append(Spacer(1, 15))
                
        # 6. Build PDF
        doc.build(story)
        
        return f"SUCCESS: Report saved to {output_path}"
        
    except Exception as e:
        return f"ERROR generating PDF: {str(e)}"