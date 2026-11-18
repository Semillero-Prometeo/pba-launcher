# Póster R-ONE — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generar `docs/poster/poster-r-one.pptx` (y su vista previa PNG) a partir de la plantilla Unilibre, con las siete secciones aprobadas, capturas reales de la interfaz y fotos/diagramas de hardware.

**Architecture:** Un único script `docs/poster/build_poster.py` copia la plantilla, conserva el encabezado (logos, título, autores), dibuja el cuerpo con python-pptx (navy/cian/esmeralda/rojo) y genera `preview-poster.png` con Pillow para detectar desbordes. Los insumos viven en `docs/poster/assets/`.

**Tech Stack:** Python 3.13, python-pptx, Pillow, matplotlib, navegador Cursor (MCP) para capturas en `http://localhost:4200`.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-11-17-poster-r-one-design.md`.
- Plantilla: `docs/poster/plantilla-poster.pptx` (35,43 × 47,24 in, una diapositiva). Conservar logos, título «R-ONE», autores y línea roja inferior.
- Colores: campo `#eef2f6`, tarjeta `#f7fafc`, navy `#0B2540`, cian `#38bdf8`, esmeralda `#059669`, rojo `#BE1818`, tinta quieta `#3d5a73`, borde `#c5d4e0`. Nunca blanco puro como superficie.
- Tipografía: títulos Montserrat Bold; cuerpo Arial. Títulos de sección ≈ 40 pt, cuerpo 22–24 pt, pies 16–18 pt, mínimo 15 pt.
- Datos solo de la documentación integral, `train5/results.csv` o los assets. Nada inventado.
- Login de capturas: `admin-prometeo@unilibre.edu.co` / `Promteo2026*`.
- Commits en español, imperativo, con punto final.
- Entregables: `docs/poster/poster-r-one.pptx`, `docs/poster/build_poster.py`, insumos en `docs/poster/assets/`, `docs/poster/assets/preview-poster.png`.

---

### Task 1: Capturas de la interfaz y curaduría de fotos

**Files:**
- Create: `docs/poster/assets/cap-vision.png`
- Create: `docs/poster/assets/cap-chat.png`
- Create: `docs/poster/assets/cap-studio.png`
- Create: `docs/poster/assets/cap-panel.png` (si aún no existe o hay que regenerarla)
- Create: `docs/poster/assets/foto-hero.jpg` (recorte de una foto real de R-ONE)
- Create: `docs/poster/assets/foto-evento-1.jpg` … `foto-evento-4.jpg`
- Create: `docs/poster/assets/yolo-curves.png` (gráfica de `train5`)

**Interfaces:**
- Consumes: `http://localhost:4200` (stack Compose en marcha), `pmas-web-main/public/assets/assets/*.jpg`, `pmai-model-vision/runs/detect/train5/results.csv`, `docs/poster/assets/{cabeza,mano,antebrazos}.jpeg`.
- Produces: PNG/JPG listos para el script, con marco redondeado opcional aplicado al pegar.

- [ ] **Step 1: Confirmar que la web responde**

Run: `curl -s -o /dev/null -w "%{http_code}\n" http://localhost:4200/`
Expected: `200`. Si no, `docker compose ps` y levantar lo que falte.

- [ ] **Step 2: Entrar y capturar Visión, Chat, Estudio y Panel**

Con el navegador MCP: ir a `http://localhost:4200/`, iniciar sesión con `admin-prometeo@unilibre.edu.co` / `Promteo2026*`, capturar:
1. Visión (objetos / cámaras) → `cap-vision.png`
2. Chat con una respuesta visible (fuente OpenAI, Gemma o caché) → `cap-chat.png`
3. Estudio de secuencias en `/sequences` (iframe) mostrando gesto + neutro → `cap-studio.png`
4. Panel / secuencias del robot → `cap-panel.png`

Guardar en `docs/poster/assets/`. Recortar a la zona útil (sin barra del navegador).

- [ ] **Step 3: Curar foto héroe y cuatro de eventos**

Elegir de `pmas-web-main/public/assets/assets/`:
- Una foto clara del robot completo o de medio cuerpo → `foto-hero.jpg` (recortar y redimensionar a ~1800 px de ancho).
- Cuatro fotos de divulgación (robot con equipo, ferias, demostraciones) → `foto-evento-1.jpg` … `foto-evento-4.jpg`. Sin nombres de premios ni lugares en los pies posteriores.

- [ ] **Step 4: Generar la gráfica YOLO**

Desde `results.csv` de `train5`, plotear Precisión / Recall / mAP50 por época (estilo TORNS: fondo papel, colores navy/cian/mid) y guardar `docs/poster/assets/yolo-curves.png`.

```python
# fragmento esperado en build_poster.py o un helper temporal
# métricas finales train5: P=0.884, R=0.932, mAP50=0.944, mAP50-95=0.654
```

Run: `ls -lh docs/poster/assets/`
Expected: aparecen `cap-*.png`, `foto-*.jpg`, `yolo-curves.png`, más los tres JPEG de hardware.

- [ ] **Step 5: Commit**

```bash
git add docs/poster/assets
git commit -m "Añade capturas y fotos curadas del póster de R-ONE."
```

---

### Task 2: Esqueleto de `build_poster.py` (primitivos y encabezado)

**Files:**
- Create: `docs/poster/build_poster.py`

**Interfaces:**
- Consumes: `docs/poster/plantilla-poster.pptx`
- Produces: funciones `emu`, `T`, `write_tf`, `rect`, `box`, `text`, `Card`, `chip`, `flow`, `figure`, `measure`, `preview`, `header`, `delete_content_placeholders`; constantes de color del DESIGN.md.

- [ ] **Step 1: Copiar el esqueleto del póster TORNS y adaptar colores**

Tomar como referencia ` /home/personal/Projects/tro-launcher/docs/presentations/poster-assets/build_poster.py` (primitivos pptx + `preview`). Cambiar:

```python
ROOT = Path("/home/personal/Projects/ulibre-prometeo/pba-launcher")
ASSETS = ROOT / "docs/poster/assets"
TEMPLATE = ROOT / "docs/poster/plantilla-poster.pptx"
OUTPUT = ROOT / "docs/poster/poster-r-one.pptx"
PREVIEW = ASSETS / "preview-poster.png"

NAVY = RGBColor(0x0B, 0x25, 0x40)
CYAN = RGBColor(0x38, 0xBD, 0xF8)
EMERALD = RGBColor(0x05, 0x96, 0x69)
RED = RGBColor(0xBE, 0x18, 0x18)
PAPER = RGBColor(0xEE, 0xF2, 0xF6)
CARD = RGBColor(0xF7, 0xFA, 0xFC)
INK = RGBColor(0x0B, 0x25, 0x40)
MUTED = RGBColor(0x3D, 0x5A, 0x73)
BORDER = RGBColor(0xC5, 0xD4, 0xE0)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
AIR = RGBColor(0xE8, 0xEE, 0xF4)
CYAN_INK = RGBColor(0x0C, 0x4A, 0x6E)
```

Conservar `emu`, `T`, `set_font`, `write_tf`, `shape`, `rect`, `box`, `text`, `Card` (banda navy + círculo rojo con número), `chip`, `flow`, `figure`, `measure`, `preview`.

- [ ] **Step 2: Encabezado de la plantilla**

La plantilla ya tiene logos y textos. Funciones:

```python
KEEP = {"Imagen 75", "Imagen 4", "TextBox 70", "TextBox 73", "TextBox 74", "AutoShape 71"}

def delete_content_placeholders(slide):
    for sh in list(slide.shapes):
        if sh.name not in KEEP:
            sh._element.getparent().remove(sh._element)

def header(slide):
    # TextBox 70 = «R-ONE» (rojo, ya está)
    # TextBox 74 = autores (ya están)
    # TextBox 73 = semillero → corregir tilde
    sem = next(s for s in slide.shapes if s.name == "TextBox 73")
    write_tf(sem.text_frame, [
        T("Semillero de Investigación PROMETEO", 40, True, INK, "Montserrat Bold", PP_ALIGN.CENTER, ls=1.0)
    ], anchor=MSO_ANCHOR.MIDDLE)
```

No borrar las imágenes ni la línea roja inferior.

- [ ] **Step 3: Fondo del cuerpo**

Tras el encabezado (~6 in), rellenar el resto de la diapositiva con un rectángulo `PAPER` detrás de las tarjetas (añadir primero para que quede al fondo, o insertar en el XML al inicio del `spTree` después de `nvGrpSpPr`).

- [ ] **Step 4: Smoke test**

Run:

```bash
python3 - <<'EOF'
from pathlib import Path
import shutil
from pptx import Presentation
# importar solo header/delete si el módulo ya existe; si no, ejecutar main mínimo
EOF
python3 docs/poster/build_poster.py  # aún puede fallar si main() no dibuja, pero no debe romper el encabezado
```

Expected: se escribe `poster-r-one.pptx` o, si `main` aún no está, al menos el módulo importa sin error (`python3 -c "import importlib.util; …"`).

- [ ] **Step 5: Commit**

```bash
git add docs/poster/build_poster.py
git commit -m "Añade el esqueleto del generador del póster de R-ONE."
```

---

### Task 3: Banda héroe y columna 1 (Introducción, Problema, Objetivos)

**Files:**
- Modify: `docs/poster/build_poster.py`

**Interfaces:**
- Consumes: `foto-hero.jpg`, primitivos de Task 2.
- Produces: zona héroe + tres `Card` en la columna izquierda.

- [ ] **Step 1: Banda héroe**

Geometría (pulgadas, diapositiva 35,43 × 47,24):

```
TOP_HERO = 6.3
HERO_H ≈ 5.2
L, C, R = 0.55, 12.1, 23.65
COL_W = 11.0
```

Dibujar tarjeta navy o papel con:
- Foto héroe a la izquierda (~5,5 in de ancho).
- Texto: «R-ONE es el androide del semillero Prometeo: ve, escucha, conversa en español y gesticula desde un miniPC.»
- Cinta `flow()`: Escucha → Ve → Comprende → Responde → Se mueve, con subtítulos «micrófono», «cámaras y YOLO», «BLIP describe la escena», «memoria y modelo», «voz y gesto».

- [ ] **Step 2: Card 01 Introducción**

Prosa corta (2–3 oraciones): base InMoov, cámaras, micrófono, parlante, Jetson; qué puede hacer hoy (saludar, reconocer integrantes, responder por chat o voz, ejecutar gestos diseñados en el estudio).

- [ ] **Step 3: Card 02 Descripción del problema**

Sin estadísticas inventadas. Idea: un androide conversacional necesita unir percepción, lenguaje y movimiento en tiempo real, con hardware modesto y sin depender siempre de internet. Caja de cita o énfasis con borde rojo fino.

- [ ] **Step 4: Card 03 Objetivos**

Caja navy con el objetivo general. Tres filas numeradas (círculos cian/navy):

1. Percibir y reconocer personas con un detector propio y seguirlas entre cámaras.
2. Conversar en español con una memoria propia y un modo sin internet.
3. Mover cabeza, brazos y manos desde secuencias del estudio y operarlas desde la mesa de control.

- [ ] **Step 5: Generar y revisar preview parcial**

Run: `python3 docs/poster/build_poster.py && ls -lh docs/poster/assets/preview-poster.png`
Expected: preview sin avisos de overflow en la columna 1; leer la imagen con la herramienta Read.

- [ ] **Step 6: Commit**

```bash
git add docs/poster/build_poster.py docs/poster/poster-r-one.pptx docs/poster/assets/preview-poster.png
git commit -m "Dibuja la banda héroe y la columna de introducción del póster."
```

---

### Task 4: Columna 2 — Metodología

**Files:**
- Modify: `docs/poster/build_poster.py`

**Interfaces:**
- Consumes: primitivos; opcionalmente diagramas de hardware si el software satura la columna 3.
- Produces: Card 04 con carriles Cuerpo / Mente y diagrama de arquitectura en formas.

- [ ] **Step 1: Card 04 Metodología — dos carriles**

Título «04 Metodología». Dos columnas internas:

**Cuerpo**
1. InMoov impreso en 3D  
2. Servos SG90 (cabeza) y DS5160 (brazos)  
3. 4 PCA9685 por I2C + Arduino Mega  
4. Comandos serie `PCA,<pca>,<servo>,<pos>,<vel>`

**Mente**
1. Videos → Label Studio (802 imágenes, 25 clases)  
2. Entrenamiento YOLO11s (`train5`)  
3. Microservicios: web, gateway, NATS  
4. Turno de conversación en Jetson Orin Nano  

Unir ambos con una flecha o chevron «MiniPC Jetson».

- [ ] **Step 2: Diagrama de arquitectura simplificado**

Con `flow()` o cajas: Web → Gateway → {Auth, Management, Robotics, mai-core} → {Voz/Arduino, Visión/BLIP/Gemma}. Etiquetas cortas; sin pegar `high-level-architecture.png` crudo.

- [ ] **Step 3: Preview y commit**

Run: `python3 docs/poster/build_poster.py`
Expected: 0 overflows en Metodología.

```bash
git add docs/poster/build_poster.py docs/poster/poster-r-one.pptx docs/poster/assets/preview-poster.png
git commit -m "Dibuja la metodología del póster de R-ONE."
```

---

### Task 5: Columna 3 — Resultados y Conclusiones

**Files:**
- Modify: `docs/poster/build_poster.py`

**Interfaces:**
- Consumes: `cap-*.png`, `yolo-curves.png`, `cabeza.jpeg`, `mano.jpeg`, `antebrazos.jpeg`.
- Produces: Card 05 y Card 06.

- [ ] **Step 1: KPIs YOLO**

Tres `chip()`: `0,88` Precisión · `0,93` Recall · `0,94` mAP50. Fuente: última época de `train5`. Pie: «YOLO11s, 25 clases (integrantes), 60 épocas».

- [ ] **Step 2: Gráfica + capturas de software**

Insertar `yolo-curves.png` a ancho moderado. Debajo, dos o tres capturas (`cap-vision`, `cap-chat`, `cap-studio` o `cap-panel`) con etiquetas E1–E3 y pies en cursiva. Si no cabe, dejar dos capturas grandes y una pequeña.

- [ ] **Step 3: Hardware**

Insertar `cabeza.jpeg`, `mano.jpeg`, `antebrazos.jpeg` con pies: «17 servos SG90 en la cabeza», «10 canales por brazo/mano», «Antebrazo: un servo por dedo». Si satura la columna, mover este bloque bajo Metodología (Card 04) según la spec.

- [ ] **Step 4: Card 06 Conclusiones**

Tres o cuatro bloques con barra de color lateral:

1. El lazo funciona: pregunta → visión → respuesta → voz y gesto en el miniPC.  
2. El detector reconoce al semillero (mAP50 0,94 en `train5`).  
3. El cuerpo responde a secuencias con par normal/neutro.  
4. Pendiente: descripciones en el catálogo de gestos; GPU de la Jetson aún sin usar.

- [ ] **Step 5: Preview y commit**

Run: `python3 docs/poster/build_poster.py`
Expected: 0 overflows; leer `preview-poster.png` completo.

```bash
git add docs/poster/build_poster.py docs/poster/poster-r-one.pptx docs/poster/assets
git commit -m "Dibuja resultados y conclusiones del póster de R-ONE."
```

---

### Task 6: Pie (eventos + referencias), verificación final y entrega

**Files:**
- Modify: `docs/poster/build_poster.py`
- Create/Update: `docs/poster/poster-r-one.pptx`, `docs/poster/assets/preview-poster.png`

**Interfaces:**
- Consumes: `foto-evento-1..4.jpg`
- Produces: Card 07 Referencias a todo el ancho; franja de eventos; verificación sin overflows.

- [ ] **Step 1: Franja de eventos**

Cuatro fotos en fila bajo las columnas, pie único: «R-ONE en eventos de divulgación.» Sin premios ni lugares.

- [ ] **Step 2: Card 07 Referencias**

Dos columnas, tipografía 15–16 pt:

```
[1] Ultralytics. YOLO11, documentación oficial.
[2] Li et al. BLIP: Bootstrapping Language-Image Pre-training. ICML, 2022.
[3] Google DeepMind / Unsloth. Gemma 4 E2B (GGUF).
[4] Milvus Lite. Zilliz.
[5] NATS.io. Documentación del servidor NATS.
[6] Lange, G. InMoov — open source 3D printed life-size robot.
[7] Alphacephei. Vosk (reconocimiento de voz).
[8] Rhasspy. Piper (síntesis de voz).
```

- [ ] **Step 3: Verificación final**

Run:

```bash
python3 docs/poster/build_poster.py
python3 - <<'EOF'
from pptx import Presentation
p = Presentation("docs/poster/poster-r-one.pptx")
assert len(p.slides) == 1
assert abs(p.slide_width/914400 - 35.43) < 0.05
print("shapes", len(p.slides[0].shapes))
print("ok")
EOF
```

Expected: `preview` con `warnings: 0`; shapes > 40; el script imprime las rutas escritas.

- [ ] **Step 4: Lectura visual**

Abrir `docs/poster/assets/preview-poster.png` con la herramienta Read. Comprobar: equilibrio de columnas, márgenes, contraste navy/papel, que el título rojo y los logos sigan visibles, y que ninguna tarjeta quede vacía o saturada. Corregir en el acto.

- [ ] **Step 5: Commit final**

```bash
git add docs/poster
git commit -m "Publica el póster de R-ONE."
```

---

## Spec coverage (self-review)

| Requisito de la spec | Task |
|---|---|
| Conservar plantilla (logos, R-ONE, autores, línea) | 2 |
| Colores DESIGN.md + rojo Unilibre acento | 2–5 |
| Banda héroe + cinta Escucha→…→Se mueve | 3 |
| Intro / Problema / Objetivos (1+3) | 3 |
| Metodología Cuerpo/Mente + arquitectura | 4 |
| Resultados software (métricas + capturas) | 1, 5 |
| Resultados hardware (3 diagramas) | 1, 5 |
| Conclusiones honestas | 5 |
| Franja eventos genérica | 1, 6 |
| Referencias | 6 |
| Preview + overflow 0 | 3–6 |
| Datos verificables (train5, docs) | 1, 5 |

Sin placeholders. Nombres de archivos y métricas fijados.
