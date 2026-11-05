# Documentación integral de R-ONE — design

Date: 2026-11-05  
Status: approved design, pending implementation plan  
Scope: un spec. Dueño: `pba-launcher` (solo `docs/`, `AGENTS.md` y `README.md`). Ningún repositorio hijo cambia código.

## Problem

El conocimiento del proyecto está repartido y en parte desactualizado:

- La memoria académica (`docs/project-docs/1. Documentación del Proyecto - Inteligencia Artificial Multimodal y Robótica Autonoma.md`, unas 2.700 líneas) viene de una conversión de Word y perdió sus imágenes: cita 246 ilustraciones y no trae ninguna. Describe con detalle la interfaz Angular, el detector YOLO, BLIP y el análisis del modelo de acción. En cambio, su capítulo de backend y robótica tiene un párrafo, habla de "4 microservicios" y no describe el turno, las rutas Básico/Complejo, el micrófono, el estudio de movimiento, el par normal/neutro ni el despliegue en la Jetson.
- El Word original (`… (1).docx`, 30 MB, 191 imágenes, sin seguimiento en git y propiedad de `root`) sí conserva las imágenes.
- El README, `AGENTS.md`, las reglas de `.cursor/rules/`, `PRODUCT.md`, `DESIGN.md`, `jetson-orin-nano-r-one.md`, `model-vision-project.md` y los README de cada repositorio cubren cada uno una parte del sistema.
- `pba-arduino-codes` figura en `.gitmodules`, pero no está clonado.

Quien llega al semillero no tiene un único documento que le explique el sistema de cero a cien.

## Goal

Un único entregable Markdown, `docs/project-docs/r-one-documentacion-integral.md`, que reemplace a la memoria académica y permita una transferencia de conocimiento completa a un público mixto: una parte conceptual para cualquier lector y otra técnica para desarrolladores.

1. Reflejar el estado actual del código. Si el código y otra fuente no coinciden, gana el código.
2. Absorber todo el contenido de la memoria: lo vigente en el cuerpo y lo histórico en un capítulo de evolución e investigación.
3. Documentar los 10 repositorios, el lanzador, `pba-arduino-codes`, la Jetson, la identidad visual y la operación con solución de problemas.
4. Explicar lo complejo en lenguaje natural, con conectores, ejemplos del propio R-ONE y referencias al código y a fuentes externas.
5. Diagramar en Mermaid dentro del mismo archivo e incorporar las imágenes curadas del Word.

## Non-goals

- Índice o resumen de las specs y planes de `docs/superpowers/`.
- Cambios de código, configuración o pruebas en cualquier repositorio.
- Documentación archivo por archivo con funciones públicas (la profundidad es por módulo; ver más abajo).
- Traducción a otro idioma.
- Capturas nuevas de la interfaz con el stack levantado.
- Reemplazar las bitácoras vivas `jetson-orin-nano-r-one.md` y `model-vision-project.md`.

## Audiencia y navegación

Público mixto. Cada parte abre con una nota de a quién va dirigida y qué puede saltarse (por ejemplo: "Si solo necesitas operar el robot, ve a la Parte IV"). Al inicio hay una tabla de contenido enlazada. Las explicaciones conceptuales y las técnicas se conectan con enlaces internos, de modo que un concepto aparece explicado una vez y referido donde haga falta.

## Estructura

Organización por capas de lectura.

### Parte I. Entender R-ONE (cualquier lector)

1. Qué es R-ONE, el semillero Prometeo (Universidad Libre, Bogotá) y los objetivos del proyecto, tomados de la memoria y actualizados.
2. El sistema en una página: diagrama de bloques que va de las cámaras y el micrófono a la voz y el movimiento.
3. Recorrido de una pregunta. Un ejemplo narrado de principio a fin: una persona frente al robot pregunta "¿qué es la Universidad Libre?" y el texto sigue la detección, la elección de la persona, BLIP, el catálogo de gestos, Milvus, el modelo, la voz y el gesto.
4. Conceptos clave con analogías: microservicio, gateway, NATS y patrones de mensaje, JWT, embeddings y búsqueda vectorial, caché semántico, detección y reidentificación, descripción de escena, LLM local frente a API, par normal/neutro.

### Parte II. Arquitectura y flujos transversales

5. Mapa de servicios y puertos según `docker-compose.yml` (Postgres, NATS, gateway, auth, management, robotics, web main, motion studio, pmai-core), con el canal entre cada par: HTTP, NATS, WebSocket o serie.
6. Flujos en diagramas de secuencia:
   - Inicio de sesión, JWT y guards.
   - Chat por la ruta Básico (`chatStructured` + `voiceService.speak`, `fuente: "OpenAI"`, `movimientos: []`).
   - Chat por la ruta Complejo (`interactionService.ask`, pasos 1–6 de `AGENTS.md`, todas las `fuente` posibles).
   - Micrófono: Vosk, voz corta, turno ocupado y frases de "pensando".
   - Ciclo de un gesto en robótica: normal → 1 s → neutro → 1 s, la cola y Detener.
   - Visión en tiempo real hacia la pantalla.
   - Creación de una secuencia en el estudio y su ingesta con `id`.
   - `declarePoema` y por qué no usa el turno.
7. Datos y persistencia: esquemas Prisma de Postgres (diagrama entidad-relación), colecciones `conocimiento` e `interacciones` de Milvus Lite, JSON canónico de secuencias de robótica, almacén de rutas del chat en management, modelos de IA en disco (GGUF de Gemma, BLIP, embeddings, Vosk, pesos YOLO) y de dónde se descargan.

### Parte III. Repositorios

Una ficha por repositorio, todas con la misma plantilla:

| Apartado | Contenido |
|---|---|
| Propósito | Qué resuelve y qué no le toca |
| Versión | Rama y commit corto documentados |
| Tecnología | Lenguaje, framework, versiones relevantes |
| Árbol | Carpetas hasta el nivel de módulo, con la función de cada una |
| Archivos clave | Nombre y propósito, empezando por el punto de entrada |
| Contratos | Patrones NATS, endpoints HTTP o WebSocket que expone y que consume |
| Configuración | Variables de entorno, archivos de ajustes y valores por defecto |
| Pruebas | Cómo se corren y qué cubren |
| Trampas | Errores conocidos o invariantes que no se deben romper |

Orden: lanzador (`pba-launcher`, scripts, Compose, `.env.template`), `pmas-web-main`, `pba-ms-gateway`, `pba-ms-auth`, `pba-ms-management`, `pba-ms-robotics`, `pmai-mai-core`, `pmai-model-context`, `pmai-model-vision-language`, `pmai-model-vision`, `pmas-web-motion-studio`, `pba-arduino-codes`.

Para `pba-arduino-codes` se clona el repositorio desde `.gitmodules`. Si el clon falla, la ficha documenta lo que `pba-ms-robotics` espera del firmware y queda marcada como pendiente de confirmar.

### Parte IV. Despliegue y operación

8. Arranque en local, en la LAN y en la Jetson Orin Nano: requisitos, `.env`, scripts `rone-up`, `rone-down`, `rone-restart`, `rone-status`, `rone-wifi`, `rone-bt`, `rone-seed`, la siembra de Milvus, UFW, el QR de red y el primer arranque, que descarga modelos y tarda. Absorbe la ficha y la configuración de `jetson-orin-nano-r-one.md`, que se cita como bitácora viva.
9. Solución de problemas por síntoma: no habla, no se mueve, no ve, no escucha, Gemma no carga, Milvus vacío o caído, OpenAI sin clave, el catálogo de gestos está vacío, la sesión venció. Cada síntoma indica qué revisar, en qué servicio y con qué comando.

### Parte V. Producto e identidad visual

Resumen de `PRODUCT.md` y `DESIGN.md`: a quién sirve la interfaz, principios, paleta (navy `#0B2540`, cian `#38bdf8`, esmeralda `#059669`), voz de operador y accesibilidad.

### Parte VI. Evolución e investigación

Lo histórico de la memoria y el contexto del proyecto: stakeholders, los nueve hitos de `project-start-plan.png`, el etiquetado del dataset (802 imágenes, 25 clases), la limpieza, el preprocesamiento, el entrenamiento y las métricas de YOLO, las pruebas de BLIP-base y Geospace, la fase de análisis del modelo de acción, la ingesta por web scraping (primera y segunda fase), el prompt engineering y las decisiones que se descartaron.

### Anexos

- A. Glosario: el de la memoria, ampliado con los términos de backend, IA y robótica.
- B. Variables de entorno: tabla completa por servicio, tomada de `docker-compose.yml`, `.env.template` y los ajustes de cada repositorio.
- C. Catálogo de patrones NATS: emisor, receptor, carga y respuesta.
- D. Endpoints HTTP del gateway: método, ruta, guard y servicio destino.
- E. Índice de diagramas e ilustraciones.

## Redacción

- Español natural en tercera persona, con párrafos encadenados por conectores. Las listas solo se usan para lo enumerable y las tablas para datos cortos; la prosa explica el porqué.
- Patrón para lo complejo: la idea en una frase, después una analogía o un ejemplo de R-ONE y al final la referencia exacta en el código (ruta y función) y, si aplica, una fuente externa (documentación de NATS, NestJS, Prisma, Angular, Ultralytics, BLIP, Milvus, llama.cpp, Vosk).
- Ejemplo de referencia del tono: "Milvus funciona como un archivo que no busca por palabras exactas, sino por parecido de significado. Si alguien ya preguntó '¿dónde queda la universidad?', la pregunta '¿en qué parte está la U?' encuentra esa respuesta sin llamar a ningún modelo." A continuación vendrían la ruta de `responder()` y el umbral que usa.
- Los nombres del código (funciones, patrones, variables, rutas) van entre comillas invertidas y tal como aparecen en el código.
- Lo que no se pueda verificar se escribe como "pendiente de confirmar" y nunca se inventa.

## Diagramas e imágenes

- Mermaid dentro del `.md`: `flowchart` para bloques y decisiones, `sequenceDiagram` para flujos entre servicios, `stateDiagram-v2` para el turno y el gesto, `erDiagram` para Postgres.
- Imágenes en `docs/project-docs/assets/`, referenciadas con rutas relativas y con pie de figura numerado ("Figura N. …").
- Fuentes de imágenes: `high-level-architecture.png`, `high-level-action-model.jpeg`, `project-start-plan.png` y las curadas del `.docx`.
- Curaduría del `.docx`: se descomprime, se cruza cada `word/media/*` con su pie "Ilustración N" mediante `word/_rels/document.xml.rels` y `word/document.xml`, y se conserva una imagen solo si explica algo que sigue siendo cierto (métricas y curvas, ejemplos de etiquetado, resultados de inferencia, diagramas conceptuales, pantallas que no cambiaron). Se descartan las capturas de código o de pantallas obsoletas. Las elegidas se renombran de forma legible, por ejemplo `vision-curva-map50.png`.

## Producción

1. Investigar cada pieza antes de redactar su parte: árbol, punto de entrada, módulos, contratos, configuración y pruebas. La exploración puede repartirse en paralelo; la redacción la hace una sola mano para mantener el tono.
2. Extraer y curar las imágenes del `.docx`.
3. Clonar `pba-arduino-codes`.
4. Escribir en el orden I → VI y después los anexos, con un commit en el lanzador por cada parte.
5. Generar al final la tabla de contenido enlazada.
6. Archivar y reapuntar:
   - Mover la memoria `.md` a `docs/project-docs/archivo/` con `git mv`.
   - Mover el `.docx` a `docs/project-docs/archivo/` (puede requerir `sudo`, porque es de `root`). No se agrega a git, porque pesa 30 MB y sus imágenes útiles ya quedan en `assets/`; se añade a `.gitignore`.
   - Actualizar la tabla de documentación de `AGENTS.md` y el `README.md` para que apunten al documento nuevo.

Tamaño esperado: entre 4.000 y 6.000 líneas.

## Verificación

- Cada bloque Mermaid se valida con `@mermaid-js/mermaid-cli` (`npx -y @mermaid-js/mermaid-cli`), si se puede instalar; si no, con revisión manual de sintaxis.
- Todas las anclas internas de la tabla de contenido y de las referencias cruzadas resuelven a un encabezado existente.
- Todas las rutas de imagen existen en disco.
- Una muestra de los identificadores técnicos de cada parte (patrones NATS, variables de entorno, puertos, rutas de archivo, nombres de función) se contrasta con `rg` contra el código.
- Ningún "TBD" ni marcador vacío; solo "pendiente de confirmar", con su motivo.
- El documento cubre todos los capítulos de la memoria anterior: cada encabezado de primer y segundo nivel de la memoria se ubica en el cuerpo o en la Parte VI.

## Risks

- El `.docx` es propiedad de `root`: moverlo puede requerir `sudo`.
- El clon de `pba-arduino-codes` puede fallar por permisos de GitHub; en ese caso la ficha queda parcial y marcada.
- Un archivo de 4.000 a 6.000 líneas es pesado de revisar; los commits por parte lo mitigan.
- Los submódulos siguen evolucionando; el documento refleja el commit de cada repositorio el día en que se escribió, y la Parte III anota ese commit en cada ficha.
