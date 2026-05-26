"""
PDF / Word файлаас даалгавар задлах модуль
"""
import re, io
import pdfplumber
from docx import Document

OPT_PAT = re.compile(r'^\s*([АБВГабвгABCDabcd])\s*[\.\)]\s*(.+)', re.MULTILINE)
ANS_PAT = re.compile(r'(?:хариулт|зөв\s*хариулт|answer)\s*[:\-]\s*([АБВГабвгABCDabcd])', re.IGNORECASE)

BLOOM_MAP = {
    'мэдлэг':'Мэдлэг','нэрл':'Мэдлэг','тодорхойл':'Мэдлэг',
    'ойлг':'Ойлголт','тайлбарл':'Ойлголт','харьцуул':'Ойлголт',
    'хэрэгл':'Хэрэглээ','тооцо':'Хэрэглээ','бод':'Хэрэглээ',
    'шинжил':'Шинжилгээ','задл':'Шинжилгээ',
    'үнэл':'Үнэлгээ','дүгн':'Үнэлгээ',
    'бүтээ':'Бүтээл','зохио':'Бүтээл',
}

KEY_MAP = {
    'а':'А','б':'Б','в':'В','г':'Г',
    'a':'А','b':'Б','c':'В','d':'Г',
    'А':'А','Б':'Б','В':'В','Г':'Г',
    'A':'А','B':'Б','C':'В','D':'Г',
}

LEVEL_SCORE = {"Мэдлэг ойлголт":1,"Чадвар":2,"Хэрэглээ":3}

def detect_bloom(text):
    t = text.lower()
    for kw, level in BLOOM_MAP.items():
        if kw in t:
            return level
    return 'Мэдлэг'

def extract_from_pdf(file_bytes):
    texts = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                texts.append(t)
    return '\n'.join(texts)

def extract_from_docx(file_bytes):
    doc = Document(io.BytesIO(file_bytes))
    return '\n'.join(p.text for p in doc.paragraphs if p.text.strip())

def parse_raw_text(raw, grade, subject, default_level='Мэдлэг ойлголт'):
    from datetime import datetime
    questions = []

    blocks = re.split(r'\n(?=\s*\d{1,3}\s*[\.\)])', raw)
    parsed_blocks = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        block = re.sub(r'^\s*\d{1,3}\s*[\.\)]\s*', '', block).strip()
        if len(block) > 10:
            parsed_blocks.append(block)

    if len(parsed_blocks) < 2:
        parsed_blocks = [b.strip() for b in re.split(r'\n{2,}', raw)
                         if b.strip() and len(b.strip()) > 10]

    for idx, body in enumerate(parsed_blocks):
        lines = [l.strip() for l in body.split('\n') if l.strip()]
        if not lines:
            continue
        q_text = lines[0]
        if len(q_text) < 5:
            continue

        opts = {'А': None, 'Б': None, 'В': None, 'Г': None}
        answer = None
        for line in lines[1:]:
            mo = OPT_PAT.match(line)
            if mo:
                letter = KEY_MAP.get(mo.group(1).strip())
                if letter:
                    opts[letter] = mo.group(2).strip()
            ans = ANS_PAT.search(line)
            if ans:
                answer = KEY_MAP.get(ans.group(1), 'А')

        bloom  = detect_bloom(q_text)
        q_type = 'Нэг сонголт' if any(opts.values()) else 'Нээлттэй'
        score  = LEVEL_SCORE.get(default_level, 1)
        q_code = f"Q{grade}-{subject[:2]}-{datetime.now().strftime('%f')}-{idx}"

        questions.append({
            'q_code':  q_code,
            'grade':   grade,
            'subject': subject,
            'level':   default_level,
            'bloom':   bloom,
            'q_type':  q_type,
            'question':q_text,
            'option_a':opts['А'],
            'option_b':opts['Б'],
            'option_c':opts['В'],
            'option_d':opts['Г'],
            'answer':  answer or 'А',
            'score':   score,
            'topic':   '',
        })

    return questions
