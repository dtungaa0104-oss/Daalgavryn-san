"""
Орхонтуул ЕБС — Сертификат, Өргөмжлөл, Талархал үүсгэгч
Reportlab дээр суурилсан, маш гоё загвартай
"""
import io, math
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

FONTS_DIR = os.path.join(os.path.dirname(__file__), 'static', 'fonts')

def _reg_fonts():
    try:
        pdfmetrics.registerFont(TTFont('MN',  os.path.join(FONTS_DIR, 'DejaVuSans.ttf')))
        pdfmetrics.registerFont(TTFont('MNB', os.path.join(FONTS_DIR, 'DejaVuSans-Bold.ttf')))
    except:
        pass
_reg_fonts()

# ── Туслах функцүүд ─────────────────────────────────────
def _hex(h):
    return colors.HexColor(h)

def _ctext(cv, text, y, font, size, color, w=None):
    if w is None: w = cv._pagesize[0]
    cv.setFont(font, size)
    cv.setFillColor(_hex(color))
    cv.drawCentredString(w/2, y, text)

def _line(cv, x1, y1, x2, y2, color, width=1):
    cv.setStrokeColor(_hex(color))
    cv.setLineWidth(width)
    cv.line(x1, y1, x2, y2)

def _star(cv, cx, cy, r, color, n=5):
    """n цухуйтай од"""
    cv.setFillColor(_hex(color))
    cv.setStrokeColor(_hex(color))
    pts = []
    for i in range(n*2):
        angle = math.pi/2 + i * math.pi / n
        radius = r if i % 2 == 0 else r * 0.42
        pts.append((cx + radius*math.cos(angle), cy + radius*math.sin(angle)))
    p = cv.beginPath()
    p.moveTo(*pts[0])
    for pt in pts[1:]: p.lineTo(*pt)
    p.close()
    cv.drawPath(p, fill=1, stroke=0)

def _corner_ornament(cv, cx, cy, size, color, flip_x=False, flip_y=False):
    """Булангийн чимэглэл"""
    cv.saveState()
    cv.translate(cx, cy)
    if flip_x: cv.scale(-1, 1)
    if flip_y: cv.scale(1, -1)
    cv.setFillColor(_hex(color))
    cv.setStrokeColor(_hex(color))
    cv.setLineWidth(1.5)
    # Гоёмсог муруй шугам
    p = cv.beginPath()
    p.moveTo(0, 0)
    p.curveTo(size*0.3, size*0.1, size*0.6, size*0.3, size*0.8, size*0.8)
    cv.drawPath(p, fill=0, stroke=1)
    p2 = cv.beginPath()
    p2.moveTo(0, 0)
    p2.curveTo(size*0.1, size*0.3, size*0.3, size*0.6, size*0.8, size*0.8)
    cv.drawPath(p2, fill=0, stroke=1)
    cv.circle(size*0.8, size*0.8, size*0.06, fill=1, stroke=0)
    cv.circle(0, 0, size*0.05, fill=1, stroke=0)
    cv.restoreState()

def _wave_border(cv, w, h, color1, color2, margin=18):
    """Давхар хүрээ + булангийн чимэглэл"""
    # Гадна хүрээ
    cv.setStrokeColor(_hex(color1))
    cv.setLineWidth(6)
    cv.rect(margin, margin, w-2*margin, h-2*margin, fill=0, stroke=1)
    # Дотор хүрээ
    cv.setStrokeColor(_hex(color2))
    cv.setLineWidth(1.5)
    cv.rect(margin+9, margin+9, w-2*(margin+9), h-2*(margin+9), fill=0, stroke=1)
    # Хос мөр дотор
    cv.setStrokeColor(_hex(color1))
    cv.setLineWidth(0.5)
    cv.rect(margin+12, margin+12, w-2*(margin+12), h-2*(margin+12), fill=0, stroke=1)
    # Булан чимэглэл
    s = 28
    _corner_ornament(cv, margin+14, margin+14, s, color1)
    _corner_ornament(cv, w-margin-14, margin+14, s, color1, flip_x=True)
    _corner_ornament(cv, margin+14, h-margin-14, s, color1, flip_y=True)
    _corner_ornament(cv, w-margin-14, h-margin-14, s, color1, flip_x=True, flip_y=True)

# ── ӨРГӨМЖЛӨЛ (Award) ──────────────────────────────────
def _gen_award(cv, w, h, name, value, subtitle, school, date):
    """Алт өнгийн тансаг өргөмжлөл"""
    GOLD1  = '#7B5E00'
    GOLD2  = '#C8960C'
    GOLD3  = '#FFD700'
    GOLD4  = '#FFF8DC'
    CREAM  = '#FFFDF0'
    DARK   = '#3D2800'
    RED    = '#8B1A1A'

    # Дэвсгэр
    cv.setFillColor(_hex(CREAM))
    cv.rect(0, 0, w, h, fill=1, stroke=0)

    # Арын чимэглэлт хээ (gradient-like concentric)
    for i in range(8):
        alpha = 0.025 - i*0.003
        cv.setFillColor(_hex(GOLD3))
        cv.setFillAlpha(max(0.005, alpha))
        m = 30 + i*18
        cv.rect(m, m, w-2*m, h-2*m, fill=1, stroke=0)
    cv.setFillAlpha(1)

    # Хүрээ
    _wave_border(cv, w, h, GOLD1, GOLD2)

    # Дээд хэсгийн чимэглэл — одны эгнээ
    star_y = h - 52
    star_xs = [w/2 - 90, w/2 - 60, w/2 - 30, w/2, w/2+30, w/2+60, w/2+90]
    for i, sx in enumerate(star_xs):
        r = 8 if i == 3 else 5
        _star(cv, sx, star_y, r, GOLD2 if i != 3 else GOLD3)

    # Сургуулийн нэр
    _ctext(cv, school.upper(), h-75, 'MNB', 11, GOLD1, w)

    # Хэвтээ алтан зураас
    _line(cv, 60, h-88, w-60, h-88, GOLD2, 1.5)

    # Гол гарчиг — ӨРГӨМЖЛӨЛ
    _ctext(cv, '🏆', h-130, 'MN', 28, GOLD2, w)  # emoji байхгүй бол хасагдана
    # Текст гарчиг
    cv.setFillColor(_hex(GOLD1))
    cv.setFont('MNB', 42)
    # Letter spacing effect
    title_text = 'ӨРГӨМЖЛӨЛ'
    title_w = cv.stringWidth(title_text, 'MNB', 42)
    cv.drawString(w/2 - title_w/2, h-138, title_text)

    # Доод зураас
    _line(cv, 60, h-148, w-60, h-148, GOLD2, 1.5)

    # Subtitle
    if subtitle:
        _ctext(cv, subtitle, h-175, 'MNB', 12, RED, w)

    # Дундын бүс — нэр
    mid_y = h/2 + 30

    # Нэрийн дээр текст
    _ctext(cv, 'Дараах хүнд гардуулна', mid_y + 55, 'MN', 11, GOLD1, w)

    # Нэрийн зураас (өргөн, алтан)
    _line(cv, 90, mid_y + 40, w-90, mid_y + 40, GOLD2, 0.8)
    _line(cv, 90, mid_y + 38, w-90, mid_y + 38, GOLD3, 2.5)
    _line(cv, 90, mid_y + 36, w-90, mid_y + 36, GOLD2, 0.8)

    # Нэр — том, алтан
    cv.setFillColor(_hex(DARK))
    cv.setFont('MNB', 34)
    name_w = cv.stringWidth(name, 'MNB', 34)
    cv.drawString(w/2 - name_w/2, mid_y + 8, name)

    # Нэрийн доор зураас
    _line(cv, 90, mid_y + 2, w-90, mid_y + 2, GOLD3, 2.5)
    _line(cv, 90, mid_y, w-90, mid_y, GOLD2, 0.8)

    # Утга/шалтгаан
    if value:
        _ctext(cv, value, mid_y - 30, 'MNB', 13, RED, w)

    # Доод хэсэг — гарын үсэг
    sig_y = 65
    # Зүүн — Захирал
    cv.setFillColor(_hex(DARK))
    cv.setFont('MN', 10)
    cv.drawString(75, sig_y + 30, 'Захирал: ____________________')
    cv.setFont('MN', 9)
    # Тамга
    _line(cv, w/2-32, sig_y+45, w/2+32, sig_y+45, GOLD2, 1)
    _line(cv, w/2-32, sig_y-5, w/2+32, sig_y-5, GOLD2, 1)
    _line(cv, w/2-32, sig_y-5, w/2-32, sig_y+45, GOLD2, 1)
    _line(cv, w/2+32, sig_y-5, w/2+32, sig_y+45, GOLD2, 1)
    cv.setFont('MNB', 8)
    cv.setFillColor(_hex(GOLD1))
    cv.drawCentredString(w/2, sig_y+22, 'ТАМГА')
    cv.drawCentredString(w/2, sig_y+10, school[:8])
    # Баруун — огноо
    if date:
        cv.setFont('MN', 11)
        cv.setFillColor(_hex(DARK))
        cv.drawRightString(w-75, sig_y+20, date)

    # Одны эгнээ доод
    for sx in star_xs:
        r = 8 if sx == w/2 else 5
        _star(cv, sx, 38, r, GOLD2 if sx != w/2 else GOLD3)

# ── СЕРТИФИКАТ (Cert) ──────────────────────────────────
def _gen_cert(cv, w, h, name, value, subtitle, school, date):
    """Ногоон сертификат"""
    G1 = '#064E3B'; G2 = '#10B981'; G3 = '#D1FAE5'; DARK = '#1e3a5f'

    cv.setFillColor(_hex('#F0FDF4'))
    cv.rect(0, 0, w, h, fill=1, stroke=0)
    # Дэвсгэр хээ
    cv.setFillColor(_hex(G2)); cv.setFillAlpha(0.04)
    for i in range(0, int(w)+40, 40):
        for j in range(0, int(h)+40, 40):
            cv.circle(i, j, 1.5, fill=1, stroke=0)
    cv.setFillAlpha(1)
    _wave_border(cv, w, h, G1, G2)
    # Одны эгнээ
    for sx in [w/2-80,w/2-50,w/2-20,w/2,w/2+20,w/2+50,w/2+80]:
        _star(cv, sx, h-50, 5 if sx!=w/2 else 8, G2)
    _ctext(cv, school.upper(), h-75, 'MNB', 11, G1, w)
    _line(cv, 60, h-88, w-60, h-88, G2, 1.5)
    cv.setFillColor(_hex(G1)); cv.setFont('MNB', 40)
    t='СЕРТИФИКАТ'; cv.drawString(w/2-cv.stringWidth(t,'MNB',40)/2, h-136, t)
    _line(cv, 60, h-148, w-60, h-148, G2, 1.5)
    if subtitle: _ctext(cv, subtitle, h-172, 'MNB', 12, '#065F46', w)
    mid_y = h/2 + 30
    _ctext(cv, 'Дараах хүнд олгоно', mid_y+55, 'MN', 11, G1, w)
    _line(cv, 90, mid_y+40, w-90, mid_y+40, G2, 2.5)
    cv.setFillColor(_hex(DARK)); cv.setFont('MNB', 34)
    cv.drawString(w/2-cv.stringWidth(name,'MNB',34)/2, mid_y+8, name)
    _line(cv, 90, mid_y, w-90, mid_y, G2, 2.5)
    if value: _ctext(cv, value, mid_y-30, 'MNB', 13, '#065F46', w)
    sig_y = 65
    cv.setFillColor(_hex(DARK)); cv.setFont('MN', 10)
    cv.drawString(75, sig_y+30, 'Захирал: ____________________')
    _line(cv, w/2-30,sig_y+45, w/2+30,sig_y+45, G2, 1)
    _line(cv, w/2-30,sig_y-5,  w/2+30,sig_y-5,  G2, 1)
    _line(cv, w/2-30,sig_y-5,  w/2-30,sig_y+45, G2, 1)
    _line(cv, w/2+30,sig_y-5,  w/2+30,sig_y+45, G2, 1)
    cv.setFont('MNB', 8); cv.setFillColor(_hex(G1))
    cv.drawCentredString(w/2, sig_y+22, 'ТАМГА')
    cv.drawCentredString(w/2, sig_y+10, school[:8])
    if date:
        cv.setFont('MN', 11); cv.setFillColor(_hex(DARK))
        cv.drawRightString(w-75, sig_y+20, date)
    for sx in [w/2-80,w/2-50,w/2-20,w/2,w/2+20,w/2+50,w/2+80]:
        _star(cv, sx, 38, 5 if sx!=w/2 else 8, G2)

# ── ТАЛАРХАЛ (Thanks) ──────────────────────────────────
def _gen_thanks(cv, w, h, name, value, subtitle, school, date):
    """Цэнхэр талархал"""
    B1='#1E3A8A'; B2='#3B82F6'; DARK='#1e3a5f'
    cv.setFillColor(_hex('#EFF6FF'))
    cv.rect(0, 0, w, h, fill=1, stroke=0)
    cv.setFillColor(_hex(B2)); cv.setFillAlpha(0.04)
    for i in range(0,int(w)+40,40):
        for j in range(0,int(h)+40,40):
            cv.circle(i,j,1.5,fill=1,stroke=0)
    cv.setFillAlpha(1)
    _wave_border(cv, w, h, B1, B2)
    for sx in [w/2-80,w/2-50,w/2-20,w/2,w/2+20,w/2+50,w/2+80]:
        _star(cv, sx, h-50, 5 if sx!=w/2 else 8, B2)
    _ctext(cv, school.upper(), h-75, 'MNB', 11, B1, w)
    _line(cv, 60, h-88, w-60, h-88, B2, 1.5)
    cv.setFillColor(_hex(B1)); cv.setFont('MNB', 40)
    t='ТАЛАРХАЛ'; cv.drawString(w/2-cv.stringWidth(t,'MNB',40)/2, h-136, t)
    _line(cv, 60, h-148, w-60, h-148, B2, 1.5)
    if subtitle: _ctext(cv, subtitle, h-172, 'MNB', 12, '#1D4ED8', w)
    mid_y = h/2+30
    _ctext(cv, 'Дараах хүнд илэрхийлнэ', mid_y+55, 'MN', 11, B1, w)
    _line(cv, 90, mid_y+40, w-90, mid_y+40, B2, 2.5)
    cv.setFillColor(_hex(DARK)); cv.setFont('MNB', 34)
    cv.drawString(w/2-cv.stringWidth(name,'MNB',34)/2, mid_y+8, name)
    _line(cv, 90, mid_y, w-90, mid_y, B2, 2.5)
    if value: _ctext(cv, value, mid_y-30, 'MNB', 13, '#1D4ED8', w)
    sig_y = 65
    cv.setFillColor(_hex(DARK)); cv.setFont('MN', 10)
    cv.drawString(75, sig_y+30, 'Захирал: ____________________')
    _line(cv, w/2-30,sig_y+45, w/2+30,sig_y+45, B2, 1)
    _line(cv, w/2-30,sig_y-5,  w/2+30,sig_y-5,  B2, 1)
    _line(cv, w/2-30,sig_y-5,  w/2-30,sig_y+45, B2, 1)
    _line(cv, w/2+30,sig_y-5,  w/2+30,sig_y+45, B2, 1)
    cv.setFont('MNB', 8); cv.setFillColor(_hex(B1))
    cv.drawCentredString(w/2, sig_y+22, 'ТАМГА')
    cv.drawCentredString(w/2, sig_y+10, school[:8])
    if date:
        cv.setFont('MN', 11); cv.setFillColor(_hex(DARK))
        cv.drawRightString(w-75, sig_y+20, date)
    for sx in [w/2-80,w/2-50,w/2-20,w/2,w/2+20,w/2+50,w/2+80]:
        _star(cv, sx, 38, 5 if sx!=w/2 else 8, B2)

# ── НИЙТИЙН ФУНКЦ ─────────────────────────────────────
def gen_certificate(name, value, school='Орхонтуул ЕБС',
                    title='СЕРТИФИКАТ', subtitle='', date='', cert_type='cert'):
    buf = io.BytesIO()
    w, h = landscape(A4)
    cv = canvas.Canvas(buf, pagesize=landscape(A4))
    if cert_type == 'award':
        _gen_award(cv, w, h, name, value, subtitle, school, date)
    elif cert_type == 'thanks':
        _gen_thanks(cv, w, h, name, value, subtitle, school, date)
    else:
        _gen_cert(cv, w, h, name, value, subtitle, school, date)
    cv.save()
    buf.seek(0)
    return buf.getvalue()

def gen_batch(names_values, school='Орхонтуул ЕБС',
              title='СЕРТИФИКАТ', subtitle='', date='', cert_type='cert'):
    from pypdf import PdfWriter, PdfReader
    writer = PdfWriter()
    for item in names_values:
        pdf_bytes = gen_certificate(
            name=item.get('name',''), value=item.get('value',''),
            school=school, title=title, subtitle=subtitle,
            date=date, cert_type=cert_type)
        reader = PdfReader(io.BytesIO(pdf_bytes))
        writer.add_page(reader.pages[0])
    out = io.BytesIO()
    writer.write(out)
    out.seek(0)
    return out.getvalue()
