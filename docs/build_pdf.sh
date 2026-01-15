#!/bin/bash
# Script pour générer le PDF du guide utilisateur Potting Management

cd /Users/ddma/Desktop/icp/projects/odoo_seventeen/icp/potting_management/docs

/Library/Developer/CommandLineTools/usr/bin/python3 << 'PYTHON_SCRIPT'
import sys
sys.path.insert(0, '/Users/ddma/Library/Python/3.9/lib/python/site-packages')

import re
from pathlib import Path
from fpdf import FPDF

SCRIPT_DIR = Path('/Users/ddma/Desktop/icp/projects/odoo_seventeen/icp/potting_management/docs')
GUIDE_MD = SCRIPT_DIR / 'GUIDE_UTILISATEUR.md'
OUTPUT_PDF = SCRIPT_DIR / 'GUIDE_UTILISATEUR.pdf'

print('Generation du Guide Utilisateur Potting Management en PDF...')

def clean(text):
    if not text:
        return ""
    text = re.sub(r'[\U0001F300-\U0001F9FF]', '', text)
    text = re.sub(r'[\u2600-\u26FF]', '', text)
    text = re.sub(r'[\u2700-\u27BF]', '', text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    text = ''.join(c if ord(c) < 256 else ' ' for c in text)
    return text.strip()

class PDFGuide(FPDF):
    def header(self):
        if self.page_no() > 1:
            self.set_font('Helvetica', 'I', 9)
            self.set_text_color(100, 100, 100)
            self.cell(0, 10, 'Module Potting Management - Guide Utilisateur', new_x='RIGHT', new_y='TOP')
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
            self.multi_cell(w, h, txt)
        except Exception:
            self.cell(0, h, txt[:80], new_x='LMARGIN', new_y='NEXT')

pdf = PDFGuide()
pdf.set_auto_page_break(auto=True, margin=20)

# Couverture
pdf.add_page()
pdf.set_fill_color(139, 90, 43)  # Marron cacao
pdf.ellipse(85, 50, 40, 40, 'F')
pdf.set_font('Helvetica', 'B', 20)
pdf.set_text_color(255, 255, 255)
pdf.set_xy(75, 58)
pdf.cell(60, 20, 'POTTING', new_x='RIGHT', new_y='TOP')

pdf.set_y(110)
pdf.set_font('Helvetica', 'B', 26)
pdf.set_text_color(139, 90, 43)
pdf.cell(0, 12, 'Potting Management', new_x='LMARGIN', new_y='NEXT', align='C')

pdf.set_font('Helvetica', 'B', 18)
pdf.set_text_color(100, 70, 30)
pdf.cell(0, 15, 'Guide Utilisateur', new_x='LMARGIN', new_y='NEXT', align='C')

pdf.ln(10)
pdf.set_font('Helvetica', '', 12)
pdf.set_text_color(100, 100, 100)
pdf.cell(0, 8, "Gestion des Empotages", new_x='LMARGIN', new_y='NEXT', align='C')
pdf.cell(0, 8, "Produits Semi-finis du Cacao", new_x='LMARGIN', new_y='NEXT', align='C')

pdf.ln(20)
pdf.set_draw_color(139, 90, 43)
pdf.set_line_width(1)
pdf.line(70, pdf.get_y(), 140, pdf.get_y())

pdf.set_y(230)
pdf.set_font('Helvetica', '', 11)
pdf.set_text_color(130, 130, 130)
pdf.cell(0, 7, "Version: 17.0.1.3.0", new_x='LMARGIN', new_y='NEXT', align='C')
pdf.cell(0, 7, "Date: Janvier 2025", new_x='LMARGIN', new_y='NEXT', align='C')
pdf.cell(0, 7, "Auteur: ICP - Ivory Cocoa Products", new_x='LMARGIN', new_y='NEXT', align='C')

pdf.set_y(270)
pdf.set_font('Helvetica', 'I', 10)
pdf.set_text_color(170, 170, 170)
pdf.cell(0, 10, 'Odoo 17 Community/Enterprise', new_x='RIGHT', new_y='TOP', align='C')

# Contenu
print('Lecture du fichier Markdown...')
with open(GUIDE_MD, 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.split('\n')
i = 0
current_list = []
in_code = False
code_lines = []
in_table = False
table_h = []
table_r = []

while i < len(lines):
    line = lines[i]
    
    if line.strip().startswith('```'):
        if in_code:
            if code_lines:
                pdf.set_fill_color(45, 45, 45)
                pdf.set_text_color(248, 248, 242)
                pdf.set_font('Courier', '', 8)
                y = pdf.get_y()
                h = min(len(code_lines), 10) * 4 + 8
                if y + h > 270:
                    pdf.add_page()
                    y = pdf.get_y()
                pdf.rect(10, y, 190, h, 'F')
                pdf.set_xy(12, y + 3)
                for cl in code_lines[:10]:
                    txt = clean(cl)[:90]
                    pdf.cell(0, 4, txt, new_x='LMARGIN', new_y='NEXT')
                pdf.ln(3)
                pdf.set_text_color(50, 50, 50)
                code_lines = []
            in_code = False
        else:
            in_code = True
        i += 1
        continue
    
    if in_code:
        code_lines.append(line)
        i += 1
        continue
    
    if '|' in line and not line.strip().startswith('#'):
        cells = [c.strip() for c in line.split('|') if c.strip()]
        if cells:
            if all(c.replace('-', '').replace(':', '') == '' for c in cells):
                i += 1
                continue
            if not in_table:
                in_table = True
                table_h = cells[:4]
            else:
                table_r.append(cells[:4])
        i += 1
        continue
    elif in_table:
        if table_h and table_r:
            ncols = len(table_h)
            col_w = 190 / max(ncols, 1)
            if pdf.get_y() + (len(table_r) + 1) * 7 > 270:
                pdf.add_page()
            pdf.set_fill_color(139, 90, 43)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font('Helvetica', 'B', 9)
            for h in table_h:
                txt = clean(h)[:int(col_w/2.5)]
                pdf.cell(col_w, 7, txt, border=1, align='C', fill=True)
            pdf.ln()
            pdf.set_text_color(50, 50, 50)
            pdf.set_font('Helvetica', '', 8)
            for ri, row in enumerate(table_r[:8]):
                fill_color = 245 if ri % 2 == 0 else 255
                pdf.set_fill_color(fill_color, fill_color, fill_color)
                for c in row:
                    txt = clean(c)[:int(col_w/2.5)]
                    pdf.cell(col_w, 6, txt, border=1, align='L', fill=True)
                for _ in range(ncols - len(row)):
                    pdf.cell(col_w, 6, '', border=1, fill=True)
                pdf.ln()
            pdf.ln(4)
        in_table = False
        table_h = []
        table_r = []
    
    if not line.strip():
        if current_list:
            pdf.set_font('Helvetica', '', 10)
            pdf.set_text_color(50, 50, 50)
            for item in current_list:
                txt = clean(item)
                if txt:
                    pdf.cell(8, 5, '-')
                    pdf.cell(0, 5, txt[:90], new_x='LMARGIN', new_y='NEXT')
            pdf.ln(2)
            current_list = []
        i += 1
        continue
    
    if line.startswith('# '):
        pdf.add_page()
        pdf.set_font('Helvetica', 'B', 18)
        pdf.set_text_color(139, 90, 43)
        txt = clean(line[2:])
        if txt:
            pdf.cell(0, 10, txt, new_x='LMARGIN', new_y='NEXT')
            pdf.set_draw_color(139, 90, 43)
            pdf.line(10, pdf.get_y() + 1, 200, pdf.get_y() + 1)
            pdf.ln(6)
        i += 1
        continue
    
    if line.startswith('## '):
        pdf.ln(4)
        pdf.set_font('Helvetica', 'B', 14)
        pdf.set_text_color(100, 70, 30)
        txt = clean(line[3:])
        if txt:
            pdf.cell(0, 8, txt, new_x='LMARGIN', new_y='NEXT')
            pdf.set_draw_color(200, 200, 200)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(4)
        i += 1
        continue
    
    if line.startswith('### '):
        pdf.ln(3)
        pdf.set_font('Helvetica', 'B', 12)
        pdf.set_text_color(80, 55, 25)
        txt = clean(line[4:])
        if txt:
            pdf.cell(0, 7, txt, new_x='LMARGIN', new_y='NEXT')
            pdf.ln(2)
        i += 1
        continue
    
    if line.startswith('#### '):
        pdf.ln(2)
        pdf.set_font('Helvetica', 'B', 11)
        pdf.set_text_color(100, 100, 100)
        txt = clean(line[5:])
        if txt:
            pdf.cell(0, 6, txt, new_x='LMARGIN', new_y='NEXT')
            pdf.ln(1)
        i += 1
        continue
    
    if line.strip() == '---':
        i += 1
        continue
    
    if line.strip().startswith('- ') or line.strip().startswith('* '):
        current_list.append(line.strip()[2:])
        i += 1
        continue
    
    if re.match(r'^\d+\. ', line.strip()):
        current_list.append(re.sub(r'^\d+\. ', '', line.strip()))
        i += 1
        continue
    
    if line.strip().startswith('>'):
        pdf.set_fill_color(255, 243, 205)
        y = pdf.get_y()
        pdf.set_draw_color(255, 193, 7)
        pdf.rect(10, y, 190, 10, 'DF')
        pdf.set_xy(15, y + 2)
        pdf.set_font('Helvetica', 'I', 9)
        pdf.set_text_color(50, 50, 50)
        txt = clean(line.strip()[1:].strip())
        if txt:
            pdf.cell(180, 5, txt[:100], new_x='LMARGIN', new_y='NEXT')
        pdf.ln(4)
        i += 1
        continue
    
    txt = clean(line)
    if txt:
        pdf.set_font('Helvetica', '', 10)
        pdf.set_text_color(50, 50, 50)
        pdf.safe_multi(0, 5, txt)
        pdf.ln(1)
    i += 1

if current_list:
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(50, 50, 50)
    for item in current_list:
        txt = clean(item)
        if txt:
            pdf.cell(8, 5, '-')
            pdf.cell(0, 5, txt[:90], new_x='LMARGIN', new_y='NEXT')
    pdf.ln(2)

print('Ecriture du PDF...')
pdf.output(str(OUTPUT_PDF))

import os
size = os.path.getsize(OUTPUT_PDF) / 1024
print(f'PDF genere avec succes!')
print(f'Fichier: {OUTPUT_PDF}')
print(f'Taille: {size:.1f} KB')
PYTHON_SCRIPT
