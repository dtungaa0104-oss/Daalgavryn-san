"""
Орхонтуул ЕБС — Сертификат & Өргөмжлөл үүсгэгч
"""
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

FONTS_DIR = os.path.join(os.path.dirname(__file__), 'static', 'fonts')

def _reg_fonts():
    try:
        pdfmetrics.registerFont(TTFont('MN', os.path.join(FONTS_DIR, 'DejaVuSans.ttf')))
        pdfmetrics.registerFont(TTFont('MNB', os.path.join(FONTS_DIR, 'DejaVuSans-Bold.ttf')))
    except:
        pass

_reg_fonts()

def _draw_border(c, w, h, color1, color2, margin=20):
    c.setStrokeColor(colors.HexColor(color1))
    c.setLineWidth(7)
    c.rect(margin, margin, w-2*margin, h-2*margin, fill=0, stroke=1)
    c.setStrokeColor(colors.HexColor(color2))
    c.setLineWidth(2)
    c.rect(margin+8, margin+8, w-2*(margin+8), h-2*(margin+8), fill=0, stroke=1)
    # Булангийн чимэглэл
    for x, y in [(margin+2,margin+2),(w-margin-2,margin+2),(margin+2,h-margin-2),(w-margin-2,h-margin-2)]:
        c.setFillColor(colors.HexColor(color1))
        c.circle(x, y, 5, fill=1, stroke=0)

def _centered_text(c, text, y, font, size, color):
    w = c._pagesize[0]
    c.setFont(font, size)
    c.setFillColor(colors.HexColor(color))
    c.drawCentredString(w/2, y, text)

def _draw_line(c, y, w, color, margin=60):
    c.setStrokeColor(colors.HexColor(color))
    c.setLineWidth(1)
    c.line(margin, y, w-margin, y)

def gen_certificate(name, value, school='Орхонтуул ЕБС',
                    title='СЕРТИФИКАТ', subtitle='', date='',
                    cert_type='cert'):
    """
    cert_type: 'cert' (сертификат) | 'award' (өргөмжлөл) | 'thanks' (талархал)
    """
    buf = io.BytesIO()
    w, h = landscape(A4)
    cv = canvas.Canvas(buf, pagesize=landscape(A4))

    THEMES = {
        'cert':  {'bg':'#f0fdf4','border1':'#166534','border2':'#4ade80','title':'#166534','text':'#1e3a5f','accent':'#15803d'},
        'award': {'bg':'#fffbeb','border1':'#92400e','border2':'#fbbf24','title':'#92400e','text':'#1e3a5f','accent':'#b45309'},
        'thanks':{'bg':'#f0f9ff','border1':'#1e40af','border2':'#60a5fa','title':'#1e40af','text':'#1e3a5f','accent':'#2563eb'},
    }
    th = THEMES.get(cert_type, THEMES['cert'])

    # Background
    cv.setFillColor(colors.HexColor(th['bg']))
    cv.rect(0, 0, w, h, fill=1, stroke=0)

    # Decorative background pattern
    cv.setFillColor(colors.HexColor(th['border2']))
    cv.setFillAlpha(0.05)
    for i in range(0, int(w)+50, 50):
        for j in range(0, int(h)+50, 50):
            cv.circle(i, j, 2, fill=1, stroke=0)
    cv.setFillAlpha(1)

    # Border
    _draw_border(cv, w, h, th['border1'], th['border2'])

    # School name top
    _centered_text(cv, school, h-55, 'MNB', 13, th['accent'])

    # Main title
    _centered_text(cv, title, h-110, 'MNB', 38, th['title'])

    # Decorative line
    _draw_line(cv, h-125, w, th['border2'])

    # Subtitle
    if subtitle:
        _centered_text(cv, subtitle, h-155, 'MN', 13, th['text'])

    # "Энэ сертификатыг" гэсэн текст
    cert_labels = {
        'cert': 'Энэ сертификатыг дараах хүнд олгоно',
        'award': 'Энэ өргөмжлөлийг дараах хүнд гардуулна',
        'thanks': 'Энэ талархалыг дараах хүнд илэрхийлнэ',
    }
    _centered_text(cv, cert_labels.get(cert_type,''), h-200, 'MN', 12, th['text'])

    # Name — том, тод
    _draw_line(cv, h/2+50, w, th['border2'], margin=100)
    _centered_text(cv, name, h/2+20, 'MNB', 32, th['title'])
    _draw_line(cv, h/2-10, w, th['border2'], margin=100)

    # Value/Reason
    if value:
        _centered_text(cv, value, h/2-50, 'MN', 13, th['text'])

    # Date & signature area
    sig_y = 80
    # Left: signature
    cv.setFont('MN', 10)
    cv.setFillColor(colors.HexColor(th['text']))
    cv.drawString(80, sig_y+30, 'Гарын үсэг: _________________')
    cv.drawString(80, sig_y+10, 'Захирал:    _________________')
    # Center: seal placeholder
    cv.setStrokeColor(colors.HexColor(th['border1']))
    cv.setFillColor(colors.HexColor(th['bg']))
    cv.setLineWidth(1.5)
    cv.circle(w/2, sig_y+20, 30, fill=1, stroke=1)
    cv.setFont('MN', 7)
    cv.setFillColor(colors.HexColor(th['border1']))
    cv.drawCentredString(w/2, sig_y+22, 'ТАМГА')
    cv.drawCentredString(w/2, sig_y+12, 'SEAL')
    # Right: date
    if date:
        cv.setFont('MN', 11)
        cv.setFillColor(colors.HexColor(th['text']))
        cv.drawRightString(w-80, sig_y+20, date)

    cv.save()
    buf.seek(0)
    return buf.getvalue()


def gen_batch(names_values, school='Орхонтуул ЕБС',
              title='СЕРТИФИКАТ', subtitle='', date='', cert_type='cert'):
    """names_values: [{'name':'...','value':'...'}, ...]"""
    from reportlab.lib.pagesizes import A4, landscape
    from pypdf import PdfWriter
    import io

    writer = PdfWriter()
    for item in names_values:
        pdf_bytes = gen_certificate(
            name=item.get('name',''),
            value=item.get('value',''),
            school=school, title=title, subtitle=subtitle,
            date=date, cert_type=cert_type
        )
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(pdf_bytes))
        writer.add_page(reader.pages[0])

    out = io.BytesIO()
    writer.write(out)
    out.seek(0)
    return out.getvalue()
