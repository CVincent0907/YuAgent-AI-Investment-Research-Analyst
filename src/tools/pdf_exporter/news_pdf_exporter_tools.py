import os
import re
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
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
    if text.strip().startswith('* ') or text.strip().startswith('- '):
        text = text.replace('* ', '&bull; ', 1).replace('- ', '&bull; ', 1)
        
    return text

@traceable(name="Tool: Export News Report to PDF", run_type="tool")
def export_news_report_to_pdf(
    subject: str,
    title: str,
    analysis_summary: str,
    news_items: list,  # List of dicts: [{'title':.., 'source':.., 'date':.., 'summary':..}]
    output_filename: str = ""
) -> str:
    """
    Generates a professional report for News, Sentiment, or People Profiles.
    Saves the output in the 'output_pdf' directory.
    """
    print(f"\n[PDF News TOOL] Starting News Report for {subject}...")
    
    # 1. Directory Handling
    target_dir = "output_pdf/news"
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    if not output_filename:
        output_filename = f"{subject.upper()}_news_summary.pdf"
    
    # Clean filename
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
        
        # Professional Color Palette
        HEADER_COLOR = colors.HexColor("#2D3748") # Dark Slate
        META_COLOR = colors.HexColor("#718096")   # Medium Grey
        ACCENT_COLOR = colors.HexColor("#E2E8F0") # Light Grey for lines
        
        # 3. Custom Styles
        title_style = ParagraphStyle(
            'T', parent=styles['Heading1'], fontSize=22, textColor=HEADER_COLOR, spaceAfter=14
        )
        meta_style = ParagraphStyle(
            'Meta', parent=styles['Normal'], fontSize=8, textColor=META_COLOR, fontName='Helvetica-Oblique'
        )
        body_style = ParagraphStyle(
            'B', parent=styles['Normal'], fontSize=10, leading=14, spaceAfter=10
        )
        news_title_style = ParagraphStyle(
            'NT', parent=styles['Normal'], fontSize=11, fontName='Helvetica-Bold', spaceBefore=10, textColor=HEADER_COLOR
        )
        bullet_style = ParagraphStyle(
            'Bullet', parent=styles['Normal'], fontSize=10, leading=14, leftIndent=15, spaceAfter=5
        )

        # 4. Header Section
        story.append(Paragraph(markdown_to_reportlab(title), title_style))
        story.append(Paragraph(f"Subject: {subject} | Generated Research Briefing", meta_style))
        story.append(Spacer(1, 15))
        
        # 5. Analysis Summary Section
        story.append(Paragraph("<b>Analysis Summary</b>", styles['Heading3']))
        lines = analysis_summary.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            formatted_line = markdown_to_reportlab(line)
            if formatted_line.startswith('&bull;'):
                story.append(Paragraph(formatted_line, bullet_style))
            else:
                story.append(Paragraph(formatted_line, body_style))
        
        story.append(Spacer(1, 10))
        
        # Horizontal Divider
        story.append(HRFlowable(width="100%", thickness=1, color=ACCENT_COLOR, spaceBefore=5, spaceAfter=15))
        
        # 6. News Feed Section
        story.append(Paragraph("<b>Recent Developments & News Feed</b>", styles['Heading3']))
        
        for item in news_items:
            # Item Title
            story.append(Paragraph(markdown_to_reportlab(item.get('title', 'No Title')), news_title_style))
            
            # Item Metadata
            source = item.get('source', 'Unknown Source')
            date = item.get('date', 'Recent')
            story.append(Paragraph(f"Source: {source} | {date}", meta_style))
            
            # Item Summary
            summary = item.get('summary', '')
            if summary:
                story.append(Paragraph(markdown_to_reportlab(summary), body_style))
            
            story.append(Spacer(1, 5))

        # 7. Final Build
        doc.build(story)
        return f"SUCCESS: News report saved to {output_path}"

    except Exception as e:
        return f"ERROR: {str(e)}"

# --- TEST BLOCK ---
if __name__ == "__main__":
    # You can test the independent file by running: python src/tools/news_exporter.py
    sample_news = [
        {
            "title": "NVIDIA Blackwell Chips Face Server Overheating Issues",
            "source": "Reuters",
            "date": "Nov 18, 2024",
            "summary": "Reports suggest that the new AI chips are causing heat issues in high-capacity server racks, potentially delaying deployments."
        },
        {
            "title": "NVIDIA Q3 Earnings Preview: Analysts Expect Record Revenue",
            "source": "Bloomberg",
            "date": "Nov 17, 2024",
            "summary": "Wall Street expects another blowout quarter driven by relentless demand for H100 and H200 series GPUs."
        }
    ]
    
    test_summary = "**Market Outlook:** NVIDIA continues to dominate the AI landscape.\n* Demand exceeds supply.\n* New hardware cycles are imminent."
    
    msg = export_news_report_to_pdf(
        subject="NVIDIA",
        title="NVIDIA (NVDA) - Qualitative Market Brief",
        analysis_summary=test_summary,
        news_items=sample_news
    )
    print(msg)