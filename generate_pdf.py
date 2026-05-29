"""
/api/generate-pdf  — Шалгалтын PDF үүсгэх endpoint
Flask route-д import хийгээд register хийнэ:

    from generate_pdf import generate_pdf_route
    app.add_url_rule('/api/generate-pdf', 'generate_pdf', generate_pdf_route, methods=['POST'])

Шаардлага:
    pip install weasyprint
"""

import io
import json
from flask import request, jsonify, send_file

# WeasyPrint — HTML → PDF хамгийн найдвартай арга
try:
    from weasyprint import HTML, CSS
    WEASYPRINT_OK = True
except ImportError:
    WEASYPRINT_OK = False


# ── HTML загвар ────────────────────────────────────────────────────────────────

CSS_STYLES = """
@page {
    size: A4;
    margin: 18mm 15mm 18mm 15mm;
    @bottom-right {
        content: "Орхонтуул ЕБС  ·  " counter(page) " / " counter(pages);
        font-size: 8pt;
        color: #888;
    }
}
* { box-sizing: border-box; }
body {
    font-family: "DejaVu Serif", "FreeSerif", serif;
    font-size: 11pt;
    line-height: 1.85;
    color: #111;
}
h1 {
    font-size: 13pt;
    text-align: center;
    border-bottom: 2pt solid #1b5e20;
    padding-bottom: 5pt;
    margin-bottom: 4pt;
}
h2 {
    font-size: 11pt;
    text-align: center;
    font-weight: normal;
    color: #444;
    margin-top: 2pt;
    margin-bottom: 10pt;
}
h3 {
    font-size: 11pt;
    font-weight: 700;
    color: #1b5e20;
    border-left: 3pt solid #1b5e20;
    padding-left: 7pt;
    margin: 14pt 0 4pt;
    page-break-after: avoid;
}
.section-title {
    font-size: 11pt;
    font-weight: 700;
    margin: 12pt 0 6pt;
    padding: 4pt 8pt;
    background: #f1f8e9;
    border-radius: 4pt;
}
.q-row {
    display: flex;
    gap: 8pt;
    margin: 9pt 0 4pt;
    page-break-inside: avoid;
}
.q-num {
    min-width: 22pt;
    font-weight: 700;
    color: #1b5e20;
}
.q-body { flex: 1; }
.q-text { margin-bottom: 3pt; }
.q-opts {
    display: flex;
    flex-wrap: wrap;
    gap: 2pt 0;
    margin-left: 4pt;
    margin-top: 3pt;
}
.q-opt { width: 50%; padding: 1pt 0; }
.q-opt.correct { font-weight: 700; color: #1b5e20; }
.q-score {
    font-size: 8.5pt;
    color: #888;
    white-space: nowrap;
    padding-top: 2pt;
}
.q-level {
    font-size: 8pt;
    padding: 1pt 6pt;
    border-radius: 10pt;
    background: #e8f5e9;
    color: #2e7d32;
    margin-right: 4pt;
}
.divider {
    border: none;
    border-top: 1.5pt solid #c8e6c9;
    margin: 10pt 0;
}
.page-break { page-break-before: always; }
/* Задгай */
.zq-block {
    margin: 12pt 0;
    page-break-inside: avoid;
}
.zq-header {
    font-weight: 700;
    color: #1b5e20;
    margin-bottom: 4pt;
}
.zq-body {
    line-height: 2;
    white-space: pre-wrap;
}
.work-space {
    border-bottom: 1pt dotted #aaa;
    min-height: 55pt;
    margin-top: 6pt;
}
/* Хариултын хуудас */
.answer-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 4pt 12pt;
    margin-top: 6pt;
}
.answer-cell {
    width: 60pt;
    font-size: 10pt;
}
.answer-val {
    font-weight: 700;
    color: #1b5e20;
}
.footer-note {
    font-size: 8.5pt;
    color: #888;
    text-align: right;
    margin-top: 20pt;
}
"""


def esc(text):
    """HTML-д аюулгүй болгох"""
    if not text:
        return ''
    return (str(text)
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;'))


def build_html(mode, title, grade, subject, duration, questions, zadgai_cards):
    """
    mode: 'test' | 'answers' | 'zadgai' | 'full'
    """
    LABELS = ['А', 'Б', 'В', 'Г']
    show_answers = mode in ('answers', 'full')
    include_test = mode in ('test', 'answers', 'full')
    include_zadgai = mode in ('zadgai', 'full')

    total_q = len(questions)
    total_s = sum(q.get('score', 1) for q in questions)
    ztotal = sum(c.get('score', 0) for c in zadgai_cards)

    html = f"""<!DOCTYPE html>
<html lang="mn">
<head>
<meta charset="UTF-8">
<style>{CSS_STYLES}</style>
</head>
<body>
<h1>{esc(title)}</h1>
<h2>{grade}-р анги &nbsp;·&nbsp; {esc(subject)} &nbsp;·&nbsp; {esc(duration)}</h2>
"""

    # ── I ХЭСЭГ — Тест ──────────────────────────────────────────────────────
    if include_test:
        html += f'<div class="section-title">I ХЭСЭГ — Тест даалгавар &nbsp;/Нийт {total_q} даалгавар, {total_s} оноо/</div>\n'
        html += '<hr class="divider">\n'

        for i, q in enumerate(questions):
            level = q.get('level', '')
            score = q.get('score', 1)
            opts_html = ''
            if q.get('options'):
                pairs = []
                for j, opt in enumerate(q['options']):
                    L = LABELS[j] if j < len(LABELS) else str(j+1)
                    ok_cls = ' correct' if show_answers and L == q.get('answer') else ''
                    pairs.append(f'<div class="q-opt{ok_cls}">{L}. {esc(opt)}</div>')
                opts_html = '<div class="q-opts">' + ''.join(pairs) + '</div>'

            html += f"""<div class="q-row">
  <div class="q-num">{i+1}.</div>
  <div class="q-body">
    <div class="q-text"><span class="q-level">{esc(level)}</span>{esc(q.get('question',''))}</div>
    {opts_html}
  </div>
  <div class="q-score">{score}п</div>
</div>\n"""

        # Хариулт хуудас
        if show_answers:
            html += '<div class="page-break"></div>\n'
            html += '<h3>Зөв хариулт — I хэсэг</h3>\n'
            html += '<div class="answer-grid">\n'
            for i, q in enumerate(questions):
                ans = esc(q.get('answer', '—'))
                html += f'<div class="answer-cell">{i+1}. <span class="answer-val">{ans}</span></div>\n'
            html += '</div>\n'

    # ── II ХЭСЭГ — Задгай ───────────────────────────────────────────────────
    if include_zadgai and zadgai_cards:
        if include_test:
            html += '<div class="page-break"></div>\n'
        html += f'<div class="section-title">II ХЭСЭГ — Задгай даалгавар &nbsp;/Нийт {ztotal} оноо/</div>\n'
        html += '<hr class="divider">\n'

        for c in zadgai_cards:
            body_text = esc(c.get('body', '')).replace('\n', '<br>')
            html += f"""<div class="zq-block">
  <div class="zq-header">{esc(c.get('num',''))}. {esc(c.get('title',''))} &nbsp;/{c.get('score',0)} оноо/</div>
  <div class="zq-body">{body_text}</div>
  <div class="work-space"></div>
</div>\n"""

        # Задгай хариулт
        if show_answers:
            html += '<div class="page-break"></div>\n'
            html += '<h3>Хариулт — II хэсэг</h3>\n'
            for c in zadgai_cards:
                answer = c.get('answer', '')
                if answer:
                    ans_text = esc(answer).replace('\n', '<br>')
                    html += f'<p><strong>{esc(c.get("num",""))}.</strong> {ans_text}</p>\n'

    html += f'<p class="footer-note">Орхонтуул ЕБС &nbsp;·&nbsp; {grade}-р анги &nbsp;·&nbsp; {esc(subject)}</p>\n'
    html += '</body></html>'
    return html


# ── Flask route ───────────────────────────────────────────────────────────────

def generate_pdf_route():
    if not WEASYPRINT_OK:
        return jsonify({
            'error': 'WeasyPrint суулгаагүй байна. pip install weasyprint'
        }), 500

    data = request.get_json(force=True)
    mode       = data.get('mode', 'test')
    title      = data.get('title', 'Шалгалт')
    grade      = data.get('grade', '')
    subject    = data.get('subject', '')
    duration   = data.get('duration', '')
    questions  = data.get('questions', [])
    zadgai     = data.get('zadgai', [])

    html_content = build_html(mode, title, grade, subject, duration, questions, zadgai)

    try:
        pdf_bytes = HTML(string=html_content).write_pdf(
            stylesheets=[CSS(string=CSS_STYLES)]
        )
    except Exception as e:
        return jsonify({'error': f'PDF үүсгэхэд алдаа: {str(e)}'}), 500

    suffix_map = {
        'test':    'тест',
        'answers': 'тест_хариулт',
        'zadgai':  'задгай',
        'full':    'бүрэн',
    }
    suffix = suffix_map.get(mode, mode)
    filename = f"{grade}_{subject}_{suffix}.pdf".replace(' ', '_')

    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )
