# Póster R-ONE Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generar `docs/poster/poster-r-one.pptx`, un póster de pliego (90 × 120 cm) sobre la plantilla del semillero que presenta R-ONE (hardware y software) a un público final.

**Architecture:** Un script Python (`docs/poster/build_poster.py`) abre la plantilla, conserva su encabezado, dibuja todo el cuerpo con formas de python-pptx y coloca imágenes curadas de `docs/poster/assets/`. El mismo script rasteriza una vista previa (`preview-poster.png`) con Pillow y avisa de cualquier texto que desborde su caja. Las capturas de la interfaz se toman antes, con el navegador sobre la pila que ya corre en `localhost`.

**Tech Stack:** Python 3.13, python-pptx 1.0.2, Pillow, matplotlib 3.10, navegador de Cursor (CDP) para capturas.

**Spec:** `docs/superpowers/specs/2026-11-17-poster-r-one-design.md`

## Global Constraints

- Lienzo: 35,43 × 47,24 in (una diapositiva). Encabezado de la plantilla en 0–6 in; línea roja inferior en 46,95 in.
- Se conservan los logos, «R-ONE» en `#BE1818`, los autores y la línea roja; «Investigacion» pasa a «Investigación».
- Campo `#eef2f6`; tarjeta `#f7fafc` con borde `#c5d4e0`; navy `#0B2540`; tinta quieta `#3d5a73`; cian `#38bdf8` con tinta `#0c4a6e`; esmeralda `#059669`; rojo `#BE1818` solo en el título, la línea inferior y el número de sección.
- Títulos Montserrat Bold; cuerpo Arial. Títulos de sección ≈ 40 pt, cuerpo 22–24 pt, pies 16–18 pt, mínimo 15 pt.
- Secciones: 01 Introducción, 02 Descripción del problema, 03 Objetivos (general + 3 específicos), 04 Metodología, 05 Resultados, 06 Conclusiones, 07 Referencias.
- Datos solo de `docs/project-docs/r-one-documentacion-integral.md`, `pmai-model-vision/runs/detect/train5/results.csv` (última época: precisión 0,88436, recall 0,93229, mAP50 0,94407, mAP50-95 0,65381) y los diagramas de `docs/poster/assets/`. Nada inventado. Fotos de eventos con pie genérico, sin premios ni lugares.
- Español natural para público final, con conectores; poco texto por bloque.
- No se escriben credenciales en ningún archivo.

---

### Task 1: Capturas e insumos curados

**Files:**
- Create: `docs/poster/assets/cap-vision.png`, `cap-chat.png`, `cap-estudio.png`, `cap-panel.png` (capturas crudas)
- Create: `docs/poster/assets/foto-hero.jpg`, `foto-evento-1.jpg` … `foto-evento-4.jpg` (copias de `pmas-web-main/public/assets/assets/`)

**Interfaces:**
- Produces: los nombres de archivo de arriba, que `build_poster.py` lee.

- [ ] **Step 1: Iniciar sesión** en `http://localhost:4200/login` con la cuenta de administrador que dio el usuario (no se guarda en disco). Viewport de escritorio 1600 × 1000.
- [ ] **Step 2: Capturar** `/robotics/vision` (objetos y cámaras con detección si hay cámara), `/robotics/chat` tras enviar una pregunta corta («Hola, ¿quién eres?») para que aparezca la respuesta con su fuente, `/sequences` (estudio con barras de gesto cian y neutro esmeralda) y `/control-panel`. Guardar con `browser_take_screenshot` y mover a `docs/poster/assets/`.
- [ ] **Step 3: Elegir fotos.** Héroe: la foto vertical del robot de cuerpo entero con mejor fondo. Eventos: cuatro fotos de grupo con el robot. Copiarlas con los nombres de arriba.
- [ ] **Step 4: Verificar** que cada archivo existe y abre con Pillow:

```bash
python3 -c "from PIL import Image; import glob; [print(f, Image.open(f).size) for f in sorted(glob.glob('docs/poster/assets/*'))]"
```

Expected: las 9 imágenes nuevas más `cabeza.jpeg`, `mano.jpeg`, `antebrazos.jpeg`.

### Task 2: Script base con vista previa y verificación de desborde

**Files:**
- Create: `docs/poster/build_poster.py`

**Interfaces:**
- Produces: `T(text, sz, b, c, f, a, sa, ls, i) -> dict`, `write_tf(tf, items, anchor, ml, mr, mt, mb)`, `shape(...)`, `rect(...)`, `box(...)`, `text(...)`, `measure(items, w_in) -> float`, `flow_text(slide, x, y, w, items) -> float`, `Section(slide, x, y, w, num, title)` con `.body` y `.close(bottom) -> float`, `picture(slide, path, x, y, w=None, h=None) -> (w, h)`, `preview(pptx_path, out) -> list[str]` (avisos `OVERFLOW …`).

- [ ] **Step 1:** Escribir los primitivos (mismos patrones que `/home/personal/Projects/tro-launcher/docs/presentations/poster-assets/build_poster.py`: `T`, `write_tf`, `shape`, `rect`, `box`, `text`, `measure`, `flow_text`, `preview`) con la paleta de las restricciones globales y `FONT_TITLE = "Montserrat"`, `FONT_BODY = "Arial"`.
- [ ] **Step 2:** `header(slide)`: localizar `TextBox 73` y reescribir «Semillero de Investigación PROMETEO» con el mismo estilo (Montserrat Bold 40 pt, `#1D1D1B`); no tocar `TextBox 70`, `TextBox 74`, `Imagen 75`, `Imagen 4` ni `AutoShape 71`.
- [ ] **Step 3:** Fondo: un rectángulo `#eef2f6` de 6,15 a 46,8 in enviado al fondo del árbol de formas (insertarlo en la posición 2 de `spTree`).
- [ ] **Step 4:** `main()` copia la plantilla a `docs/poster/poster-r-one.pptx`, aplica encabezado y fondo, guarda y llama a `preview` a 40 dpi.
- [ ] **Step 5: Verificar**

```bash
python3 docs/poster/build_poster.py && python3 -c "from pptx import Presentation; Presentation('docs/poster/poster-r-one.pptx')"
```

Expected: `warnings: 0` y `docs/poster/assets/preview-poster.png` con el encabezado intacto.

### Task 3: Banda héroe y columna 1

**Files:**
- Modify: `docs/poster/build_poster.py`

**Interfaces:**
- Consumes: primitivos de la Task 2; `foto-hero.jpg`.

- [ ] **Step 1: Banda héroe** (≈ 6,5–14 in): tarjeta navy a todo lo ancho; foto héroe recortada a la izquierda; frase grande en `#eef2f6` («Un androide que escucha, mira, entiende y responde con voz y gestos»); cinta de cinco pasos (Escucha · micrófono y Vosk; Ve · cámaras y YOLO; Comprende · BLIP describe la escena; Responde · memoria propia, nube o modelo local; Se mueve · voz y gesto en los servos), cada paso un círculo con icono dibujado con formas y conectores cian.
- [ ] **Step 2: 01 Introducción** (2 párrafos), **02 Descripción del problema** (párrafo + tres retos en tarjetas: tiempo real, hardware modesto, sin internet), **03 Objetivos** (general en tarjeta navy; tres específicos numerados en cian, emparejados con los carriles de la metodología).
- [ ] **Step 3: Verificar** `python3 docs/poster/build_poster.py` → `warnings: 0`; revisar la vista previa.

### Task 4: Columna 2 (Metodología) y columna 3 (Resultados y Conclusiones)

**Files:**
- Modify: `docs/poster/build_poster.py`
- Create: `docs/poster/assets/ev-yolo.png` (generada)

**Interfaces:**
- Consumes: primitivos; capturas y diagramas de la Task 1; `results.csv` de `train5`.
- Produces: `make_yolo_chart(path, w_in, h_in)`.

- [ ] **Step 1: 04 Metodología**: dos carriles paralelos con pasos numerados (Cuerpo: InMoov impreso en 3D → servos SG90 y DS5160 → 4 PCA9685 por I2C y Arduino Mega → comandos serie; Mente: videos → Label Studio, 802 imágenes y 25 clases → YOLO11s → microservicios web, gateway y NATS → turno de conversación) que convergen en una tarjeta «Jetson Orin Nano». Debajo, diagrama de arquitectura con formas: Interfaz → Gateway → NATS → (Gestión · Núcleo de IA · Robótica) → Arduino.
- [ ] **Step 2: Resultados de hardware** bajo Metodología si la columna 3 no los admite: cabeza (17 servos SG90), mano y antebrazo (10 servos por brazo), con pies cortos.
- [ ] **Step 3: 05 Resultados (software)**: tres chips (0,88 · 0,93 · 0,94), curva por época generada con matplotlib en la paleta, y las cuatro capturas recortadas con marco redondeado y etiqueta.
- [ ] **Step 4: 06 Conclusiones**: cuatro tarjetas con barra lateral de color.
- [ ] **Step 5: Verificar** `warnings: 0`; las tres columnas terminan a ±0,3 in de la misma altura.

### Task 5: Pie, referencias y revisión final

**Files:**
- Modify: `docs/poster/build_poster.py`

- [ ] **Step 1:** Franja de cuatro fotos de eventos con pie «R-ONE en eventos de divulgación del semillero».
- [ ] **Step 2: 07 Referencias** en dos columnas: Ultralytics YOLO (2024); Li et al., BLIP (ICML 2022); Google DeepMind, Gemma (2025); Milvus; NATS; Langevin, InMoov; Vosk (Alpha Cephei); Piper (Rhasspy).
- [ ] **Step 3: Revisión visual** de la vista previa a tamaño completo: márgenes ≥ 0,9 in, ningún bloque vacío o saturado, texto ≥ 15 pt, el rojo solo donde lo permiten las restricciones.
- [ ] **Step 4: Commit**

```bash
git add docs/poster/build_poster.py docs/poster/poster-r-one.pptx docs/poster/assets docs/poster/plantilla-poster.pptx
git commit -m "Crea el póster de R-ONE para impresión en pliego."
```
