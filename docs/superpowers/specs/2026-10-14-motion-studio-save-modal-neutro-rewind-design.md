# Motion Studio: barra, modal de guardar y neutro rebobinado — design

Date: 2026-10-14  
Status: approved by user on 2026-10-14  
Scope: reordenar la barra del estudio, pedir nombre / descripción / categoría / Arduino en un diálogo al guardar, exigir descripción de al menos 10 caracteres, generar el neutro como rebobinado que deshace el camino del gesto, y pintar el iframe con la misma identidad de `PRODUCT.md` / `DESIGN.md` (marco navy, papel frío, cian de acción, esmeralda en Neutro). Dueños: `pmas-web-motion-studio` (UI + `generate_neutro` + `editor.css`), `pba-ms-robotics` (ingest + `is_complete_pair`), y los dos Markdown de la raíz del lanzador.

Relación: el spec `2026-10-14-sequence-neutro-runtime-design.md` sigue vigente para JSON de dos pistas, categorías, cola normal → 1 s → neutro → 1 s, `getActions` y el panel. Este corte **cambia** cómo se rellenan `blocks_neutro`, **cuándo** se piden los metadatos y **cómo se ve** el iframe. El spec `2026-10-14-navy-chrome-chat-tabs-design.md` no se reabre: sus tokens se **reutilizan** aquí, no se redefinen.

Cortes pendientes (specs propias, no este archivo):

1. Autenticación: 401/expiración cierra la UI, crear usuarios, roles con efecto real.
2. Visión: más refresco, sin Preview, cámaras a tamaño útil, objetos observados arriba.

## Problem

La cabecera del estudio mezcla identidad, nombre, descripción, categoría y Arduino en una sola fila rígida. Play, Stop, Agregar, pistas, Generar neutro, Guardar y Actualizar no siguen un orden de tarea. Guardar escribe en cuanto hay nombre y categoría, con descripción opcional (0–280). El turno usa esa frase en el prompt: una descripción vacía o de dos letras no sirve.

El iframe sigue en noche industrial (`--bg: #000f1d`, texto claro, tipo de 10 px en modo y campos). Encajado en el panel navy/papel se lee como otra aplicación. PRODUCT exige una identidad; DESIGN no tiene un segundo sistema dentro del estudio.

**Generar neutro** hoy no copia el gesto. Por cada `(pca, servo)` toma la `pos` de menor `inicio`, la pone en el segundo 0 y le asigna duración 2. El operador pidió lo contrario: los mismos pasos, rebobinados, misma duración, deshaciendo el camino hasta el reposo.

## Goal

1. Encabezado solo con «Motion Studio» y el modo (Suelto / Acoplado).
2. Barra, izquierda a derecha: Play, Stop, Agregar, Gesto | Neutro, Generar neutro, Guardar, Actualizar.
3. Guardar abre un diálogo. Campos: nombre (1–80), descripción (10–280, una línea), categoría (una de las seis), Arduino (entero ≥ 0, default 0). Si la secuencia ya estaba abierta, los cuatro vienen llenos.
4. Generar neutro: rebobinado que deshace el camino (algoritmo abajo). Confirmación si ya hay pista. Después se edita a mano.
5. Ingest y guardado local rechazan descripción de menos de 10 caracteres. Un par sin esa frase no entra a `getActions`.
6. El iframe usa los mismos hex, roles y escala de tipo que `DESIGN.md`. No hay `DESIGN.md` ni paleta propia dentro de `pmas-web-motion-studio`. `PRODUCT.md` deja de listar el estudio como corte visual pendiente y apunta el CSS del iframe como evidencia.

## Non-goals

- Autenticación y visión.
- Cambiar el turno, `executeAction`, `declarePoema` o `{ reply, fuente, movimientos }`.
- Cambiar la forma del JSON (sigue `blocks` + `blocks_neutro` + `category`).
- Reescribir `interfaz_record9_5_1.py`.
- Cambiar la gramática de la línea de tiempo (reglas, arrastre, playhead, inspector de bloque, lista lateral). Se pinta; no se convierte en tabla ni en formulario.
- Copiar componentes Angular al iframe. El estudio sigue en HTML/CSS/JS; solo comparte tokens.
- Neutral de emergencia al Stop.
- Borradores vs publicar. No hay tercer estado de archivo.

## Approach

Opción A aprobada: diálogo, barra e identidad viven en el iframe (`index.html` + `editor.js` + `editor.css`). La función pura `generate_neutro` en Python y `generateNeutroFrom` en JS implementan el mismo rebobinado. Robótica valida descripción ≥ 10 en `ingest_save`. El modal no se sube a Angular. PRODUCT.md y DESIGN.md se actualizan en la raíz; no se duplican en el repo del estudio.

## Barra y cromo

Regla **Task Strip**: la barra es una sola fila de acciones, no un formulario.

Orden fijo:

| # | Control | Hace |
|---|---|---|
| 1 | Play | Reproduce la pista activa |
| 2 | Stop | Corta playhead y pide `/sequence/stop` |
| 3 | Agregar | Bloque nuevo en la pista activa |
| 4 | Gesto \| Neutro | Un control de dos lados (`track-gesto` / `track-neutro`) |
| 5 | Generar neutro | Rebobina; no guarda |
| 6 | Guardar | Abre el diálogo; no escribe hasta confirmar |
| 7 | Actualizar | Recarga la lista; no abre el diálogo |

Nombre, descripción, categoría y Arduino salen del `<header class="chrome">`.

## Identidad (PRODUCT / DESIGN)

Regla **One Skin**: el iframe no es un mundo aparte. Los `:root` de `editor.css` mapean 1:1 a DESIGN:

| Token actual | Pasa a | Rol |
|---|---|---|
| `--bg: #000f1d` | `#eef2f6` | Campo |
| `--surface / --panel` | `#f7fafc` | Tarjeta (cromo interno, lista, inspector, diálogo) |
| `--line` | `#c5d4e0` | Borde |
| `--text: #e8eef4` | `#0B2540` | Tinta |
| `--muted: #b8c4ce` | `#3d5a73` | Tinta quieta |
| `--cyan` | `#38bdf8` | Play, Guardar, pista Gesto activa, foco |
| `--emerald` | `#059669` (no `#10b981`) | Neutro (pista activa, Generar neutro, ok) |
| `--rose` | `#dc2626` | Stop y eliminar bloque |

Cabecera del iframe: fondo `#0B2540`, tinta `#eef2f6` (Navy Frame). Cuerpo y escenario: papel frío. Diálogo: tarjeta `#f7fafc` + borde + radio xl, sin glow. Play y Guardar son acción cian. Stop es rojo. El lado Neutro del conmutador, activo, es esmeralda; el lado Gesto, activo, es cian. Bloques de la pista neutra se leen en esmeralda; los del gesto en cian. Prohibido `text-[8px]`–`text-[10px]`, tracking extremo y mayúsculas sostenidas salvo el chip de modo (Suelto / Acoplado).

Cargar Inter y Space Grotesk en `index.html` (las mismas caras que el operador). Cada botón de la barra lleva icono Material Symbols a la izquierda de la palabra. Etiquetas: Play, Stop, Agregar, Gesto, Neutro, Generar neutro, Guardar, Actualizar — las que el operador ya usa. No hay «System Override» ni hex de consola.

`PRODUCT.md`: principio «Cortes siguientes» deja de citar el estudio como deuda visual; Evidence incluye `pmas-web-motion-studio/src/static/editor.css`. `DESIGN.md`: un bullet de Layout para el iframe (barra en orden del Goal 2, diálogo de guardar, escenario en papel frío). No se crea un DESIGN.md dentro del repo del estudio.

## Diálogo de guardar

Regla **Save Dialog**: metadatos se piden al guardar, no mientras se edita el tiempo.

- `<dialog>` modal. Foco atrapado. Escape y Cancelar cierran sin escribir.
- Confirmar llama a `saveLocal` o `saveCoupled` según el modo, con el payload de siempre.
- Errores en el diálogo (nombre vacío, descripción &lt; 10, categoría vacía). La franja `#status` sigue para fallos de red.
- Sigue haciendo falta `blocks` no vacío, `blocks_neutro` no vacío y categoría válida.
- Actualizar no abre el diálogo.

## Neutro rebobinado

Regla **Rewind Neutro**: el neutro generado es el gesto hacia atrás, deshaciendo cada pose.

Gesto vacío: mensaje «Agrega bloques al gesto»; no se toca la pista. Pista neutra ya existente: `confirm` y reemplazo, igual que hoy.

Algoritmo (JS y Python idénticos):

1. Enumerar `blocks` con su índice original. Ordenar por `(inicio, índice)`.
2. `prev[(pca, servo)] = 0` (reposo).
3. Recorrer en ese orden. Por cada bloque `b` emitir un deshacer `{ pca, servo, inicio: b.inicio, dur: b.dur, pos: prev[key], vel: b.vel, nombre: b.nombre }` y luego `prev[key] = b.pos`.
4. `T = max(inicio + dur)` sobre el gesto.
5. Cada deshacer recibe `inicio' = T - (inicio + dur)`. Mismos `dur`, `vel`, `nombre`. `pos` es la del deshacer.
6. El arreglo `blocks_neutro` es esa lista (tuplas de 7). El orden del arreglo es por `inicio'` y, en empate, el inverso del índice original.

Ejemplo: servo 0 a 200 (inicio 0, dur 1) y luego a 400 (inicio 1, dur 0,5). `T = 1,5`. Neutro: `[0,0,0,0.5,200,…]` y `[0,0,0.5,1,0,…]`.

Un servo que aparece una vez vuelve a 0 con la misma duración. Huecos del gesto se espejan en el neutro. Play sigue en la pista activa. Robótica no cambia la cola.

## Validación

| Superficie | Descripción &lt; 10 o vacía |
|---|---|
| Diálogo | No confirma; texto bajo el campo |
| `local_sequences._normalize` | `ValueError` |
| `ingest_save` | `ValueError` «Descripción inválida» |
| `is_complete_pair` | `False` si `len(description.strip()) < 10` (no entra a `getActions` ni al panel de ejecución) |

`listSequences` puede seguir mostrando el archivo. Overwrite de una secuencia existente exige la misma regla. Archivos legado con descripción corta: visibles en lista, no en el catálogo del turno.

`description` se recorta a 280, una línea (se sustituyen saltos por espacio **antes** de medir; si tras eso queda &lt; 10, rechazo).

## Pruebas

- `tests/test_neutro.py`: dos pasos del mismo servo; dos servos; empate de `inicio`; hueco en el timeline; `replace=False` sigue fallando si ya hay pista.
- `tests/test_app.py`: cromo sin inputs de nombre/descripción/categoría; esos ids viven en el `<dialog>`; barra en el orden de Goal 2; descripción del diálogo `minlength="10"`.
- Spec-as-file-read sobre `editor.css`: `--bg` es `#eef2f6`, cabecera navy `#0B2540`, esmeralda `#059669`, no queda `#000f1d` ni `#10b981`. Tipo de cromo, barra y diálogo ≥ 12 px.
- `tests/test_local_sequences.py`: rechazo de descripción de 9 caracteres; aceptación de 10.
- `pba-ms-robotics/tests/test_sequence_ingest.py`: ingest con 9 caracteres falla; `is_complete_pair` falso si la frase es corta.

No se añade prueba de navegador del iframe en este corte.

## Error handling

- Generar sin gesto: status de error, pista intacta.
- Confirmar diálogo con red caída: el diálogo permanece; `#status` muestra el error.
- Categoría ausente o neutro vacío: mismo rechazo de hoy, ahora también visible en el diálogo si aplica.

## Lo que no se toca

`pmai-mai-core`, `pmas-web-main` (el iframe se verá distinto al recargar; no se edita Angular salvo que un wrapper del estudio rompa el corte), chat, visión, auth, gateway DTO de secuencia más allá de aceptar la misma forma. No se reabre la paleta de Angular.
