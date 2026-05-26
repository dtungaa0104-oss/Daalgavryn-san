import os, sqlite3, re
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, jsonify, redirect, url_for, session

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "orkhontul-ebs-2025")
DB_PATH        = os.environ.get("DB_PATH", "questions.db")

EXAM_TYPES = {
    "ulsiin": {
        "id":"ulsiin","name":"Улсын шалгалт","icon":"🏆","color":"#f0a500",
        "grades":[5,9,12],
        "blueprint":{"total":40,"duration":"90 минут",
                     "Мэдлэг ойлголт":12,"Чадвар":16,"Хэрэглээ":12,
                     "note":"Улсын журмын албан ёсны шалгалт"}
    },
    "devshih": {
        "id":"devshih","name":"Анги дэвших шалгалт","icon":"📋","color":"#3b82f6",
        "grades":[3,4,6,7,8,10,11],
        "blueprint":{"total":25,"duration":"60 минут",
                     "Мэдлэг ойлголт":8,"Чадвар":10,"Хэрэглээ":7,
                     "note":"Дараагийн анги руу дэвших шалгалт"}
    },
    "guitsegdel": {
        "id":"guitsegdel","name":"Гүйцэтгэлийн үнэлгээ","icon":"📝","color":"#22c55e",
        "grades":list(range(2,12)),
        "blueprint":{"total":10,"duration":"30 минут",
                     "Мэдлэг ойлголт":4,"Чадвар":4,"Хэрэглээ":2,
                     "note":"Оноогоор дүгнэхгүй — гүйцэтгэлийн үнэлгээ"}
    },
    "elselt": {
        "id":"elselt","name":"Элсэлтийн шалгалт","icon":"🎓","color":"#a855f7",
        "grades":[12],
        "blueprint":{"total":40,"duration":"90 минут",
                     "Мэдлэг ойлголт":10,"Чадвар":18,"Хэрэглээ":12,
                     "note":"1 буруу = −0.2 оноо · Нийт 100 оноо"}
    },
}

GRADE_EXAM_MAP = {}
for eid, et in EXAM_TYPES.items():
    for g in et["grades"]:
        if g not in GRADE_EXAM_MAP:
            GRADE_EXAM_MAP[g] = eid
GRADE_EXAM_MAP[1] = "guitsegdel"

SUBJECTS = {
    "1-5":   ["Монгол хэл, уран зохиол","Математик","Байгалийн ухаан","Нийгэм судлал"],
    "6-9":   ["Монгол хэл, уран зохиол","Физик","Хими","Биологи","Газарзүй","Түүх","Англи хэл"],
    "10-12": ["Монгол хэл, уран зохиол","Математик","Физик","Хими","Биологи","Газарзүй","Түүх","Англи хэл","Нийгмийн ухаан"]
}

# Бүх хичээлийн нэгдсэн жагсаалт (давхардалгүй, дарааллаар)
ALL_SUBJECTS = [
    "Монгол хэл, уран зохиол","Математик","Байгалийн ухаан","Нийгэм судлал",
    "Физик","Хими","Биологи","Газарзүй","Түүх","Англи хэл","Нийгмийн ухаан"
]

LEVELS      = ["Мэдлэг ойлголт","Чадвар","Хэрэглээ"]
BLOOM       = ["Мэдлэг","Ойлголт","Хэрэглээ","Шинжилгээ","Үнэлгээ","Бүтээл"]
Q_TYPES     = ["Нэг сонголт","Олон сонголт","Нээлттэй","Гүйцэтгэлийн","Олимпиад"]
ADMIN_PW    = os.environ.get("ADMIN_PASSWORD","orkhontul2025")
LEVEL_SCORE = {"Мэдлэг ойлголт":1,"Чадвар":2,"Хэрэглээ":3}

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        q_code TEXT UNIQUE, grade INTEGER NOT NULL, subject TEXT NOT NULL,
        level TEXT NOT NULL, bloom TEXT NOT NULL, q_type TEXT NOT NULL,
        question TEXT NOT NULL,
        option_a TEXT, option_b TEXT, option_c TEXT, option_d TEXT,
        answer TEXT, score INTEGER DEFAULT 1, topic TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
    try:
        conn.execute("ALTER TABLE questions ADD COLUMN level TEXT NOT NULL DEFAULT 'Мэдлэг ойлголт'")
    except: pass
    conn.commit(); conn.close()

init_db()

def row_to_dict(row):
    d = dict(row)
    d["options"] = (
        [f"А. {d['option_a']}",f"Б. {d['option_b']}",
         f"В. {d['option_c']}",f"Г. {d['option_d']}"]
        if d.get("option_a") else None)
    return d

def login_required(f):
    @wraps(f)
    def dec(*a,**kw):
        if not session.get("admin"):
            return redirect(url_for("admin_login"))
        return f(*a,**kw)
    return dec

# ══ PUBLIC ════════════════════════════════════════════════
@app.route("/")
def index():
    return render_template("index.html", subjects=SUBJECTS,
        all_subjects=ALL_SUBJECTS,
        exam_types=EXAM_TYPES, grade_exam_map=GRADE_EXAM_MAP)

@app.route("/questions")
def questions_page():
    return render_template("questions.html", subjects=SUBJECTS,
        all_subjects=ALL_SUBJECTS,
        levels=LEVELS, blooms=BLOOM,
        exam_types=EXAM_TYPES, grade_exam_map=GRADE_EXAM_MAP)

@app.route("/blueprint")
def blueprint_page():
    return render_template("blueprint.html", subjects=SUBJECTS,
        all_subjects=ALL_SUBJECTS,
        exam_types=EXAM_TYPES, levels=LEVELS,
        blooms=BLOOM, grade_exam_map=GRADE_EXAM_MAP)

@app.route("/olympiad")
def olympiad_page():
    return render_template("olympiad.html", subjects=SUBJECTS,
        all_subjects=ALL_SUBJECTS,
        levels=LEVELS, blooms=BLOOM, grade_exam_map=GRADE_EXAM_MAP)

@app.route("/interactive")
def interactive_page():
    return render_template("interactive.html", subjects=SUBJECTS,
        all_subjects=ALL_SUBJECTS,
        levels=LEVELS, blooms=BLOOM, grade_exam_map=GRADE_EXAM_MAP)

# ══ БОСГО ШАЛГАЛТ ═════════════════════════════════════════
@app.route("/mongol-bichig")
def mongol_bichig_page():
    conn = get_db()
    years = conn.execute(
        "SELECT DISTINCT topic FROM questions WHERE subject='Монгол хэл бичгийн босго шалгалт' ORDER BY topic DESC"
    ).fetchall()
    recent = conn.execute(
        "SELECT * FROM questions WHERE subject='Монгол хэл бичгийн босго шалгалт' ORDER BY id DESC LIMIT 20"
    ).fetchall()
    total = conn.execute(
        "SELECT COUNT(*) FROM questions WHERE subject='Монгол хэл бичгийн босго шалгалт'"
    ).fetchone()[0]
    conn.close()
    return render_template("mongol_bichig.html",
        years=[r['topic'] for r in years],
        recent=recent, total=total,
        levels=LEVELS, blooms=BLOOM)

@app.route("/api/update-topic")
def update_topic():
    subject = request.args.get("subject","")
    topic   = request.args.get("topic","")
    if not subject or not topic:
        return jsonify({"ok": False})
    conn = get_db()
    conn.execute(
        "UPDATE questions SET topic=? WHERE subject=? AND (topic IS NULL OR topic='')",
        (topic, subject))
    conn.commit(); conn.close()
    return jsonify({"ok": True})

# ══ API ═══════════════════════════════════════════════════
@app.route("/api/questions")
def api_questions():
    grade   = request.args.get("grade","")
    subject = request.args.get("subject","")
    level   = request.args.get("level","all")
    bloom   = request.args.get("bloom","all")
    q_type  = request.args.get("q_type","all")
    count   = int(request.args.get("count",20))
    conn=get_db(); sql,params="SELECT * FROM questions WHERE 1=1",[]
    if grade:         sql+=" AND grade=?";   params.append(int(grade))
    if subject:       sql+=" AND subject=?"; params.append(subject)
    if level!="all":  sql+=" AND level=?";   params.append(level)
    if bloom!="all":  sql+=" AND bloom=?";   params.append(bloom)
    if q_type!="all": sql+=" AND q_type=?";  params.append(q_type)
    sql+=" ORDER BY RANDOM() LIMIT ?"; params.append(count)
    rows=conn.execute(sql,params).fetchall(); conn.close()
    return jsonify({"questions":[row_to_dict(r) for r in rows],"total":len(rows)})

@app.route("/api/generate-exam",methods=["POST"])
def generate_exam():
    data=request.json; grade=data.get("grade",9); subject=data.get("subject","Математик")
    exam_id=data.get("exam_id","devshih"); blueprint=data.get("blueprint",{})
    use_ai=data.get("use_ai",True)
    et=EXAM_TYPES.get(exam_id,EXAM_TYPES["devshih"]); bp=et["blueprint"]
    conn=get_db(); selected=[]; ai_generated=0
    for lvl in LEVELS:
        cnt=int(blueprint.get(lvl,bp.get(lvl,0)))
        if cnt<=0: continue
        rows=conn.execute(
            "SELECT * FROM questions WHERE grade=? AND subject=? AND level=? ORDER BY RANDOM() LIMIT ?",
            (grade,subject,lvl,cnt)).fetchall()
        db_qs=[row_to_dict(r) for r in rows]
        selected.extend(db_qs)
        need=cnt-len(db_qs)
        if need>0 and use_ai:
            api_key=os.environ.get("ANTHROPIC_API_KEY","")
            if api_key:
                try:
                    import anthropic,json as _json
                    score=LEVEL_SCORE.get(lvl,1)
                    prompt=f"""Та Монгол боловсролын {grade}-р ангийн {subject} хичээлийн багш.
Блупринтийн түвшин: {lvl}
{need} даалгавар зохио. Зөвхөн JSON array буцаа, тайлбаргүй.
Формат: [{{"question":"...","option_a":"...","option_b":"...","option_c":"...","option_d":"...","answer":"А"}}]
Монгол хэлээр."""
                    client=anthropic.Anthropic(api_key=api_key)
                    msg=client.messages.create(model="claude-sonnet-4-5",max_tokens=3000,
                        messages=[{"role":"user","content":prompt}])
                    raw=msg.content[0].text.strip()
                    raw=re.sub(r'^```json\s*','',raw); raw=re.sub(r'^```\s*','',raw); raw=re.sub(r'\s*```$','',raw).strip()
                    ai_qs=_json.loads(raw)
                    if not isinstance(ai_qs,list): ai_qs=[ai_qs]
                    for idx,q in enumerate(ai_qs[:need]):
                        q_code=f"Q{grade}-{subject[:2]}-AI-{datetime.now().strftime('%f')}-{idx}"
                        try:
                            conn.execute("""INSERT INTO questions(q_code,grade,subject,level,bloom,q_type,
                                question,option_a,option_b,option_c,option_d,answer,score,topic)
                                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                                (q_code,grade,subject,lvl,'Мэдлэг','Нэг сонголт',q.get('question',''),
                                 q.get('option_a'),q.get('option_b'),q.get('option_c'),q.get('option_d'),
                                 q.get('answer','А'),score,''))
                            conn.commit()
                            saved=conn.execute("SELECT * FROM questions WHERE q_code=?",(q_code,)).fetchone()
                            if saved:
                                selected.append(row_to_dict(saved))
                                ai_generated+=1
                        except: pass
                except: pass
    conn.close()
    if not selected:
        api_key=os.environ.get("ANTHROPIC_API_KEY","")
        if not api_key:
            return jsonify({"error":f"{grade}-р ангийн '{subject}' даалгавар байхгүй. ANTHROPIC_API_KEY тохируулна уу."})
        return jsonify({"error":f"{grade}-р ангийн '{subject}' даалгавар үүсгэж чадсангүй."})
    msg_parts=[]
    db_count=len(selected)-ai_generated
    if db_count>0: msg_parts.append(f"DB: {db_count}")
    if ai_generated>0: msg_parts.append(f"AI: {ai_generated}")
    return jsonify({"exam_id":exam_id,"exam_type":et["name"],"exam_icon":et["icon"],
        "title":f"{grade}-р ангийн {subject} — {et['name']}","grade":grade,"subject":subject,
        "total_questions":len(selected),"total_score":sum(q["score"] for q in selected),
        "duration":bp["duration"],"note":bp.get("note",""),
        "ai_generated":ai_generated,
        "source_note":" · ".join(msg_parts) if msg_parts else "",
        "questions":selected})

@app.route("/api/stats")
def stats():
    conn=get_db()
    total=conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
    grades=conn.execute("SELECT COUNT(DISTINCT grade) FROM questions").fetchone()[0]
    subjects=conn.execute("SELECT COUNT(DISTINCT subject) FROM questions").fetchone()[0]
    conn.close()
    return jsonify({"total_questions":total,"grades":grades or 12,
                    "subjects":subjects or 10,"blueprints":len(EXAM_TYPES)})

# ══ ADMIN ═════════════════════════════════════════════════
@app.route("/admin/login",methods=["GET","POST"])
def admin_login():
    error=None
    if request.method=="POST":
        if request.form.get("password")==ADMIN_PW:
            session["admin"]=True; return redirect(url_for("admin_dashboard"))
        error="Нууц үг буруу байна!"
    return render_template("admin_login.html",error=error)

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin",None); return redirect(url_for("admin_login"))

@app.route("/admin")
@login_required
def admin_dashboard():
    conn=get_db()
    total=conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
    by_level=conn.execute("SELECT level,COUNT(*) cnt FROM questions GROUP BY level").fetchall()
    by_sub=conn.execute("SELECT subject,COUNT(*) cnt FROM questions GROUP BY subject ORDER BY cnt DESC").fetchall()
    recent=conn.execute("SELECT * FROM questions ORDER BY id DESC LIMIT 8").fetchall()
    conn.close()
    return render_template("admin_dashboard.html",total=total,by_level=by_level,
        by_sub=by_sub,recent=recent,subjects=SUBJECTS,
        all_subjects=ALL_SUBJECTS,levels=LEVELS,blooms=BLOOM,q_types=Q_TYPES)

@app.route("/admin/add",methods=["GET","POST"])
@login_required
def admin_add():
    if request.method=="POST":
        f=request.form; lvl=f["level"]; score=LEVEL_SCORE.get(lvl,1)
        q_code=f"Q{f['grade']}-{f['subject'][:3]}-{datetime.now().strftime('%f')}"
        conn=get_db()
        conn.execute("""INSERT INTO questions(q_code,grade,subject,level,bloom,q_type,question,
            option_a,option_b,option_c,option_d,answer,score,topic)VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (q_code,int(f["grade"]),f["subject"],lvl,f["bloom"],f["q_type"],f["question"],
             f.get("option_a"),f.get("option_b"),f.get("option_c"),f.get("option_d"),
             f.get("answer"),score,f.get("topic","")))
        conn.commit(); conn.close(); return redirect(url_for("admin_list"))
    return render_template("admin_add.html",q=None,
        subjects=SUBJECTS,
        all_subjects=ALL_SUBJECTS,levels=LEVELS,blooms=BLOOM,q_types=Q_TYPES)

@app.route("/admin/edit/<int:qid>",methods=["GET","POST"])
@login_required
def admin_edit(qid):
    conn=get_db()
    if request.method=="POST":
        f=request.form; lvl=f["level"]; score=LEVEL_SCORE.get(lvl,1)
        conn.execute("""UPDATE questions SET grade=?,subject=?,level=?,bloom=?,q_type=?,
            question=?,option_a=?,option_b=?,option_c=?,option_d=?,answer=?,score=?,topic=? WHERE id=?""",
            (int(f["grade"]),f["subject"],lvl,f["bloom"],f["q_type"],f["question"],
             f.get("option_a"),f.get("option_b"),f.get("option_c"),f.get("option_d"),
             f.get("answer"),score,f.get("topic",""),qid))
        conn.commit(); conn.close(); return redirect(url_for("admin_list"))
    q=conn.execute("SELECT * FROM questions WHERE id=?",(qid,)).fetchone(); conn.close()
    return render_template("admin_add.html",q=q,
        subjects=SUBJECTS,
        all_subjects=ALL_SUBJECTS,levels=LEVELS,blooms=BLOOM,q_types=Q_TYPES)

@app.route("/admin/list")
@login_required
def admin_list():
    grade=request.args.get("grade",""); subject=request.args.get("subject","")
    lvl=request.args.get("level","")
    conn=get_db(); sql,params="SELECT * FROM questions WHERE 1=1",[]
    if grade:   sql+=" AND grade=?";   params.append(int(grade))
    if subject: sql+=" AND subject=?"; params.append(subject)
    if lvl:     sql+=" AND level=?";   params.append(lvl)
    sql+=" ORDER BY id DESC"
    rows=conn.execute(sql,params).fetchall(); conn.close()
    return render_template("admin_list.html",questions=rows,subjects=SUBJECTS,
        all_subjects=ALL_SUBJECTS,levels=LEVELS,
        sel_grade=grade,sel_subject=subject,sel_level=lvl)

@app.route("/admin/delete/<int:qid>",methods=["POST"])
@login_required
def admin_delete(qid):
    conn=get_db(); conn.execute("DELETE FROM questions WHERE id=?",(qid,))
    conn.commit(); conn.close(); return redirect(url_for("admin_list"))

@app.route("/admin/import",methods=["GET","POST"])
@login_required
def admin_import():
    if request.method=="POST":
        from file_importer import extract_from_pdf,extract_from_docx,parse_raw_text
        f=request.files.get("file"); grade=int(request.form.get("grade",9))
        subject=request.form.get("subject","Математик")
        # default_level өгөгдөөгүй бол автоматаар тодорхойлно
        lvl=request.form.get("default_level","auto")
        if not f or f.filename=="":
            return jsonify({"error":"Файл сонгоогүй байна"}),400
        file_bytes=f.read(); fname=f.filename.lower()
        try:
            if fname.endswith(".pdf"):             raw=extract_from_pdf(file_bytes)
            elif fname.endswith((".docx",".doc")): raw=extract_from_docx(file_bytes)
            elif fname.endswith(".txt"):            raw=file_bytes.decode("utf-8",errors="ignore")
            else: return jsonify({"error":"PDF, Word (.docx), эсвэл .txt файл оруулна уу"}),400
            questions=parse_raw_text(raw,grade,subject,lvl)
            if not questions:
                return jsonify({"error":"Даалгавар илрүүлж чадсангүй."}),400
            conn=get_db(); saved=skipped=0
            for q in questions:
                try:
                    conn.execute("""INSERT INTO questions(q_code,grade,subject,level,bloom,q_type,
                        question,option_a,option_b,option_c,option_d,answer,score,topic)
                        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (q['q_code'],q['grade'],q['subject'],q.get('level',lvl),q['bloom'],q['q_type'],
                         q['question'],q['option_a'],q['option_b'],q['option_c'],q['option_d'],
                         q['answer'],q['score'],q['topic']))
                    saved+=1
                except: skipped+=1
            conn.commit(); conn.close()
            return jsonify({"success":True,"saved":saved,"skipped":skipped,"preview":questions[:3]})
        except Exception as e:
            return jsonify({"error":f"Файл уншихад алдаа: {str(e)}"}),500
    return render_template("admin_import.html",subjects=SUBJECTS,
        all_subjects=ALL_SUBJECTS,levels=LEVELS)

@app.route("/admin/ai-generate",methods=["GET","POST"])
@login_required
def admin_ai_generate():
    if request.method=="POST":
        import anthropic,json as _json
        grade=int(request.form.get("grade",9)); subject=request.form.get("subject","Математик")
        topic=request.form.get("topic",""); lvl=request.form.get("level","Мэдлэг ойлголт")
        bloom=request.form.get("bloom","Мэдлэг"); q_type=request.form.get("q_type","Нэг сонголт")
        count=min(int(request.form.get("count",5)),20)
        api_key=os.environ.get("ANTHROPIC_API_KEY","")
        if not api_key:
            return jsonify({"error":"ANTHROPIC_API_KEY тохируулаагүй."}),400
        has_options=q_type in("Нэг сонголт","Олон сонголт")
        score=LEVEL_SCORE.get(lvl,1)
        prompt=f"""Та Монгол боловсролын {grade}-р ангийн {subject} хичээлийн багш.
{"Сэдэв: "+topic if topic else ""}
Блупринтийн түвшин: {lvl} | Блумын шат: {bloom} | Төрөл: {q_type}
{count} даалгавар зохио. Зөвхөн JSON array буцаа, тайлбаргүй.
Формат: [{{"question":"...","option_a":"...","option_b":"...","option_c":"...","option_d":"...","answer":"А","topic":"{topic or subject}"}}]
{"Нээлттэй бол option_a..d = null." if not has_options else ""}
Монгол хэлээр."""
        try:
            client=anthropic.Anthropic(api_key=api_key)
            msg=client.messages.create(model="claude-sonnet-4-5",max_tokens=4000,
                messages=[{"role":"user","content":prompt}])
            raw_text=msg.content[0].text.strip()
            raw_text=re.sub(r'^```json\s*','',raw_text)
            raw_text=re.sub(r'^```\s*','',raw_text)
            raw_text=re.sub(r'\s*```$','',raw_text).strip()
            ai_qs=_json.loads(raw_text)
            if not isinstance(ai_qs,list): ai_qs=[ai_qs]
            conn=get_db(); saved=0
            for idx,q in enumerate(ai_qs):
                q_code=f"Q{grade}-{subject[:2]}-AI-{datetime.now().strftime('%f')}-{idx}"
                try:
                    conn.execute("""INSERT INTO questions(q_code,grade,subject,level,bloom,q_type,
                        question,option_a,option_b,option_c,option_d,answer,score,topic)
                        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (q_code,grade,subject,lvl,bloom,q_type,q.get('question',''),
                         q.get('option_a'),q.get('option_b'),q.get('option_c'),q.get('option_d'),
                         q.get('answer','А'),score,q.get('topic',topic)))
                    saved+=1
                except: pass
            conn.commit(); conn.close()
            return jsonify({"success":True,"saved":saved,"questions":ai_qs})
        except _json.JSONDecodeError as e:
            return jsonify({"error":f"JSON алдаа: {str(e)}"}),500
        except Exception as e:
            return jsonify({"error":str(e)}),500
    return render_template("admin_ai_generate.html",
        subjects=SUBJECTS,
        all_subjects=ALL_SUBJECTS,levels=LEVELS,blooms=BLOOM,q_types=Q_TYPES)


# ══ БАГШ ТАНД ══════════════════════════════════════════════
@app.route("/teacher")
def teacher_page():
    return render_template("teacher.html",
        subjects=SUBJECTS, all_subjects=ALL_SUBJECTS,
        levels=LEVELS, blooms=BLOOM)

@app.route("/api/teacher-ai", methods=["POST"])
def teacher_ai():
    import anthropic, json as _json
    data    = request.json
    prompt  = data.get("prompt","")
    api_key = os.environ.get("ANTHROPIC_API_KEY","")
    if not api_key:
        return jsonify({"error":"ANTHROPIC_API_KEY тохируулаагүй. Render → Environment-д нэмнэ үү."}), 400
    if not prompt:
        return jsonify({"error":"Prompt хоосон байна"}), 400
    try:
        client  = anthropic.Anthropic(api_key=api_key)
        msg     = client.messages.create(
            model="claude-sonnet-4-5", max_tokens=3000,
            messages=[{"role":"user","content": prompt}])
        result  = msg.content[0].text.strip()
        return jsonify({"result": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ══ ЧАТБОТ ════════════════════════════════════════════════
@app.route("/api/chat", methods=["POST"])
def chatbot():
    import anthropic
    data     = request.json
    messages = data.get("messages", [])
    api_key  = os.environ.get("ANTHROPIC_API_KEY","")
    if not api_key:
        return jsonify({"error":"API тохируулаагүй"}), 400
    if not messages:
        return jsonify({"error":"Мессеж хоосон"}), 400
    try:
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1000,
            system="""Та Орхонтуул ЕБС-ийн ухаалаг туслах чатбот.
Сурагч, багш нарт дараах чиглэлээр туслана:
- Математик, физик, хими, биологи, монгол хэл болон бусад хичээлийн тайлбар
- Даалгавар бодоход тусламж (хариулт шууд өгөхгүй, зааварчилгаа өгнө)
- Шалгалтад бэлтгэх зөвлөгөө
- Ерөнхий боловсролын асуултанд хариулах
Монгол хэлээр товч, тод хариулна. Найрсаг, урамшуулах өнгө аяс хадгална.""",
            messages=messages
        )
        return jsonify({"reply": msg.content[0].text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ══ START ══════════════════════════════════════════════════
if __name__=="__main__":
    port=int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0",port=port)
