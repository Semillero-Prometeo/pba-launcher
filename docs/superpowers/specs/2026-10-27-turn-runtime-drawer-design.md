# Cajón de cola en hardware (turno) — design

Date: 2026-10-27  
Status: approved by user on 2026-10-27  
Scope: un spec. Dueños: `pba-ms-robotics`, `pmas-web-main`. Gateway: proxy transparente, sin DTO nuevo.  
El turno no se reabre. `declarePoema`, `getActions`, `executeAction` y `{ reply, fuente, movimientos }` no cambian de contrato.  
Importar JSON `formato: normalizado` y borrar secuencias quedan para un spec posterior.

Relación: el spec `2026-10-14-sequence-neutro-runtime-design.md` sigue vigente para la cola **normal → 1 s → neutro → 1 s**, `source`, Stop y `GET /sequence/runtime`. Este corte **amplía** el snapshot (duración, restante, bloques del paso actual) y **mueve** la vista «En hardware» del panel de control a un cajón del `admin-shell`.

## Problem

El turno encola gestos y el panel de control es el único sitio con cola en vivo. El chat guarda `{ movimientos }` y no los pinta. Un turno por micrófono no pasa por esa respuesta HTTP. En secuencias, chat o visión no hay vista de control. El recuadro **En hardware** no muestra cuenta atrás ni servos del paso actual.

## Goal

1. En todo el backoffice autenticado (chat, visión, secuencias, panel, usuarios): ver en vivo la cola del robot.
2. Auto-abrir el cajón al empezar un **turno**. Botón fijo para abrir o cerrar a mano.
3. Lista paso a paso (Normal, Neutro, espera) con duración prevista; cuenta atrás en el actual; servos del paso en curso.
4. **Detener** = el Stop de siempre.
5. Quitar el recuadro **En hardware** del panel. Play/Neutro se quedan.

## Non-goals

- Importar el JSON de objetos `bloques` / `formato: normalizado`.
- Borrar secuencias desde el estudio o el panel.
- WebSocket.
- Cambiar `_fire_blocks` (sigue terminando al enviar el último comando).
- Neutro de emergencia al Stop.
- Cambiar el turno, `declarePoema`, TTS o `{ reply, fuente, movimientos }`.
- Empujar el layout (el iframe del estudio no se recorta).
- Poll fuera del `admin-shell` (login y páginas públicas no ven el cajón).

## Approach

Opción A aprobada: ampliar `GET /sequence/runtime` y consultarlo desde un servicio del `admin-shell`. La cuenta atrás va a saltos del poll (~0,5 s).

---

## 1. Arquitectura

| Pieza | Hace | No hace |
|---|---|---|
| `pba-ms-robotics` | Snapshot con `duration_ms`, `remaining_ms`, `blocks` + `fired` del **current** | No empuja eventos; no cambia la cola |
| `pba-ms-gateway` | `GET /sequence/runtime` y `POST /sequence/stop` como hoy; el JSON nuevo pasa | No arma la cola |
| `pmas-web-main` admin-shell | Servicio compartido, cajón, botón fijo, Detener | No infiere la cola desde el chat |
| Panel de control | Play/Neutro; `busy` del servicio compartido; sin recuadro En hardware | No hace poll propio |
| `pmai-mai-core` | Nada | Sigue encolando y no espera |

Un turno por chat o por micrófono aparece igual: el estado vive en robótica.

---

## 2. Snapshot

`GET /sequence/runtime` (JWT). Idle:

```json
{
  "busy": false,
  "source": null,
  "current": null,
  "queue": []
}
```

Ocupado:

```json
{
  "busy": true,
  "source": "turno",
  "current": {
    "id": 1,
    "name": "asentir",
    "mode": "normal",
    "source": "turno",
    "duration_ms": 0,
    "remaining_ms": 0,
    "blocks": [
      {
        "nombre": "cuello_arr_abj",
        "pca": 0,
        "servo": 2,
        "inicio": 0.0,
        "dur": 1.0,
        "pos": 500,
        "vel": 5,
        "fired": true
      }
    ]
  },
  "queue": [
    {
      "id": 1,
      "name": "asentir",
      "mode": "espera",
      "source": "turno",
      "duration_ms": 1000
    }
  ]
}
```

| Campo | Regla |
|---|---|
| `busy` / `source` | Como hoy. `source` del snapshot es el del paso actual, o el de `queue[0]` si aún no hay current. |
| Cada paso | `id`, `name`, `mode`, `source`, `duration_ms` (entero ≥ 0). |
| `current.remaining_ms` | Entero ≥ 0. Baja con el reloj del paso en robótica. Solo en `current`. |
| `current.blocks` | Solo en `current`. En `espera` o sin bloques: `[]`. |
| `queue` | Sin `blocks` y sin `remaining_ms`. |

### Duración de un paso

El reproductor termina el gesto al **enviar** el último comando (`max(inicio)`), no al cumplir `dur`.

| `mode` | `duration_ms` |
|---|---|
| `espera` | `1000` |
| `normal` o `neutro` | `round(max(inicio) * 1000)`. Sin bloques: `0`. |

`dur` se muestra en cada servo, no en la fila del paso. Si todos los `inicio` son 0, el paso dura 0 ms y todos los bloques salen `fired` en el primer snapshot útil.

`fired`: `elapsed_s >= inicio` con `elapsed_s` medido desde el arranque de ese paso. En espera no hay `fired`.

`remaining_ms` se recorta a `[0, duration_ms]`. Al cambiar de paso, se reinicia.

El gateway no añade DTO si hoy el proxy es transparente. Angular lee los campos nuevos y trata `blocks` ausente como `[]`.

---

## 3. Shell: poll, auto-abrir, Detener

Servicio en raíz, arranca con el `admin-shell` (sesión JWT). No corre en el layout público.

| Estado | Intervalo |
|---|---|
| `busy` o cajón abierto | 500 ms |
| idle y cajón cerrado | 3 s |
| runtime falla | 500 ms (no se detiene el poll) |

**Auto-abrir** cuando empieza una **racha de turno**: `busy && source === 'turno'` y el poll anterior no lo era. Cubre el flanco idle→turno y el caso panel/estudio→turno (un `executeAction` encolado detrás de un Play). Play que empieza como `panel` o `estudio` no abre solo.

**Racha de turno:** dura mientras `busy && source === 'turno'`. Termina al idle o al cambiar `source`.

**Cerrar a mano durante una racha de turno:** no se reabre hasta la **siguiente** racha. Abrir a mano siempre permitido.

**Abrir a mano (o cajón ya abierto):** pinta lo que haya (`turno`, `panel`, `estudio`) o «Nada pendiente.»

**Detener:** `POST /sequence/stop`. Vacía la cola, corta espera, última posición PWM. Stop idle: ok. El botón Detener del cajón está siempre clicable.

El panel deja de llamar a `/sequence/runtime`. Inyecta el servicio para `playLocked` (unreachable o `busy`). El Stop del recuadro En hardware desaparece con el recuadro; el Stop del cajón es el único de cola.

---

## 4. Interfaz

Cajón **overlay** (no empuja). Escritorio: derecha, ~22 rem. Móvil/compacto: hoja inferior por encima de la nav inferior, scroll interno. z-index por encima de nav y chrome; por debajo del modal de compartir LAN si ambos existieran.

Botón fijo en todo el backoffice, esquina inferior derecha (en compacto, encima de la nav). Idle: icono en reposo. `busy`: el mismo en color de acento. Alterna el cajón.

Cabecera: título **En hardware**, origen (`Turno` / `Panel` / `Estudio` / —), **Detener**, X. Cierre también con el botón fijo o toque en el fondo.

Cuerpo: pasos en orden (`current` y luego `queue`). Fila: nombre, fase (Normal / Neutro / Espera), `duration_ms`. El actual muestra `remaining_ms` y, debajo, la tabla de servos (`nombre`, pca, servo, pos, `dur`); `fired` se distingue de pendiente. Espera no lista servos.

Vacío: «Nada pendiente.»  
Runtime caído: «No hay estado del robot. Detener sigue disponible.»

---

## 5. Fallos

| Situación | Resultado |
|---|---|
| `GET /sequence/runtime` falla | Mensaje de sin estado; Play del panel como ocupado; Detener sigue; poll no para; no auto-abre |
| `POST /sequence/stop` falla | Texto de error en el cajón; no se finge idle |
| Stop idle | 200 / ok, como hoy |
| Empieza racha `panel` o `estudio` | No auto-abre |
| Cajón abierto con Play de panel | Muestra esa cola |
| `duration_ms` 0 | Fila visible; restante 0; servos `fired` si `inicio` 0 |
| `blocks` ausente en un cliente | Tratar como `[]` |

---

## 6. Pruebas

Pytest en `pba-ms-robotics` (cola, sin Arduino):

1. Espera → `duration_ms == 1000`.
2. Gesto con `inicio` 0 y 1.5 → `duration_ms == 1500`.
3. `remaining_ms` del current baja (o llega a 0) mientras el paso corre; al pasar de paso se reinicia.
4. `blocks` solo en `current`; `espera` → `[]`.
5. `fired` falso si `elapsed < inicio`, verdadero si `elapsed >= inicio`.
6. Stop → idle (`busy` false, `current` null, `queue` `[]`).

Angular (unidad del servicio / cajón, sin e2e del iframe):

1. Empieza racha de turno → cajón abierto.
2. Empieza `panel` o `estudio` → cajón cerrado si el usuario no lo abrió.
3. Cerrar a mano en racha de turno → no reabre hasta la siguiente racha (idle o `source` distinto, luego otra vez `turno`).
4. Panel: Play bloqueado con `busy` o unreachable del servicio; no hay recuadro En hardware.

Gateway: sin prueba extra (proxy transparente).

---

## Repos

| Repo | Cambio |
|---|---|
| `pba-ms-robotics` | Reloj de paso en la cola; campos nuevos del snapshot |
| `pba-ms-gateway` | Sin DTO nuevo si el proxy sigue transparente |
| `pmas-web-main` | Servicio, cajón, botón; quitar En hardware y el poll del panel |
| Lanzador | Este spec |

`pmai-mai-core`, management y el estudio no cambian de contrato. El cajón cubre la página de secuencias (overlay sobre el iframe).
