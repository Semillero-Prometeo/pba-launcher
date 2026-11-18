# Póster R-ONE — diseño

Fecha: 2026-11-17. Estado: aprobado por el usuario.

## Objetivo

Un póster impreso en pliego (90 × 120 cm) que presenta R-ONE de punta a punta, hardware y software, a un público final. Secciones obligatorias: Introducción, Descripción del problema, Objetivos (general y tres específicos), Metodología, Resultados, Conclusiones y Referencias. Lenguaje natural con conectores, poco texto y capturas suficientes de cada parte.

## Entregables

- `docs/poster/poster-r-one.pptx`: el póster editable, construido sobre `docs/poster/plantilla-poster.pptx` (una diapositiva de 35,43 × 47,24 in).
- `docs/poster/build_poster.py`: el script que lo genera (python-pptx, Pillow, matplotlib).
- `docs/poster/assets/`: insumos curados (fotos, capturas, gráficas) y `preview-poster.png`, la vista previa que genera el script.

## Marco visual

- Se conservan de la plantilla los dos logos, el título «R-ONE» en rojo `#BE1818`, los autores y la línea roja inferior. El texto «Semillero de Investigacion PROMETEO» pasa a «Semillero de Investigación PROMETEO».
- Campo papel frío `#eef2f6`; tarjetas `#f7fafc` con borde `#c5d4e0`; nunca blanco puro como superficie.
- Navy `#0B2540` es la estructura: bandas de sección, tarjetas oscuras, tinta de títulos. Tinta quieta `#3d5a73`.
- Cian `#38bdf8` (tinta `#0c4a6e`) marca datos y acción; esmeralda `#059669` marca ok y Neutro.
- El rojo Unilibre aparece solo en el título, la línea inferior y el número de cada sección.
- Títulos en Montserrat Bold (la fuente de la plantilla); cuerpo en Arial para que imprima igual en cualquier equipo.
- Tamaños: títulos de sección ≈ 40 pt, cuerpo 22–24 pt, pies 16–18 pt, nada por debajo de 15 pt.

## Distribución

1. **Encabezado** (0–6 in): el de la plantilla.
2. **Banda héroe** a todo lo ancho: foto real de R-ONE a la izquierda; a la derecha una frase y la cinta Escucha → Ve → Comprende → Responde → Se mueve, cada paso con icono dibujado con formas y una línea corta.
3. **Tres columnas**:
   - Columna 1: 01 Introducción, 02 Descripción del problema, 03 Objetivos.
   - Columna 2: 04 Metodología en dos carriles (Cuerpo y Mente) que convergen, más un diagrama de arquitectura simplificado dibujado con formas.
   - Columna 3: 05 Resultados (software: métricas YOLO `train5` y capturas reales; hardware: diagramas de cabeza, mano y antebrazo) y 06 Conclusiones. Si la columna 3 se satura, el bloque de hardware baja bajo Metodología.
4. **Pie**: franja de cuatro fotos de eventos con pie genérico («R-ONE en eventos de divulgación», sin premios ni lugares) y 07 Referencias.

## Contenido

- Introducción: qué es R-ONE (androide de base InMoov del semillero) y qué hace hoy.
- Problema: integrar percepción, lenguaje y movimiento en tiempo real con hardware modesto y sin depender siempre de internet. Sin estadísticas inventadas.
- Objetivo general: desarrollar un androide que perciba a las personas, converse en español y responda con voz y gestos, integrando visión, modelos de lenguaje y control robótico en un miniPC.
- Objetivos específicos: (1) percibir y reconocer personas con un detector propio y seguirlas entre cámaras; (2) conversar con una memoria propia y un modo sin internet; (3) mover cabeza, brazos y manos desde secuencias diseñadas en un estudio web y operar todo desde una mesa de control.
- Metodología: Cuerpo (InMoov impreso, servos SG90 y DS5160, 4 PCA9685 por I2C con Arduino Mega, comandos serie) y Mente (videos → Label Studio, 802 imágenes y 25 clases → YOLO11s; microservicios web, gateway y NATS; turno de conversación; Jetson Orin Nano).
- Resultados: precisión 0,88, recall 0,93 y mAP50 0,94 de `train5`; capturas de Visión, Chat, estudio de secuencias y panel; diagramas de hardware con conteos tomados de ellos (17 servos en la cabeza, 10 por brazo y mano).
- Conclusiones: tres o cuatro tarjetas honestas sobre lo que funciona y lo pendiente (catálogo de gestos sin descripciones, GPU sin aprovechar).
- Referencias: Ultralytics YOLO, BLIP, Gemma, Milvus, NATS, InMoov, Vosk y Piper.

Todos los datos salen de `docs/project-docs/r-one-documentacion-integral.md` o de los insumos de `docs/poster/assets/`. Ningún dato se inventa.

## Insumos

- Hardware: `docs/poster/assets/cabeza.jpeg`, `mano.jpeg`, `antebrazos.jpeg`.
- Fotos reales: `pmas-web-main/public/assets/assets/*.jpg`.
- Métricas: `pmai-model-vision/runs/detect/train5/results.csv`.
- Capturas: la interfaz en marcha (`http://localhost:4200`), con la cuenta de administrador que dio el usuario.

## Verificación

- El script genera `preview-poster.png` y reporta cualquier texto que desborde su caja; el resultado final no tiene avisos.
- Revisión visual de la vista previa: equilibrio entre columnas, márgenes, legibilidad a distancia y que ninguna sección quede vacía o saturada.
- `python-pptx` reabre el archivo sin errores.
