#!/bin/bash
# Script pour générer le PDF du workflow acteurs Potting Management

cd /Users/ddma/Desktop/icp/projects/odoo_seventeen/icp/potting_management/docs

/Library/Developer/CommandLineTools/usr/bin/python3 << 'PYTHON_SCRIPT'
import sys
sys.path.insert(0, '/Users/ddma/Library/Python/3.9/lib/python/site-packages')

import re
from pathlib import Path
from fpdf import FPDF

SCRIPT_DIR = Path('/Users/ddma/Desktop/icp/projects/odoo_seventeen/icp/potting_management/docs')
WORKFLOW_MD = SCRIPT_DIR / 'WORKFLOW_ACTEURS.md'
OUTPUT_PDF = SCRIPT_DIR / 'WORKFLOW_ACTEURS.pdf'

print('Generation du Workflow Acteurs Potting Management en PDF...')

def clean(text):
    """Nettoie le texte des caractères spéciaux et emoji"""
    if not text:
        return ""
    # Supprimer les emojis
    text = re.sub(r'[\U0001F300-\U0001F9FF]', '', text)
    text = re.sub(r'[\u2600-\u26FF]', '', text)
    text = re.sub(r'[\u2700-\u27BF]', '', text)
    text = re.sub(r'[\U0001F600-\U0001F64F]', '', text)
    text = re.sub(r'[\U0001F680-\U0001F6FF]', '', text)
    # Supprimer le formatage markdown
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    # Garder uniquement les caractères latin-1
    text = ''.join(c if ord(c) < 256 else ' ' for c in text)
    return text.strip()

class PDFWorkflow(FPDF):
    def header(self):
        if self.page_no() > 1:
            self.set_font('Helvetica', 'I', 9)
            self.set_text_color(100, 100, 100)
            self.cell(0, 10, 'Potting Management - Workflow des Acteurs', new_x='RIGHT', new_y='TOP')
            self.ln(15)
    
    def footer(self):
        if self.page_no() > 1:
            self.set_y(-15)
            self.set_font('Helvetica', 'I', 9)
            self.set_text_color(100, 100, 100)
            self.cell(0, 10, f'Page {self.page_no()}', new_x='RIGHT', new_y='TOP')
    
    def safe_multi(self, w, h, txt):
        txt = clean(txt)
        if not txt or len(txt.strip()) == 0:
            return
        try:
            self.multi_cell(w, h, txt, new_x='LEFT', new_y='NEXT')
        except Exception:
            pass
    
    def chapter_title(self, title, level=1):
        title = clean(title)
        if not title:
            return
        
        if level == 1:
            self.set_font('Helvetica', 'B', 18)
            self.set_text_color(31, 73, 125)
            self.ln(8)
        elif level == 2:
            self.set_font('Helvetica', 'B', 14)
            self.set_text_color(68, 114, 196)
            self.ln(5)
        elif level == 3:
            self.set_font('Helvetica', 'B', 12)
            self.set_text_color(89, 89, 89)
            self.ln(4)
        elif level == 4:
            self.set_font('Helvetica', 'B', 11)
            self.set_text_color(100, 100, 100)
            self.ln(3)
        
        self.multi_cell(0, 7, title, new_x='LEFT', new_y='NEXT')
        self.ln(3)
    
    def body_text(self, text):
        self.set_font('Helvetica', '', 10)
        self.set_text_color(0, 0, 0)
        self.safe_multi(0, 5, text)
    
    def code_block(self, lines):
        """Affiche un bloc de code/diagramme"""
        self.set_font('Courier', '', 7)
        self.set_fill_color(245, 245, 245)
        self.set_text_color(50, 50, 50)
        
        y_start = self.get_y()
        max_width = 0
        
        for line in lines:
            line = clean(line)
            width = self.get_string_width(line)
            if width > max_width:
                max_width = width
        
        # Dessiner le fond
        x_start = 10
        block_width = min(max_width + 10, 190)
        block_height = len(lines) * 4 + 4
        
        # Vérifier s'il y a assez de place
        if self.get_y() + block_height > 270:
            self.add_page()
        
        self.set_fill_color(245, 245, 245)
        self.rect(x_start, self.get_y(), block_width, block_height, 'F')
        
        self.ln(2)
        for line in lines:
            line = clean(line)
            if line:
                try:
                    self.cell(0, 4, line[:120], new_x='LEFT', new_y='NEXT')
                except:
                    pass
        self.ln(3)
    
    def table_row(self, cells, header=False):
        """Affiche une ligne de tableau"""
        if header:
            self.set_font('Helvetica', 'B', 9)
            self.set_fill_color(68, 114, 196)
            self.set_text_color(255, 255, 255)
        else:
            self.set_font('Helvetica', '', 9)
            self.set_fill_color(255, 255, 255)
            self.set_text_color(0, 0, 0)
        
        # Calculer les largeurs de colonnes
        num_cols = len(cells)
        if num_cols == 0:
            return
        col_width = 190 / num_cols
        
        for cell in cells:
            cell = clean(cell)[:40]  # Limiter la longueur
            self.cell(col_width, 6, cell, border=1, fill=True)
        self.ln()

def parse_markdown(file_path):
    """Parse le fichier markdown et retourne les sections"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    return content

def generate_pdf():
    """Génère le PDF"""
    pdf = PDFWorkflow()
    pdf.set_auto_page_break(auto=True, margin=20)
    
    # Page de titre
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 28)
    pdf.set_text_color(31, 73, 125)
    pdf.ln(40)
    pdf.cell(0, 15, 'WORKFLOW DU MODULE', new_x='LEFT', new_y='NEXT', align='C')
    pdf.cell(0, 15, 'POTTING MANAGEMENT', new_x='LEFT', new_y='NEXT', align='C')
    
    pdf.ln(20)
    pdf.set_font('Helvetica', '', 14)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 10, 'Guide des Acteurs et Processus d\'Exportation', new_x='LEFT', new_y='NEXT', align='C')
    
    pdf.ln(30)
    pdf.set_font('Helvetica', 'I', 12)
    pdf.cell(0, 8, 'ICP - Ivory Cocoa Products', new_x='LEFT', new_y='NEXT', align='C')
    pdf.cell(0, 8, 'Module Odoo 17 - Version 2.0', new_x='LEFT', new_y='NEXT', align='C')
    pdf.cell(0, 8, 'Fevrier 2026', new_x='LEFT', new_y='NEXT', align='C')
    
    # Lire le contenu markdown
    content = parse_markdown(WORKFLOW_MD)
    lines = content.split('\n')
    
    in_code_block = False
    code_lines = []
    in_table = False
    table_rows = []
    
    for line in lines:
        # Ignorer les premières lignes de titre déjà traitées
        if line.startswith('# ') and 'WORKFLOW' in line:
            continue
        if line.startswith('## Guide'):
            continue
        if line.startswith('> **'):
            continue
            
        # Détecter les blocs de code
        if line.strip().startswith('```'):
            if in_code_block:
                # Fin du bloc
                if code_lines:
                    pdf.code_block(code_lines)
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
            if cells and not all(c.replace('-', '') == '' for c in cells):
                if not in_table:
                    in_table = True
                    pdf.ln(3)
                    pdf.table_row(cells, header=True)
                else:
                    pdf.table_row(cells, header=False)
            continue
        else:
            if in_table:
                in_table = False
                pdf.ln(3)
        
        # Titres
        if line.startswith('## '):
            pdf.add_page()
            pdf.chapter_title(line[3:], level=1)
        elif line.startswith('### '):
            pdf.chapter_title(line[4:], level=2)
        elif line.startswith('#### '):
            pdf.chapter_title(line[5:], level=3)
        elif line.strip().startswith('---'):
            pdf.ln(5)
        elif line.strip():
            # Texte normal
            cleaned = clean(line)
            if cleaned:
                pdf.body_text(cleaned)
    
    # Sauvegarder
    pdf.output(str(OUTPUT_PDF))
    print(f'PDF genere avec succes: {OUTPUT_PDF}')
    print(f'Taille: {OUTPUT_PDF.stat().st_size / 1024:.1f} Ko')

if __name__ == '__main__':
    try:
        generate_pdf()
    except Exception as e:
        print(f'Erreur: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)
PYTHON_SCRIPT
