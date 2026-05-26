import os, sqlite3, re
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, jsonify, redirect, url_for, session

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "orkhontul-ebs-2025")
DB_PATH        = os.environ.get("DB_PATH", "questions.db")

# ── Шалгалтын төрлүүд ─────────────────────────────────────────────────────────
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
    "1-5":   ["Монгол хэл","Математик","Байгалийн ухаан","Нийгэм судлал"],
    "6-9":   ["Монгол хэл","Монгол уран зохиол","Математик","Физик",
               "Хими","Биологи","Газарзүй","Түүх","Англи хэл"],
    "10-12": ["Монгол хэл","Монгол уран зохиол","Математик","Физик",
               "Хими","Биологи","Газарзүй","Түүх","Англи хэл","Нийгмийн ухаан"]
}

LEVELS      = ["Мэдлэг ойлголт","Чадвар","Хэрэглээ"]
BLOOM       = ["Мэдлэг","Ойлголт","Хэрэглээ","Шинжилгээ","Үнэлгээ","Бүтээл"]
Q_TYPES     = ["Нэг сонголт","Олон сонголт","Нээлттэй","Гүйцэтгэлийн"]
ADMIN_PW    = os.environ.get("ADMIN_PASSWORD","orkhontul2025")
LEVEL_SCORE = {"Мэдлэг ойлголт":1,"Чадвар":2,"Хэрэглээ":3}

# ── Олимпиадын өгөгдөл ────────────────────────────────────────────────────────
SUBJ_ICONS = {
    "Математик":"📐","Физик":"⚛️","Хими":"🧪","Биологи":"🌿",
    "Монгол хэл":"📝","Монгол уран зохиол":"📖","Газарзүй":"🌍",
    "Түүх":"🏛","Англи хэл":"🇬🇧","Нийгмийн ухаан":"⚖️",
    "Байгалийн ухаан":"🔬","Мэдээлэл зүй":"💻",
}
SUBJ_COLORS = {
    "Математик":"#2196F3","Физик":"#9C27B0","Хими":"#F44336","Биологи":"#4CAF50",
    "Монгол хэл":"#FF9800","Монгол уран зохиол":"#FF5722","Газарзүй":"#009688",
    "Түүх":"#795548","Англи хэл":"#3F51B5","Нийгмийн ухаан":"#607D8B",
    "Байгалийн ухаан":"#8BC34A","Мэдээлэл зүй":"#00BCD4",
}
OLYMPIAD_LEVELS = ["Сургуулийн шат","Дүүргийн шат","Аймгийн шат","Улсын шат"]
LEVEL_KEYS = {
    "Сургуулийн шат":"school","Дүүргийн шат":"district",
    "Аймгийн шат":"aimag","Улсын шат":"uls",
}

OLYMPIAD_MATERIALS = [
    # МАТЕМАТИК
    {"id":1,"subject":"Математик","year":"2024","level":"Улсын шат","level_key":"uls",
     "title":"2024 Математикийн улсын олимпиад",
     "desc":"Монгол улсын математикийн олимпиадын 2024 оны улсын шатны даалгавар",
     "icon":"📐","color":"#2196F3","file_url":"","answer_url":"","has_answer":False},
    {"id":2,"subject":"Математик","year":"2023","level":"Улсын шат","level_key":"uls",
     "title":"2023 Математикийн улсын олимпиад",
     "desc":"Монгол улсын математикийн олимпиадын 2023 оны улсын шатны даалгавар",
     "icon":"📐","color":"#2196F3","file_url":"","answer_url":"","has_answer":False},
    {"id":3,"subject":"Математик","year":"2023","level":"Аймгийн шат","level_key":"aimag",
     "title":"2023 Математик — Аймгийн шат",
     "desc":"2023 оны аймгийн олимпиадын математикийн даалгавар, хариулт",
     "icon":"📐","color":"#2196F3","file_url":"","answer_url":"","has_answer":True},
    {"id":4,"subject":"Математик","year":"2022","level":"Улсын шат","level_key":"uls",
     "title":"2022 Математикийн улсын олимпиад",
     "desc":"2022 оны улсын шатны математикийн бүрэн даалгавар",
     "icon":"📐","color":"#2196F3","file_url":"","answer_url":"","has_answer":True},
    # ФИЗИК
    {"id":5,"subject":"Физик","year":"2024","level":"Улсын шат","level_key":"uls",
     "title":"2024 Физикийн улсын олимпиад",
     "desc":"2024 оны физикийн улсын олимпиадын онолын болон практик даалгавар",
     "icon":"⚛️","color":"#9C27B0","file_url":"","answer_url":"","has_answer":False},
    {"id":6,"subject":"Физик","year":"2023","level":"Аймгийн шат","level_key":"aimag",
     "title":"2023 Физик — Аймгийн шат",
     "desc":"2023 оны аймгийн физикийн олимпиадын даалгавар",
     "icon":"⚛️","color":"#9C27B0","file_url":"","answer_url":"","has_answer":True},
    {"id":7,"subject":"Физик","year":"2022","level":"Улсын шат","level_key":"uls",
     "title":"2022 Физикийн улсын олимпиад",
     "desc":"2022 оны улсын шатны физикийн бүрэн даалгавар, хариулт",
     "icon":"⚛️","color":"#9C27B0","file_url":"","answer_url":"","has_answer":True},
    # ХИМИ
    {"id":8,"subject":"Хими","year":"2024","level":"Улсын шат","level_key":"uls",
     "title":"2024 Химийн улсын олимпиад",
     "desc":"2024 оны химийн улсын олимпиадын даалгавар",
     "icon":"🧪","color":"#F44336","file_url":"","answer_url":"","has_answer":False},
    {"id":9,"subject":"Хими","year":"2023","level":"Аймгийн шат","level_key":"aimag",
     "title":"2023 Хими — Аймгийн шат",
     "desc":"2023 оны аймгийн химийн олимпиадын даалгавар",
     "icon":"🧪","color":"#F44336","file_url":"","answer_url":"","has_answer":True},
    # БИОЛОГИ
    {"id":10,"subject":"Биологи","year":"2024","level":"Улсын шат","level_key":"uls",
     "title":"2024 Биологийн улсын олимпиад",
     "desc":"2024 оны биологийн улсын олимпиадын даалгавар",
     "icon":"🌿","color":"#4CAF50","file_url":"","answer_url":"","has_answer":False},
    {"id":11,"subject":"Биологи","year":"2023","level":"Улсын шат","level_key":"uls",
     "title":"2023 Биологийн улсын олимпиад",
     "desc":"2023 оны биологийн улсын олимпиадын даалгавар, хариулт",
     "icon":"🌿","color":"#4CAF50","file_url":"","answer_url":"","has_answer":True},
    # МОНГОЛ ХЭЛ
    {"id":12,"subject":"Монгол хэл","year":"2024","level":"Улсын шат","level_key":"uls",
     "title":"2024 Монгол хэлний улсын олимпиад",
     "desc":"2024 оны монгол хэлний улсын олимпиадын даалгавар",
     "icon":"📝","color":"#FF9800","file_url":"","answer_url":"","has_answer":False},
    {"id":13,"subject":"Монгол хэл","year":"2023","level":"Аймгийн шат","level_key":"aimag",
     "title":"2023 Монгол хэл — Аймгийн шат",
     "desc":"2023 оны аймгийн монгол хэлний олимпиадын даалгавар",
     "icon":"📝","color":"#FF9800","file_url":"","answer_url":"","has_answer":True},
    # ГАЗАРЗҮЙ
    {"id":14,"subject":"Газарзүй","year":"2024","level":"Улсын шат","level_key":"uls",
     "title":"2024 Газарзүйн улсын олимпиад",
     "desc":"2024 оны газарзүйн улсын олимпиадын даалгавар",
     "icon":"🌍","color":"#009688","file_url":"","answer_url":"","has_answer":False},
    # ТҮҮХ
    {"id":15,"subject":"Түүх","year":"2024","level":"Улсын шат","level_key":"uls",
     "title":"2024 Түүхийн улсын олимпиад",
     "desc":"2024 оны түүхийн улсын олимпиадын даалгавар",
     "icon":"🏛","color":"#795548","file_url":"","answer_url":"","has_answer":False},
    # АНГЛИ ХЭЛ
    {"id":16,"subject":"Англи хэл","year":"2024","level":"Улсын шат","level_key":"uls",
     "title":"2024 Англи хэлний улсын олимпиад",
     "desc":"2024 оны англи хэлний улсын олимпиадын бичгийн болон аман даалгавар",
     "icon":"🇬🇧","color":"#3F51B5","file_url":"","answer_url":"","has_answer":False},
    {"id":17,"subject":"Англи хэл","year":"2023","level":"Аймгийн шат","level_key":"aimag",
     "title":"2023 Англи хэл — Аймгийн шат",
     "desc":"2023 оны аймгийн англи хэлний олимпиадын даалгавар",
     "icon":"🇬🇧","color":"#3F51B5","file_url":"","answer_url":"","has_answer":True},
    # МЭДЭЭЛЭЛ ЗҮЙ
    {"id":18,"subject":"Мэдээлэл зүй","year":"2024","level":"Улсын шат","level_key":"uls",
     "title":"2024 Мэдээлэл зүйн улсын олимпиад",
     "desc":"2024 оны мэдээлэл зүй, програмчлалын улсын олимпиадын даалгавар",
     "icon":"💻","color":"#00BCD4","file_url":"","answer_url":"","has_answer":False},
]

OLYMPIAD_SUBJECTS = sorted(list(set(m["subject"] for m in OLYMPIAD_MATERIALS)))
OLYMPIAD_YEARS    = sorted(list(set(m["year"]    for m in OLYMPIAD_MATERIALS)), reverse=True)

# ── Интерактив платформын өгөгдөл ─────────────────────────────────────────────
INTER_CATEGORIES = [
    {"id":"math",     "name":"Математик",        "icon":"📐","color":"#2196F3"},
    {"id":"science",  "name":"Байгалийн ухаан",  "icon":"🔬","color":"#4CAF50"},
    {"id":"lang",     "name":"Хэл",              "icon":"📖","color":"#FF9800"},
    {"id":"coding",   "name":"Програмчлал",      "icon":"💻","color":"#00BCD4"},
    {"id":"general",  "name":"Ерөнхий боловсрол","icon":"🌐","color":"#9C27B0"},
    {"id":"olympiad", "name":"Олимпиад бэлтгэл", "icon":"🏆","color":"#FF5722"},
]

INTERACTIVE_SITES = [
    {"name":"Khan Academy","desc":"1-12-р ангийн математик, алгебр, геометр, тооны онол — видео хичээл, дасгалтай",
     "url":"https://www.khanacademy.org/math","icon":"🎓","color":"#1AA260",
     "category":"math","subjects":["Математик","Алгебр","Геометр"],
     "tags":["математик","алгебр","геометр","khan"],"lang":"Англи / Монгол","free":True,"featured":True},
    {"name":"GeoGebra","desc":"Геометр, алгебр, статистик, тооцооны интерактив хэрэгсэл. Багш, сурагч хоёуланд",
     "url":"https://www.geogebra.org","icon":"📐","color":"#8A4182",
     "category":"math","subjects":["Математик","Геометр","Алгебр"],
     "tags":["геометр","алгебр","geogebra","математик"],"lang":"Монгол хэлтэй","free":True,"featured":True},
    {"name":"Brilliant.org","desc":"Математик, тооны онол, логик — гүнзгий бодох чадвар хөгжүүлэх платформ",
     "url":"https://brilliant.org","icon":"✨","color":"#F97316",
     "category":"math","subjects":["Математик","Логик","Тооны онол"],
     "tags":["математик","логик","тооны онол","brilliant"],"lang":"Англи","free":False,"featured":False},
    {"name":"Desmos","desc":"Онлайн график калькулятор — функц, тэгшитгэл, геометр интерактивоор зурах",
     "url":"https://www.desmos.com","icon":"📈","color":"#6B21A8",
     "category":"math","subjects":["Математик","Алгебр","Функц"],
     "tags":["график","калькулятор","функц","тэгшитгэл"],"lang":"Англи","free":True,"featured":False},
    {"name":"Wolfram Alpha","desc":"Математик, физик, хими, статистикийн тооцоо — нарийн хариулт, тайлбартай",
     "url":"https://www.wolframalpha.com","icon":"🔢","color":"#DD1100",
     "category":"math","subjects":["Математик","Физик","Хими"],
     "tags":["математик","физик","хими","тооцоо","wolfram"],"lang":"Англи","free":True,"featured":False},
    {"name":"PhET Simulations","desc":"Физик, хими, биологи, газарзүйн шинжлэх ухааны интерактив симуляци — Colorado их сургуулийн бүтээл",
     "url":"https://phet.colorado.edu","icon":"⚗️","color":"#1A73E8",
     "category":"science","subjects":["Физик","Хими","Биологи"],
     "tags":["физик","хими","биологи","симуляци","phet"],"lang":"Монгол хэлтэй","free":True,"featured":True},
    {"name":"Khan Academy Science","desc":"Биологи, хими, физик, дэлхий судлал — анги тус бүрийн хичээл",
     "url":"https://www.khanacademy.org/science","icon":"🔬","color":"#1AA260",
     "category":"science","subjects":["Биологи","Хими","Физик"],
     "tags":["биологи","хими","физик","байгалийн ухаан"],"lang":"Англи","free":True,"featured":False},
    {"name":"CK-12","desc":"Байгалийн ухааны интерактив ном, симуляци, PLIX дасгалуудтай",
     "url":"https://www.ck12.org","icon":"📚","color":"#0077B6",
     "category":"science","subjects":["Физик","Хими","Биологи","Газарзүй"],
     "tags":["физик","хими","биологи","ck12"],"lang":"Англи","free":True,"featured":False},
    {"name":"Duolingo","desc":"Англи болон бусад хэл сурах хамгийн алдартай интерактив платформ",
     "url":"https://www.duolingo.com","icon":"🦜","color":"#58CC02",
     "category":"lang","subjects":["Англи хэл"],
     "tags":["англи хэл","хэл сурах","duolingo"],"lang":"Монгол хэлтэй","free":True,"featured":True},
    {"name":"British Council LearnEnglish","desc":"British Council-ийн ерөнхий болон шалгалтын англи хэлний дасгал, контент",
     "url":"https://learnenglish.britishcouncil.org","icon":"🇬🇧","color":"#012169",
     "category":"lang","subjects":["Англи хэл"],
     "tags":["англи хэл","british council","grammar"],"lang":"Англи","free":True,"featured":False},
    {"name":"BBC Learning English","desc":"BBC-ийн англи хэлний хичээл — видео, подкаст, дасгалтай",
     "url":"https://www.bbc.co.uk/learningenglish","icon":"📻","color":"#BB1919",
     "category":"lang","subjects":["Англи хэл"],
     "tags":["англи хэл","bbc","сонсох"],"lang":"Англи","free":True,"featured":False},
    {"name":"Scratch","desc":"MIT-ийн бүтээл — блок програмчлалаар бага насны сурагчдад зориулсан хамгийн тохиромжтой орчин",
     "url":"https://scratch.mit.edu","icon":"🐱","color":"#FF8C00",
     "category":"coding","subjects":["Мэдээлэл зүй","Програмчлал"],
     "tags":["scratch","програмчлал","бага анги","блок"],"lang":"Монгол хэлтэй","free":True,"featured":True},
    {"name":"Code.org","desc":"1-р ангиас эхлэн компьютерийн шинжлэх ухаан — дасгал, төсөл, интерактив",
     "url":"https://code.org","icon":"💻","color":"#00ADBC",
     "category":"coding","subjects":["Мэдээлэл зүй","Програмчлал"],
     "tags":["програмчлал","code.org","компьютер"],"lang":"Монгол хэлтэй","free":True,"featured":False},
    {"name":"Tinkercad","desc":"Autodesk-ийн 3D загварчлал, Arduino симуляци — хэрэглээний технологи",
     "url":"https://www.tinkercad.com","icon":"🔧","color":"#FF6D00",
     "category":"coding","subjects":["Мэдээлэл зүй","Технологи"],
     "tags":["3d","arduino","загварчлал","технологи"],"lang":"Англи","free":True,"featured":False},
    {"name":"Quizlet","desc":"Флаш карт, тест, тоглоомоор дурсамжийн технологи ашиглан хурдан цээжлэх",
     "url":"https://quizlet.com","icon":"🃏","color":"#4255FF",
     "category":"general","subjects":["Бүх хичээл"],
     "tags":["цээжлэх","тест","flashcard","quizlet"],"lang":"Монгол хэлтэй","free":True,"featured":False},
    {"name":"Kahoot!","desc":"Багшийн удирдлагатай анги дотор хэрэглэх интерактив викторин тоглоом",
     "url":"https://kahoot.com","icon":"🎮","color":"#46178F",
     "category":"general","subjects":["Бүх хичээл"],
     "tags":["тоглоом","викторин","kahoot","анги"],"lang":"Монгол хэлтэй","free":True,"featured":False},
    {"name":"Edpuzzle","desc":"Видео хичээл дотор асуулт оруулах — анги дотрын интерактив видео платформ",
     "url":"https://edpuzzle.com","icon":"🎬","color":"#00A3A4",
     "category":"general","subjects":["Бүх хичээл"],
     "tags":["видео","асуулт","edpuzzle"],"lang":"Англи","free":True,"featured":False},
    {"name":"Art of Problem Solving (AoPS)","desc":"Математикийн олимпиадын бэлтгэлд хамгийн тохиромжтой — AMC, IMO түвшний бодлого",
     "url":"https://artofproblemsolving.com","icon":"🏆","color":"#1565C0",
     "category":"olympiad","subjects":["Математик"],
     "tags":["олимпиад","математик","aops","amc","imo"],"lang":"Англи","free":True,"featured":True},
    {"name":"Science Olympiad","desc":"Биологи, хими, физик олимпиадын бэлтгэл материал, өмнөх оны даалгаврууд",
     "url":"https://www.scienceolympiad.com","icon":"🔬","color":"#2E7D32",
     "category":"olympiad","subjects":["Биологи","Хими","Физик"],
     "tags":["олимпиад","биологи","хими","физик"],"lang":"Англи","free":True,"featured":False},
    {"name":"Codeforces","desc":"Програмчлалын олимпиадын бэлтгэл — мэдээлэл зүйн улсын болон олон улсын шалгалт",
     "url":"https://codeforces.com","icon":"⌨️","color":"#1A73E8",
     "category":"olympiad","subjects":["Мэдээлэл зүй","Програмчлал"],
     "tags":["олимпиад","програмчлал","codeforces","мэдээлэл зүй"],"lang":"Англи","free":True,"featured":False},
]

# ── DB ─────────────────────────────────────────────────────────────────────────
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

# ── Public routes ──────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html", subjects=SUBJECTS,
        exam_types=EXAM_TYPES, grade_exam_map=GRADE_EXAM_MAP)

@app.route("/questions")
def questions_page():
    return render_template("questions.html", subjects=SUBJECTS,
        levels=LEVELS, blooms=BLOOM,
        exam_types=EXAM_TYPES, grade_exam_map=GRADE_EXAM_MAP)

@app.route("/blueprint")
def blueprint_page():
    return render_template("blueprint.html", subjects=SUBJECTS,
        exam_types=EXAM_TYPES, levels=LEVELS,
        blooms=BLOOM, grade_exam_map=GRADE_EXAM_MAP)

@app.route("/olympiad")
def olympiad_page():
    return render_template("olympiad.html",
        materials=OLYMPIAD_MATERIALS,
        subjects=OLYMPIAD_SUBJECTS,
        years=OLYMPIAD_YEARS,
        levels=OLYMPIAD_LEVELS,
        subj_icons=SUBJ_ICONS)

@app.route("/interactive")
def interactive_page():
    return render_template("interactive.html",
        sites=INTERACTIVE_SITES,
        categories=INTER_CATEGORIES)

# ── API ────────────────────────────────────────────────────────────────────────
@app.route("/api/questions")
def api_questions():
    grade=request.args.get("grade",""); subject=request.args.get("subject","")
    level=request.args.get("level","all"); bloom=request.args.get("bloom","all")
    count=int(request.args.get("count",20))
    conn=get_db(); sql,params="SELECT * FROM questions WHERE 1=1",[]
    if grade:        sql+=" AND grade=?";   params.append(int(grade))
    if subject:      sql+=" AND subject=?"; params.append(subject)
    if level!="all": sql+=" AND level=?";   params.append(level)
    if bloom!="all": sql+=" AND bloom=?";   params.append(bloom)
    sql+=" ORDER BY RANDOM() LIMIT ?"; params.append(count)
    rows=conn.execute(sql,params).fetchall(); conn.close()
    return jsonify({"questions":[row_to_dict(r) for r in rows],"total":len(rows)})

@app.route("/api/generate-exam",methods=["POST"])
def generate_exam():
    data=request.json; grade=data.get("grade",9); subject=data.get("subject","Математик")
    exam_id=data.get("exam_id","devshih"); blueprint=data.get("blueprint",{})
    et=EXAM_TYPES.get(exam_id,EXAM_TYPES["devshih"]); bp=et["blueprint"]
    conn=get_db(); selected=[]
    for lvl in LEVELS:
        cnt=int(blueprint.get(lvl,bp.get(lvl,0)))
        if cnt<=0: continue
        rows=conn.execute(
            "SELECT * FROM questions WHERE grade=? AND subject=? AND level=? ORDER BY RANDOM() LIMIT ?",
            (grade,subject,lvl,cnt)).fetchall()
        selected.extend([row_to_dict(r) for r in rows])
    conn.close()
    if not selected:
        return jsonify({"error":f"{grade}-р ангийн '{subject}' даалгавар байхгүй. Admin → Нэмэх"})
    return jsonify({"exam_id":exam_id,"exam_type":et["name"],"exam_icon":et["icon"],
        "title":f"{grade}-р ангийн {subject} — {et['name']}","grade":grade,"subject":subject,
        "total_questions":len(selected),"total_score":sum(q["score"] for q in selected),
        "duration":bp["duration"],"note":bp.get("note",""),"questions":selected})

@app.route("/api/save-question", methods=["POST"])
def save_question():
    """AI үүсгэсэн даалгаврыг мэдээллийн санд хадгалах."""
    data = request.json
    try:
        grade   = int(data.get("grade", 1))
        subject = data.get("subject", "")
        lvl     = data.get("level", data.get("difficulty", "Мэдлэг ойлголт"))
        score   = data.get("score") or LEVEL_SCORE.get(lvl, 1)
        q_code  = f"AI-Q{grade}-{subject[:3]}-{datetime.now().strftime('%H%M%S%f')}"
        conn = get_db()
        conn.execute("""INSERT INTO questions
            (q_code,grade,subject,level,bloom,q_type,question,
             option_a,option_b,option_c,option_d,answer,score,topic)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (q_code, grade, subject, lvl,
             data.get("bloom","Мэдлэг"),
             data.get("q_type","Нэг сонголт"),
             data.get("question",""),
             data.get("option_a"), data.get("option_b"),
             data.get("option_c"), data.get("option_d"),
             data.get("answer",""), int(score),
             data.get("topic","")))
        conn.commit(); conn.close()
        return jsonify({"success":True,"q_code":q_code})
    except Exception as e:
        return jsonify({"success":False,"error":str(e)}),400

@app.route("/api/stats")
def stats():
    conn=get_db()
    total=conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
    grades=conn.execute("SELECT COUNT(DISTINCT grade) FROM questions").fetchone()[0]
    subjects=conn.execute("SELECT COUNT(DISTINCT subject) FROM questions").fetchone()[0]
    conn.close()
    return jsonify({"total_questions":total,"grades":grades or 12,
                    "subjects":subjects or 10,"blueprints":len(EXAM_TYPES)})

# ── Admin ──────────────────────────────────────────────────────────────────────
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
        by_sub=by_sub,recent=recent,subjects=SUBJECTS,levels=LEVELS,blooms=BLOOM,q_types=Q_TYPES)

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
        subjects=SUBJECTS,levels=LEVELS,blooms=BLOOM,q_types=Q_TYPES)

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
        subjects=SUBJECTS,levels=LEVELS,blooms=BLOOM,q_types=Q_TYPES)

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
    return render_template("admin_list.html",questions=rows,subjects=SUBJECTS,levels=LEVELS,
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
        lvl=request.form.get("default_level","Мэдлэг ойлголт")
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
    return render_template("admin_import.html",subjects=SUBJECTS,levels=LEVELS)

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
            return jsonify({"error":"ANTHROPIC_API_KEY тохируулаагүй. Render → Environment-д нэмнэ үү."}),400
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
            msg=client.messages.create(model="claude-sonnet-4-20250514",max_tokens=4000,
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
        subjects=SUBJECTS,levels=LEVELS,blooms=BLOOM,q_types=Q_TYPES)

# ── Admin: Олимпиад материал нэмэх ────────────────────────────────────────────
@app.route("/admin/olympiad/add", methods=["GET","POST"])
@login_required
def admin_olympiad_add():
    if request.method=="POST":
        f=request.form
        new_item={
            "id":        len(OLYMPIAD_MATERIALS)+1,
            "subject":   f["subject"],
            "year":      f["year"],
            "level":     f["level"],
            "level_key": LEVEL_KEYS.get(f["level"],"school"),
            "title":     f["title"],
            "desc":      f.get("desc",""),
            "icon":      SUBJ_ICONS.get(f["subject"],"📖"),
            "color":     SUBJ_COLORS.get(f["subject"],"#888"),
            "file_url":  f.get("file_url",""),
            "answer_url":f.get("answer_url",""),
            "has_answer":bool(f.get("answer_url")),
        }
        OLYMPIAD_MATERIALS.append(new_item)
        return redirect(url_for("olympiad_page"))
    return render_template("admin_olympiad_add.html",
        subjects=OLYMPIAD_SUBJECTS, years=OLYMPIAD_YEARS, levels=OLYMPIAD_LEVELS)

if __name__=="__main__":
    port=int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0",port=port)
