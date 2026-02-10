#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script professionnel pour générer le PDF du workflow d'exportation ICP
Version 3.1 - Sans troncature de texte - Février 2026
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
COLOR_PRIMARY = (31, 73, 125)      # Bleu foncé
COLOR_SECONDARY = (68, 114, 196)   # Bleu clair
COLOR_ACCENT = (146, 89, 33)       # Marron cacao
COLOR_SUCCESS = (56, 142, 60)      # Vert
COLOR_WARNING = (255, 152, 0)      # Orange
COLOR_TEXT = (33, 33, 33)          # Noir doux
COLOR_LIGHT_BG = (248, 249, 250)   # Fond clair


def clean_text(text):
    """Nettoie le texte des caractères spéciaux et formatage markdown"""
    if not text:
        return ""
    
    # Supprimer les emojis
    emoji_pattern = re.compile("["
        u"\U0001F300-\U0001F9FF"
        u"\u2600-\u26FF"
        u"\u2700-\u27BF"
        "]+", flags=re.UNICODE)
    text = emoji_pattern.sub('', text)
    
    # Supprimer le formatage markdown
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # Bold
    text = re.sub(r'\*([^*]+)\*', r'\1', text)       # Italic
    text = re.sub(r'`([^`]+)`', r'\1', text)         # Code inline
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)  # Links
    
    # Convertir en latin-1 compatible
    result = ""
    for char in text:
        if ord(char) < 256:
            result += char
        elif char in '─│┌┐└┘├┤┬┴┼═║╔╗╚╝╠╣╦╩╬▶▼►◀←→↓↑':
            # Remplacer les caractères de dessin par des équivalents simples
            replacements = {
                '─': '-', '│': '|', '┌': '+', '┐': '+', '└': '+', '┘': '+',
                '├': '+', '┤': '+', '┬': '+', '┴': '+', '┼': '+',
                '═': '=', '║': '|', '╔': '+', '╗': '+', '╚': '+', '╝': '+',
                '╠': '+', '╣': '+', '╦': '+', '╩': '+', '╬': '+',
                '▶': '>', '▼': 'v', '►': '>', '◀': '<', '←': '<', '→': '>',
                '↓': 'v', '↑': '^'
            }
            result += replacements.get(char, ' ')
        else:
            result += ' '
    
    return result.strip()


class ProfessionalPDF(FPDF):
    """Classe PDF personnalisée pour le guide ICP"""
    
    def __init__(self):
        super().__init__()
        self.current_chapter = ""
        self.in_toc = False
        self.toc_entries = []
        
    def header(self):
        if self.page_no() > 1 and not self.in_toc:
            # Ligne de séparation
            self.set_draw_color(*COLOR_PRIMARY)
            self.set_line_width(0.5)
            self.line(10, 12, 200, 12)
            
            # Titre à gauche
            self.set_font('Helvetica', 'I', 8)
            self.set_text_color(*COLOR_SECONDARY)
            self.set_xy(10, 6)
            self.cell(100, 6, 'ICP - Guide du Workflow d\'Exportation', align='L')
            
            # Chapitre à droite (sans troncature excessive)
            self.set_xy(110, 6)
            chapter_text = clean_text(self.current_chapter) if self.current_chapter else ''
            if len(chapter_text) > 50:
                chapter_text = chapter_text[:47] + '...'
            self.cell(90, 6, chapter_text, align='R')
            
            self.ln(15)
    
    def footer(self):
        if self.page_no() > 1:
            self.set_y(-15)
            
            # Ligne de séparation
            self.set_draw_color(*COLOR_PRIMARY)
            self.set_line_width(0.3)
            self.line(10, self.get_y() - 2, 200, self.get_y() - 2)
            
            # Numéro de page
            self.set_font('Helvetica', '', 9)
            self.set_text_color(*COLOR_TEXT)
            self.cell(0, 10, f'Page {self.page_no()}', align='C')
    
    def check_page_break(self, height=10):
        """Vérifie si on doit sauter de page"""
        if self.get_y() + height > 275:
            self.add_page()
            return True
        return False
    
    def add_cover_page(self):
        """Page de couverture professionnelle"""
        self.add_page()
        
        # Rectangle décoratif en haut
        self.set_fill_color(*COLOR_PRIMARY)
        self.rect(0, 0, 210, 80, 'F')
        
        # Logo texte ICP
        self.set_font('Helvetica', 'B', 48)
        self.set_text_color(255, 255, 255)
        self.set_xy(0, 25)
        self.cell(210, 20, 'ICP', align='C')
        
        self.set_font('Helvetica', '', 14)
        self.set_xy(0, 50)
        self.cell(210, 10, 'Ivory Cocoa Products', align='C')
        
        # Titre principal
        self.set_font('Helvetica', 'B', 28)
        self.set_text_color(*COLOR_PRIMARY)
        self.set_xy(0, 100)
        self.cell(210, 15, 'GUIDE COMPLET DU WORKFLOW', align='C')
        
        self.set_font('Helvetica', 'B', 24)
        self.set_xy(0, 120)
        self.cell(210, 15, 'D\'EXPORTATION', align='C')
        
        # Sous-titre
        self.set_font('Helvetica', '', 14)
        self.set_text_color(*COLOR_SECONDARY)
        self.set_xy(0, 145)
        self.cell(210, 10, 'Module Potting Management', align='C')
        
        # Ligne décorative
        self.set_draw_color(*COLOR_ACCENT)
        self.set_line_width(2)
        self.line(60, 165, 150, 165)
        
        # Description
        self.set_font('Helvetica', 'I', 11)
        self.set_text_color(*COLOR_TEXT)
        self.set_xy(30, 180)
        self.multi_cell(150, 6, 
            "Ce document decrit le processus complet d'exportation des produits "
            "semi-finis du cacao, les acteurs impliques et leurs responsabilites.",
            align='C')
        
        # Informations version
        self.set_fill_color(*COLOR_LIGHT_BG)
        self.rect(50, 220, 110, 40, 'F')
        
        self.set_font('Helvetica', '', 10)
        self.set_text_color(*COLOR_TEXT)
        self.set_xy(50, 225)
        self.cell(110, 6, f'Version 3.1 - Fevrier 2026', align='C')
        self.set_xy(50, 233)
        self.cell(110, 6, 'Document confidentiel - Usage interne ICP', align='C')
        self.set_xy(50, 241)
        self.cell(110, 6, 'Module Odoo 17 - Potting Management', align='C')
        
        # Pied de page couverture
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(150, 150, 150)
        self.set_xy(0, 275)
        self.cell(210, 5, 'Cote d\'Ivoire - Premier producteur mondial de cacao', align='C')
    
    def add_toc_page(self):
        """Page de table des matières"""
        self.in_toc = True
        self.add_page()
        
        self.set_font('Helvetica', 'B', 20)
        self.set_text_color(*COLOR_PRIMARY)
        self.cell(0, 15, 'TABLE DES MATIERES', align='C')
        self.ln(20)
        
        toc_items = [
            ('1', 'Introduction a l\'Activite d\'Exportation', 3),
            ('2', 'Les Produits Exportes', 5),
            ('3', 'Les Acteurs et Leurs Roles', 7),
            ('4', 'Le Cycle de Vie d\'une Exportation', 13),
            ('5', 'Phase 1 : Autorisations et Preparation', 15),
            ('6', 'Phase 2 : Commerce et Negociation', 18),
            ('7', 'Phase 3 : Logistique et Empotage', 21),
            ('8', 'Phase 4 : Paiements et Cloture', 23),
            ('9', 'Les Etats des Documents', 27),
            ('10', 'Cas Pratiques Detailles', 28),
            ('11', 'Annexes et References', 31),
        ]
        
        for num, title, page in toc_items:
            self.set_font('Helvetica', 'B', 11)
            self.set_text_color(*COLOR_SECONDARY)
            self.cell(10, 8, num)
            
            self.set_font('Helvetica', '', 11)
            self.set_text_color(*COLOR_TEXT)
            
            # Titre avec points de conduite
            title_width = self.get_string_width(title)
            self.cell(title_width + 2, 8, title)
            
            # Points
            dots_width = 180 - 10 - title_width - 15
            dots = '.' * int(dots_width / 1.5)
            self.set_text_color(180, 180, 180)
            self.cell(dots_width, 8, dots)
            
            # Numéro de page
            self.set_text_color(*COLOR_TEXT)
            self.cell(15, 8, str(page), align='R')
            self.ln()
        
        self.in_toc = False
    
    def chapter_title(self, title, level=1):
        """Affiche un titre de chapitre sans troncature"""
        title = clean_text(title)
        if not title or len(title.strip()) < 2:
            return
        
        try:
            if level == 1:
                self.add_page()
                self.current_chapter = title
                
                # Bande de couleur
                self.set_fill_color(*COLOR_PRIMARY)
                self.rect(0, 30, 8, 30, 'F')
                
                self.set_font('Helvetica', 'B', 20)
                self.set_text_color(*COLOR_PRIMARY)
                self.set_xy(15, 35)
                self.multi_cell(180, 9, title)
                self.ln(8)
                
            elif level == 2:
                self.check_page_break(20)
                self.ln(6)
                self.set_font('Helvetica', 'B', 13)
                self.set_text_color(*COLOR_SECONDARY)
                self.multi_cell(190, 7, title)
                self.ln(2)
                
            elif level == 3:
                self.check_page_break(15)
                self.ln(4)
                self.set_font('Helvetica', 'B', 11)
                self.set_text_color(*COLOR_ACCENT)
                self.multi_cell(190, 6, title)
                self.ln(1)
                
            elif level == 4:
                self.check_page_break(12)
                self.ln(3)
                self.set_font('Helvetica', 'B', 10)
                self.set_text_color(*COLOR_TEXT)
                self.multi_cell(190, 5, title)
                self.ln(1)
        except Exception as e:
            pass
    
    def body_text(self, text):
        """Texte normal sans troncature"""
        text = clean_text(text)
        if not text or len(text.strip()) < 2:
            return
        
        self.check_page_break(8)
        
        self.set_font('Helvetica', '', 10)
        self.set_text_color(*COLOR_TEXT)
        
        try:
            # Gestion des listes à puces
            if text.startswith('- ') or text.startswith('* '):
                self.set_x(15)
                self.cell(5, 5, chr(149))  # Bullet point
                self.multi_cell(175, 5, text[2:])
            else:
                self.multi_cell(190, 5, text)
        except Exception:
            pass
    
    def info_box(self, title, content, box_type='info'):
        """Boite d'information coloree sans troncature"""
        colors = {
            'info': COLOR_SECONDARY,
            'success': COLOR_SUCCESS,
            'warning': COLOR_WARNING,
            'accent': COLOR_ACCENT
        }
        color = colors.get(box_type, COLOR_SECONDARY)
        
        title = clean_text(title)
        content = clean_text(content)
        
        if not content or len(content) < 3:
            return
        
        # Calculer la hauteur nécessaire
        self.set_font('Helvetica', '', 9)
        # Estimer le nombre de lignes
        lines_needed = len(content) / 80 + 2
        box_height = max(20, int(lines_needed * 5) + 10)
        
        self.check_page_break(box_height + 5)
        
        try:
            start_y = self.get_y()
            
            # Barre laterale
            self.set_fill_color(*color)
            self.rect(10, start_y, 3, box_height, 'F')
            
            # Fond
            self.set_fill_color(min(color[0] + 180, 255), min(color[1] + 180, 255), min(color[2] + 180, 255))
            self.rect(13, start_y, 187, box_height, 'F')
            
            # Titre
            self.set_font('Helvetica', 'B', 10)
            self.set_text_color(*color)
            self.set_xy(18, start_y + 2)
            self.cell(170, 5, title)
            
            # Contenu
            self.set_font('Helvetica', '', 9)
            self.set_text_color(*COLOR_TEXT)
            self.set_xy(18, start_y + 8)
            self.multi_cell(170, 4, content)
            
            self.set_y(start_y + box_height + 3)
        except Exception:
            pass
    
    def diagram_box(self, lines):
        """Affiche un diagramme ASCII dans une boîte - police plus petite pour éviter troncature"""
        if not lines:
            return
            
        # Filtrer les lignes vides au début et à la fin
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()
        
        if not lines:
            return
        
        # Calculer la hauteur nécessaire
        block_height = len(lines) * 3.5 + 8
        
        self.check_page_break(block_height + 5)
        
        start_y = self.get_y()
        
        # Fond du diagramme
        self.set_fill_color(*COLOR_LIGHT_BG)
        self.rect(10, start_y, 190, block_height, 'F')
        
        # Bordure
        self.set_draw_color(*COLOR_SECONDARY)
        self.set_line_width(0.3)
        self.rect(10, start_y, 190, block_height, 'D')
        
        # Contenu avec police plus petite
        self.set_font('Courier', '', 5.5)
        self.set_text_color(*COLOR_TEXT)
        self.set_xy(12, start_y + 4)
        
        for line in lines:
            line = clean_text(line)
            if line:
                try:
                    # Ne pas tronquer, utiliser une police assez petite
                    self.cell(186, 3.5, line)
                except:
                    pass
            self.ln(3.5)
            self.set_x(12)
        
        self.set_y(start_y + block_height + 3)
    
    def table(self, headers, rows):
        """Affiche un tableau formaté avec auto-ajustement"""
        if not headers or not rows:
            return
        
        num_cols = len(headers)
        if num_cols == 0:
            return
        
        # Calculer les largeurs optimales
        total_width = 190
        col_widths = []
        
        # Calculer la largeur max de chaque colonne
        self.set_font('Helvetica', 'B', 8)
        for i, header in enumerate(headers):
            max_width = self.get_string_width(clean_text(header)) + 4
            for row in rows:
                if i < len(row):
                    cell_width = self.get_string_width(clean_text(row[i])) + 4
                    max_width = max(max_width, cell_width)
            col_widths.append(min(max_width, total_width / num_cols * 1.5))
        
        # Normaliser pour que ça rentre dans la page
        total_calc = sum(col_widths)
        if total_calc > total_width:
            col_widths = [w * total_width / total_calc for w in col_widths]
        
        # Calculer la hauteur du tableau
        table_height = (len(rows) + 1) * 6
        self.check_page_break(table_height + 5)
        
        # En-tête
        self.set_font('Helvetica', 'B', 8)
        self.set_fill_color(*COLOR_PRIMARY)
        self.set_text_color(255, 255, 255)
        
        for i, header in enumerate(headers):
            header = clean_text(header)
            self.cell(col_widths[i], 6, header, border=1, fill=True, align='C')
        self.ln()
        
        # Lignes
        self.set_font('Helvetica', '', 8)
        self.set_text_color(*COLOR_TEXT)
        
        for row_idx, row in enumerate(rows):
            # Alternance de couleurs
            if row_idx % 2 == 0:
                self.set_fill_color(255, 255, 255)
            else:
                self.set_fill_color(*COLOR_LIGHT_BG)
            
            for i, col_width in enumerate(col_widths):
                cell_text = clean_text(row[i]) if i < len(row) else ''
                self.cell(col_width, 5, cell_text, border=1, fill=True)
            self.ln()
        
        self.ln(3)


def parse_markdown(content):
    """Parse le contenu markdown et retourne une liste de sections"""
    lines = content.split('\n')
    sections = []
    in_code_block = False
    code_lines = []
    in_table = False
    table_headers = []
    table_rows = []
    
    for line in lines:
        # Détecter les blocs de code
        if line.strip().startswith('```'):
            if in_code_block:
                if code_lines:
                    sections.append({'type': 'diagram', 'content': code_lines})
                code_lines = []
                in_code_block = False
            else:
                in_code_block = True
            continue
        
        if in_code_block:
            code_lines.append(line)
            continue
        
        # Détecter les tableaux
        if '|' in line and line.strip().startswith('|'):
            cells = [c.strip() for c in line.split('|')[1:-1]]
            if cells:
                # Ignorer la ligne de séparation
                if all(c.replace('-', '').replace(':', '') == '' for c in cells):
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
        if line.startswith('# ') and 'TABLE DES' not in line:
            sections.append({'type': 'title', 'level': 1, 'content': line[2:]})
        elif line.startswith('## '):
            sections.append({'type': 'title', 'level': 2, 'content': line[3:]})
        elif line.startswith('### '):
            sections.append({'type': 'title', 'level': 3, 'content': line[4:]})
        elif line.startswith('#### '):
            sections.append({'type': 'title', 'level': 4, 'content': line[5:]})
        elif line.strip().startswith('---'):
            continue  # Ignorer les séparateurs
        elif line.strip().startswith('>'):
            sections.append({'type': 'quote', 'content': line.strip()[1:].strip()})
        elif line.strip():
            sections.append({'type': 'text', 'content': line})
    
    # Ne pas oublier le dernier tableau si présent
    if in_table and table_headers and table_rows:
        sections.append({'type': 'table', 'headers': table_headers, 'rows': table_rows})
    
    return sections


def generate_pdf():
    """Génère le PDF professionnel"""
    print("="*60)
    print("Generation du PDF Workflow ICP - Version 3.1")
    print("(Sans troncature de texte)")
    print("="*60)
    
    # Créer le PDF
    pdf = ProfessionalPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    
    # Page de couverture
    print("  [1/4] Creation de la page de couverture...")
    pdf.add_cover_page()
    
    # Table des matières
    print("  [2/4] Creation de la table des matieres...")
    pdf.add_toc_page()
    
    # Lire le contenu markdown
    print("  [3/4] Analyse du document markdown...")
    with open(WORKFLOW_MD, 'r', encoding='utf-8') as f:
        content = f.read()
    
    sections = parse_markdown(content)
    
    # Générer le contenu
    print("  [4/4] Generation du contenu...")
    
    skip_first_title = True
    for section in sections:
        if section['type'] == 'title':
            if skip_first_title and section['level'] == 1:
                skip_first_title = False
                continue
            pdf.chapter_title(section['content'], section['level'])
        
        elif section['type'] == 'text':
            pdf.body_text(section['content'])
        
        elif section['type'] == 'diagram':
            pdf.diagram_box(section['content'])
        
        elif section['type'] == 'table':
            pdf.table(section['headers'], section['rows'])
        
        elif section['type'] == 'quote':
            pdf.info_box('Note', section['content'], 'info')
    
    # Sauvegarder
    pdf.output(str(OUTPUT_PDF))
    
    print("="*60)
    print(f"PDF genere avec succes!")
    print(f"Fichier: {OUTPUT_PDF}")
    print(f"Taille: {OUTPUT_PDF.stat().st_size / 1024:.1f} Ko")
    print("="*60)


if __name__ == '__main__':
    try:
        generate_pdf()
    except Exception as e:
        print(f"ERREUR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
