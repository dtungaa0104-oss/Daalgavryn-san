"""
PDF / Word файлаас даалгавар задлах модуль
"""
import re, io
import pdfplumber
from docx import Document

# Даалгавар эхлэх загвар
Q_START = re.compile(
    r'(?:^|\n)\s*(\d{1,3})\s*[\.\)]\s+(.+?)(?=\n\s*\d{1,3}\s*[\.\)]|\Z)',
    re.DOTALL
)
OPT_PAT = re.compile(
    r'^\s*([АБВГабвгABCDabcd])\s*[\.\)]\s*(.+)', re.MULTILINE
)
ANS_PAT = re.compile(
    r'(?:хариулт|зөв\s*хариулт|answer)\s*[:\-]\s*([АБВГабвгABCDabcd])',
    re.IGNORECASE
)
DIFF_PAT = re.compile(r'\b(хялбар|дунд|хүнд)\b', re.IGNORECASE)
BLOOM_MAP = {
    'мэдлэг':'Мэдлэг','нэрл':'Мэдлэг','тодорхойл':'Мэдлэг',
    'ойлг':'Ойлголт','тайлбарл':'Ойлголт','харьцуул':'Ойлголт',
    'хэрэгл':'Хэрэглээ','тооцо':'Хэрэглээ','бод':'Хэрэглээ',
    'шинжил':'Шинжилгээ','задл':'Шинжилгээ',
    'үнэл':'Үнэлгээ','дүгн':'Үнэлгээ',
    'бүтээ':'Бүтээл','зохио':'Бүтээл',
}

def detect_bloom(text):
    t = text.lower()
    for kw, level in BLOOM_MAP.items():
        if kw in t:
            return level
    return 'Мэдлэг'

def detect_difficulty(text):
    m = DIFF_PAT.search(text)
    if m:
        d = m.group(1).lower()
        return 'Хялбар' if d=='хялбар' else ('Дунд' if d=='дунд' else 'Хүнд')
    return None

KEY_MAP = {
    'а':'А','б':'Б','в':'В','г':'Г',
    'a':'А','b':'Б','c':'В','d':'Г',
    'А':'А','Б':'Б','В':'В','Г':'Г',
    'A':'А','B':'Б','C':'В','D':'Г',
}

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

def parse_raw_text(raw, grade, subject, default_diff='Дунд'):
    """Текстийг задлан даалгавруудын жагсаалт буцаана"""
    from datetime import datetime
    questions = []

    # Арга 1: "1. асуулт" загвараар задлах
    blocks = re.split(r'\n(?=\s*\d{1,3}\s*[\.\)])', raw)

    parsed_blocks = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        # Дугаарыг хасах
        block = re.sub(r'^\s*\d{1,3}\s*[\.\)]\s*', '', block).strip()
        if len(block) > 10:
            parsed_blocks.append(block)

    if len(parsed_blocks) < 2:
        # Арга 2: хоосон мөрөөр хуваах
        parsed_blocks = [b.strip() for b in re.split(r'\n{2,}', raw) if b.strip() and len(b.strip()) > 10]

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

        diff  = detect_difficulty(body) or default_diff
        bloom = detect_bloom(q_text)
        score = 1 if diff=='Хялбар' else (2 if diff=='Дунд' else 3)
        q_type = 'Нэг сонголт' if any(opts.values()) else 'Нээлттэй'
        q_code = f"Q{grade}-{subject[:2]}-{datetime.now().strftime('%f')}-{idx}"

        questions.append({
            'q_code':   q_code,
            'grade':    grade,
            'subject':  subject,
            'difficulty': diff,
            'bloom':    bloom,
            'q_type':   q_type,
            'question': q_text,
            'option_a': opts['А'],
            'option_b': opts['Б'],
            'option_c': opts['В'],
            'option_d': opts['Г'],
            'answer':   answer or 'А',
            'score':    score,
            'topic':    '',
        })

    return questions
