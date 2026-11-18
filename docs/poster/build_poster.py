#!/usr/bin/env python3
"""Póster R-ONE: pliego Unilibre, paleta suave, Nunito, se lee solo."""

from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE, MSO_SHAPE_TYPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Pt

ROOT = Path("/home/personal/Projects/ulibre-prometeo/pba-launcher")
ASSETS = ROOT / "docs/poster/assets"
FONTS = ROOT / "docs/poster/fonts"
WEB = ROOT / "pmas-web-main/public/assets/assets"
TEMPLATE = ROOT / "docs/poster/plantilla-poster.pptx"
OUTPUT = ROOT / "docs/poster/poster-r-one.pptx"
PREVIEW = ASSETS / "preview-poster.png"

# Paleta suave: pizarra, teal y sage, papel cálido. El rojo Unilibre
# queda en el título de la plantilla, la línea del pie y el número de sección.
SLATE = RGBColor(0x4A, 0x65, 0x76)
TEAL = RGBColor(0x7E, 0xB6, 0xC4)
TEAL_DEEP = RGBColor(0x3E, 0x72, 0x82)
SAGE = RGBColor(0x7D, 0xAA, 0x96)
SAGE_DEEP = RGBColor(0x4A, 0x7A, 0x68)
RED = RGBColor(0xBE, 0x18, 0x18)
PAPER = RGBColor(0xF4, 0xF1, 0xEB)
CARD = RGBColor(0xFC, 0xFA, 0xF6)
INK = RGBColor(0x2F, 0x3E, 0x4C)
MUTED = RGBColor(0x5C, 0x6E, 0x7A)
BORDER = RGBColor(0xD5, 0xDC, 0xE0)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
AIR = RGBColor(0xEE, 0xF3, 0xF5)
MIST = RGBColor(0xE4, 0xED, 0xF0)
CHIP = RGBColor(0xC3, 0xDE, 0xE6)
CHIP_SAGE = RGBColor(0xC6, 0xE0, 0xD2)
HERO_BG = RGBColor(0xE6, 0xEE, 0xF1)

HEX = {
    "navy": "#4A6576",
    "paper": "#F4F1EB",
    "card": "#FCFAF6",
    "cyan": "#7EB6C4",
    "emerald": "#7DAA96",
    "red": "#BE1818",
    "ink": "#2F3E4C",
    "muted": "#5C6E7A",
    "air": "#EEF3F5",
    "border": "#D5DCE0",
    "mist": "#E4EDF0",
}

FONT_REG = str(FONTS / "Nunito-Regular.ttf")
FONT_BOLD = str(FONTS / "Nunito-Bold.ttf")
FONT_SEMI = str(FONTS / "Nunito-SemiBold.ttf")
FONT_IT = str(FONTS / "Nunito-Italic.ttf")
FONT_MONTS = str(FONTS / "Montserrat-Bold.ttf")
SCALE = {"Calibri": 1.0, "Arial": 1.0, "Montserrat Bold": 1.0, "Nunito": 1.0}
KEEP = {
    "Imagen 75",
    "Imagen 4",
    "TextBox 70",
    "TextBox 73",
    "TextBox 74",
    "AutoShape 71",
}

TITLE = "Nunito"
BODYF = "Nunito"
HEAD_F = "Montserrat Bold"
HEAD_H = 1.05
BODY = 26
SUB = 23
CAP = 18
H1 = 34

HERO_SRC = WEB / "IMG-20251031-WA0005.jpg"
EVENT_A = ASSETS / "IMG-20260423-WA0007 (1).jpg"
EVENT_B = ASSETS / "IMG-20260423-WA0022.jpg"
EVENT_C = ASSETS / "IMG-20260424-WA0035.jpg"


def emu(inches: float) -> int:
    return int(round(inches * 914400))


def T(t, sz=BODY, b=False, c=INK, f=BODYF, a=PP_ALIGN.LEFT, sa=0, ls=1.22, i=False):
    return {
        "t": t,
        "sz": sz,
        "b": b,
        "c": c,
        "f": f,
        "a": a,
        "sa": sa,
        "ls": ls,
        "i": i,
    }


def set_font(run, name: str) -> None:
    rpr = run._r.get_or_add_rPr()
    latin = rpr.find(qn("a:latin"))
    if latin is None:
        latin = rpr.makeelement(qn("a:latin"), {})
        rpr.append(latin)
    latin.set("typeface", name)
    run.font.name = name


def write_tf(tf, items, anchor=MSO_ANCHOR.TOP, ml=0.0, mr=0.0, mt=0.0, mb=0.0):
    tf.clear()
    tf.word_wrap = True
    tf.auto_size = None
    tf.vertical_anchor = anchor
    tf.margin_left = emu(ml)
    tf.margin_right = emu(mr)
    tf.margin_top = emu(mt)
    tf.margin_bottom = emu(mb)
    for n, item in enumerate(items):
        p = tf.paragraphs[0] if n == 0 else tf.add_paragraph()
        p.alignment = item["a"]
        p.space_after = Pt(item["sa"])
        p.line_spacing = item["ls"]
        run = p.add_run()
        run.text = item["t"]
        run.font.size = Pt(item["sz"])
        run.font.bold = item["b"]
        run.font.italic = item["i"]
        run.font.color.rgb = item["c"]
        set_font(run, item["f"])


def shape(slide, kind, x, y, w, h, fill, line=None, adj=None):
    sh = slide.shapes.add_shape(kind, emu(x), emu(y), emu(w), emu(h))
    if adj is not None:
        try:
            sh.adjustments[0] = adj
        except Exception:
            pass
    sh.fill.solid()
    sh.fill.fore_color.rgb = fill
    if line is None:
        sh.line.fill.background()
    else:
        sh.line.color.rgb = line
        sh.line.width = Pt(1.5)
    sh.shadow.inherit = False
    return sh


def rect(slide, x, y, w, h, fill, line=None, adj=0.04):
    return shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h, fill, line, adj)


def box(
    slide,
    x,
    y,
    w,
    h,
    fill,
    items,
    anchor=MSO_ANCHOR.MIDDLE,
    line=None,
    adj=0.08,
    pad=(0.14, 0.14, 0.1, 0.1),
    kind=MSO_SHAPE.ROUNDED_RECTANGLE,
):
    sh = shape(slide, kind, x, y, w, h, fill, line, adj)
    write_tf(
        sh.text_frame, items, anchor=anchor, ml=pad[0], mr=pad[1], mt=pad[2], mb=pad[3]
    )
    return sh


def text(slide, x, y, w, h, items, anchor=MSO_ANCHOR.TOP):
    tb = slide.shapes.add_textbox(emu(x), emu(y), emu(w), emu(h))
    write_tf(tb.text_frame, items, anchor=anchor)
    return tb


def _font(sz_px, bold, italic, family=""):
    fam = family or ""
    if "Montserrat" in fam:
        pathf = FONT_MONTS
    elif italic:
        pathf = FONT_IT
    elif bold:
        pathf = FONT_BOLD
    else:
        pathf = FONT_REG
    return ImageFont.truetype(pathf, max(6, int(sz_px)))


def measure(items, w_in, dpi=100) -> float:
    d = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    width_px = max(8, w_in * dpi)
    total = 0.0
    for it in items:
        f = _font(
            it["sz"] * dpi / 72 * SCALE.get(it["f"], 1.0), it["b"], it["i"], it["f"]
        )
        lh = it["sz"] * dpi / 72 * 1.2 * it["ls"]
        n = 0
        for hard in it["t"].split("\n"):
            cur = ""
            n += 1
            for wd in hard.split(" "):
                trial = (cur + " " + wd).strip()
                if d.textlength(trial, font=f) <= width_px or not cur:
                    cur = trial
                else:
                    n += 1
                    cur = wd
        total += n * lh + it["sa"] * dpi / 72
    return total / dpi * 1.1 + 0.05


def flow_text(slide, x, y, w, items) -> float:
    h = measure(items, w)
    text(slide, x, y, w, h, items)
    return y + h


class Card:
    def __init__(self, slide, x, y, w, num, title):
        self.x, self.y, self.w, self.slide = x, y, w, slide
        self.bg = rect(slide, x, y, w, 1.5, CARD, line=BORDER, adj=0.025)
        box(
            slide,
            x + 0.22,
            y + 0.18,
            0.72,
            0.72,
            RED,
            [T(num, 18, True, WHITE, TITLE, PP_ALIGN.CENTER, ls=1.0)],
            kind=MSO_SHAPE.OVAL,
            pad=(0, 0, 0, 0),
        )
        text(
            slide,
            x + 1.08,
            y,
            w - 1.28,
            HEAD_H,
            [T(title, H1, True, SLATE, TITLE, ls=1.0)],
            anchor=MSO_ANCHOR.MIDDLE,
        )
        shape(
            slide,
            MSO_SHAPE.RECTANGLE,
            x + 0.22,
            y + HEAD_H - 0.04,
            w - 0.44,
            0.055,
            TEAL,
        )
        self.body = y + HEAD_H + 0.22

    def close(self, bottom: float) -> float:
        self.bg.height = emu(max(0.4, bottom - self.y))
        return bottom


def round_rgba(im: Image.Image, radius_frac=0.045) -> Image.Image:
    im = im.convert("RGBA")
    w, h = im.size
    r = max(8, int(min(w, h) * radius_frac))
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w - 1, h - 1), r, fill=255)
    im.putalpha(mask)
    return im


def cover_crop(im: Image.Image, aspect: float, focus: str) -> Image.Image:
    src = im.width / im.height
    if src < aspect:
        new_h = max(1, int(im.width / aspect))
        extra = im.height - new_h
        if focus == "top":
            top = 0
        elif focus == "bottom":
            top = extra
        elif focus == "people":
            top = int(extra * 0.38)
        else:
            top = extra // 4
        return im.crop((0, top, im.width, top + new_h))
    new_w = max(1, int(im.height * aspect))
    extra = im.width - new_w
    left = extra // 2 if focus != "left" else extra // 5
    return im.crop((left, 0, left + new_w, im.height))


def picture(slide, src: Path, x, y, w, h, focus="center", round_it=True) -> None:
    with Image.open(src) as im:
        im = cover_crop(im.convert("RGB"), w / h, focus)
        im = im.resize(
            (max(8, int(w * 140)), max(8, int(h * 140))), Image.Resampling.LANCZOS
        )
        if round_it:
            im = round_rgba(im)
            tmp = ASSETS / "_fit.png"
            im.save(tmp, "PNG")
        else:
            tmp = ASSETS / "_fit.jpg"
            im.save(tmp, "JPEG", quality=90)
    slide.shapes.add_picture(str(tmp), emu(x), emu(y), width=emu(w), height=emu(h))


def im_aspect(path: Path) -> float:
    with Image.open(path) as im:
        return im.height / im.width


def picture_contain(slide, src: Path, x, y, w, max_h) -> float:
    with Image.open(src) as im:
        im = im.convert("RGB")
        h = w * im.height / im.width
        use_w = w
        if h > max_h:
            h = max_h
            use_w = h * im.width / im.height
            x = x + (w - use_w) / 2
        im = round_rgba(
            im.resize(
                (max(8, int(use_w * 140)), max(8, int(h * 140))),
                Image.Resampling.LANCZOS,
            ),
            0.03,
        )
        tmp = ASSETS / "_fit.png"
        im.save(tmp, "PNG")
    slide.shapes.add_picture(str(tmp), emu(x), emu(y), width=emu(use_w), height=emu(h))
    return h


def delete_content(slide) -> None:
    for sh in list(slide.shapes):
        if sh.name not in KEEP:
            sh._element.getparent().remove(sh._element)


def fix_header(slide) -> None:
    sem = next(s for s in slide.shapes if s.name == "TextBox 73")
    write_tf(
        sem.text_frame,
        [
            T(
                "Semillero de Investigación PROMETEO",
                40,
                True,
                INK,
                HEAD_F,
                PP_ALIGN.CENTER,
                ls=1.0,
            )
        ],
        anchor=MSO_ANCHOR.MIDDLE,
    )


def send_to_back(slide, sh) -> None:
    tree = slide.shapes._spTree
    el = sh._element
    tree.remove(el)
    tree.insert(2, el)


def chevrons(slide, x, y, w, h, steps):
    n = len(steps)
    k = h * 0.34
    sw = (w + (n - 1) * k * 0.55) / n
    for i, (label, sub, fill, ink) in enumerate(steps):
        kind = MSO_SHAPE.PENTAGON if i == 0 else MSO_SHAPE.CHEVRON
        sx = x + i * (sw - k * 0.55)
        box(
            slide,
            sx,
            y,
            sw,
            h,
            fill,
            [
                T(label, 22, True, ink, TITLE, PP_ALIGN.CENTER, sa=3, ls=1.0),
                T(sub, 16, False, ink, TITLE, PP_ALIGN.CENTER, ls=1.0),
            ],
            kind=kind,
            adj=None,
            pad=(k * 0.9 if i else 0.12, k * 0.55, 0.08, 0.08),
        )


def soft_chip(slide, x, y, w, h, value, label, fill=CHIP, ink=TEAL_DEEP):
    box(
        slide,
        x,
        y,
        w,
        h,
        fill,
        [
            T(value, 32, True, ink, TITLE, PP_ALIGN.CENTER, sa=4, ls=1.0),
            T(label, 16, False, MUTED, TITLE, PP_ALIGN.CENTER, ls=1.05),
        ],
        adj=0.14,
    )


def main() -> None:
    shutil.copyfile(TEMPLATE, OUTPUT)
    prs = Presentation(str(OUTPUT))
    slide = prs.slides[0]
    delete_content(slide)
    fix_header(slide)

    bg = rect(slide, 0, 6.02, 35.43, 40.92, PAPER, adj=0.0)
    send_to_back(slide, bg)

    # ── héroe claro ───────────────────────────────────────
    hy, hh = 6.16, 5.72
    rect(slide, 0.36, hy, 34.71, hh, HERO_BG, line=BORDER, adj=0.016)
    ph, pw = hh - 0.36, 5.05
    picture(slide, HERO_SRC, 0.54, hy + 0.18, pw, ph, focus="top")
    tx = 0.54 + pw + 0.42
    tw = 34.71 - tx + 0.18
    box(
        slide,
        tx,
        hy + 0.22,
        9.4,
        0.48,
        CHIP,
        [
            T(
                "Semillero Prometeo  ·  Universidad Libre",
                16,
                True,
                TEAL_DEEP,
                TITLE,
                PP_ALIGN.CENTER,
                ls=1.0,
            )
        ],
        adj=0.4,
        pad=(0.1, 0.1, 0.04, 0.04),
    )
    text(
        slide,
        tx,
        hy + 0.82,
        tw,
        1.55,
        [
            T(
                "Un androide que escucha, mira y responde",
                36,
                True,
                SLATE,
                TITLE,
                sa=8,
                ls=1.02,
            ),
            T(
                "R-ONE ve a quien tiene delante, conversa en español y gesticula desde un miniPC.",
                24,
                False,
                MUTED,
                ls=1.16,
            ),
        ],
    )
    chevrons(
        slide,
        tx,
        hy + 2.52,
        tw,
        1.42,
        [
            ("Escucha", "micrófono", TEAL_DEEP, WHITE),
            ("Ve", "cámaras", SAGE_DEEP, WHITE),
            ("Comprende", "la escena", TEAL_DEEP, WHITE),
            ("Responde", "en español", SAGE_DEEP, WHITE),
            ("Se mueve", "voz y gesto", TEAL_DEEP, WHITE),
        ],
    )
    text(
        slide,
        tx,
        hy + 4.12,
        tw,
        hh - 4.32,
        [
            T(
                "Una pregunta a la vez. Entra por el chat o por el micrófono. Sale en voz y, si hay un gesto válido en el catálogo, también en el cuerpo.",
                22,
                False,
                MUTED,
                ls=1.2,
            )
        ],
        anchor=MSO_ANCHOR.MIDDLE,
    )

    # ── columnas ──────────────────────────────────────────
    M, G = 0.38, 0.30
    W = (35.43 - 2 * M - 2 * G) / 3
    L, C, R = M, M + W + G, M + 2 * (W + G)
    TOP, BOT = 12.08, 38.72
    PAD = 0.32
    IW = W - 2 * PAD

    # 01 Introducción
    xi = L + PAD
    card = Card(slide, L, TOP, W, "01", "Introducción")
    y = flow_text(
        slide,
        xi,
        card.body,
        IW,
        [
            T(
                "R-ONE es un androide de tamaño humano del semillero Prometeo, en la Universidad Libre. El cuerpo parte de InMoov: cabeza, brazos y manos impresos en 3D, movidos por servomotores.",
                BODY,
                sa=16,
                ls=1.22,
            ),
            T(
                "Le pusimos cámaras, micrófono, parlante y un miniPC Jetson. Hoy reconoce a los integrantes, conversa en español y ejecuta gestos diseñados en un estudio web.",
                BODY,
                ls=1.22,
            ),
        ],
    )
    b1 = card.close(y + 0.28)

    # 02 Problema
    card = Card(slide, L, b1 + G, W, "02", "El problema")
    y = flow_text(
        slide,
        xi,
        card.body,
        IW,
        [
            T(
                "Conversar de verdad pide tres cosas a la vez: ver a la persona, entender la pregunta y mover el cuerpo. Si una de las tres falla, la conversación se corta.",
                BODY,
                sa=16,
                ls=1.22,
            ),
            T(
                "Eso tiene que ocurrir en el propio robot, con un computador modesto y sin depender siempre de internet. Por eso existe una mesa de control: para ver si el robot está libre y lanzar un gesto con Normal o Neutro.",
                BODY,
                ls=1.22,
            ),
        ],
    )
    b2 = card.close(y + 0.28)

    # 03 Objetivos
    card = Card(slide, L, b2 + G, W, "03", "Objetivos")
    gen = [
        T("Objetivo general", 18, True, TEAL_DEEP, TITLE, sa=8, ls=1.0),
        T(
            "Percibir a las personas, conversar en español y responder con voz y gesto, integrando visión, lenguaje y control en un miniPC.",
            24,
            False,
            INK,
            ls=1.2,
        ),
    ]
    gh = measure(gen, IW - 0.48) + 0.5
    y = card.body
    box(
        slide,
        xi,
        y,
        IW,
        gh,
        MIST,
        gen,
        line=BORDER,
        adj=0.07,
        pad=(0.24, 0.24, 0.16, 0.16),
    )
    y += gh + 0.22
    specs = [
        (
            SAGE,
            "Percibir",
            "Reconocer a los integrantes del semillero con un detector propio, entrenado con nuestras imágenes, y seguirlos cuando pasan de una cámara a otra.",
        ),
        (
            TEAL_DEEP,
            "Conversar",
            "Responder en español con una memoria propia. Si la pregunta no está ahí, usar la nube; si no hay red, un modelo local en el miniPC.",
        ),
        (
            SLATE,
            "Mover",
            "Diseñar secuencias de cabeza, brazos y manos en un estudio web, y lanzarlas desde la mesa de control con el par Normal y Neutro.",
        ),
    ]
    row = (BOT - 0.22 - y - 0.18 * 2) / 3
    for n, (fill, verb, para) in enumerate(specs):
        rect(slide, xi, y, IW, row, AIR if n % 2 else CARD, line=BORDER, adj=0.07)
        box(
            slide,
            xi + 0.16,
            y + 0.22,
            0.7,
            0.7,
            fill,
            [T(str(n + 1), 22, True, WHITE, TITLE, PP_ALIGN.CENTER, ls=1.0)],
            kind=MSO_SHAPE.OVAL,
            pad=(0, 0, 0, 0),
        )
        text(
            slide,
            xi + 1.02,
            y + 0.12,
            IW - 1.18,
            row - 0.2,
            [
                T(verb, 26, True, SLATE, TITLE, sa=8, ls=1.0),
                T(para, BODY, False, INK, ls=1.2),
            ],
        )
        y += row + 0.18
    card.close(BOT)

    # 04 Metodología
    xi = C + PAD
    card = Card(slide, C, TOP, W, "04", "Metodología")
    y = flow_text(
        slide,
        xi,
        card.body,
        IW,
        [
            T(
                "El trabajo tiene dos caminos que se encuentran en el miniPC. El cuerpo ejecuta el movimiento. La mente decide qué decir y qué gesto lanzar.",
                BODY,
                ls=1.22,
            ),
        ],
    )
    y += 0.2
    for name, fill, para, bg in (
        (
            "Cuerpo",
            SAGE_DEEP,
            "El androide es InMoov impreso en 3D. Lo mueven servos SG90 y DS5160, cuatro placas PCA9685 por I2C y un Arduino Mega por puerto serie.",
            CHIP_SAGE,
        ),
        (
            "Mente",
            TEAL_DEEP,
            "La mente parte de 802 imágenes y 25 clases, un detector YOLO11s, la web con gateway y NATS, y el turno de conversación en la Jetson.",
            CHIP,
        ),
    ):
        items = [
            T(name, 22, True, fill, TITLE, sa=8, ls=1.0),
            T(para, BODY, False, INK, ls=1.2),
        ]
        lh = measure(items, IW - 0.48) + 0.42
        box(
            slide,
            xi,
            y,
            IW,
            lh,
            bg,
            items,
            anchor=MSO_ANCHOR.TOP,
            line=BORDER,
            adj=0.07,
            pad=(0.22, 0.22, 0.16, 0.16),
        )
        y += lh + 0.16
    y = flow_text(
        slide,
        xi,
        y,
        IW,
        [
            T("De la pregunta al gesto", 26, True, SLATE, TITLE, sa=10, ls=1.0),
            T(
                "La pregunta entra por el chat o el micrófono. El detector mira a la persona y BLIP describe la escena. Si esa pregunta ya está en la memoria, R-ONE responde al momento. Si no, usa la nube o, sin internet, Gemma en el miniPC. El gesto solo se mueve si está en el catálogo de esa llamada.",
                BODY,
                ls=1.22,
            ),
        ],
    )
    y += 0.18
    chevrons(
        slide,
        xi,
        y,
        IW,
        1.18,
        [
            ("Chat", "o micrófono", TEAL_DEEP, WHITE),
            ("Visión", "YOLO y BLIP", SAGE_DEEP, WHITE),
            ("Memoria", "o Gemma", TEAL_DEEP, WHITE),
            ("Voz", "y gesto", SAGE_DEEP, WHITE),
        ],
    )
    y += 1.36
    cw = (IW - 0.16 * 2) / 3
    for i, (val, lab, fill, ink) in enumerate(
        (
            ("17", "servos en la cabeza", CHIP, TEAL_DEEP),
            ("4", "placas PCA9685", CHIP_SAGE, SAGE_DEEP),
            ("10", "canales por brazo", CHIP, TEAL_DEEP),
        )
    ):
        soft_chip(slide, xi + i * (cw + 0.16), y, cw, 1.62, val, lab, fill, ink)
    y += 1.8
    remain = BOT - 0.18 - y
    img_h = picture_contain(
        slide, ASSETS / "cabeza.jpeg", xi, y, IW, max(2.6, remain - 0.72)
    )
    y += img_h + 0.1
    y = flow_text(
        slide,
        xi,
        y,
        IW,
        [
            T(
                "Cabeza: 17 servos SG90 sobre PCA9685. El Arduino solo recibe posición y velocidad.",
                CAP,
                False,
                MUTED,
                i=True,
                ls=1.08,
            ),
        ],
    )
    card.close(max(y + 0.16, BOT))

    # 05 Resultados
    xi = R + PAD
    card = Card(slide, R, TOP, W, "05", "Resultados")
    y = flow_text(
        slide,
        xi,
        card.body,
        IW,
        [
            T(
                "El detector propio se entrenó con 802 imágenes y 25 clases: cada clase es un integrante del semillero, no una persona genérica. En la corrida train5, YOLO11s llega a 0,88 de precisión, 0,93 de recall y 0,94 de mAP50, en 60 épocas.",
                BODY,
                ls=1.22,
            ),
        ],
    )
    y += 0.18
    cw3 = (IW - 0.14) / 3
    for i, (val, lab, fill, ink) in enumerate(
        (
            ("0,88", "Precisión", CHIP, TEAL_DEEP),
            ("0,93", "Recall", CHIP_SAGE, SAGE_DEEP),
            ("0,94", "mAP50", CHIP, TEAL_DEEP),
        )
    ):
        soft_chip(slide, xi + i * (cw3 + 0.07), y, cw3, 1.58, val, lab, fill, ink)
    y += 1.74
    y = flow_text(
        slide,
        xi,
        y,
        IW,
        [
            T(
                "En la mesa de control eso se ve en vivo: el sistema nombra a la persona y la sigue entre cámaras. Aquí, Johel Arias.",
                BODY,
                ls=1.2,
            ),
        ],
    )
    y += 0.16
    vis = ASSETS / "_cap-vision.png"
    with Image.open(ASSETS / "cap-vision.png") as im:
        im.convert("RGB").crop((52, 328, im.width, im.height)).save(vis)
    vis_h = min(4.5, IW * im_aspect(vis))
    picture(slide, vis, xi, y, IW, vis_h, focus="center")
    b5 = card.close(y + vis_h + 0.22)

    # 06 Conclusiones
    card = Card(slide, R, b5 + G, W, "06", "Conclusiones")
    blocks = [
        (
            SAGE,
            "El lazo ya cierra.",
            "Una pregunta recorre visión, memoria y voz. Si el catálogo trae un gesto válido, el cuerpo también responde.",
        ),
        (
            TEAL_DEEP,
            "El detector reconoce al semillero.",
            "En train5 el mAP50 llega a 0,94. La clase es un integrante, no un rostro anónimo.",
        ),
        (
            SLATE,
            "El cuerpo ya tiene lenguaje.",
            "Cabeza, brazos y manos se mueven con el par gesto y reposo, diseñado en el estudio web.",
        ),
        (
            RED,
            "Todavía falta trabajo.",
            "Varios gestos aún no tienen descripción, y la GPU de la Jetson no se está usando.",
        ),
    ]
    y = card.body
    avail = BOT - 0.2 - y
    bh = (avail - 0.16 * 3) / 4
    for color, title, body in blocks:
        rect(slide, xi, y, IW, bh, CARD, line=BORDER, adj=0.07)
        shape(slide, MSO_SHAPE.RECTANGLE, xi, y, 0.12, bh, color)
        text(
            slide,
            xi + 0.34,
            y,
            IW - 0.5,
            bh,
            [
                T(title, 24, True, SLATE, TITLE, sa=8, ls=1.0),
                T(body, BODY, False, INK, ls=1.2),
            ],
            anchor=MSO_ANCHOR.MIDDLE,
        )
        y += bh + 0.16
    card.close(BOT)

    # ── tres fotos de eventos, proporción propia ──────────
    ey, eh = 38.92, 5.72
    rect(slide, M, ey, 35.43 - 2 * M, eh, CARD, line=BORDER, adj=0.02)
    pic_h = eh - 0.28
    py = ey + 0.14
    portrait_w = pic_h * 0.58
    group_w = pic_h * 1.72
    gap = 0.18
    x0 = M + 0.16
    picture(slide, EVENT_A, x0, py, portrait_w, pic_h, focus="center")
    x0 += portrait_w + gap
    picture(slide, EVENT_B, x0, py, group_w, pic_h, focus="people")
    x0 += group_w + gap
    picture(slide, EVENT_C, x0, py, group_w, pic_h, focus="people")
    x0 += group_w + 0.28
    cap_w = 35.43 - M - 0.2 - x0
    text(
        slide,
        x0,
        py,
        cap_w,
        pic_h,
        [
            T("R-ONE en divulgación", 28, True, SLATE, TITLE, sa=14, ls=1.05),
            T(
                "El semillero Prometeo saca al androide del laboratorio. El cuerpo es InMoov. La mente corre en un miniPC: escucha, mira y responde.",
                22,
                False,
                MUTED,
                ls=1.22,
            ),
        ],
        anchor=MSO_ANCHOR.MIDDLE,
    )

    # ── referencias ───────────────────────────────────────
    ry = 44.78
    rect(slide, M, ry, 35.43 - 2 * M, 2.08, SLATE, adj=0.02)
    text(
        slide,
        M + 0.24,
        ry + 0.1,
        18,
        0.4,
        [T("07   Referencias", 20, True, WHITE, TITLE, ls=1.0)],
    )
    refs_a = [
        "[1] Ultralytics. Documentación de YOLO11.",
        "[2] Li et al. BLIP. ICML, 2022.",
        "[3] Google DeepMind. Gemma, familia de modelos.",
        "[4] Zilliz. Milvus Lite.",
    ]
    refs_b = [
        "[5] NATS.io. Documentación del servidor.",
        "[6] Lange, G. InMoov, robot abierto de tamaño humano.",
        "[7] Alphacephei. Vosk, reconocimiento de voz.",
        "[8] Rhasspy. Piper, síntesis de voz.",
    ]
    text(
        slide,
        M + 0.24,
        ry + 0.55,
        16.8,
        1.4,
        [T(r, 16, False, WHITE, sa=4, ls=1.08) for r in refs_a],
    )
    text(
        slide,
        18.3,
        ry + 0.55,
        16.6,
        1.4,
        [T(r, 16, False, WHITE, sa=4, ls=1.08) for r in refs_b],
    )

    prs.save(str(OUTPUT))
    warns = preview(OUTPUT, PREVIEW)
    for tmp in ASSETS.glob("_*.png"):
        tmp.unlink(missing_ok=True)
    for tmp in ASSETS.glob("_*.jpg"):
        tmp.unlink(missing_ok=True)
    for wmsg in warns:
        print(wmsg)
    print("Wrote", OUTPUT)
    print("Preview", PREVIEW, "warnings:", len(warns))


def preview(pptx_path: Path, out: Path, dpi: int = 34) -> list[str]:
    prs = Presentation(str(pptx_path))
    slide = prs.slides[0]
    W = int(prs.slide_width / 914400 * dpi)
    H = int(prs.slide_height / 914400 * dpi)
    canvas = Image.new("RGB", (W, H), HEX["paper"])
    d = ImageDraw.Draw(canvas)
    warnings = []

    def px(v):
        return v / 914400 * dpi

    for sh in slide.shapes:
        x, y, w, h = px(sh.left), px(sh.top), px(sh.width), px(sh.height)
        if sh.shape_type == MSO_SHAPE_TYPE.PICTURE:
            tmp = ASSETS / "_pv.png"
            tmp.write_bytes(sh.image.blob)
            im = (
                Image.open(tmp)
                .convert("RGBA")
                .resize((max(1, int(w)), max(1, int(h))), Image.Resampling.LANCZOS)
            )
            canvas.paste(im, (int(x), int(y)), im)
            tmp.unlink(missing_ok=True)
            continue
        if sh.shape_type == MSO_SHAPE_TYPE.LINE:
            d.line((x, y, x + w, y + h), fill=HEX["red"], width=max(2, dpi // 14))
            continue
        if sh.shape_type == MSO_SHAPE_TYPE.AUTO_SHAPE:
            try:
                fill = f"#{sh.fill.fore_color.rgb}"
            except Exception:
                fill = None
            outline = None
            try:
                if sh.line.color.rgb is not None:
                    outline = f"#{sh.line.color.rgb}"
            except Exception:
                outline = None
            try:
                kind = sh.auto_shape_type
            except ValueError:
                kind = None
            if kind == MSO_SHAPE.OVAL:
                d.ellipse((x, y, x + w, y + h), fill=fill, outline=outline)
            elif kind in (MSO_SHAPE.CHEVRON, MSO_SHAPE.PENTAGON):
                k = h * 0.35
                pts = [
                    (x, y),
                    (x + w - k, y),
                    (x + w, y + h / 2),
                    (x + w - k, y + h),
                    (x, y + h),
                ]
                if kind == MSO_SHAPE.CHEVRON:
                    pts.append((x + k, y + h / 2))
                d.polygon(pts, fill=fill, outline=outline)
            else:
                d.rounded_rectangle(
                    (x, y, x + w, y + h),
                    radius=max(2, min(w, h) * 0.05),
                    fill=fill,
                    outline=outline,
                    width=1,
                )
        if not sh.has_text_frame or not sh.text_frame.text.strip():
            continue
        tf = sh.text_frame
        ml, mr = px(tf.margin_left or 0), px(tf.margin_right or 0)
        mt, mb = px(tf.margin_top or 0), px(tf.margin_bottom or 0)
        inner_w = max(8, w - ml - mr)
        lines = []
        for p in tf.paragraphs:
            if not p.runs:
                continue
            run = p.runs[0]
            sz = run.font.size.pt if run.font.size else 16
            fam = run.font.name or "Nunito"
            f = _font(
                sz * dpi / 72 * SCALE.get(fam, 1.0),
                bool(run.font.bold),
                bool(run.font.italic),
                fam,
            )
            raw_ls = p.line_spacing
            mult = raw_ls if isinstance(raw_ls, float) and raw_ls < 4 else 1.05
            lh = sz * dpi / 72 * 1.18 * mult
            try:
                color = f"#{run.font.color.rgb}"
            except Exception:
                color = HEX["ink"]
            for hard in p.text.split("\n"):
                cur = ""
                for wd in hard.split(" "):
                    trial = (cur + " " + wd).strip()
                    if d.textlength(trial, font=f) <= inner_w or not cur:
                        cur = trial
                    else:
                        lines.append((cur, f, lh, color, p.alignment))
                        cur = wd
                lines.append((cur, f, lh, color, p.alignment))
        total = sum(l[2] for l in lines)
        avail = h - mt - mb
        if total > avail + 2 and tf.text.strip() != "R-ONE":
            warnings.append(
                f"OVERFLOW {total / dpi:.2f}>{avail / dpi:.2f} :: {tf.text[:60]!r}"
            )
        if tf.vertical_anchor == MSO_ANCHOR.MIDDLE:
            cy = y + mt + max(0, (avail - total) / 2)
        else:
            cy = y + mt
        for t, f, lh, color, align in lines:
            tw = d.textlength(t, font=f)
            tx = x + ml + (inner_w - tw) / 2 if align == PP_ALIGN.CENTER else x + ml
            d.text((tx, cy), t, font=f, fill=color)
            cy += lh
    canvas.save(out, "PNG")
    return warnings


if __name__ == "__main__":
    main()
