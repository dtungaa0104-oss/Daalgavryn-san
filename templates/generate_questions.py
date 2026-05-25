"""
generate_questions.py  —  Орхонтуул ЕБС
AI-аар даалгавар автоматаар үүсгэж DB-д оруулах

Ажиллуулах:
  pip install anthropic
  set ANTHROPIC_API_KEY=sk-ant-...   (Windows)
  python generate_questions.py
"""

import os, json, sqlite3, time, sys

try:
    import anthropic
except ImportError:
    print("pip install anthropic"); sys.exit(1)

# ══════════════════════════════════════════════════════
#  ТОХИРГОО — энд өөрчлөнө
# ══════════════════════════════════════════════════════

DB_PATH = "questions.db"   # app.py-тай ижил хавтаст байх ёстой
DELAY   = 2                # API дуудлага хоорондын хүлээлт (сек)
BATCH   = 6                # Нэг дуудлагад хэдэн даалгавар

# Хичээл → зорилт ангиуд
PLAN = [
    ("Математик",       [3, 4, 6, 7, 8, 10, 11]),
    ("Монгол хэл",      [3, 4, 6, 7, 8, 10, 11]),
    ("Физик",           [6, 7, 8, 10, 11]),
    ("Хими",            [6, 7, 8, 10, 11]),
    ("Биологи",         [6, 7, 8, 10, 11]),
    ("Газарзүй",        [6, 7, 8, 10, 11]),
    ("Түүх",            [3, 4, 6, 7, 8, 10, 11]),
    ("Англи хэл",       [3, 4, 6, 7, 8, 10, 11]),
    ("Байгалийн ухаан", [3, 4]),
    ("Нийгэм судлал",   [3, 4, 6, 7]),
]

# Нэг (хичээл, анги) тус бүрд хэдэн даалгавар
# Хялбар:Дунд:Хүнд = 3:3:2 → 8 даалгавар
COUNTS = {"Хялбар": 3, "Дунд": 3, "Хүнд": 2}

# ══════════════════════════════════════════════════════

BLOOM = {
    "Хялбар": "Мэдлэг",
    "Дунд":   "Хэрэглээ",
    "Хүнд":   "Шинжилгээ",
}

DIFF_HINT = {
    "Хялбар": "Энгийн тодорхойлолт, ойлголт. 1 зөв сонголттой тест.",
    "Дунд":   "Тооцоолол, хэрэглэлт шаарддаг. 4 сонголттой тест.",
    "Хүнд":   "Шинжилгээ, нэгтгэл шаарддаг. Нээлттэй эсвэл 4 сонголт.",
}

PROMPT_TMPL = """\
Та {grade}-р ангийн "{subject}" хичээлийн мэргэжлийн багш.
{difficulty} ({hint}) түвшний {count} ширхэг даалгавар үүсгэнэ үү.
Блумын шат: {bloom}.

Дүрэм:
- Монгол хэл (Кирилл), {grade}-р ангийн түвшинд тохирсон
- "Нэг сонголт" даалгаварт option_a..d бөглөнө, answer нь А/Б/В/Г
- "Нээлттэй" даалгаварт option_a..d хоосон (""), answer нь товч текст
- Сонголтуудыг ойролцоо, бодохуйц байлга

Зөвхөн JSON массив буцаа. Өөр текст нэмэхгүй.

[
  {{
    "grade": {grade},
    "subject": "{subject}",
    "difficulty": "{difficulty}",
    "bloom": "{bloom}",
    "q_type": "Нэг сонголт",
    "question": "...",
    "option_a": "...",
    "option_b": "...",
    "option_c": "...",
    "option_d": "...",
    "answer": "А",
    "topic": "..."
  }}
]"""

def ensure_db(path):
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            grade      INTEGER NOT NULL,
            subject    TEXT NOT NULL,
            difficulty TEXT NOT NULL,
            bloom      TEXT,
            q_type     TEXT,
            question   TEXT NOT NULL,
            option_a   TEXT,
            option_b   TEXT,
            option_c   TEXT,
            option_d   TEXT,
            answer     TEXT,
            topic      TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )""")
    conn.commit()
    return conn

def call_api(client, subject, grade, diff, count):
    prompt = PROMPT_TMPL.format(
        grade=grade, subject=subject,
        difficulty=diff, hint=DIFF_HINT[diff],
        bloom=BLOOM[diff], count=count
    )
    try:
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=3000,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = msg.content[0].text.strip()
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"): raw = raw[4:]
        qs = json.loads(raw.strip())
        valid = []
        for q in qs:
            if not q.get("question"): continue
            for f in ["option_a","option_b","option_c","option_d"]:
                q[f] = q.get(f) or None
            valid.append(q)
        return valid
    except Exception as e:
        print(f"    ⚠ {e}")
        return []

def insert(conn, rows):
    conn.executemany("""
        INSERT INTO questions
          (grade,subject,difficulty,bloom,q_type,
           question,option_a,option_b,option_c,option_d,answer,topic)
        VALUES
          (:grade,:subject,:difficulty,:bloom,:q_type,
           :question,:option_a,:option_b,:option_c,:option_d,:answer,:topic)
    """, rows)
    conn.commit()

def main():
    key = os.environ.get("ANTHROPIC_API_KEY","")
    if not key:
        print("❌  ANTHROPIC_API_KEY тохируулаагүй.")
        print("    Windows:   set ANTHROPIC_API_KEY=sk-ant-...")
        print("    Mac/Linux: export ANTHROPIC_API_KEY=sk-ant-...")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=key)
    conn   = ensure_db(DB_PATH)

    total_combos = sum(len(g) for _,g in PLAN)
    q_per_combo  = sum(COUNTS.values())
    print(f"\n{'═'*55}")
    print(f"  Орхонтуул ЕБС — Даалгавар автомат үүсгэгч")
    print(f"{'═'*55}")
    print(f"  Нийт combo  : {total_combos}  ({len(PLAN)} хичээл × ангиуд)")
    print(f"  Combo тус бүр: {q_per_combo} даалгавар")
    print(f"  Нийт зорилго : ~{total_combos * q_per_combo} даалгавар")
    print(f"{'═'*55}\n")

    done = 0
    combo = 0
    t0 = time.time()

    for subject, grades in PLAN:
        for grade in grades:
            combo += 1
            print(f"[{combo}/{total_combos}] {grade}-р анги — {subject}")
            batch_rows = []

            for diff, count in COUNTS.items():
                # Batch-аар хуваах
                left = count
                while left > 0:
                    n = min(left, BATCH)
                    print(f"  {diff} ×{n} ...", end="", flush=True)
                    rows = call_api(client, subject, grade, diff, n)
                    batch_rows.extend(rows)
                    print(f" ✓ {len(rows)}")
                    left -= n
                    if left > 0: time.sleep(DELAY)
                time.sleep(DELAY)

            if batch_rows:
                insert(conn, batch_rows)
                done += len(batch_rows)
                print(f"  → DB-д {len(batch_rows)} орлоо  (нийт: {done})\n")
            else:
                print(f"  ⚠ Энэ combo-д даалгавар ирсэнгүй\n")

    elapsed = time.time() - t0
    print(f"{'═'*55}")
    print(f"  ✅ ДУУСЛАА — {done} даалгавар, {elapsed/60:.1f} мин")
    print(f"  DB: {os.path.abspath(DB_PATH)}")
    print(f"{'═'*55}")
    conn.close()

if __name__ == "__main__":
    main()
