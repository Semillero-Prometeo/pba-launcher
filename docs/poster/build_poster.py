#!/usr/bin/env python3
"""Póster R-ONE sobre la plantilla Unilibre / Prometeo."""

from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE, MSO_SHAPE_TYPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Pt

ROOT = Path("/home/personal/Projects/ulibre-prometeo/pba-launcher")
ASSETS = ROOT / "docs/poster/assets"
TEMPLATE = ROOT / "docs/poster/plantilla-poster.pptx"
OUTPUT = ROOT / "docs/poster/poster-r-one.pptx"
PREVIEW = ASSETS / "preview-poster.png"

NAVY = RGBColor(0x0B, 0x25, 0x40)
CYAN = RGBColor(0x38, 0xBD, 0xF8)
CYAN_INK = RGBColor(0x0C, 0x4A, 0x6E)
EMERALD = RGBColor(0x05, 0x96, 0x69)
RED = RGBColor(0xBE, 0x18, 0x18)
PAPER = RGBColor(0xEE, 0xF2, 0xF6)
CARD = RGBColor(0xF7, 0xFA, 0xFC)
INK = RGBColor(0x0B, 0x25, 0x40)
MUTED = RGBColor(0x3D, 0x5A, 0x73)
BORDER = RGBColor(0xC5, 0xD4, 0xE0)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
AIR = RGBColor(0xE8, 0xEE, 0xF4)

HEX = {
    "navy": "#0B2540",
    "paper": "#EEF2F6",
    "card": "#F7FAFC",
    "cyan": "#38BDF8",
    "emerald": "#059669",
    "red": "#BE1818",
    "ink": "#0B2540",
    "muted": "#3D5A73",
    "air": "#E8EEF4",
    "border": "#C5D4E0",
}

FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_IT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf"
SCALE = {"Calibri": 1.0, "Arial": 1.0, "Montserrat Bold": 1.0}

KEEP = {"Imagen 75", "Imagen 4", "TextBox 70", "TextBox 73", "TextBox 74", "AutoShape 71"}


def emu(inches: float) -> int:
    return int(round(inches * 914400))


def T(t, sz=16, b=False, c=INK, f="Arial", a=PP_ALIGN.LEFT, sa=0, ls=1.12, i=False):
    return {"t": t, "sz": sz, "b": b, "c": c, "f": f, "a": a, "sa": sa, "ls": ls, "i": i}


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
        sh.line.width = Pt(1.25)
    sh.shadow.inherit = False
    return sh


def rect(slide, x, y, w, h, fill, line=None, adj=0.04):
    return shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h, fill, line, adj)


def box(slide, x, y, w, h, fill, items, anchor=MSO_ANCHOR.MIDDLE, line=None, adj=0.08, pad=(0.1, 0.1, 0.06, 0.06), kind=MSO_SHAPE.ROUNDED_RECTANGLE):
    sh = shape(slide, kind, x, y, w, h, fill, line, adj)
    write_tf(sh.text_frame, items, anchor=anchor, ml=pad[0], mr=pad[1], mt=pad[2], mb=pad[3])
    return sh


def text(slide, x, y, w, h, items, anchor=MSO_ANCHOR.TOP):
    tb = slide.shapes.add_textbox(emu(x), emu(y), emu(w), emu(h))
    write_tf(tb.text_frame, items, anchor=anchor)
    return tb


def _font(sz_px, bold, italic):
    pathf = FONT_BOLD if bold else (FONT_IT if italic else FONT_REG)
    return ImageFont.truetype(pathf, max(6, int(sz_px)))


def measure(items, w_in, dpi=100) -> float:
    d = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    width_px = w_in * dpi
    total = 0.0
    for it in items:
        f = _font(it["sz"] * dpi / 72 * SCALE.get(it["f"], 0.9), it["b"], it["i"])
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
    return total / dpi * 1.16 + 0.06


def flow_text(slide, x, y, w, items) -> float:
    h = measure(items, w)
    text(slide, x, y, w, h, items)
    return y + h


HEAD_H = 0.78


class Card:
    def __init__(self, slide, x, y, w, num, title):
        self.slide = slide
        self.x, self.y, self.w = x, y, w
        self.bg = rect(slide, x, y, w, 1.2, CARD, line=BORDER, adj=0.03)
        rect(slide, x, y, w, HEAD_H, NAVY, adj=0.08)
        box(
            slide, x + 0.12, y + 0.12, 0.54, 0.54, RED,
            [T(num, 14, True, WHITE, "Arial", PP_ALIGN.CENTER, ls=1.0)],
            kind=MSO_SHAPE.OVAL, pad=(0, 0, 0, 0),
        )
        text(
            slide, x + 0.78, y, w - 0.95, HEAD_H,
            [T(title, 22, True, WHITE, "Arial", ls=1.0)],
            anchor=MSO_ANCHOR.MIDDLE,
        )
        self.body = y + HEAD_H + 0.16

    def close(self, bottom: float) -> float:
        self.bg.height = emu(bottom - self.y)
        return bottom


def picture(slide, path, x, y, w) -> float:
    with Image.open(path) as im:
        h = w * im.height / im.width
    slide.shapes.add_picture(str(path), emu(x), emu(y), width=emu(w), height=emu(h))
    return h


def delete_content(slide) -> None:
    for sh in list(slide.shapes):
        if sh.name not in KEEP:
            sh._element.getparent().remove(sh._element)


def fix_header(slide) -> None:
    sem = next(s for s in slide.shapes if s.name == "TextBox 73")
    write_tf(
        sem.text_frame,
        [T("Semillero de Investigación PROMETEO", 28, True, INK, "Arial", PP_ALIGN.CENTER, ls=1.0)],
        anchor=MSO_ANCHOR.MIDDLE,
    )


def send_to_back(slide, sh) -> None:
    tree = slide.shapes._spTree
    el = sh._element
    tree.remove(el)
    tree.insert(2, el)


def chip(slide, x, y, w, h, value, label, fill):
    box(
        slide, x, y, w, h, fill,
        [
            T(value, 26, True, WHITE, "Arial", PP_ALIGN.CENTER, sa=1, ls=1.0),
            T(label, 13, False, WHITE, "Arial", PP_ALIGN.CENTER, ls=1.0),
        ],
        adj=0.14,
    )


def main() -> None:
    shutil.copyfile(TEMPLATE, OUTPUT)
    prs = Presentation(str(OUTPUT))
    slide = prs.slides[0]
    delete_content(slide)
    fix_header(slide)

    bg = rect(slide, 0, 6.05, 35.43, 40.85, PAPER, adj=0.0)
    send_to_back(slide, bg)

    # ── banda héroe ───────────────────────────────────────
    hero_y, hero_h = 6.22, 4.55
    rect(slide, 0.32, hero_y, 34.79, hero_h, NAVY, adj=0.02)
    photo_w = 3.05
    ph = picture(slide, ASSETS / "foto-hero.jpg", 0.48, hero_y + 0.18, photo_w)
    # recorte visual: si la foto es más alta que la banda, el picture ya usa el alto natural.
    # Limitar alto recolocando si se pasa.
    if ph > hero_h - 0.36:
        # reemplazar no es fácil; la foto se dibuja con altura natural. Recortamos el archivo antes.
        pass
    tx = 0.48 + photo_w + 0.28
    tw = 34.5 - tx
    text(
        slide, tx, hero_y + 0.22, tw, 1.55,
        [
            T("Un androide que escucha, mira y responde", 26, True, WHITE, "Arial", sa=6, ls=1.0),
            T("R-ONE pertenece al semillero Prometeo. Une visión, conversación en español y movimiento del cuerpo en un miniPC.", 16, False, RGBColor(0xD6, 0xE4, 0xF0), ls=1.12),
        ],
    )
    steps = [
        ("Escucha", "micrófono"),
        ("Ve", "cámaras"),
        ("Comprende", "la escena"),
        ("Responde", "en español"),
        ("Se mueve", "voz y gesto"),
    ]
    sw = (tw - 0.16 * 4) / 5
    fills = (CYAN_INK, RGBColor(0x0E, 0x4A, 0x72), EMERALD, RGBColor(0x0E, 0x6B, 0x8A), CYAN_INK)
    for i, ((name, sub), fill) in enumerate(zip(steps, fills)):
        box(
            slide, tx + i * (sw + 0.16), hero_y + 2.05, sw, 2.15, fill,
            [
                T(str(i + 1), 14, True, CYAN, "Arial", PP_ALIGN.CENTER, sa=4, ls=1.0),
                T(name, 18, True, WHITE, "Arial", PP_ALIGN.CENTER, sa=4, ls=1.0),
                T(sub, 13, False, RGBColor(0xD6, 0xE4, 0xF0), "Arial", PP_ALIGN.CENTER, ls=1.0),
            ],
            adj=0.12,
        )

    # ── columnas ──────────────────────────────────────────
    L, GAP, W = 0.32, 0.22, 11.45
    C = L + W + GAP
    R = C + W + GAP
    TOP = 11.0
    COL_BOT = 40.55
    PAD = 0.22
    IW = W - 2 * PAD
    BODY = 15

    # 01
    xi = L + PAD
    card = Card(slide, L, TOP, W, "01", "Introducción")
    y = flow_text(slide, xi, card.body, IW, [
        T("R-ONE es un androide de tamaño humano. El cuerpo parte del diseño abierto InMoov: cabeza, brazos y manos impresos, movidos por servomotores.", BODY, sa=8, ls=1.12),
        T("El semillero le añadió cámaras, un micrófono, un parlante y un miniPC. Hoy reconoce a los integrantes, conversa por el chat o por la voz y ejecuta gestos diseñados en un estudio web.", BODY, ls=1.12),
    ])
    b1 = card.close(y + 0.22)

    # 02
    card = Card(slide, L, b1 + GAP, W, "02", "Descripción del problema")
    y = flow_text(slide, xi, card.body, IW, [
        T("Conversar de verdad exige tres cosas a la vez: ver a la persona, entender la pregunta y mover el cuerpo.", BODY, sa=8, ls=1.12),
        T("Eso tiene que ocurrir en el propio robot, con un computador modesto y sin depender siempre de internet. Si falla la visión, la voz o el gesto, la conversación se corta.", BODY, ls=1.12),
    ])
    quote = [
        T("La pregunta entra por el chat o por el micrófono. La respuesta sale en voz y, si hay un gesto válido, también en el cuerpo.", 15, False, NAVY, i=True, ls=1.12),
    ]
    qh = measure(quote, IW - 0.4) + 0.36
    rect(slide, xi, y + 0.16, IW, qh, AIR, line=BORDER, adj=0.08)
    shape(slide, MSO_SHAPE.RECTANGLE, xi, y + 0.16, 0.1, qh, RED)
    text(slide, xi + 0.28, y + 0.16, IW - 0.4, qh, quote, anchor=MSO_ANCHOR.MIDDLE)
    b2 = card.close(y + 0.16 + qh + 0.22)

    # 03 objetivos llenan hasta COL_BOT
    card = Card(slide, L, b2 + GAP, W, "03", "Objetivos")
    gen = [
        T("OBJETIVO GENERAL", 12, True, CYAN, "Arial", sa=4, ls=1.0),
        T("Percibir a las personas, conversar en español y responder con voz y gesto, desde un miniPC.", 16, False, WHITE, ls=1.12),
    ]
    gh = measure(gen, IW - 0.4) + 0.28
    y = card.body
    box(slide, xi, y, IW, gh, NAVY, gen, adj=0.1, pad=(0.18, 0.18, 0.1, 0.1))
    y += gh + 0.14
    specs = [
        ("Percibir", "Reconocer a los integrantes con un detector propio y seguirlos entre cámaras."),
        ("Conversar", "Responder con una memoria propia y, si no hay red, con un modelo local."),
        ("Mover", "Diseñar secuencias en un estudio y lanzarlas desde la mesa de control."),
    ]
    row = 1.35
    for n, (verb, rest) in enumerate(specs):
        rect(slide, xi, y, IW, row, (CARD, AIR)[n % 2], line=BORDER, adj=0.1)
        box(
            slide, xi + 0.14, y + (row - 0.5) / 2, 0.5, 0.5, (NAVY, EMERALD, CYAN_INK)[n],
            [T(str(n + 1), 16, True, WHITE, "Arial", PP_ALIGN.CENTER, ls=1.0)],
            kind=MSO_SHAPE.OVAL, pad=(0, 0, 0, 0),
        )
        text(
            slide, xi + 0.78, y, IW - 0.95, row,
            [T(verb, 16, True, NAVY, "Arial", sa=2, ls=1.0), T(rest, 14, ls=1.08)],
            anchor=MSO_ANCHOR.MIDDLE,
        )
        y += row + 0.1
    y += 0.06
    y = flow_text(slide, xi, y, IW, [
        T("El estudio de secuencias", 15, True, NAVY, "Arial", ls=1.0),
    ])
    y += 0.06
    hs = picture(slide, ASSETS / "cap-studio.png", xi, y, IW)
    y += hs + 0.04
    y = flow_text(slide, xi, y, IW, [
        T("Ahí se arma el gesto, en cian, y su reposo. Luego el panel lo lanza con Normal o Neutro.", 13, False, MUTED, i=True, ls=1.05),
    ])
    card.close(y + 0.18)

    # 04 metodología
    xi = C + PAD
    card = Card(slide, C, TOP, W, "04", "Metodología")
    y = flow_text(slide, xi, card.body, IW, [
        T("Dos caminos se encuentran en el miniPC: el cuerpo, que ejecuta, y la mente, que decide qué decir y qué mover.", BODY, ls=1.12),
    ])
    y += 0.12
    half = (IW - 0.16) / 2
    lanes = [
        ("Cuerpo", NAVY, [
            "InMoov impreso en 3D",
            "Servos SG90 y DS5160",
            "4 placas PCA9685 por I2C",
            "Arduino Mega, puerto serie",
        ]),
        ("Mente", CYAN_INK, [
            "802 imágenes, 25 clases",
            "Detector YOLO11s",
            "Web, gateway y NATS",
            "Turno en la Jetson",
        ]),
    ]
    lane_h = 2.55
    for i, (name, fill, lines) in enumerate(lanes):
        lx = xi + i * (half + 0.16)
        rect(slide, lx, y, half, lane_h, CARD, line=BORDER, adj=0.08)
        box(slide, lx, y, half, 0.42, fill, [T(name, 15, True, WHITE, "Arial", PP_ALIGN.CENTER, ls=1.0)], adj=0.0, pad=(0, 0, 0, 0))
        text(
            slide, lx + 0.12, y + 0.5, half - 0.2, lane_h - 0.55,
            [T(line, 13, sa=4, ls=1.05) for line in lines],
        )
    y += lane_h + 0.16
    y = flow_text(slide, xi, y, IW, [T("De la pregunta al gesto", 15, True, NAVY, "Arial", ls=1.0)])
    y += 0.08
    chain = [("Chat", NAVY), ("Visión", CYAN_INK), ("Memoria", EMERALD), ("Voz", NAVY), ("Gesto", CYAN_INK)]
    cw = (IW - 0.1 * 4) / 5
    for i, (lab, fill) in enumerate(chain):
        box(slide, xi + i * (cw + 0.1), y, cw, 0.48, fill, [T(lab, 12, True, WHITE, "Arial", PP_ALIGN.CENTER, ls=1.0)], adj=0.2, pad=(0.02, 0.02, 0, 0))
    y += 0.62
    y = flow_text(slide, xi, y, IW, [
        T("Si la pregunta ya está en la memoria, responde al momento. Si no, usa la nube o, sin internet, Gemma en el miniPC. El gesto solo sale si está en el catálogo.", 14, False, MUTED, ls=1.08),
    ])
    # hardware thumbs under methodology if space
    y += 0.1
    hw = (IW - 0.16) / 2
    # cabeza is wide diagram; show mano + antebrazo as pair and cabeza full width if room
    remain = COL_BOT - y - 0.2
    if remain > 3.2:
        cap_h = picture(slide, ASSETS / "cabeza.jpeg", xi, y, IW * 0.48)
        picture(slide, ASSETS / "mano.jpeg", xi + IW * 0.52, y, IW * 0.48)
        y += max(cap_h, picture.__defaults__ and 0 or cap_h) 
        # picture already drawn; height is cap_h if same aspect roughly. mano may differ.
        with Image.open(ASSETS / "mano.jpeg") as im:
            mh = (IW * 0.48) * im.height / im.width
        y = y - cap_h + max(cap_h, mh) + 0.08
        y = flow_text(slide, xi, y, IW, [
            T("Cabeza (17 servos SG90) y un brazo (10 canales). El antebrazo lleva un servo por dedo.", 13, False, MUTED, i=True, ls=1.05),
        ])
    card.close(max(y + 0.16, COL_BOT) if y + 0.16 < COL_BOT + 0.4 else y + 0.16)
    # force card to COL_BOT if content is shorter
    if y + 0.16 < COL_BOT:
        card.close(COL_BOT)

    # 05 resultados
    xi = R + PAD
    card = Card(slide, R, TOP, W, "05", "Resultados")
    y = card.body
    cw3 = (IW - 0.16) / 3
    for i, (val, lab, fill) in enumerate((("0,88", "Precisión", NAVY), ("0,93", "Recall", EMERALD), ("0,94", "mAP50", CYAN_INK))):
        chip(slide, xi + i * (cw3 + 0.08), y, cw3, 1.15, val, lab, fill)
    y += 1.28
    ch = picture(slide, ASSETS / "yolo-curves.png", xi, y, IW)
    y += ch + 0.04
    y = flow_text(slide, xi, y, IW, [
        T("YOLO11s, 25 clases del semillero, 60 épocas. Manda la corrida train5.", 12, False, MUTED, i=True, ls=1.05),
    ])
    y += 0.06
    hv = picture(slide, ASSETS / "cap-vision.png", xi, y, IW)
    y += hv + 0.02
    y = flow_text(slide, xi, y, IW, [
        T("Visión: el detector nombra al integrante y sigue el rostro en las cámaras.", 12, False, MUTED, i=True, ls=1.02),
    ])
    y += 0.04
    shot_w = (IW - 0.12) / 2
    h3 = picture(slide, ASSETS / "cap-chat.png", xi, y, shot_w)
    h4 = picture(slide, ASSETS / "cap-panel.png", xi + shot_w + 0.12, y, shot_w)
    y += max(h3, h4) + 0.02
    y = flow_text(slide, xi, y, IW, [
        T("Chat (la fuente queda escrita) y panel: Normal mueve, Neutro vuelve al reposo.", 12, False, MUTED, i=True, ls=1.02),
    ])
    b5 = card.close(y + 0.14)

    # 06 conclusiones
    card = Card(slide, R, b5 + GAP, W, "06", "Conclusiones")
    blocks = [
        (EMERALD, "El lazo cierra.", "Una pregunta recorre visión, memoria y voz, y puede terminar en un gesto."),
        (CYAN_INK, "El detector reconoce al semillero.", "En train5 el mAP50 llega a 0,94. La clase es un integrante, no una persona genérica."),
        (NAVY, "El cuerpo ya tiene lenguaje.", "Cabeza, brazos y manos se mueven con secuencias de gesto y de reposo."),
        (RED, "Queda trabajo.", "Varios gestos aún no tienen descripción, y la GPU de la Jetson no se usa."),
    ]
    y = card.body
    avail = COL_BOT - y - 0.12
    bh = (avail - 0.1 * 3) / 4
    for i, (color, title, body) in enumerate(blocks):
        rect(slide, xi, y, IW, bh, CARD, line=BORDER, adj=0.1)
        shape(slide, MSO_SHAPE.RECTANGLE, xi, y, 0.1, bh, color)
        text(
            slide, xi + 0.24, y, IW - 0.36, bh,
            [T(title, 14, True, NAVY, "Arial", sa=2, ls=1.0), T(body, 13, ls=1.08)],
            anchor=MSO_ANCHOR.MIDDLE,
        )
        y += bh + 0.1
    card.close(COL_BOT)

    # ── eventos ───────────────────────────────────────────
    ey = 40.72
    rect(slide, 0.32, ey, 34.79, 3.55, CARD, line=BORDER, adj=0.02)
    text(slide, 0.5, ey + 0.08, 20, 0.36, [T("R-ONE en eventos de divulgación", 16, True, NAVY, "Arial", ls=1.0)])
    ew = (34.4 - 0.14 * 3) / 4
    for i in range(4):
        picture(slide, ASSETS / f"foto-evento-{i+1}.jpg", 0.48 + i * (ew + 0.14), ey + 0.48, ew)

    # ── referencias ───────────────────────────────────────
    ry = 44.42
    rect(slide, 0.32, ry, 34.79, 2.35, NAVY, adj=0.02)
    text(slide, 0.5, ry + 0.08, 10, 0.36, [T("07  Referencias", 16, True, WHITE, "Arial", ls=1.0)])
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
    text(slide, 0.5, ry + 0.5, 16.6, 1.7, [T(r, 13, False, WHITE, sa=3, ls=1.05) for r in refs_a])
    text(slide, 17.4, ry + 0.5, 16.6, 1.7, [T(r, 13, False, WHITE, sa=3, ls=1.05) for r in refs_b])

    prs.save(str(OUTPUT))
    warns = preview(OUTPUT, PREVIEW)
    for w in warns:
        print(w)
    print("Wrote", OUTPUT)
    print("Preview", PREVIEW, "warnings:", len(warns))


def preview(pptx_path: Path, out: Path, dpi: int = 28) -> list[str]:
    prs = Presentation(str(pptx_path))
    slide = prs.slides[0]
    W = int(prs.slide_width / 914400 * dpi)
    H = int(prs.slide_height / 914400 * dpi)
    canvas = Image.new("RGB", (W, H), HEX["paper"])
    d = ImageDraw.Draw(canvas)
    warnings = []

    def px(v):
        return v / 914400 * dpi

    shapes = list(slide.shapes)
    for sh in shapes:
        x, y, w, h = px(sh.left), px(sh.top), px(sh.width), px(sh.height)
        if sh.shape_type == MSO_SHAPE_TYPE.PICTURE:
            tmp = ASSETS / "_pv.png"
            tmp.write_bytes(sh.image.blob)
            im = Image.open(tmp).convert("RGB").resize((max(1, int(w)), max(1, int(h))), Image.Resampling.LANCZOS)
            canvas.paste(im, (int(x), int(y)))
            tmp.unlink(missing_ok=True)
            continue
        if sh.shape_type == MSO_SHAPE_TYPE.LINE:
            d.line((x, y, x + w, y + h), fill=HEX["red"], width=max(2, dpi // 16))
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
            else:
                d.rounded_rectangle((x, y, x + w, y + h), radius=max(2, min(w, h) * 0.06), fill=fill, outline=outline, width=1)
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
            fam = run.font.name or "Arial"
            f = _font(sz * dpi / 72 * SCALE.get(fam, 0.9), bool(run.font.bold), bool(run.font.italic))
            raw_ls = p.line_spacing
            mult = raw_ls if isinstance(raw_ls, float) and raw_ls < 4 else 1.05
            lh = sz * dpi / 72 * 1.15 * mult
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
        if total > avail + 2:
            warnings.append(f"OVERFLOW {total/dpi:.2f}>{avail/dpi:.2f} :: {tf.text[:50]!r}")
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
