"""
PDF / Word файлаас даалгавар задлах + автомат түвшин тодорхойлох
"""
import re, io
import pdfplumber
from docx import Document
from datetime import datetime

# ── Хариултын түлхүүр ──────────────────────────────────
KEY_MAP = {
    'а':'А','б':'Б','в':'В','г':'Г',
    'a':'А','b':'Б','c':'В','d':'Г',
    'А':'А','Б':'Б','В':'В','Г':'Г',
    'A':'А','B':'Б','C':'В','D':'Г',
}

LEVEL_SCORE = {"Мэдлэг ойлголт":1,"Чадвар":2,"Хэрэглээ":3}

# ── Блумын шатны үгс ───────────────────────────────────
BLOOM_MAP = {
    'мэдлэг':'Мэдлэг','нэрл':'Мэдлэг','тодорхойл':'Мэдлэг','жагсаа':'Мэдлэг',
    'ойлг':'Ойлголт','тайлбарл':'Ойлголт','харьцуул':'Ойлголт','тайлбар':'Ойлголт',
    'хэрэгл':'Хэрэглээ','тооцо':'Хэрэглээ','бод':'Хэрэглээ','олж':'Хэрэглээ',
    'шинжил':'Шинжилгээ','задл':'Шинжилгээ','ялга':'Шинжилгээ',
    'үнэл':'Үнэлгээ','дүгн':'Үнэлгээ','шүүмжл':'Үнэлгээ',
    'бүтээ':'Бүтээл','зохио':'Бүтээл','төлөвл':'Бүтээл',
}

# ── Автомат түвшин тодорхойлох ─────────────────────────
# Мэдлэг ойлголт: энгийн асуулт, дугаарлалт, нэрлэх
LEVEL1_PATTERNS = [
    r'\bюу вэ\b', r'\bхэн вэ\b', r'\bхэд вэ\b', r'\bаль вэ\b',
    r'\bнэрлэ\b', r'\bжагсаа\b', r'\bтодорхойл\b', r'\bтайлбарла\b',
    r'\bхэзээ\b', r'\bхаана\b', r'\bямар\b',
    # Математик: үржүүлэх, нэмэх, хасах, хуваах
    r'[\+\-\×\÷\=].*[\+\-\×\÷\=]',
    r'\d+\s*[\+\-\×\÷]\s*\d+',
]

# Чадвар: тооцох, олох, шийдвэрлэх
LEVEL2_PATTERNS = [
    r'\bолж\b', r'\bтооцо\b', r'\bшийдв?эрл\b', r'\bбод\b',
    r'\bгүйцэтгэ\b', r'\bхэрэглэ\b', r'\bуншиж\b', r'\bбичиж\b',
    r'\bхувирга\b', r'\bтооцоол\b', r'\bбодолт\b',
    r'x\s*=', r'y\s*=',  # тэгшитгэл
]

# Хэрэглээ: шинжлэх, үнэлэх, бүтээх, зохиох
LEVEL3_PATTERNS = [
    r'\bшинжил\b', r'\bүнэл\b', r'\bдүгн\b', r'\bзохио\b',
    r'\bтайлбарла.*яагаад\b', r'\bяагаад\b', r'\bучрыг\b',
    r'\bхарьцуул.*дүгн\b', r'\bнотол\b', r'\bбатал\b',
    r'\bтөлөвл\b', r'\bзурагл\b', r'\bбүтэц\b',
]

def detect_level(text):
    """Даалгаврын текстийг шинжлэн түвшин тодорхойлно"""
    t = text.lower()
    score3 = sum(1 for p in LEVEL3_PATTERNS if re.search(p, t))
    score2 = sum(1 for p in LEVEL2_PATTERNS if re.search(p, t))
    score1 = sum(1 for p in LEVEL1_PATTERNS if re.search(p, t))

    # Хамгийн өндөр оноотой түвшин
    if score3 >= 1:
        return "Хэрэглээ"
    elif score2 >= 1:
        return "Чадвар"
    elif score1 >= 1:
        return "Мэдлэг ойлголт"

    # Хэрэв дугаар → тодорхойлолт шиг харагдвал Мэдлэг ойлголт
    if len(text) < 60:
        return "Мэдлэг ойлголт"
    elif len(text) < 150:
        return "Чадвар"
    else:
        return "Хэрэглээ"

def detect_bloom(text):
    t = text.lower()
    for kw, level in BLOOM_MAP.items():
        if kw in t:
            return level
    return 'Мэдлэг'

def extract_from_pdf(file_bytes):
    """PDF-с текст гаргах — CID encoding автоматаар шийднэ"""
    texts = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages[:50]:
            # Энгийн extraction
            text = page.extract_text(x_tolerance=3, y_tolerance=3) or ''
            
            # CID тэмдэгт байвал char-level авах
            if '(cid:' in text:
                char_parts = []
                prev_y = None
                for ch in page.chars:
                    ch_txt = ch.get('text', '')
                    ch_y   = round(ch.get('top', 0))
                    if prev_y is not None and abs(ch_y - prev_y) > 3:
                        char_parts.append('\n')
                    char_parts.append(ch_txt)
                    prev_y = ch_y
                char_text = ''.join(char_parts)
                if char_text.strip():
                    text = char_text
            
            # Үлдсэн CID хоосон болгох
            import re as _re
            text = _re.sub(r'\(cid:\d+\)', '', text)
            text = _re.sub(r' {3,}', '  ', text)
            text = _re.sub(r'\n{3,}', '\n\n', text)
            
            if text.strip():
                texts.append(text.strip())
    return '\n\n'.join(texts)

def extract_from_docx(file_bytes):
    doc = Document(io.BytesIO(file_bytes))
    return '\n'.join(p.text for p in doc.paragraphs if p.text.strip())

OPT_PAT = re.compile(r'^\s*([АБВГабвгABCDabcd])\s*[\.\)]\s*(.+)', re.MULTILINE)
ANS_PAT = re.compile(r'(?:хариулт|зөв\s*хариулт|answer)\s*[:\-]\s*([АБВГабвгABCDabcd])', re.IGNORECASE)

def parse_raw_text(raw, grade, subject, default_level='Мэдлэг ойлголт'):
    """
    Текстийг задлан даалгавруудын жагсаалт буцаана.
    default_level зааж өгсөн ч автоматаар тодорхойлно.
    """
    questions = []

    # Даалгавруудыг тусгаарлах
    blocks = re.split(r'\n(?=\s*\d{1,3}\s*[\.\)])', raw)
    parsed_blocks = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        block = re.sub(r'^\s*\d{1,3}\s*[\.\)]\s*', '', block).strip()
        if len(block) > 8:
            parsed_blocks.append(block)

    if len(parsed_blocks) < 2:
        parsed_blocks = [b.strip() for b in re.split(r'\n{2,}', raw)
                         if b.strip() and len(b.strip()) > 8]

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

        # ── Автомат түвшин тодорхойлох ──
        level = detect_level(q_text + ' ' + body)
        bloom = detect_bloom(q_text)
        score = LEVEL_SCORE.get(level, 1)
        q_type = 'Нэг сонголт' if any(opts.values()) else 'Нээлттэй'
        q_code = f"Q{grade}-{subject[:2]}-{datetime.now().strftime('%f')}-{idx}"

        questions.append({
            'q_code':   q_code,
            'grade':    grade,
            'subject':  subject,
            'level':    level,        # Автоматаар тодорхойлсон
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
