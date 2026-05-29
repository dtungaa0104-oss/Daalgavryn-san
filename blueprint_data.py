"""
Блюпринт өгөгдлийн удирдлага
─────────────────────────────────────────────────────────────────────
1. PDF-с блюпринт задлан Firebase-д хадгалах  →  import_blueprint_pdf()
2. Flask endpoint /api/get-blueprint           →  get_blueprint_route()

Firebase бүтэц:
  blueprints/{subject}_{grade}/
    nj: [
      {
        id: "nj_1",
        name: "Үнэлгээний нэгж нэр",
        surd: [
          {
            id: "srd_1_1",
            name: "Суралцахуйн үр дүн текст",
            shalguur: [
              {
                id:    "sh_1_1_1",
                text:  "Шалгуурын текст",
                level: "Мэдлэг ойлголт",   # | "Чадвар" | "Хэрэглээ"
                score: 1,                   # оноо/нэгж
                d_tоо: 1,                   # даалгаврын тоо блюпринтэд
                d_onoо: 1                   # оноо блюпринтэд
              }
            ]
          }
        ]
      }
    ]

Суулгах:
    pip install pdfplumber firebase-admin
"""

import re
import uuid
import json
from flask import request, jsonify

# ═══════════════════════════════════════════════════════════════════
# FIREBASE ХОЛБОГЧ
# ═══════════════════════════════════════════════════════════════════
try:
    import firebase_admin
    from firebase_admin import credentials, firestore as fb_firestore
    _FB_OK = True
except ImportError:
    _FB_OK = False

_db = None

def get_db():
    global _db
    if _db:
        return _db
    if not _FB_OK:
        raise RuntimeError("firebase-admin суулгаагүй байна")
    if not firebase_admin._apps:
        # serviceAccountKey.json байх шаардлагатай
        cred = credentials.Certificate("serviceAccountKey.json")
        firebase_admin.initialize_app(cred)
    _db = fb_firestore.client()
    return _db


# ═══════════════════════════════════════════════════════════════════
# PDF ЗАДЛАГЧ
# ═══════════════════════════════════════════════════════════════════
try:
    import pdfplumber
    _PDF_OK = True
except ImportError:
    _PDF_OK = False


def _clean(t):
    """Мөр дэх олон зай, таб-ыг цэвэрлэх"""
    if not t:
        return ""
    return re.sub(r'\s+', ' ', str(t)).strip()


def _level_from_col(col_idx, headers):
    """Баганы индексээс түвшин тодорхойлох"""
    if col_idx < len(headers):
        h = headers[col_idx].lower()
        if 'мэдлэг' in h or 'ойлголт' in h:
            return 'Мэдлэг ойлголт'
        if 'чадвар' in h:
            return 'Чадвар'
        if 'хэрэглээ' in h:
            return 'Хэрэглээ'
    return 'Мэдлэг ойлголт'


def parse_blueprint_pdf(pdf_path, subject, grade):
    """
    БҮТ-ийн стандарт блюпринт PDF-с өгөгдөл задлах.
    Returns: list of NJ objects (Firebase бүтцэд тохирсон)
    """
    if not _PDF_OK:
        raise RuntimeError("pdfplumber суулгаагүй. pip install pdfplumber")

    nj_list = []
    nj_map  = {}   # nj_name -> nj объект
    cur_nj  = None
    cur_surd = None

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            # Хүснэгт олох
            tables = page.extract_tables()
            if not tables:
                continue

            for table in tables:
                if not table or len(table) < 2:
                    continue

                # Header мөр олох
                header_row = None
                data_rows  = []
                for i, row in enumerate(table):
                    cells = [_clean(c) for c in (row or [])]
                    row_text = ' '.join(cells).lower()
                    if 'мэдлэг' in row_text and ('чадвар' in row_text or 'оноо' in row_text):
                        header_row = cells
                        data_rows  = table[i+1:]
                        break

                if header_row is None:
                    # Header олдсонгүй — анхны мөрийг header болгох
                    header_row = [_clean(c) for c in (table[0] or [])]
                    data_rows  = table[1:]

                # Баганын индексүүд
                col_nj    = _find_col(header_row, ['үнэлгээний нэгж','нэгж'])
                col_surd  = _find_col(header_row, ['суралцахуйн үр дүн','үр дүн'])
                col_sh    = _find_col(header_row, ['шалгуур','үр дүнгийн шалгуур'])
                col_m_dt  = _find_col(header_row, ['мэдлэг', 'ойлголт'])
                col_c_dt  = _find_col(header_row, ['чадвар'])
                col_x_dt  = _find_col(header_row, ['хэрэглээ'])

                for row in data_rows:
                    cells = [_clean(c) for c in (row or [])]
                    if not any(cells):
                        continue

                    nj_text   = cells[col_nj]   if col_nj   < len(cells) else ''
                    surd_text = cells[col_surd]  if col_surd < len(cells) else ''
                    sh_text   = cells[col_sh]    if col_sh   < len(cells) else ''

                    if not sh_text:
                        continue

                    # Мэдлэг/Чадвар/Хэрэглээ тоо оноог авах
                    def get_pair(idx):
                        """idx баганаас д/тоо ба оноо авах (дараагийн багана оноо)"""
                        if idx < 0 or idx >= len(cells):
                            return 0, 0
                        v1 = _to_int(cells[idx])
                        v2 = _to_int(cells[idx+1]) if idx+1 < len(cells) else v1
                        return v1, v2

                    m_dt, m_on = get_pair(col_m_dt)
                    c_dt, c_on = get_pair(col_c_dt)
                    x_dt, x_on = get_pair(col_x_dt)

                    # NJ нэмэх / олох
                    if nj_text and nj_text not in nj_map:
                        nj_obj = {
                            'id':   'nj_' + str(len(nj_list)+1),
                            'name': nj_text,
                            'surd': []
                        }
                        nj_map[nj_text] = nj_obj
                        nj_list.append(nj_obj)
                    if nj_text:
                        cur_nj = nj_map[nj_text]

                    if cur_nj is None:
                        continue

                    # Суралцахуйн үр дүн нэмэх / олох
                    surd_key = surd_text or '__default__'
                    existing_surd = None
                    for s in cur_nj['surd']:
                        if s['name'] == surd_key:
                            existing_surd = s
                            break
                    if existing_surd is None:
                        existing_surd = {
                            'id':      cur_nj['id'] + '_s' + str(len(cur_nj['surd'])+1),
                            'name':    surd_text,
                            'shalguur': []
                        }
                        cur_nj['surd'].append(existing_surd)
                    cur_surd = existing_surd

                    # Шалгуур нэмэх — түвшин тус бүрт
                    sh_base_id = cur_surd['id'] + '_sh' + str(len(cur_surd['shalguur'])+1)

                    if m_dt > 0:
                        cur_surd['shalguur'].append({
                            'id':    sh_base_id + '_m',
                            'text':  sh_text,
                            'level': 'Мэдлэг ойлголт',
                            'score': (m_on // m_dt) if m_dt else 1,
                            'd_too': m_dt,
                            'd_onoo': m_on
                        })
                    if c_dt > 0:
                        cur_surd['shalguur'].append({
                            'id':    sh_base_id + '_c',
                            'text':  sh_text,
                            'level': 'Чадвар',
                            'score': (c_on // c_dt) if c_dt else 2,
                            'd_too': c_dt,
                            'd_onoo': c_on
                        })
                    if x_dt > 0:
                        cur_surd['shalguur'].append({
                            'id':    sh_base_id + '_x',
                            'text':  sh_text,
                            'level': 'Хэрэглээ',
                            'score': (x_on // x_dt) if x_dt else 3,
                            'd_too': x_dt,
                            'd_onoo': x_on
                        })

                    # Хэрвээ ямар ч тоо олдоогүй бол Мэдлэг ойлголт-аар нэмэх
                    if m_dt == 0 and c_dt == 0 and x_dt == 0:
                        cur_surd['shalguur'].append({
                            'id':    sh_base_id,
                            'text':  sh_text,
                            'level': 'Мэдлэг ойлголт',
                            'score': 1,
                            'd_too': 1,
                            'd_onoo': 1
                        })

    return nj_list


def _find_col(headers, keywords):
    """Header массиваас keyword агуулсан баганын индекс олох"""
    for i, h in enumerate(headers):
        h_low = (h or '').lower()
        if any(k in h_low for k in keywords):
            return i
    return 0


def _to_int(val):
    try:
        return int(str(val).strip()) if val else 0
    except (ValueError, TypeError):
        return 0


# ═══════════════════════════════════════════════════════════════════
# FIREBASE ХАДГАЛАХ
# ═══════════════════════════════════════════════════════════════════

def save_blueprint_to_firebase(subject, grade, nj_list):
    """
    Firebase-д блюпринт хадгалах.
    Collection: blueprints
    Document:   {subject}_{grade}
    """
    db = get_db()
    doc_id = f"{subject}_{grade}".replace(' ', '_').replace('/', '_')
    db.collection('blueprints').document(doc_id).set({
        'subject': subject,
        'grade':   str(grade),
        'nj':      nj_list,
        'updated': fb_firestore.SERVER_TIMESTAMP
    })
    print(f"✓ Хадгаллаа: blueprints/{doc_id} — {len(nj_list)} нэгж")


def import_blueprint_pdf(pdf_path, subject, grade):
    """
    PDF-с задлаад Firebase-д хадгалах.
    Жишээ:
        import_blueprint_pdf('2025_blueprint.pdf', 'Математик', 9)
    """
    print(f"PDF задалж байна: {pdf_path}")
    nj_list = parse_blueprint_pdf(pdf_path, subject, grade)
    print(f"Олдсон нэгж: {len(nj_list)}")
    for nj in nj_list:
        total_sh = sum(len(s['shalguur']) for s in nj.get('surd', []))
        print(f"  • {nj['name']}: {len(nj.get('surd',[]))} үр дүн, {total_sh} шалгуур")
    save_blueprint_to_firebase(subject, grade, nj_list)
    return nj_list


# ═══════════════════════════════════════════════════════════════════
# FLASK ENDPOINT — /api/get-blueprint
# ═══════════════════════════════════════════════════════════════════

def get_blueprint_route():
    """
    GET /api/get-blueprint?subject=Математик&grade=9
    Returns: { blueprint: [ {id, name, surd:[{id,name,shalguur:[...]}]} ] }
    """
    subject = request.args.get('subject', '')
    grade   = request.args.get('grade', '')

    if not subject:
        return jsonify({'error': 'subject заавал шаардлагатай'}), 400

    try:
        db = get_db()
        doc_id = f"{subject}_{grade}".replace(' ', '_').replace('/', '_')
        doc = db.collection('blueprints').document(doc_id).get()

        if doc.exists:
            data = doc.to_dict()
            return jsonify({'blueprint': data.get('nj', [])})

        # Grade-гүй хайх (fallback)
        doc2 = db.collection('blueprints').document(subject.replace(' ', '_')).get()
        if doc2.exists:
            data = doc2.to_dict()
            return jsonify({'blueprint': data.get('nj', [])})

        # Олдсонгүй
        return jsonify({
            'blueprint': [],
            'warning': f'{subject} хичээлийн блюпринт Firebase-д байхгүй байна. '
                       f'import_blueprint_pdf() ашиглан нэмнэ үү.'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ═══════════════════════════════════════════════════════════════════
# APP.PY-Д НЭМЭХ ЖИШЭЭ
# ═══════════════════════════════════════════════════════════════════
"""
from blueprint_data import get_blueprint_route, import_blueprint_pdf

# Route бүртгэх
app.add_url_rule('/api/get-blueprint', 'get_blueprint', get_blueprint_route, methods=['GET'])

# PDF-с блюпринт оруулах (нэг удаа ажиллуулна):
# import_blueprint_pdf('2025-Улсын-шалгалт-Дэлгэрэнгүй-Блюпринт.pdf', 'Математик', 9)
# import_blueprint_pdf('2025-Улсын-шалгалт-Дэлгэрэнгүй-Блюпринт.pdf', 'Математик', 5)
# import_blueprint_pdf('2025-Улсын-шалгалт-Дэлгэрэнгүй-Блюпринт.pdf', 'Монгол хэл', 9)
# ... гэх мэт хичээл тус бүрт
"""


# ═══════════════════════════════════════════════════════════════════
# /api/generate-exam — шинэ blueprint_rows параметрийг дэмжих
# ═══════════════════════════════════════════════════════════════════
"""
generate-exam endpoint-д blueprint_rows нэмэгдсэн тул backend-д дараах өөрчлөлт хийнэ:

payload = {
  grade: 9,
  subject: "Математик",
  exam_id: "devshih",
  blueprint_rows: [          # ← ШИНЭ
    {
      njName: "Тоон олонлог",
      shText: "Иррационал тоог таньдаг...",
      count: 1,
      score: 1,
      level: "М"             # "М"|"Ч"|"Х"
    },
    ...
  ],
  use_ai: true
}

Flask backend-д:
    blueprint_rows = data.get('blueprint_rows', [])
    # count тус бүрт тухайн шалгуурт тохирох даалгавар сонгоно
    for row in blueprint_rows:
        questions = db.collection('questions')
            .where('subject', '==', subject)
            .where('grade', '==', grade)
            .where('shalguur_text', '==', row['shText'])
            .where('level', '==', level_full(row['level']))
            .limit(row['count']).get()
        # Хүрэлцэхгүй бол AI нэмэх
"""
