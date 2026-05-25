"""
PDF → Даалгавар задлагч
Монгол ЕБС-ийн сурах бичиг, шалгалтын PDF-ийг задлан
даалгаврыг мэдэн бүтэцлэнэ.
"""
import pdfplumber
import re

# ── Дүрэм ─────────────────────────────────────────────────────────────────
# Даалгавар эхлэх загвар: "1.", "1)", "Даалгавар 1", "№1"
Q_START = re.compile(
    r'^(\d{1,3}[\.\)]\s+|№\s*\d+[\.\):]?\s*|Даалгавар\s*\d+[\.\):]?\s*)',
    re.MULTILINE | re.IGNORECASE
)
# Сонголтын загвар: А. / а) / A. / a)
OPT_PAT = re.compile(
    r'^([АБВГабвгABCDabcd][\.\)]\s*)(.+)',
    re.MULTILINE
)
# Хариулт: "Хариулт: А", "Зөв: Б"
ANS_PAT = re.compile(
    r'(?:хариулт|зөв|answer)[:\s]+([АБВГабвгABCDabcd])',
    re.IGNORECASE
)
# Хүндрэлийн түвшин
DIFF_PAT = re.compile(r'\b(хялбар|дунд|хүнд)\b', re.IGNORECASE)
# Блумын шат
BLOOM_MAP = {
    'мэдлэг': 'Мэдлэг', 'тодорхойл': 'Мэдлэг', 'нэрл': 'Мэдлэг',
    'ойлг': 'Ойлголт', 'тайлбарл': 'Ойлголт', 'харьцуул': 'Ойлголт',
    'хэрэгл': 'Хэрэглээ', 'тооцо': 'Хэрэглээ', 'бодо': 'Хэрэглээ',
    'шинжил': 'Шинжилгээ', 'задл': 'Шинжилгээ',
    'үнэл': 'Үнэлгээ', 'дүгн': 'Үнэлгээ',
    'бүтээ': 'Бүтээл', 'зохио': 'Бүтээл',
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
        return 'Хялбар' if d == 'хялбар' else ('Дунд' if d == 'дунд' else 'Хүнд')
    return None

def extract_text_from_pdf(path):
    pages_text = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                pages_text.append(t)
    return '\n'.join(pages_text)

def parse_questions(raw_text, grade, subject, default_difficulty='Дунд'):
    """
    Текстийг задлан даалгаварын жагсаалт буцаана.
    """
    questions = []
    # Даалгавруудыг тусгаарлах
    parts = Q_START.split(raw_text)
    # parts = [pre, num1, body1, num2, body2, ...]
    # Хос индекс: body
    bodies = []
    i = 0
    while i < len(parts):
        if Q_START.match(parts[i]) or (i > 0 and re.match(r'^\d', parts[i])):
            if i + 1 < len(parts):
                bodies.append(parts[i + 1])
                i += 2
            else:
                i += 1
        else:
            i += 1

    # Хэрэв тусгаарлаагүй бол мөр тутам шалгах
    if not bodies:
        lines = raw_text.split('\n')
        current = []
        for line in lines:
            if Q_START.match(line.strip()):
                if current:
                    bodies.append('\n'.join(current))
                current = [line]
            else:
                current.append(line)
        if current:
            bodies.append('\n'.join(current))

    import re as _re, random as _rand
    from datetime import datetime

    for idx, body in enumerate(bodies):
        if not body.strip() or len(body.strip()) < 8:
            continue

        lines = [l.strip() for l in body.strip().split('\n') if l.strip()]
        if not lines:
            continue

        # Эхний мөр = асуулт
        q_text = lines[0]
        if len(q_text) < 5:
            continue

        # Сонголтууд
        opts = {'А': None, 'Б': None, 'В': None, 'Г': None}
        key_map = {'а': 'А', 'б': 'Б', 'в': 'В', 'г': 'Г',
                   'a': 'А', 'b': 'Б', 'c': 'В', 'd': 'Г',
                   'А': 'А', 'Б': 'Б', 'В': 'В', 'Г': 'Г',
                   'A': 'А', 'B': 'Б', 'C': 'В', 'D': 'Г'}
        answer = None
        for line in lines[1:]:
            mo = OPT_PAT.match(line)
            if mo:
                letter = mo.group(1).strip().rstrip('.)')
                norm = key_map.get(letter)
                if norm:
                    opts[norm] = mo.group(2).strip()
            ans = ANS_PAT.search(line)
            if ans:
                answer = key_map.get(ans.group(1), 'А')

        has_opts = any(v for v in opts.values())

        # Хүндрэл
        diff = detect_difficulty(body) or default_difficulty
        bloom = detect_bloom(q_text)
        score = 1 if diff == 'Хялбар' else (2 if diff == 'Дунд' else 3)
        q_code = f"Q{grade}-{subject[:3]}-PDF-{datetime.now().strftime('%f')}-{idx}"
        q_type = 'Нэг сонголт' if has_opts else 'Нээлттэй'

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
