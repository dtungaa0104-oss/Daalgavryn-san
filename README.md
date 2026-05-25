# 🏫 Орхонтуул ЕБС — Даалгаврын Сан

**1–12-р ангийн бүх хичээлийн даалгаврын вэб сайт**

[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-green)](https://flask.palletsprojects.com)

---

## ✨ Боломжууд

| Боломж | Тайлбар |
|--------|---------|
| 📚 Даалгаврын сан | 1–12-р ангийн бүх хичээлийн даалгавар |
| 🔍 Шүүлтүүр | Анги, хичээл, хүндрэл, Блумын шат |
| 🏆 Улсын шалгалт | Блупринтийн дагуу 40 даалгавар, 90 минут |
| 📋 Анги дэвших | Блупринтийн дагуу 25 даалгавар, 60 минут |
| ⬇ Татаж авах | Сонгосон даалгаварыг .txt файлаар татах |
| 📊 Блупринт | Хүндрэлийн харьцааг тохируулах |

---

## 🚀 Суулгах заавар

### 1. Репозитори татах
```bash
git clone https://github.com/таны-нэр/orkhontul-school.git
cd orkhontul-school
```

### 2. Virtual environment үүсгэх
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate
```

### 3. Хэрэгцээт packages суулгах
```bash
pip install -r requirements.txt
```

### 4. Сайт ажиллуулах
```bash
python app.py
```

### 5. Браузерт нээх
```
http://localhost:5000
```

---

## 📁 Файлын бүтэц

```
orkhontul-school/
├── app.py                  # Flask backend
├── requirements.txt        # Python packages
├── templates/
│   ├── base.html           # Navbar, footer
│   ├── index.html          # Нүүр хуудас
│   ├── questions.html      # Даалгавар хайх
│   └── blueprint.html      # Блупринт / шалгалт үүсгэх
├── static/
│   ├── css/main.css        # Stylesheet
│   └── js/main.js          # Frontend JS
└── data/                   # Даалгаврын өгөгдөл (ирээдүйд)
    ├── questions/
    └── blueprints/
```

---

## 📊 Блупринт тайлбар

| Хүндрэл | Оноо | Улсын шалгалт | Анги дэвших |
|---------|------|--------------|------------|
| Хялбар  | 1п   | 12 даалгавар | 8 даалгавар |
| Дунд    | 2п   | 16 даалгавар | 10 даалгавар |
| Хүнд    | 3п   | 12 даалгавар | 7 даалгавар |

---

## 🔧 Өгөгдлийн сан холбох (ирээдүйд)

`app.py` файлын `generate_questions()` функцийг жинхэнэ өгөгдлийн сантай солих:

```python
import sqlite3
def get_questions_from_db(grade, subject, difficulty, bloom, count):
    conn = sqlite3.connect('questions.db')
    # SQL query ...
    return questions
```

---

## 📄 Лиценз

Орхонтуул ЕБС — Боловсруулсан сургуулийн хэрэгцээнд зориулан
