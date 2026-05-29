# ══════════════════════════════════════════════════════════
# app.py-д нэмэх код
# Байршил: @app.route("/admin/ai-generate") дорд хэсэг
# ══════════════════════════════════════════════════════════

@app.route("/admin/import-blueprint", methods=["GET", "POST"])
@login_required
def admin_import_blueprint():
    """
    Admin панелаас блюпринт PDF оруулах.
    GET  → upload form харуулна
    POST → PDF задлаад Supabase-д хадгална
    """
    import io as _io
    import json as _json

    if request.method == "GET":
        return render_template_string("""
{% extends "base.html" %}
{% block title %}Блюпринт оруулах{% endblock %}
{% block content %}
<div style="max-width:600px;margin:2rem auto;padding:1.5rem;background:#fff;border-radius:12px;border:1.5px solid #e2e8f0">
  <h2 style="font-size:1.1rem;font-weight:800;margin:0 0 1rem">📋 Блюпринт PDF оруулах</h2>

  {% if result %}
  <div style="background:{% if result.error %}#fff3f3{% else %}#f0fdf4{% endif %};border-radius:8px;padding:1rem;margin-bottom:1rem;border:1px solid {% if result.error %}#fca5a5{% else %}#86efac{% endif %}">
    {% if result.error %}
      <p style="color:#c62828;font-weight:700">❌ {{ result.error }}</p>
    {% else %}
      <p style="color:#166534;font-weight:700">✅ Амжилттай хадгаллаа!</p>
      <p style="font-size:.85rem;color:#166534">{{ result.subject }} {{ result.grade }}-р анги: {{ result.nj_count }} үнэлгээний нэгж</p>
      {% for nj in result.preview %}
      <p style="font-size:.78rem;color:#14532d;margin:.2rem 0">  • {{ nj.name }}: {{ nj.surd|length }} үр дүн</p>
      {% endfor %}
    {% endif %}
  </div>
  {% endif %}

  <form method="POST" enctype="multipart/form-data">
    <div style="margin-bottom:1rem">
      <label style="font-size:.8rem;font-weight:700;display:block;margin-bottom:.3rem">Хичээл</label>
      <select name="subject" style="width:100%;padding:.5rem;border:1.5px solid #e2e8f0;border-radius:8px;font-size:.9rem">
        {% for s in all_subjects %}
        <option>{{ s }}</option>
        {% endfor %}
      </select>
    </div>
    <div style="margin-bottom:1rem">
      <label style="font-size:.8rem;font-weight:700;display:block;margin-bottom:.3rem">Анги</label>
      <select name="grade" style="width:100%;padding:.5rem;border:1.5px solid #e2e8f0;border-radius:8px;font-size:.9rem">
        {% for g in range(1,13) %}
        <option value="{{ g }}">{{ g }}-р анги</option>
        {% endfor %}
      </select>
    </div>
    <div style="margin-bottom:1.2rem">
      <label style="font-size:.8rem;font-weight:700;display:block;margin-bottom:.3rem">Блюпринт PDF файл</label>
      <input type="file" name="pdf" accept=".pdf"
        style="width:100%;padding:.5rem;border:1.5px solid #e2e8f0;border-radius:8px;font-size:.85rem">
      <p style="font-size:.72rem;color:#64748b;margin-top:.3rem">БҮТ-ийн стандарт блюпринт PDF (2025 оны улсын шалгалтын дэлгэрэнгүй блюпринт г.м)</p>
    </div>
    <button type="submit"
      style="width:100%;padding:.7rem;background:#0f766e;color:#fff;border:none;border-radius:8px;font-size:.9rem;font-weight:700;cursor:pointer">
      📥 Оруулах
    </button>
  </form>

  <div style="margin-top:1.5rem;padding-top:1rem;border-top:1px solid #e2e8f0">
    <p style="font-size:.75rem;color:#64748b;font-weight:700;margin-bottom:.4rem">Одоо хадгалагдсан блюпринтүүд:</p>
    {% for bp in blueprints %}
    <div style="display:flex;align-items:center;justify-content:space-between;padding:.3rem .5rem;font-size:.78rem;background:#f8fafc;border-radius:5px;margin-bottom:.2rem">
      <span>{{ bp.subject }} {{ bp.grade }}-р анги</span>
      <span style="color:#64748b">{{ bp.nj_count }} нэгж</span>
    </div>
    {% else %}
    <p style="font-size:.78rem;color:#94a3b8">Одоогоор блюпринт байхгүй</p>
    {% endfor %}
  </div>
</div>
{% endblock %}
""", all_subjects=ALL_SUBJECTS, result=None,
        blueprints=_get_blueprint_list())

    # POST — PDF задлах
    f       = request.files.get("pdf")
    subject = request.form.get("subject", "Математик")
    grade   = int(request.form.get("grade", 9))

    if not f or f.filename == "":
        return render_template_string("""...""",
            all_subjects=ALL_SUBJECTS,
            result={"error": "PDF файл сонгоогүй байна"},
            blueprints=_get_blueprint_list())

    try:
        import pdfplumber
        pdf_bytes = f.read()

        # PDF задлах
        with pdfplumber.open(_io.BytesIO(pdf_bytes)) as pdf:
            pass  # pdfplumber шалгах

        # blueprint_data.py-н parse функц дуудах
        from blueprint_data import parse_blueprint_pdf
        import tempfile, os as _os

        # Түр файл үүсгэж задлах
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name

        try:
            nj_list = parse_blueprint_pdf(tmp_path, subject, grade)
        finally:
            _os.unlink(tmp_path)

        if not nj_list:
            return render_template_string("""...""",
                all_subjects=ALL_SUBJECTS,
                result={"error": "PDF-с блюпринт олдсонгүй. Хүснэгтийн бүтэц таарахгүй байж болно."},
                blueprints=_get_blueprint_list())

        # Supabase-д хадгалах
        nj_json = _json.dumps(nj_list, ensure_ascii=False)
        conn = get_db()
        try:
            conn.execute("""
                INSERT INTO blueprints (subject, grade, nj, updated_at)
                VALUES (%s, %s, %s, NOW())
                ON CONFLICT (subject, grade)
                DO UPDATE SET nj = EXCLUDED.nj, updated_at = NOW()
            """, (subject, grade, nj_json))
            conn.commit()
        finally:
            conn.close()

        result = {
            "subject":   subject,
            "grade":     grade,
            "nj_count":  len(nj_list),
            "preview":   nj_list[:5]
        }

    except ImportError:
        result = {"error": "pdfplumber суулгаагүй. requirements.txt-д нэмнэ үү: pdfplumber"}
    except Exception as e:
        import traceback
        print("Blueprint import error:", traceback.format_exc())
        result = {"error": str(e)}

    return render_template_string("""
{% extends "base.html" %}
{% block title %}Блюпринт оруулах{% endblock %}
{% block content %}
<div style="max-width:600px;margin:2rem auto;padding:1.5rem;background:#fff;border-radius:12px;border:1.5px solid #e2e8f0">
  <h2 style="font-size:1.1rem;font-weight:800;margin:0 0 1rem">📋 Блюпринт PDF оруулах</h2>

  {% if result %}
  <div style="background:{% if result.error %}#fff3f3{% else %}#f0fdf4{% endif %};border-radius:8px;padding:1rem;margin-bottom:1rem;border:1px solid {% if result.error %}#fca5a5{% else %}#86efac{% endif %}">
    {% if result.error %}
      <p style="color:#c62828;font-weight:700">❌ {{ result.error }}</p>
    {% else %}
      <p style="color:#166534;font-weight:700">✅ Амжилттай хадгаллаа!</p>
      <p style="font-size:.85rem;color:#166534">{{ result.subject }} {{ result.grade }}-р анги: {{ result.nj_count }} үнэлгээний нэгж</p>
      {% for nj in result.preview %}
      <p style="font-size:.78rem;color:#14532d;margin:.2rem 0">  • {{ nj.name }}: {{ nj.surd|length }} үр дүн</p>
      {% endfor %}
    {% endif %}
  </div>
  {% endif %}

  <form method="POST" enctype="multipart/form-data">
    <div style="margin-bottom:1rem">
      <label style="font-size:.8rem;font-weight:700;display:block;margin-bottom:.3rem">Хичээл</label>
      <select name="subject" style="width:100%;padding:.5rem;border:1.5px solid #e2e8f0;border-radius:8px;font-size:.9rem">
        {% for s in all_subjects %}<option>{{ s }}</option>{% endfor %}
      </select>
    </div>
    <div style="margin-bottom:1rem">
      <label style="font-size:.8rem;font-weight:700;display:block;margin-bottom:.3rem">Анги</label>
      <select name="grade" style="width:100%;padding:.5rem;border:1.5px solid #e2e8f0;border-radius:8px;font-size:.9rem">
        {% for g in range(1,13) %}<option value="{{ g }}">{{ g }}-р анги</option>{% endfor %}
      </select>
    </div>
    <div style="margin-bottom:1.2rem">
      <label style="font-size:.8rem;font-weight:700;display:block;margin-bottom:.3rem">Блюпринт PDF файл</label>
      <input type="file" name="pdf" accept=".pdf"
        style="width:100%;padding:.5rem;border:1.5px solid #e2e8f0;border-radius:8px;font-size:.85rem">
      <p style="font-size:.72rem;color:#64748b;margin-top:.3rem">БҮТ-ийн стандарт блюпринт PDF</p>
    </div>
    <button type="submit"
      style="width:100%;padding:.7rem;background:#0f766e;color:#fff;border:none;border-radius:8px;font-size:.9rem;font-weight:700;cursor:pointer">
      📥 Оруулах
    </button>
  </form>

  <div style="margin-top:1.5rem;padding-top:1rem;border-top:1px solid #e2e8f0">
    <p style="font-size:.75rem;color:#64748b;font-weight:700;margin-bottom:.4rem">Одоо хадгалагдсан блюпринтүүд:</p>
    {% for bp in blueprints %}
    <div style="display:flex;align-items:center;justify-content:space-between;padding:.3rem .5rem;font-size:.78rem;background:#f8fafc;border-radius:5px;margin-bottom:.2rem">
      <span>{{ bp.subject }} {{ bp.grade }}-р анги</span>
      <span style="color:#64748b">{{ bp.nj_count }} нэгж</span>
    </div>
    {% else %}
    <p style="font-size:.78rem;color:#94a3b8">Одоогоор блюпринт байхгүй</p>
    {% endfor %}
  </div>
</div>
{% endblock %}
""", all_subjects=ALL_SUBJECTS, result=result,
        blueprints=_get_blueprint_list())


def _get_blueprint_list():
    """Хадгалагдсан блюпринтүүдийн жагсаалт авах"""
    try:
        conn = get_db()
        rows = conn.execute(
            "SELECT subject, grade, nj FROM blueprints ORDER BY subject, grade"
        ).fetchall()
        conn.close()
        result = []
        for r in rows:
            nj = r['nj'] if isinstance(r['nj'], list) else __import__('json').loads(r['nj'] or '[]')
            result.append({
                "subject":  r['subject'],
                "grade":    r['grade'],
                "nj_count": len(nj)
            })
        return result
    except Exception:
        return []
