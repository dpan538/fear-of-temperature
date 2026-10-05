#!/usr/bin/env python3
"""Export the proposal's supported Markdown structure to HTML, PDF and TXT.

The source uses headings, paragraphs, blockquotes, simple lists and tables.
Unsupported fenced blocks raise an error rather than silently losing content.
Dependencies: reportlab. Paths are relative to this script, not the shell cwd.
"""
from pathlib import Path
import re
import html
import json
import hashlib
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Image,
)
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT = Path(__file__).resolve().parent
fontdir = Path('/System/Library/Fonts/Supplemental')
for family, filename in [('Times', 'Times New Roman'), ('Helvetica', 'Arial')]:
    normal = 'Times-Roman' if family == 'Times' else 'Helvetica'
    italic = 'Times-Italic' if family == 'Times' else 'Helvetica-Oblique'
    bolditalic = 'Times-BoldItalic' if family == 'Times' else 'Helvetica-BoldOblique'
    for alias, suffix in [(normal, ''), (family+'-Bold', ' Bold'), (italic, ' Italic'), (bolditalic, ' Bold Italic')]:
        pdfmetrics.registerFont(TTFont(alias, str(fontdir/(filename+suffix+'.ttf'))))
    pdfmetrics.registerFontFamily(normal, normal=normal, bold=family+'-Bold', italic=italic, boldItalic=bolditalic)
SOURCE = ROOT / 'draft_proposal.md'
raw = SOURCE.read_text(encoding='utf-8')
bibraw = (ROOT / 'references.bib').read_text(encoding='utf-8')
title = re.search(r'^title: "(.*)"$', raw, re.M).group(1)
author = re.search(r'^author: "(.*)"$', raw, re.M).group(1)
supervisor = re.search(r'^supervisor: "(.*)"$', raw, re.M).group(1)
submission_date = re.search(r'^date: "(.*)"$', raw, re.M).group(1)
body = raw.split('---', 2)[2]
body = body[body.index('# Use of AI Statement'):]
if '```' in body:
    raise ValueError('Add fenced-block support before exporting this source.')

entries = {}
for match in re.finditer(r'^@\w+\{([^,]+),\n(.*?)^\}', bibraw, re.M | re.S):
    key, fields = match.groups()
    item = {m.group(1): m.group(2).replace('{', '').replace('}', '')
            for m in re.finditer(r'^\s*(\w+)\s*=\s*\{(.*)\},?$', fields, re.M)}
    if key in entries:
        raise ValueError(f'Duplicate bibliography key: {key}')
    entries[key] = item
keys = set(re.findall(r'@([A-Za-z][\w]*)', body))
if keys != set(entries):
    raise ValueError(f'Citation mismatch: {keys ^ set(entries)}')

def clean(s):
    return (s.replace('--', '-').replace('—', ' - ').replace('–', '-')
            .replace('‑', '-').replace('’', "'").replace('‘', "'")
            .replace('“', '"').replace('”', '"'))

def citation_label(key):
    e = entries[key]
    names = e.get('author', '').split(' and ')
    org = {'ipcc_history': 'IPCC', 'unfccc_kyoto': 'UNFCCC', 'unfccc_paris': 'UNFCCC'}
    if key in org:
        who = org[key]
    else:
        surnames = [n.split(',')[0] for n in names]
        who = surnames[0] + (' et al.' if len(names) > 2 else
                            ' & ' + surnames[1] if len(names) == 2 else '')
    when = e.get('year', 'n.d.')
    if key == 'unfccc_kyoto': when = 'n.d.-a'
    if key == 'unfccc_paris': when = 'n.d.-b'
    return f'{who}, {when}'

def replace_citations(s, links=False):
    def group(m):
        labels = []
        for k in re.findall(r'@([\w]+)', m.group(0)):
            label = citation_label(k)
            labels.append(f'[{label}](#ref-{k})' if links else label)
        return '(' + '; '.join(labels) + ')'
    return re.sub(r'\[@[^\]]+\]', group, s)

def plain(s):
    s = replace_citations(clean(s))
    s = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'\1', s)
    return s.replace('**', '').replace('`', '')

def rich(s, pdf=False):
    s = html.escape(replace_citations(clean(s), links=not pdf), quote=False)
    s = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', s)
    s = re.sub(r'`([^`]+)`', r'<font face="Courier">\1</font>' if pdf else r'<code>\1</code>', s)
    def link(m):
        label, href = m.groups()
        return f'<a href="{html.escape(href, quote=True)}">{label}</a>'
    return re.sub(r'\[([^\]]+)\]\(([^)]+)\)', link, s)

blocks = []
lines = body.splitlines()
i = 0
skip = False
while i < len(lines):
    line = lines[i].strip()
    if not line:
        i += 1; continue
    heading = re.match(r'^(#{1,3}) (.*)', line)
    if heading:
        level, text = len(heading[1]), heading[2]
        skip = text in ('Contents', 'References')
        blocks.append(('toc' if text == 'Contents' else 'refs' if text == 'References' else 'h', level, text))
        i += 1; continue
    if skip:
        i += 1; continue
    if line.startswith('|'):
        rows = []
        while i < len(lines) and lines[i].strip().startswith('|'):
            cells = [x.strip() for x in lines[i].strip().strip('|').split('|')]
            if not all(re.fullmatch(r':?-+:?', x) for x in cells):
                rows.append(cells)
            i += 1
        blocks.append(('table', rows)); continue
    if line.startswith('>'):
        note = []
        while i < len(lines) and lines[i].strip().startswith('>'):
            note.append(lines[i].strip()[1:].strip()); i += 1
        blocks.append(('note', ' '.join(note))); continue
    bullet = re.match(r'^(\d+\.|-) (.*)', line)
    if bullet:
        blocks.append(('item', bullet[1], bullet[2])); i += 1; continue
    para = [line]; i += 1
    while i < len(lines) and lines[i].strip() and not re.match(r'^(#|>|\||\d+\. |\- )', lines[i].strip()):
        para.append(lines[i].strip()); i += 1
    blocks.append(('p', ' '.join(para)))

refrows = []
for key, e in sorted(entries.items(), key=lambda pair: (pair[1].get('author', ''), citation_label(pair[0]))):
    names = []
    for name in e['author'].split(' and '):
        parts = name.split(', ', 1)
        names.append(parts[0] + (', ' + ' '.join(w[0] + '.' for w in parts[1].split()) if len(parts) > 1 else ''))
    authors = '; '.join(names)
    when = citation_label(key).rsplit(', ', 1)[1]
    where = e.get('journal', e.get('booktitle', e.get('howpublished', '')))
    if 'volume' in e: where += ' ' + e['volume']
    if 'number' in e: where += '(' + e['number'] + ')'
    if 'pages' in e: where += ', ' + e['pages']
    if 'eprint' in e: where = 'arXiv:' + e['eprint']
    url = 'https://doi.org/' + e['doi'] if 'doi' in e else e.get('url', '')
    ref = f'{authors} ({when}). {e["title"]}.' + (f' {where}.' if where else '')
    if not e.get('year') and e.get('urldate'): ref += f' Accessed {e["urldate"]}.'
    refrows.append((key, clean(ref), url))

headings = [(b[1], b[2]) for b in blocks if b[0] == 'h'] + [(1, 'References')]
anchor = lambda s: re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')
draftnote = ('Discussion draft updated 15 September 2026. Introduction, research questions and initial methods are drafted. '
             'The literature review, detailed evaluation, timetable and ethics sections remain in development. '
             'The submission date is provisional; some AI-use details remain to be confirmed.')
txt = [clean(title), f'Author: {author}', f'Supervision: {supervisor}',
       f'Submission date: {submission_date}', draftnote, '']
fragments = []
for b in blocks:
    kind = b[0]
    if kind == 'h':
        fragments.append(f'<h{b[1]} id="{anchor(b[2])}">{rich(b[2])}</h{b[1]}>')
        txt.extend([plain(b[2]), ''])
        if b[2] == 'Use of AI Statement': fragments.append(f'<aside>{draftnote}</aside>')
    elif kind in ('toc', 'refs'):
        fragments.append(f'<h1 id="{anchor(b[2])}">{b[2]}</h1>'); txt.extend([b[2], ''])
        if kind == 'toc':
            fragments.append('<nav class="contents">' + ''.join(f'<a class="level-{lev}" href="#{anchor(h)}">{html.escape(h)}</a>' for lev, h in headings if lev <= 2) + '</nav>')
            txt.extend([plain(h) for lev, h in headings if lev <= 2] + [''])
        else:
            for k, ref, url in refrows:
                fragments.append(f'<p class="reference" id="ref-{k}">{html.escape(ref)} <a href="{html.escape(url, quote=True)}">{html.escape(url)}</a></p>')
                txt.extend([ref + ' ' + url, ''])
    elif kind == 'table':
        fragments.append('<table><thead><tr>' + ''.join('<th>' + rich(c) + '</th>' for c in b[1][0]) + '</tr></thead><tbody>')
        for row in b[1][1:]: fragments.append('<tr>' + ''.join('<td>' + rich(c) + '</td>' for c in row) + '</tr>')
        fragments.append('</tbody></table>')
        txt.extend([' | '.join(plain(c) for c in row) for row in b[1]] + [''])
    else:
        content = b[1] if kind in ('p', 'note') else b[1] + ' ' + b[2]
        tag = 'aside' if kind == 'note' else 'p'
        fragments.append(f'<{tag}>{rich(content)}</{tag}>'); txt.extend([plain(content), ''])

css = '''
:root{color-scheme:light;--ink:#202129;--purple:#51247a}
*{box-sizing:border-box}body{margin:0;background:#f0eff3;color:var(--ink);font:17px/1.65 Georgia,serif}
main{max-width:900px;margin:36px auto;background:white;padding:70px 80px;box-shadow:0 4px 28px #23203812}
.cover{text-align:center;padding:35px 0 65px;border-bottom:1px solid #ddd}.cover img{width:60%;height:auto}
.cover h1{font:700 32px/1.25 Georgia,serif;margin:50px 0 36px}.cover p{margin:12px}
h1,h2,h3{line-height:1.3;break-after:avoid}h1{font-size:28px;color:var(--purple);margin-top:52px}h2{font-size:22px;margin-top:30px}h3{font-size:18px;margin-top:24px}
p{margin:0 0 15px}a{color:#51247a;overflow-wrap:anywhere}aside{background:#f6f3f9;border-left:3px solid #9d80b6;padding:12px 16px;margin:18px 0;font:14px/1.6 system-ui,sans-serif}
table{border-collapse:collapse;width:100%;font-size:14px;margin:20px 0}th,td{text-align:left;vertical-align:top;border:1px solid #ddd;padding:10px}th{background:#f1edf5}
.contents a{display:block;text-decoration:none}.contents .level-2{padding-left:24px}.reference{font-size:15px;padding-left:20px;text-indent:-20px}
@media(max-width:700px){main{margin:0;padding:24px}.cover h1{font-size:27px}table{font-size:12px}}
@media print{body{background:white}main{margin:0;max-width:none;box-shadow:none;padding:0}.cover{break-after:page;border:0}h1{break-before:page}a{color:inherit}aside{border:1px solid #bbb}}
'''
htmltext = ('<!doctype html><html lang="en-AU"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{html.escape(title)} - discussion draft</title><style>{css}</style></head><body><main>'
            f'<header class="cover"><img src="assets/UQ_Logo.png" alt="The University of Queensland"><h1>{html.escape(title)}</h1>'
            f'<p>by<br>{html.escape(author)}</p><p>under the supervision of<br>{html.escape(supervisor)}</p><p>{html.escape(submission_date)}</p></header>'
            + ''.join(fragments) + '</main></body></html>')
(ROOT / 'draft_proposal.html').write_text(htmltext, encoding='utf-8')
(ROOT / 'draft_proposal.txt').write_text('\n'.join(txt), encoding='utf-8')

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='BodyDraft', fontName='Times-Roman', fontSize=11, leading=14, spaceAfter=8))
styles.add(ParagraphStyle(name='NoteDraft', fontName='Helvetica', fontSize=9, leading=12, textColor=colors.HexColor('#594966'), spaceAfter=10))
styles.add(ParagraphStyle(name='TableDraft', fontName='Helvetica', fontSize=8.4, leading=11))
styles.add(ParagraphStyle(name='ReferenceDraft', fontName='Times-Roman', fontSize=10, leading=13, leftIndent=12, firstLineIndent=-12, spaceAfter=11, splitLongWords=True))
for n, size in [('Heading1',20), ('Heading2',14), ('Heading3',11.5)]:
    styles[n].fontName = 'Times-Bold'; styles[n].fontSize = size
    styles[n].leading = size * 1.25; styles[n].spaceBefore = 14; styles[n].spaceAfter = 9
    styles[n].keepWithNext = True
styles['Heading1'].textColor = colors.HexColor('#51247a')
styles.add(ParagraphStyle(name='CoverTitle', fontName='Times-Bold', fontSize=25, leading=31, alignment=1, spaceAfter=30))
styles.add(ParagraphStyle(name='CoverMeta', fontName='Times-Italic', fontSize=13, leading=19, alignment=1, spaceAfter=22))

class DraftDoc(SimpleDocTemplate):
    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph) and flowable.style.name in ('Heading1', 'Heading2'):
            text = flowable.getPlainText()
            if text == 'Contents': return
            key = anchor(text)
            self.canv.bookmarkPage(key)
            level = 0 if flowable.style.name == 'Heading1' else 1
            self.notify('TOCEntry', (level, text, self.page, key))

W,H = A4
width = W - 50*mm
doc = DraftDoc(str(ROOT/'draft_proposal.pdf'), pagesize=A4,
               leftMargin=25*mm,rightMargin=25*mm,topMargin=25*mm,bottomMargin=23*mm,
               title=clean(title), author=clean(author))
logo = Image(str(ROOT/'assets/UQ_Logo.png'))
logo.drawHeight = logo.imageHeight / logo.imageWidth * width * .6
logo.drawWidth = width * .6
story = [Spacer(1,25*mm), logo, Spacer(1,25*mm), Paragraph(html.escape(clean(title)),styles['CoverTitle']),
         Paragraph('by<br/>'+html.escape(author), styles['CoverMeta']),
         Paragraph('under the supervision of<br/>'+html.escape(supervisor), styles['CoverMeta']),
         Spacer(1,20*mm), Paragraph(html.escape(submission_date),styles['CoverMeta']), PageBreak()]
first = True
for b in blocks:
    kind = b[0]
    if kind in ('h','toc','refs'):
        level, text = b[1:]
        if level == 1 and not first: story.append(PageBreak())
        first = False
        story.append(Paragraph(rich(text,pdf=True), styles[f'Heading{level}']))
        if text == 'Use of AI Statement': story.append(Paragraph(draftnote,styles['NoteDraft']))
        if kind == 'toc':
            toc = TableOfContents()
            toc.levelStyles = [ParagraphStyle(name='TOC1',fontName='Times-Bold',fontSize=11,leading=17,spaceBefore=8),
                               ParagraphStyle(name='TOC2',fontName='Times-Roman',fontSize=10,leading=15,leftIndent=16)]
            story.append(toc)
        elif kind == 'refs':
            for k, ref, url in refrows:
                story.append(Paragraph(html.escape(ref) + '<br/><a href="' + html.escape(url,quote=True) + '">' + html.escape(url) + '</a>', styles['ReferenceDraft']))
    elif kind == 'table':
        rows = [[Paragraph(rich(c,pdf=True),styles['TableDraft']) for c in row] for row in b[1]]
        table = Table(rows,colWidths=[width*.37,width*.63],repeatRows=1,hAlign='LEFT')
        table.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('GRID',(0,0),(-1,-1),.35,colors.HexColor('#cccccc')),
                                   ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#f1edf5')),('LEFTPADDING',(0,0),(-1,-1),7),
                                   ('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
        story.extend([table,Spacer(1,10)])
    else:
        content = b[1] if kind in ('p','note') else b[1] + ' ' + b[2]
        story.append(Paragraph(rich(content,pdf=True),styles['NoteDraft' if kind == 'note' else 'BodyDraft']))

def footer(canvas, document):
    if document.page == 1: return
    canvas.saveState()
    canvas.setFont('Helvetica',8)
    canvas.setFillColor(colors.HexColor('#666666'))
    canvas.drawString(25*mm,H-15*mm,'FEAR OF TEMPERATURE  |  DISCUSSION DRAFT')
    canvas.drawString(25*mm,13*mm,'Updated 15 September 2026')
    canvas.drawRightString(W-25*mm,13*mm,str(document.page))
    canvas.restoreState()

doc.multiBuild(story,onFirstPage=footer,onLaterPages=footer)
(ROOT/'qa').mkdir(exist_ok=True)
manifest = {'source_sha256':hashlib.sha256(raw.encode()).hexdigest(),
            'bibliography_sha256':hashlib.sha256(bibraw.encode()).hexdigest(),
            'citation_count':len(keys),'citation_keys':sorted(keys),
            'outputs':['draft_proposal.html','draft_proposal.pdf','draft_proposal.txt'],
            'content_blocks':len(blocks),'source_word_count_including_editorial_material':len(body.split()),
            'status':'Discussion draft; incomplete chapters explicitly marked; not a submission word count'}
(ROOT/'qa/export_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(manifest,indent=2))
