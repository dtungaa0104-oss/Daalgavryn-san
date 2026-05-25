from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import os, sqlite3, random
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "orkhontul-ebs-2025")
DB_PATH        = os.environ.get("DB_PATH", "questions.db")

# ══════════════════════════════════════════════════════════
#  ШАЛГАЛТЫН БҮТЭЦ — Монгол ЕБС-ийн бодит стандарт
# ══════════════════════════════════════════════════════════
EXAM_TYPES = {
    "ulsiin": {
        "id":     "ulsiin",
        "name":   "Улсын шалгалт",
        "icon":   "🏆",
        "color":  "#f0a500",
        "grades": [5, 9, 12],
        "blueprint": {
            "total": 40, "duration": "90 минут",
            "Хялбар": 12, "Дунд": 16, "Хүнд": 12,
            "note": "Улсын журмын албан ёсны шалгалт"
        }
    },
    "devshih": {
        "id":     "devshih",
        "name":   "Анги дэвших шалгалт",
        "icon":   "📋",
        "color":  "#3b82f6",
        "grades": [3, 4, 6, 7, 8, 10, 11],
        "blueprint": {
            "total": 25, "duration": "60 минут",
            "Хялбар": 8, "Дунд": 10, "Хүнд": 7,
            "note": "Дараагийн анги руу дэвших шалгалт"
        }
    },
    "guitsegdel": {
        "id":     "guitsegdel",
        "name":   "Гүйцэтгэлийн үнэлгээ",
        "icon":   "📝",
        "color":  "#22c55e",
        "grades": list(range(2, 12)),   # 2–11-р анги
        "blueprint": {
            "total": 10, "duration": "30 минут",
            "Хялбар": 4, "Дунд": 4, "Хүнд": 2,
            "note": "Оноогоор дүгнэхгүй — гүйцэтгэлийн үнэлгээ"
        }
    },
    "elselt": {
        "id":     "elselt",
        "name":   "Элсэлтийн шалгалт",
        "icon":   "🎓",
        "color":  "#a855f7",
        "grades": [12],
        "blueprint": {
            "total": 40, "duration": "90 минут",
            "Хялбар": 10, "Дунд": 18, "Хүнд": 12,
            "note": "1 буруу = −0.2 оноо · Нийт 100 оноо"
        }
    },
}

# Анги → шалгалтын төрлийн харилцаа
GRADE_EXAM_MAP = {}
for eid, et in EXAM_TYPES.items():
    for g in et["grades"]:
        if g not in GRADE_EXAM_MAP:
            GRADE_EXAM_MAP[g] = eid
# 1-р анги → гүйцэтгэл байхгүй тул ulsiin-ийн ойрын
GRADE_EXAM_MAP[1] = "guitsegdel"

SUBJECTS = {
    "1-5":   ["Монгол хэл", "Математик", "Байгалийн ухаан", "Нийгэм судлал"],
    "6-9":   ["Монгол хэл", "Монгол уран зохиол", "Математик", "Физик",
               "Хими", "Биологи", "Газарзүй", "Түүх", "Англи хэл"],
    "10-12": ["Монгол хэл", "Монгол уран зохиол", "Математик", "Физик",
               "Хими", "Биологи", "Газарзүй", "Түүх", "Англи хэл", "Нийгмийн ухаан"]
}
DIFFICULTY = ["Хялбар", "Дунд", "Хүнд"]
BLOOM      = ["Мэдлэг", "Ойлголт", "Хэрэглээ", "Шинжилгээ", "Үнэлгээ", "Бүтээл"]
Q_TYPES    = ["Нэг сонголт", "Олон сонголт", "Нээлттэй", "Гүйцэтгэлийн"]
ADMIN_PW   = os.environ.get("ADMIN_PASSWORD", "orkhontul2025")

# ══ DB ═══════════════════════════════════════════════════
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            q_code TEXT UNIQUE,
            grade INTEGER NOT NULL,
            subject TEXT NOT NULL,
            difficulty TEXT NOT NULL,
            bloom TEXT NOT NULL,
            q_type TEXT NOT NULL,
            question TEXT NOT NULL,
            option_a TEXT, option_b TEXT, option_c TEXT, option_d TEXT,
            answer TEXT,
            score INTEGER DEFAULT 1,
            topic TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit(); conn.close()

init_db()

def row_to_dict(row):
    d = dict(row)
    d["options"] = (
        [f"А. {d['option_a']}", f"Б. {d['option_b']}",
         f"В. {d['option_c']}", f"Г. {d['option_d']}"]
        if d.get("option_a") else None
    )
    return d

# ══ Auth ══════════════════════════════════════════════════
def login_required(f):
    from functools import wraps
    @wraps(f)
    def dec(*a, **kw):
        if not session.get("admin"):
            return redirect(url_for("admin_login"))
        return f(*a, **kw)
    return dec

# ══ Public pages ══════════════════════════════════════════
@app.route("/")
def index():
    return render_template("index.html", subjects=SUBJECTS, exam_types=EXAM_TYPES)

@app.route("/questions")
def questions_page():
    return render_template("questions.html", subjects=SUBJECTS,
                           difficulties=DIFFICULTY, blooms=BLOOM, exam_types=EXAM_TYPES)

@app.route("/blueprint")
def blueprint_page():
    return render_template("blueprint.html",
        subjects=SUBJECTS, exam_types=EXAM_TYPES,
        difficulties=DIFFICULTY, blooms=BLOOM,
        grade_exam_map=GRADE_EXAM_MAP)

# ══ API ═══════════════════════════════════════════════════
@app.route("/api/questions")
def api_questions():
    grade      = request.args.get("grade", "")
    subject    = request.args.get("subject", "")
    difficulty = request.args.get("difficulty", "all")
    bloom      = request.args.get("bloom", "all")
    count      = int(request.args.get("count", 20))

    conn = get_db()
    sql, params = "SELECT * FROM questions WHERE 1=1", []
    if grade:      sql += " AND grade=?";      params.append(int(grade))
    if subject:    sql += " AND subject=?";    params.append(subject)
    if difficulty != "all": sql += " AND difficulty=?"; params.append(difficulty)
    if bloom != "all":      sql += " AND bloom=?";      params.append(bloom)
    sql += " ORDER BY RANDOM() LIMIT ?"
    params.append(count)
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return jsonify({"questions": [row_to_dict(r) for r in rows], "total": len(rows)})

@app.route("/api/generate-exam", methods=["POST"])
def generate_exam():
    data      = request.json
    grade     = data.get("grade", 9)
    subject   = data.get("subject", "Математик")
    exam_id   = data.get("exam_id", "devshih")
    blueprint = data.get("blueprint", {})

    et = EXAM_TYPES.get(exam_id, EXAM_TYPES["devshih"])
    bp = et["blueprint"]

    conn     = get_db()
    selected = []
    for diff in ["Хялбар", "Дунд", "Хүнд"]:
        cnt = int(blueprint.get(diff, bp.get(diff, 0)))
        if cnt <= 0:
            continue
        rows = conn.execute(
            "SELECT * FROM questions WHERE grade=? AND subject=? AND difficulty=?"
            " ORDER BY RANDOM() LIMIT ?",
            (grade, subject, diff, cnt)
        ).fetchall()
        selected.extend([row_to_dict(r) for r in rows])
    conn.close()

    if not selected:
        return jsonify({"error": f"{grade}-р ангийн '{subject}' хичээлийн даалгавар байхгүй байна. Admin панелаас нэмнэ үү."})

    return jsonify({
        "exam_id":        exam_id,
        "exam_type":      et["name"],
        "exam_icon":      et["icon"],
        "title":          f"{grade}-р ангийн {subject} — {et['name']}",
        "grade":          grade,
        "subject":        subject,
        "total_questions":len(selected),
        "total_score":    sum(q["score"] for q in selected),
        "duration":       bp["duration"],
        "note":           bp.get("note", ""),
        "questions":      selected,
    })

@app.route("/api/stats")
def stats():
    conn = get_db()
    total    = conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
    grades   = conn.execute("SELECT COUNT(DISTINCT grade) FROM questions").fetchone()[0]
    subjects = conn.execute("SELECT COUNT(DISTINCT subject) FROM questions").fetchone()[0]
    conn.close()
    return jsonify({"total_questions": total, "grades": grades or 12,
                    "subjects": subjects or 10, "blueprints": len(EXAM_TYPES)})

# ══ Admin ══════════════════════════════════════════════════
@app.route("/admin/login", methods=["GET","POST"])
def admin_login():
    error = None
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PW:
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
    by_diff = conn.execute("SELECT difficulty, COUNT(*) cnt FROM questions GROUP BY difficulty").fetchall()
    by_sub  = conn.execute("SELECT subject, COUNT(*) cnt FROM questions GROUP BY subject ORDER BY cnt DESC").fetchall()
    recent  = conn.execute("SELECT * FROM questions ORDER BY id DESC LIMIT 8").fetchall()
    conn.close()
    return render_template("admin_dashboard.html", total=total,
        by_diff=by_diff, by_sub=by_sub, recent=recent,
        subjects=SUBJECTS, difficulties=DIFFICULTY, blooms=BLOOM, q_types=Q_TYPES)

@app.route("/admin/add", methods=["GET","POST"])
@login_required
def admin_add():
    if request.method == "POST":
        f = request.form
        diff   = f["difficulty"]
        score  = 1 if diff=="Хялбар" else (2 if diff=="Дунд" else 3)
        q_code = f"Q{f['grade']}-{f['subject'][:3]}-{datetime.now().strftime('%f')}"
        conn   = get_db()
        conn.execute("""INSERT INTO questions
            (q_code,grade,subject,difficulty,bloom,q_type,question,
             option_a,option_b,option_c,option_d,answer,score,topic)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (q_code,int(f["grade"]),f["subject"],diff,f["bloom"],f["q_type"],f["question"],
             f.get("option_a"),f.get("option_b"),f.get("option_c"),f.get("option_d"),
             f.get("answer"),score,f.get("topic","")))
        conn.commit(); conn.close()
        return redirect(url_for("admin_list"))
    return render_template("admin_add.html", q=None,
        subjects=SUBJECTS, difficulties=DIFFICULTY, blooms=BLOOM, q_types=Q_TYPES)

@app.route("/admin/edit/<int:qid>", methods=["GET","POST"])
@login_required
def admin_edit(qid):
    conn = get_db()
    if request.method == "POST":
        f     = request.form
        score = 1 if f["difficulty"]=="Хялбар" else (2 if f["difficulty"]=="Дунд" else 3)
        conn.execute("""UPDATE questions SET grade=?,subject=?,difficulty=?,bloom=?,q_type=?,
            question=?,option_a=?,option_b=?,option_c=?,option_d=?,answer=?,score=?,topic=?
            WHERE id=?""",
            (int(f["grade"]),f["subject"],f["difficulty"],f["bloom"],f["q_type"],f["question"],
             f.get("option_a"),f.get("option_b"),f.get("option_c"),f.get("option_d"),
             f.get("answer"),score,f.get("topic",""),qid))
        conn.commit(); conn.close()
        return redirect(url_for("admin_list"))
    q = conn.execute("SELECT * FROM questions WHERE id=?", (qid,)).fetchone()
    conn.close()
    return render_template("admin_add.html", q=q,
        subjects=SUBJECTS, difficulties=DIFFICULTY, blooms=BLOOM, q_types=Q_TYPES)

@app.route("/admin/list")
@login_required
def admin_list():
    grade   = request.args.get("grade","")
    subject = request.args.get("subject","")
    diff    = request.args.get("difficulty","")
    conn    = get_db()
    sql, params = "SELECT * FROM questions WHERE 1=1", []
    if grade:   sql+=" AND grade=?";      params.append(int(grade))
    if subject: sql+=" AND subject=?";   params.append(subject)
    if diff:    sql+=" AND difficulty=?"; params.append(diff)
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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
