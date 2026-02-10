#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script professionnel pour générer le PDF du workflow d'exportation ICP
Version 4.0 - Correction complète des troncatures - Février 2026
"""

import sys
sys.path.insert(0, '/Users/ddma/Library/Python/3.9/lib/python/site-packages')

import re
from pathlib import Path
from datetime import datetime

try:
    from fpdf import FPDF
except ImportError:
    print("Installation de fpdf2...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "fpdf2"])
    from fpdf import FPDF

SCRIPT_DIR = Path('/Users/ddma/Desktop/icp/projects/odoo_seventeen/icp/potting_management/docs')
WORKFLOW_MD = SCRIPT_DIR / 'WORKFLOW_ACTEURS_V2.md'
OUTPUT_PDF = SCRIPT_DIR / 'WORKFLOW_ACTEURS_V2.pdf'

# Couleurs ICP
COLOR_PRIMARY = (31, 73, 125)
COLOR_SECONDARY = (68, 114, 196)
COLOR_ACCENT = (146, 89, 33)
COLOR_TEXT = (33, 33, 33)
COLOR_LIGHT_BG = (248, 249, 250)


def safe_latin1(text):
    """Convertit le texte en caractères latin-1 compatibles sans perdre de sens"""
    if not text:
        return ""
    
    # Mapping étendu pour les caractères spéciaux
    char_map = {
        # Caractères de dessin de boîte
        '─': '-', '━': '-', '│': '|', '┃': '|',
        '┌': '+', '┐': '+', '└': '+', '┘': '+',
        '├': '+', '┤': '+', '┬': '+', '┴': '+', '┼': '+',
        '═': '=', '║': '|', '╔': '+', '╗': '+', '╚': '+', '╝': '+',
        '╠': '+', '╣': '+', '╦': '+', '╩': '+', '╬': '+',
        '╭': '+', '╮': '+', '╯': '+', '╰': '+',
        # Flèches
        '▶': '>', '▷': '>', '►': '>', '→': '->', '⟶': '->',
        '◀': '<', '◁': '<', '◄': '<', '←': '<-', '⟵': '<-',
        '▼': 'v', '▽': 'v', '↓': 'v',
        '▲': '^', '△': '^', '↑': '^',
        # Puces et symboles
        '•': '*', '●': '*', '○': 'o', '◦': '-',
        '■': '#', '□': '[ ]', '▪': '*', '▫': '-',
        '✓': '[x]', '✔': '[x]', '✗': '[ ]', '✘': '[ ]',
        # Guillemets et apostrophes
        ''': "'", ''': "'", '"': '"', '"': '"',
        '«': '"', '»': '"',
        # Tirets
        '–': '-', '—': '-', '−': '-',
        # Autres
        '…': '...', '′': "'", '″': '"',
        '×': 'x', '÷': '/', '±': '+/-',
        '≤': '<=', '≥': '>=', '≠': '!=', '≈': '~',
    }
    
    result = []
    for char in text:
        if ord(char) < 256:
            result.append(char)
        elif char in char_map:
            result.append(char_map[char])
        else:
            # Pour les autres caractères Unicode, essayer de les translittérer
            result.append(' ')
    
    return ''.join(result)


def clean_markdown(text):
    """Nettoie le formatage markdown tout en préservant le texte"""
    if not text:
        return ""
    
    # Supprimer les emojis
    text = re.sub(r'[\U0001F300-\U0001F9FF\u2600-\u26FF\u2700-\u27BF]+', '', text)
    
    # Convertir le markdown en texte simple
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # Bold -> normal
    text = re.sub(r'\*([^*]+)\*', r'\1', text)       # Italic -> normal
    text = re.sub(r'`([^`]+)`', r'\1', text)         # Code -> normal
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)  # Links -> texte seul
    
    # Convertir en latin-1
    return safe_latin1(text).strip()


class WorkflowPDF(FPDF):
    """Générateur PDF sans troncature"""
    
    def __init__(self):
        super().__init__()
        # Définir les marges explicitement: gauche=10, haut=10, droite=10
        self.set_margins(10, 10, 10)
        self.current_chapter = ""
        self.skip_header = False
        
    def header(self):
        if self.page_no() > 1 and not self.skip_header:
            self.set_y(10)  # Position fixe en haut
            self.set_x(10)
            self.set_font('Helvetica', 'I', 8)
            self.set_text_color(*COLOR_SECONDARY)
            # Tronquer le chapitre à 40 caractères max pour éviter débordement
            chapter = clean_markdown(self.current_chapter)[:40]
            self.cell(90, 6, 'ICP - Guide du Workflow', align='L')
            self.cell(90, 6, chapter, align='R')
            # Ligne SOUS le texte (y = position actuelle + marge)
            line_y = self.get_y() + 8
            self.set_draw_color(*COLOR_PRIMARY)
            self.line(10, line_y, 200, line_y)
            self.set_y(line_y + 5)  # Positionner le contenu sous la ligne
    
    def footer(self):
        if self.page_no() > 1:
            self.set_y(-12)
            self.set_draw_color(*COLOR_PRIMARY)
            self.line(10, self.get_y(), 200, self.get_y())
            self.set_font('Helvetica', '', 8)
            self.set_text_color(*COLOR_TEXT)
            self.cell(0, 10, f'Page {self.page_no()}', align='C')
    
    def need_page_break(self, height=15):
        """Vérifie si un saut de page est nécessaire"""
        return self.get_y() + height > 275
    
    def write_cover(self):
        """Page de couverture"""
        self.skip_header = True
        self.add_page()
        
        # Bandeau bleu
        self.set_fill_color(*COLOR_PRIMARY)
        self.rect(0, 0, 210, 75, 'F')
        
        # Titre ICP
        self.set_font('Helvetica', 'B', 48)
        self.set_text_color(255, 255, 255)
        self.set_xy(0, 20)
        self.cell(210, 20, 'ICP', align='C')
        
        self.set_font('Helvetica', '', 14)
        self.set_xy(0, 45)
        self.cell(210, 10, 'Ivory Cocoa Products', align='C')
        
        # Titre du document
        self.set_font('Helvetica', 'B', 26)
        self.set_text_color(*COLOR_PRIMARY)
        self.set_xy(0, 95)
        self.cell(210, 12, 'GUIDE COMPLET DU WORKFLOW', align='C')
        self.set_xy(0, 112)
        self.cell(210, 12, "D'EXPORTATION", align='C')
        
        # Sous-titre
        self.set_font('Helvetica', '', 14)
        self.set_text_color(*COLOR_SECONDARY)
        self.set_xy(0, 135)
        self.cell(210, 10, 'Module Potting Management', align='C')
        
        # Ligne décorative
        self.set_draw_color(*COLOR_ACCENT)
        self.set_line_width(2)
        self.line(70, 155, 140, 155)
        
        # Description
        self.set_font('Helvetica', 'I', 11)
        self.set_text_color(*COLOR_TEXT)
        self.set_xy(25, 170)
        self.multi_cell(160, 6, 
            "Ce document decrit le processus complet d'exportation des produits "
            "semi-finis du cacao, les acteurs impliques et leurs responsabilites "
            "au sein du module Potting Management.",
            align='C')
        
        # Encadré version
        self.set_fill_color(*COLOR_LIGHT_BG)
        self.rect(55, 210, 100, 35, 'F')
        self.set_font('Helvetica', '', 10)
        self.set_text_color(*COLOR_TEXT)
        self.set_xy(55, 215)
        self.cell(100, 6, 'Version 4.0 - Fevrier 2026', align='C')
        self.set_xy(55, 223)
        self.cell(100, 6, 'Document interne ICP', align='C')
        self.set_xy(55, 231)
        self.cell(100, 6, 'Module Odoo 17', align='C')
        
        self.skip_header = False
    
    def write_toc(self):
        """Table des matières"""
        self.skip_header = True
        self.add_page()
        
        self.set_font('Helvetica', 'B', 18)
        self.set_text_color(*COLOR_PRIMARY)
        self.cell(0, 12, 'TABLE DES MATIERES', align='C')
        self.ln(15)
        
        toc = [
            ('1', "Introduction a l'Activite d'Exportation"),
            ('2', 'Les Produits Exportes'),
            ('3', 'Les Acteurs et Leurs Roles'),
            ('4', "Le Cycle de Vie d'une Exportation"),
            ('5', 'Phase 1 : Autorisations et Preparation'),
            ('6', 'Phase 2 : Commerce et Negociation'),
            ('7', 'Phase 3 : Logistique et Empotage'),
            ('8', 'Phase 4 : Paiements et Cloture'),
            ('9', 'Les Etats des Documents'),
            ('10', 'Cas Pratiques Detailles'),
            ('11', 'Annexes et References'),
        ]
        
        for num, title in toc:
            # Forcer la position x au début de chaque ligne
            self.set_x(10)
            self.set_font('Helvetica', 'B', 11)
            self.set_text_color(*COLOR_SECONDARY)
            self.cell(15, 7, num + '.', align='R')  # Largeur augmentée
            
            self.set_font('Helvetica', '', 11)
            self.set_text_color(*COLOR_TEXT)
            # Utiliser multi_cell pour éviter débordement
            self.multi_cell(160, 7, title)  # Largeur réduite
            # Pas de ln() car multi_cell fait déjà le retour
        
        self.skip_header = False
    
    def write_chapter_title(self, title, level=1):
        """Écrit un titre de chapitre"""
        title = clean_markdown(title)
        if not title:
            return
        
        if level == 1:
            self.add_page()
            self.current_chapter = title
            
            # Barre latérale colorée
            self.set_fill_color(*COLOR_PRIMARY)
            self.rect(0, 25, 6, 25, 'F')
            
            self.set_font('Helvetica', 'B', 18)
            self.set_text_color(*COLOR_PRIMARY)
            self.set_xy(12, 28)
            self.multi_cell(185, 8, title)
            self.ln(5)
            
        elif level == 2:
            if self.need_page_break(18):
                self.add_page()
            self.ln(5)
            self.set_font('Helvetica', 'B', 13)
            self.set_text_color(*COLOR_SECONDARY)
            self.set_x(10)  # Forcer position gauche
            self.multi_cell(185, 7, title)  # Réduit de 190 à 185
            self.ln(2)
            
        elif level == 3:
            if self.need_page_break(14):
                self.add_page()
            self.ln(4)
            self.set_font('Helvetica', 'B', 11)
            self.set_text_color(*COLOR_ACCENT)
            self.set_x(10)  # Forcer position gauche
            self.multi_cell(185, 6, title)
            self.ln(1)
            
        elif level == 4:
            if self.need_page_break(12):
                self.add_page()
            self.ln(3)
            self.set_font('Helvetica', 'B', 10)
            self.set_text_color(*COLOR_TEXT)
            self.set_x(10)  # Forcer position gauche
            self.multi_cell(185, 5, title)
    
    def write_paragraph(self, text):
        """Écrit un paragraphe de texte"""
        text = clean_markdown(text)
        if not text or len(text) < 2:
            return
        
        if self.need_page_break(10):
            self.add_page()
        
        self.set_font('Helvetica', '', 10)
        self.set_text_color(*COLOR_TEXT)
        
        # Gérer les listes à puces
        if text.startswith('- ') or text.startswith('* '):
            self.set_x(15)
            self.cell(5, 5, chr(149))
            self.multi_cell(170, 5, text[2:])  # Réduit de 175 à 170
        else:
            self.set_x(10)  # Forcer position gauche
            self.multi_cell(185, 5, text)  # Réduit de 190 à 185
    
    def write_note(self, content):
        """Écrit une note encadrée"""
        content = clean_markdown(content)
        if not content:
            return
        
        # Calculer hauteur approximative
        lines = len(content) // 70 + 2
        height = max(18, lines * 5 + 10)
        
        if self.need_page_break(height + 5):
            self.add_page()
        
        y = self.get_y()
        
        # Barre latérale
        self.set_fill_color(*COLOR_SECONDARY)
        self.rect(10, y, 3, height, 'F')
        
        # Fond
        self.set_fill_color(220, 230, 245)
        self.rect(13, y, 187, height, 'F')
        
        # Titre
        self.set_font('Helvetica', 'B', 9)
        self.set_text_color(*COLOR_SECONDARY)
        self.set_xy(17, y + 3)
        self.cell(50, 5, 'Note')
        
        # Contenu
        self.set_font('Helvetica', '', 9)
        self.set_text_color(*COLOR_TEXT)
        self.set_xy(17, y + 9)
        self.multi_cell(173, 4, content)  # Réduit de 178 à 173
        
        self.set_y(y + height + 3)
    
    def write_diagram(self, lines):
        """Écrit un diagramme ASCII proprement"""
        if not lines:
            return
        
        # Nettoyer les lignes
        clean_lines = []
        for line in lines:
            clean_line = safe_latin1(line)
            if clean_line or (lines.index(line) > 0 and lines.index(line) < len(lines) - 1):
                clean_lines.append(clean_line)
        
        # Supprimer les lignes vides en début et fin
        while clean_lines and not clean_lines[0].strip():
            clean_lines.pop(0)
        while clean_lines and not clean_lines[-1].strip():
            clean_lines.pop()
        
        if not clean_lines:
            return
        
        # Calculer la hauteur
        line_height = 3.2
        height = len(clean_lines) * line_height + 8
        
        if self.need_page_break(height + 5):
            self.add_page()
        
        y = self.get_y()
        
        # Fond gris clair
        self.set_fill_color(*COLOR_LIGHT_BG)
        self.rect(10, y, 190, height, 'F')
        
        # Bordure
        self.set_draw_color(*COLOR_SECONDARY)
        self.set_line_width(0.3)
        self.rect(10, y, 190, height, 'D')
        
        # Contenu avec police monospace très petite
        self.set_font('Courier', '', 5)
        self.set_text_color(*COLOR_TEXT)
        
        # Avec Courier 5pt, environ 120 caractères max dans 186mm
        max_chars = 120
        
        current_y = y + 4
        for line in clean_lines:
            self.set_xy(12, current_y)
            # Tronquer la ligne si trop longue pour éviter débordement
            display_line = line[:max_chars] if len(line) > max_chars else line
            self.cell(186, line_height, display_line)
            current_y += line_height
        
        self.set_y(y + height + 3)
    
    def write_table(self, headers, rows):
        """Écrit un tableau avec ajustement automatique"""
        if not headers or not rows:
            return
        
        num_cols = len(headers)
        
        # Calculer les largeurs de colonnes - utiliser la largeur disponible
        total_width = 190
        col_width = total_width / num_cols
        
        # Estimer la hauteur du tableau
        table_height = (len(rows) + 1) * 6 + 5
        if self.need_page_break(table_height):
            self.add_page()
        
        # En-tête
        self.set_font('Helvetica', 'B', 8)
        self.set_fill_color(*COLOR_PRIMARY)
        self.set_text_color(255, 255, 255)
        
        # Estimer le nombre max de caractères par colonne (Helvetica 8pt ~ 2.5mm par char)
        max_chars_per_col = int(col_width / 2.0)  # ~2mm par caractère en Helvetica 8pt
        
        for header in headers:
            h = clean_markdown(header)
            # Tronquer si trop long
            h = h[:max_chars_per_col] if len(h) > max_chars_per_col else h
            self.cell(col_width, 6, h, border=1, fill=True, align='C')
        self.ln()
        
        # Lignes de données
        self.set_font('Helvetica', '', 8)
        self.set_text_color(*COLOR_TEXT)
        
        for i, row in enumerate(rows):
            if i % 2 == 0:
                self.set_fill_color(255, 255, 255)
            else:
                self.set_fill_color(*COLOR_LIGHT_BG)
            
            for j in range(num_cols):
                cell_text = clean_markdown(row[j]) if j < len(row) else ''
                # Tronquer si trop long
                cell_text = cell_text[:max_chars_per_col] if len(cell_text) > max_chars_per_col else cell_text
                self.cell(col_width, 5, cell_text, border=1, fill=True)
            self.ln()
        
        self.ln(3)


def parse_markdown_file(filepath):
    """Parse le fichier markdown en sections"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    sections = []
    lines = content.split('\n')
    
    in_code = False
    code_lines = []
    
    in_table = False
    table_headers = []
    table_rows = []
    
    for line in lines:
        # Blocs de code
        if line.strip().startswith('```'):
            if in_code:
                if code_lines:
                    sections.append({'type': 'diagram', 'lines': code_lines})
                code_lines = []
                in_code = False
            else:
                in_code = True
            continue
        
        if in_code:
            code_lines.append(line)
            continue
        
        # Tableaux
        if '|' in line and line.strip().startswith('|'):
            cells = [c.strip() for c in line.split('|')[1:-1]]
            if cells:
                # Ligne de séparation ?
                if all(set(c) <= set('-: ') for c in cells):
                    continue
                if not in_table:
                    in_table = True
                    table_headers = cells
                else:
                    table_rows.append(cells)
            continue
        else:
            if in_table:
                if table_headers and table_rows:
                    sections.append({'type': 'table', 'headers': table_headers, 'rows': table_rows})
                table_headers = []
                table_rows = []
                in_table = False
        
        # Titres
        if line.startswith('# ') and 'TABLE DES' not in line.upper():
            sections.append({'type': 'h1', 'text': line[2:]})
        elif line.startswith('## '):
            sections.append({'type': 'h2', 'text': line[3:]})
        elif line.startswith('### '):
            sections.append({'type': 'h3', 'text': line[4:]})
        elif line.startswith('#### '):
            sections.append({'type': 'h4', 'text': line[5:]})
        elif line.strip().startswith('>'):
            sections.append({'type': 'note', 'text': line.strip()[1:].strip()})
        elif line.strip() and not line.startswith('---'):
            sections.append({'type': 'text', 'text': line})
    
    # Tableau final
    if in_table and table_headers and table_rows:
        sections.append({'type': 'table', 'headers': table_headers, 'rows': table_rows})
    
    return sections


def generate():
    """Génère le PDF"""
    print("=" * 60)
    print("Generation du PDF Workflow ICP - Version 4.0")
    print("(Correction complete des troncatures)")
    print("=" * 60)
    
    pdf = WorkflowPDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    
    print("  [1/4] Page de couverture...")
    pdf.write_cover()
    
    print("  [2/4] Table des matieres...")
    pdf.write_toc()
    
    print("  [3/4] Analyse du markdown...")
    sections = parse_markdown_file(WORKFLOW_MD)
    
    print("  [4/4] Generation du contenu ({} sections)...".format(len(sections)))
    
    first_h1 = True
    for section in sections:
        t = section['type']
        
        if t == 'h1':
            if first_h1:
                first_h1 = False
                continue
            pdf.write_chapter_title(section['text'], 1)
        elif t == 'h2':
            pdf.write_chapter_title(section['text'], 2)
        elif t == 'h3':
            pdf.write_chapter_title(section['text'], 3)
        elif t == 'h4':
            pdf.write_chapter_title(section['text'], 4)
        elif t == 'text':
            pdf.write_paragraph(section['text'])
        elif t == 'note':
            pdf.write_note(section['text'])
        elif t == 'diagram':
            pdf.write_diagram(section['lines'])
        elif t == 'table':
            pdf.write_table(section['headers'], section['rows'])
    
    pdf.output(str(OUTPUT_PDF))
    
    size_kb = OUTPUT_PDF.stat().st_size / 1024
    print("=" * 60)
    print(f"PDF genere: {OUTPUT_PDF.name}")
    print(f"Taille: {size_kb:.1f} Ko")
    print("=" * 60)


if __name__ == '__main__':
    try:
        generate()
    except Exception as e:
        print(f"ERREUR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
