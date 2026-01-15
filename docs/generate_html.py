#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Génère une version HTML du guide utilisateur Potting Management
"""

import markdown
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
GUIDE_MD = SCRIPT_DIR / "GUIDE_UTILISATEUR.md"
OUTPUT_HTML = SCRIPT_DIR / "GUIDE_UTILISATEUR.html"

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Guide Utilisateur - Module Potting Management</title>
    <style>
        @media print {{
            body {{ margin: 0; padding: 20px; }}
            .no-print {{ display: none; }}
            h1 {{ page-break-before: always; }}
            h1:first-of-type {{ page-break-before: avoid; }}
        }}
        
        * {{ box-sizing: border-box; }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 900px;
            margin: 0 auto;
            padding: 40px 20px;
            background: #f9f9f9;
        }}
        
        .container {{
            background: white;
            padding: 40px 60px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        
        /* Couverture */
        .cover {{
            text-align: center;
            padding: 80px 20px;
            margin-bottom: 40px;
            border-bottom: 3px solid #6c4f3d;
        }}
        
        .cover-logo {{
            width: 100px;
            height: 100px;
            background: linear-gradient(135deg, #8b5e3c, #6c4f3d);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 30px;
            color: white;
            font-size: 28px;
            font-weight: bold;
        }}
        
        .cover h1 {{
            color: #6c4f3d;
            font-size: 2.5em;
            margin: 0 0 10px;
        }}
        
        .cover h2 {{
            color: #8b5e3c;
            font-size: 1.5em;
            font-weight: normal;
            margin: 0 0 30px;
        }}
        
        .cover .meta {{
            color: #888;
            font-size: 0.95em;
        }}
        
        /* Titres */
        h1 {{
            color: #6c4f3d;
            border-bottom: 2px solid #6c4f3d;
            padding-bottom: 10px;
            margin-top: 50px;
        }}
        
        h2 {{
            color: #8b5e3c;
            margin-top: 35px;
        }}
        
        h3 {{
            color: #5a4231;
            margin-top: 25px;
        }}
        
        h4 {{
            color: #666;
            margin-top: 20px;
        }}
        
        /* Tableaux */
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 0.95em;
        }}
        
        th, td {{
            border: 1px solid #ddd;
            padding: 12px 15px;
            text-align: left;
        }}
        
        th {{
            background: #f5f2f0;
            color: #5a4231;
            font-weight: 600;
        }}
        
        tr:nth-child(even) {{
            background: #fafafa;
        }}
        
        tr:hover {{
            background: #f5f2f0;
        }}
        
        /* Listes */
        ul, ol {{
            padding-left: 25px;
        }}
        
        li {{
            margin: 8px 0;
        }}
        
        /* Code */
        code {{
            background: #f4f4f4;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 0.9em;
            color: #6c4f3d;
        }}
        
        pre {{
            background: #2d2d2d;
            color: #f8f8f2;
            padding: 20px;
            border-radius: 8px;
            overflow-x: auto;
        }}
        
        pre code {{
            background: none;
            color: inherit;
            padding: 0;
        }}
        
        /* Citations */
        blockquote {{
            border-left: 4px solid #8b5e3c;
            margin: 20px 0;
            padding: 15px 20px;
            background: #faf7f5;
            font-style: italic;
            color: #666;
        }}
        
        /* Liens */
        a {{
            color: #6c4f3d;
            text-decoration: none;
        }}
        
        a:hover {{
            text-decoration: underline;
        }}
        
        /* Info boxes */
        .info-box {{
            padding: 15px 20px;
            border-radius: 8px;
            margin: 20px 0;
        }}
        
        .info-box.warning {{
            background: #fff3cd;
            border-left: 4px solid #ffc107;
        }}
        
        .info-box.info {{
            background: #d1ecf1;
            border-left: 4px solid #17a2b8;
        }}
        
        .info-box.success {{
            background: #d4edda;
            border-left: 4px solid #28a745;
        }}
        
        /* Bouton impression */
        .print-btn {{
            position: fixed;
            top: 20px;
            right: 20px;
            background: #6c4f3d;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 25px;
            cursor: pointer;
            font-size: 14px;
            box-shadow: 0 2px 10px rgba(108, 79, 61, 0.3);
            z-index: 1000;
        }}
        
        .print-btn:hover {{
            background: #5a4231;
        }}
        
        /* Footer */
        .footer {{
            margin-top: 60px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            text-align: center;
            color: #888;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <button class="print-btn no-print" onclick="window.print()">📄 Imprimer / PDF</button>
    
    <div class="container">
        <div class="cover">
            <div class="cover-logo">☕</div>
            <h1>Module Potting Management</h1>
            <h2>Guide Utilisateur</h2>
            <p>Gestion des Exportations de Cacao<br>Réglementation CCC - Côte d'Ivoire</p>
            <div class="meta">
                <p>Version 17.0.1.3.0 | Janvier 2026</p>
                <p>Odoo 17 Community/Enterprise</p>
            </div>
        </div>
        
        {content}
        
        <div class="footer">
            <p>© ICP - Module Potting Management pour Odoo 17</p>
            <p>Documentation générée automatiquement</p>
        </div>
    </div>
</body>
</html>
"""


def main():
    print("Lecture du Guide Utilisateur Potting Management...")
    
    if not GUIDE_MD.exists():
        print(f"ERREUR: Fichier non trouvé: {GUIDE_MD}")
        return False
    
    md_content = GUIDE_MD.read_text(encoding='utf-8')
    print(f"Fichier lu: {len(md_content)} caractères")
    
    # Conversion Markdown -> HTML
    print("Conversion en HTML...")
    md = markdown.Markdown(extensions=['tables', 'fenced_code', 'toc'])
    html_content = md.convert(md_content)
    
    # Génération du HTML final
    final_html = HTML_TEMPLATE.format(content=html_content)
    
    # Écriture du fichier
    OUTPUT_HTML.write_text(final_html, encoding='utf-8')
    print(f"✅ HTML généré: {OUTPUT_HTML}")
    print()
    print("Pour générer le PDF:")
    print(f"  1. Ouvrir le fichier HTML dans un navigateur:")
    print(f"     open \"{OUTPUT_HTML}\"")
    print("  2. Cliquer sur 'Imprimer / PDF' ou Cmd+P")
    print("  3. Sélectionner 'Enregistrer en PDF'")
    
    return True


if __name__ == '__main__':
    main()
