import os
import re # Added for markdown conversion
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from langsmith import traceable

def markdown_to_reportlab(text: str) -> str:
    """
    Converts standard Markdown (bold, bullets) into ReportLab-compatible XML tags.
    """
    # 1. Convert **bold** to <b>bold</b>
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    
    # 2. Convert bullet points (* or -) to indented bullet symbols
    # This handles lines starting with '* ' or '- '
    if text.strip().startswith('* ') or text.strip().startswith('- '):
        text = text.replace('* ', '&bull; ', 1).replace('- ', '&bull; ', 1)
        
    return text

@traceable(name="Tool: Export Financials to PDF", run_type="tool")
def export_financial_findings_to_pdf(
    ticker: str,
    title: str,
    explanation: str,
    tables_data: dict,
    output_filename: str = ""
) -> str:
    """
    Generates a professional financial analysis report with support for bold and bullet formatting.
    """
    print(f"\n[PDF Financials TOOL] Starting PDF generation for {ticker}...")
    
    # 1. Directory Handling
    target_dir = "output_pdf/financials"
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    if not output_filename:
        output_filename = f"{ticker.upper()}_financial_analysis_report.pdf"
    
    output_filename = output_filename.replace(" ", "_").replace("/", "_")
    output_path = os.path.abspath(os.path.join(target_dir, output_filename))
    
    try:
        # 2. Setup Document
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=inch*0.5,
            leftMargin=inch*0.5,
            topMargin=inch*0.5,
            bottomMargin=inch*0.5
        )
        
        story = []
        styles = getSampleStyleSheet()
        
        # Financial Palette
        PRIMARY_NAVY = colors.HexColor("#1A365D")
        BG_LIGHT = colors.HexColor("#F7FAFC")
        
        # Styles
        title_style = ParagraphStyle(
            'T', parent=styles['Heading1'], fontSize=22, textColor=PRIMARY_NAVY, spaceAfter=12
        )
        body_style = ParagraphStyle(
            'B', parent=styles['Normal'], fontSize=10, leading=14, alignment=0 # 0=Left, 4=Justified
        )
        bullet_style = ParagraphStyle(
            'Bullet', parent=styles['Normal'], fontSize=10, leading=14, leftIndent=15, spaceAfter=5
        )
        header_style = ParagraphStyle(
            'H', parent=styles['Normal'], fontSize=9, textColor=colors.white, fontName='Helvetica-Bold', alignment=1
        )

        # 3. Add Header
        story.append(Paragraph(markdown_to_reportlab(title), title_style))
        story.append(Spacer(1, 10))
        
        # 4. Add Narrative (Explanation)
        # We split by line to detect bullet points vs normal paragraphs
        lines = explanation.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                story.append(Spacer(1, 6))
                continue
            
            # Convert Markdown to XML tags
            formatted_text = markdown_to_reportlab(line)
            
            # Apply bullet style if it's a bullet, otherwise normal body
            if formatted_text.startswith('&bull;'):
                story.append(Paragraph(formatted_text, bullet_style))
            else:
                story.append(Paragraph(formatted_text, body_style))

        # 5. Add Tables
        if tables_data:
            for t_title, rows in tables_data.items():
                story.append(Spacer(1, 15))
                story.append(Paragraph(f"<b>{t_title}</b>", styles['Heading3']))
                story.append(Spacer(1, 5))
                
                formatted_rows = []
                for r_idx, row in enumerate(rows):
                    formatted_row = []
                    for cell in row:
                        # Also support bolding inside table cells
                        cell_content = markdown_to_reportlab(str(cell))
                        p_cell = Paragraph(cell_content, header_style if r_idx == 0 else body_style)
                        formatted_row.append(p_cell)
                    formatted_rows.append(formatted_row)

                # Ensure columns are balanced
                col_widths = [doc.width/len(rows[0])] * len(rows[0])
                t = Table(formatted_rows, colWidths=col_widths)
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_NAVY),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, BG_LIGHT])
                ]))
                story.append(t)

        # 6. Build File
        doc.build(story)
        return f"SUCCESS: Report saved to {output_path}"

    except Exception as e:
        return f"ERROR generating PDF: {str(e)}"