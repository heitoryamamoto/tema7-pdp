"""
Converte documento_tecnico.md para documento_tecnico.pdf
Uso: python3 scripts/gerar_pdf.py
"""
import markdown
from weasyprint import HTML
import os

MD_FILE = "documento_tecnico.md"
PDF_FILE = "documento_tecnico.pdf"

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

@page {
    size: A4;
    margin: 2.5cm 2.5cm 2.5cm 2.5cm;
    @bottom-center {
        content: counter(page) " / " counter(pages);
        font-size: 10px;
        color: #888;
    }
}

body {
    font-family: 'Inter', Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.6;
    color: #1a1a1a;
}

h1 {
    font-size: 20pt;
    font-weight: 700;
    color: #1a1a2e;
    text-align: center;
    margin-bottom: 4px;
    border-bottom: 2px solid #1a1a2e;
    padding-bottom: 8px;
}

h2, h3 {
    font-size: 14pt;
    font-weight: 600;
    color: #1a1a2e;
    margin-top: 24px;
    margin-bottom: 8px;
}

h3 {
    font-size: 12pt;
    color: #2d4a7a;
    border-left: 3px solid #2d4a7a;
    padding-left: 8px;
}

p { margin: 8px 0; }

strong { color: #1a1a2e; }

code {
    font-family: 'Courier New', monospace;
    font-size: 9.5pt;
    background: #f4f4f8;
    padding: 1px 5px;
    border-radius: 3px;
    color: #c0392b;
}

pre {
    background: #f4f4f8;
    border: 1px solid #dde;
    border-left: 4px solid #2d4a7a;
    border-radius: 4px;
    padding: 12px 14px;
    overflow-x: auto;
    font-size: 9pt;
    line-height: 1.45;
}

pre code {
    background: none;
    padding: 0;
    color: #1a1a1a;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin: 16px 0;
    font-size: 10pt;
}

th {
    background: #1a1a2e;
    color: white;
    padding: 8px 10px;
    text-align: left;
    font-weight: 600;
}

td {
    padding: 7px 10px;
    border-bottom: 1px solid #dde;
}

tr:nth-child(even) td { background: #f8f8fc; }

hr {
    border: none;
    border-top: 1px solid #dde;
    margin: 24px 0;
}

blockquote {
    border-left: 4px solid #2d4a7a;
    margin: 0;
    padding: 8px 16px;
    background: #f0f4fa;
    color: #444;
}

ul, ol {
    margin: 8px 0;
    padding-left: 24px;
}

li { margin: 4px 0; }
"""

with open(MD_FILE, "r", encoding="utf-8") as f:
    md_content = f.read()

html_body = markdown.markdown(
    md_content,
    extensions=["tables", "fenced_code", "toc", "nl2br"]
)

html_full = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<style>{CSS}</style>
</head>
<body>
{html_body}
</body>
</html>"""

print(f"Gerando {PDF_FILE}...")
HTML(string=html_full, base_url=os.getcwd()).write_pdf(PDF_FILE)
print(f"PDF gerado: {PDF_FILE}")
