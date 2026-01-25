"""
Markdown utility functions for KOReader Store
"""

import markdown
import re
from PyQt6.QtGui import QTextDocument


def convert_markdown_to_html(text):
    """Convert markdown to HTML for display in Qt widgets using proper markdown library"""
    if not text:
        return ""
    
    try:
        # Use proper markdown library with extensions for better security and functionality
        html = markdown.markdown(
            text, 
            extensions=[
                "fenced_code", 
                "tables", 
                "codehilite",
                "toc",
                "nl2br"
            ],
            extension_configs={
                'codehilite': {
                    'css_class': 'highlight',
                    'use_pygments': False
                }
            }
        )
        
        # Apply Qt-friendly styling with proper colors
        styled_html = apply_qt_styling(html)
        
        return styled_html
        
    except Exception as e:
        # Fallback to basic conversion if markdown library fails
        return f"<p>Error rendering markdown: {e}</p><pre>{text}</pre>"


def apply_qt_styling(html):
    """Apply Qt-friendly styling to markdown HTML"""
    # Style the HTML for better display in Qt widgets
    styled = f"""
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            font-size: 13px;
            line-height: 1.5;
            color: #374151;
            margin: 10px;
        }}
        
        h1, h2, h3, h4, h5, h6 {{
            color: #a78bfa;
            margin-top: 20px;
            margin-bottom: 10px;
            font-weight: 600;
        }}
        
        h1 {{ font-size: 20px; }}
        h2 {{ font-size: 18px; }}
        h3 {{ font-size: 16px; }}
        
        p {{
            margin: 10px 0;
            color: #374151;
        }}
        
        code {{
            background-color: #f3f4f6;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 12px;
            color: #1f2937;
            border: 1px solid #e5e7eb;
        }}
        
        pre {{
            background-color: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 12px;
            overflow-x: auto;
            margin: 10px 0;
        }}
        
        pre code {{
            background-color: transparent;
            padding: 0;
            border: none;
        }}
        
        blockquote {{
            border-left: 4px solid #a78bfa;
            margin: 15px 0;
            padding: 10px 20px;
            background-color: #f9fafb;
            color: #4b5563;
        }}
        
        ul, ol {{
            margin: 10px 0;
            padding-left: 30px;
            color: #374151;
        }}
        
        li {{
            margin: 5px 0;
        }}
        
        a {{
            color: #3b82f6;
            text-decoration: none;
        }}
        
        a:hover {{
            color: #2563eb;
            text-decoration: underline;
        }}
        
        table {{
            border-collapse: collapse;
            margin: 15px 0;
            width: 100%;
        }}
        
        th, td {{
            border: 1px solid #e5e7eb;
            padding: 8px 12px;
            text-align: left;
        }}
        
        th {{
            background-color: #f9fafb;
            font-weight: 600;
            color: #374151;
        }}
        
        img {{
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            margin: 10px 0;
        }}
        
        .highlight {{
            background-color: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 12px;
            overflow-x: auto;
            margin: 10px 0;
        }}
    </style>
    <body>
    {html}
    </body>
    """
    
    return styled


def extract_text_from_html(html):
    """Extract plain text from HTML for text-only operations"""
    if not html:
        return ""
    
    # Remove style tags first
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
    
    # Create a QTextDocument to render HTML to plain text
    doc = QTextDocument()
    doc.setHtml(html)
    return doc.toPlainText()
