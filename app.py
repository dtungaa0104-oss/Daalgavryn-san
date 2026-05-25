from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import os, random, sqlite3
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "orkhontul-ebs-2025-secret")
DB_PATH = os.environ.get("DB_PATH", "questions.db")

# ═══════════════════════════════════════════════════════
#  ТОГТМОЛ УТГУУД — Монгол ЕБС-ийн бүтэцтэй тааруулсан
# ═══════════════════════════════════════════════════════

SUBJECTS = {
    "1-5":  ["Монгол хэл", "Математик", "Байгалийн ухаан", "Нийгэм судлал"],
    "6-9":  ["Монгол хэл", "Монгол уран зохиол", "Математик", "Физик",
             "Хими", "Биологи", "Газарзүй", "Түүх", "Англи хэл"],
    "10-12":["Монгол хэл", "Монгол уран зохиол", "Математик", "Физик",
             "Хими", "Биологи", "Газарзүй", "Түүх", "Англи хэл", "Нийгмийн ухаан"]
}

DIFFICULTY = ["Хялбар", "Дунд", "Хүнд"]
BLOOM      = ["Мэдлэг", "Ойлголт", "Хэрэглээ", "Шинжилгээ", "Үнэлгээ", "Бүтээл"]
Q_TYPES    = ["Нэг сонголт", "Олон сонголт", "Нээлттэй", "Гүйцэтгэлийн"]

# ── Шалгалтын төрлүүд ────────────────────────────────────────────────────────
EXAM_TYPES = {
    "ulsiin": {
        "id":      "ulsiin",
        "name":    "Улсын шалгалт",
        "icon":    "🏆",
        "grades":  [5, 9, 12],
        "color":   "#f0a500",
        "desc":    "5, 9, 12-р ангийн улсын журмын шалгалт",
        "blueprint": {"Хялбар": 12, "Дунд": 16, "Хүнд": 12,
                      "total": 40, "duration": "90 минут", "score": 72},
    },
    "devshih": {
        "id":      "devshih",
        "name":    "Анги дэвших шалгалт",
        "icon":    "📋",
        "grades":  [6, 7, 8, 10, 11],
        "color":   "#3b82f6",
        "desc":    "6, 7, 8, 10, 11-р ангийн дэвших шалгалт",
        "blueprint": {"Хялбар": 8, "Дунд": 10, "Хүнд": 7,
                      "total": 25, "duration": "60 минут", "score": 49},
    },
    "guitsegdel": {
        "id":      "guitsegdel",
        "name":    "Гүйцэтгэлийн үнэлгээ",
        "icon":    "📝",
        "grades":  [1, 2, 3, 4],
        "color":   "#22c55e",
        "desc":    "1–4-р ангийн дотоод гүйцэтгэлийн үнэлгээ. Нормчилсон оноогүй.",
        "blueprint": {"Хялбар": 5, "Дунд": 5, "Хүнд": 0,
                      "total": 10, "duration": "30 минут", "score": 10,
                      "note": "Оноогүй, ажиглалтын дэвтэр хөтлөнө"},
    },
    "elselt": {
        "id":      "elselt",
        "name":    "Элсэлтийн шалгалт",
        "icon":    "🎓",
        "grades":  [12],          # 12-р ангийн дараа ИДС
        "color":   "#a855f7",
        "desc":    "Их, дээд сургуульд элсэх ЭЕШ (МИС)-ийн загвар шалгалт",
        "blueprint": {"Хялбар": 10, "Дунд": 20, "Хүнд": 10,
                      "total": 40, "duration": "90 минут", "score": 100,
                      "note": "100 оноо. Нэг буруу = -0.2 оноо"},
    },
}

# Ангийн → шалгалтын төрлийн харьцаа
GRADE_EXAM_MAP = {}
for etype in EXAM_TYPES.values():
    for g in etype["grades"]:
        GRADE_EXAM_MAP[g] = etype["id"]

def get_exam_for_grade(grade: int) -> dict:
    eid = GRADE_EXAM_MAP.get(grade, "guitsegdel")
    return EXAM_TYPES[eid]

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "orkhontul2025")

# ═══════════════════════════════════════════════════════
#  DATABASE
# ═══════════════════════════════════════════════════════
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            q_code      TEXT UNIQUE,
            grade       INTEGER NOT NULL,
            subject     TEXT NOT NULL,
            difficulty  TEXT NOT NULL,
            bloom       TEXT NOT NULL,
            q_type      TEXT NOT NULL,
            question    TEXT NOT NULL,
            option_a    TEXT,
            option_b    TEXT,
            option_c    TEXT,
            option_d    TEXT,
            answer      TEXT,
            score       INTEGER DEFAULT 1,
            topic       TEXT,
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ── Auth ──────────────────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated

def row_to_dict(row):
    d = dict(row)
    if d.get("option_a"):
        d["options"] = [f"А. {d['option_a']}", f"Б. {d['option_b']}",
                        f"В. {d['option_c']}", f"Г. {d['option_d']}"]
    else:
        d["options"] = None
    return d

# ═══════════════════════════════════════════════════════
#  PUBLIC ROUTES
# ═══════════════════════════════════════════════════════
@app.route("/")
def index():
    return render_template("index.html",
        subjects=SUBJECTS, exam_types=EXAM_TYPES,
        grade_exam_map=GRADE_EXAM_MAP)

@app.route("/questions")
def questions_page():
    return render_template("questions.html",
        subjects=SUBJECTS, difficulties=DIFFICULTY,
        blooms=BLOOM, exam_types=EXAM_TYPES)

@app.route("/blueprint")
def blueprint_page():
    return render_template("blueprint.html",
        subjects=SUBJECTS, exam_types=EXAM_TYPES,
        blooms=BLOOM, difficulties=DIFFICULTY,
        grade_exam_map=GRADE_EXAM_MAP)

# ═══════════════════════════════════════════════════════
#  API
# ═══════════════════════════════════════════════════════
@app.route("/api/questions")
def api_questions():
    grade      = request.args.get("grade", "")
    subject    = request.args.get("subject", "")
    difficulty = request.args.get("difficulty", "all")
    bloom      = request.args.get("bloom", "all")
    count      = int(request.args.get("count", 20))

    conn   = get_db()
    sql    = "SELECT * FROM questions WHERE 1=1"
    params = []
    if grade:             sql += " AND grade=?";      params.append(int(grade))
    if subject:           sql += " AND subject=?";    params.append(subject)
    if difficulty != "all": sql += " AND difficulty=?"; params.append(difficulty)
    if bloom != "all":    sql += " AND bloom=?";      params.append(bloom)
    sql += " ORDER BY RANDOM() LIMIT ?"
    params.append(count)
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return jsonify({"questions": [row_to_dict(r) for r in rows], "total": len(rows)})

@app.route("/api/grade-info/<int:grade>")
def grade_info(grade):
    et = get_exam_for_grade(grade)
    return jsonify({"grade": grade, "exam_type": et})

@app.route("/api/generate-exam", methods=["POST"])
def generate_exam():
    data      = request.json
    grade     = int(data.get("grade", 9))
    subject   = data.get("subject", "Математик")
    exam_id   = data.get("exam_id", "")
    custom_bp = data.get("blueprint", {})

    # Шалгалтын мэдээлэл
    if exam_id and exam_id in EXAM_TYPES:
        et = EXAM_TYPES[exam_id]
    else:
        et = get_exam_for_grade(grade)

    bp     = et["blueprint"]
    use_bp = custom_bp if custom_bp else {k: bp[k] for k in ["Хялбар","Дунд","Хүнд"]}

    conn     = get_db()
    selected = []
    for diff, cnt in use_bp.items():
        if int(cnt) == 0:
            continue
        rows = conn.execute(
            "SELECT * FROM questions WHERE grade=? AND subject=? AND difficulty=? ORDER BY RANDOM() LIMIT ?",
            (grade, subject, diff, int(cnt))
        ).fetchall()
        selected.extend([row_to_dict(r) for r in rows])

    # Дутвал нөхнө
    if len(selected) < bp.get("total", 10):
        gotten = [q["id"] for q in selected if "id" in q]
        need   = bp["total"] - len(selected)
        ph     = ",".join("?" * len(gotten)) if gotten else "0"
        extra  = conn.execute(
            f"SELECT * FROM questions WHERE grade=? AND subject=? AND id NOT IN ({ph}) ORDER BY RANDOM() LIMIT ?",
            [grade, subject] + gotten + [need]
        ).fetchall()
        selected.extend([row_to_dict(r) for r in extra])
    conn.close()

    return jsonify({
        "title":           f"{grade}-р ангийн {subject} — {et['name']}",
        "grade":           grade,
        "subject":         subject,
        "exam_type":       et["name"],
        "exam_id":         et["id"],
        "exam_icon":       et["icon"],
        "exam_color":      et["color"],
        "total_questions": len(selected),
        "total_score":     sum(q["score"] for q in selected),
        "duration":        bp.get("duration","60 минут"),
        "note":            bp.get("note",""),
        "blueprint":       use_bp,
        "questions":       selected,
    })

@app.route("/api/stats")
def stats():
    conn = get_db()
    total    = conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
    grades   = conn.execute("SELECT COUNT(DISTINCT grade) FROM questions").fetchone()[0]
    subjects = conn.execute("SELECT COUNT(DISTINCT subject) FROM questions").fetchone()[0]
    conn.close()
    return jsonify({"total_questions": total or 0, "grades": grades or 12,
                    "subjects": subjects or 10, "blueprints": len(EXAM_TYPES)})

# ═══════════════════════════════════════════════════════
#  ADMIN
# ═══════════════════════════════════════════════════════
@app.route("/admin/login", methods=["GET","POST"])
def admin_login():
    error = None
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect(url_for("admin_dashboard"))
        error = "Нууц үг буруу байна!"
    return render_template("admin_login.html", error=error)

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    return redirect(url_for("admin_login"))

@app.route("/admin")
@login_required
def admin_dashboard():
    conn    = get_db()
    total   = conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
    by_diff = conn.execute("SELECT difficulty, COUNT(*) as cnt FROM questions GROUP BY difficulty").fetchall()
    by_sub  = conn.execute("SELECT subject, COUNT(*) as cnt FROM questions GROUP BY subject ORDER BY cnt DESC").fetchall()
    recent  = conn.execute("SELECT * FROM questions ORDER BY id DESC LIMIT 8").fetchall()
    conn.close()
    return render_template("admin_dashboard.html",
        total=total, by_diff=by_diff, by_sub=by_sub, recent=recent,
        subjects=SUBJECTS, difficulties=DIFFICULTY, blooms=BLOOM, q_types=Q_TYPES)

@app.route("/admin/add", methods=["GET","POST"])
@login_required
def admin_add():
    if request.method == "POST":
        f      = request.form
        grade  = int(f["grade"])
        diff   = f["difficulty"]
        q_code = f"Q{grade}-{f['subject'][:3]}-{datetime.now().strftime('%H%M%S%f')}"
        score  = 1 if diff == "Хялбар" else (2 if diff == "Дунд" else 3)
        conn   = get_db()
        conn.execute("""
            INSERT INTO questions (q_code,grade,subject,difficulty,bloom,q_type,question,
                                   option_a,option_b,option_c,option_d,answer,score,topic)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (q_code, grade, f["subject"], diff, f["bloom"], f["q_type"], f["question"],
              f.get("option_a"), f.get("option_b"), f.get("option_c"), f.get("option_d"),
              f.get("answer"), score, f.get("topic","")))
        conn.commit(); conn.close()
        return redirect(url_for("admin_list"))
    return render_template("admin_add.html",
        subjects=SUBJECTS, difficulties=DIFFICULTY, blooms=BLOOM, q_types=Q_TYPES)

@app.route("/admin/list")
@login_required
def admin_list():
    grade   = request.args.get("grade","")
    subject = request.args.get("subject","")
    diff    = request.args.get("difficulty","")
    conn    = get_db()
    sql     = "SELECT * FROM questions WHERE 1=1"
    params  = []
    if grade:   sql += " AND grade=?";      params.append(int(grade))
    if subject: sql += " AND subject=?";    params.append(subject)
    if diff:    sql += " AND difficulty=?"; params.append(diff)
    sql += " ORDER BY id DESC"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return render_template("admin_list.html", questions=rows,
        subjects=SUBJECTS, difficulties=DIFFICULTY,
        sel_grade=grade, sel_subject=subject, sel_diff=diff)

@app.route("/admin/delete/<int:qid>", methods=["POST"])
@login_required
def admin_delete(qid):
    conn = get_db()
    conn.execute("DELETE FROM questions WHERE id=?", (qid,))
    conn.commit(); conn.close()
    return redirect(url_for("admin_list"))

@app.route("/admin/edit/<int:qid>", methods=["GET","POST"])
@login_required
def admin_edit(qid):
    conn = get_db()
    if request.method == "POST":
        f     = request.form
        score = 1 if f["difficulty"]=="Хялбар" else (2 if f["difficulty"]=="Дунд" else 3)
        conn.execute("""
            UPDATE questions SET grade=?,subject=?,difficulty=?,bloom=?,q_type=?,question=?,
            option_a=?,option_b=?,option_c=?,option_d=?,answer=?,score=?,topic=?
            WHERE id=?
        """, (int(f["grade"]), f["subject"], f["difficulty"], f["bloom"], f["q_type"],
              f["question"], f.get("option_a"), f.get("option_b"), f.get("option_c"),
              f.get("option_d"), f.get("answer"), score, f.get("topic",""), qid))
        conn.commit(); conn.close()
        return redirect(url_for("admin_list"))
    q = conn.execute("SELECT * FROM questions WHERE id=?", (qid,)).fetchone()
    conn.close()
    return render_template("admin_add.html", q=q,
        subjects=SUBJECTS, difficulties=DIFFICULTY, blooms=BLOOM, q_types=Q_TYPES)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
