# Identidad visual clara y panel de control — design

Date: 2026-10-14  
Status: approved by user on 2026-10-14  
Scope: identidad de escritorio claro para R-ONE (PRODUCT.md + DESIGN.md en la raíz del lanzador) y reescritura del cascarón interno más el panel de control como página bandera. Las demás páginas con sesión heredan color; no se redibuja su layout.

Relación: el spec `2026-10-14-sequence-neutro-runtime-design.md` sigue vigente para categorías, Normal/Neutro, En hardware, cola y candado `busy`. Este corte **no** cambia el turno, el JSON de secuencias ni robótica. Es el primero de cuatro cortes independientes (visual → estudio → auth → visión).

## Problem

La interfaz interna es una consola nocturna rígida: fondo `#000f1d`, grilla de puntos, copy en inglés de teatro (`System Override`, `0x4F22-ALPHA`, `Robotic Control Interface`, Uptime y Signal inventados). El panel es la mesa de trabajo del semillero y no se siente como un tablero de gestión. No hay PRODUCT.md ni DESIGN.md del proyecto; el `example/` de Davivienda es gramática ajena (portal bancario rojo), no la marca Prometeo.

## Goal

1. Documentar la verdad de producto y el mundo visual en la **raíz del lanzador**: `PRODUCT.md` y `DESIGN.md`.
2. Sustituir la paleta noche-industrial por un escritorio claro: fondo de trabajo, tarjetas blancas, texto oscuro, acento cian Prometeo `#38bdf8` y esmeralda para libre/ok.
3. Cascarón interno (navbar, sidebar, drawer, footer) claro, en español de operador, mismas rutas.
4. Panel de control como dashboard: cabecera española, cuatro KPI reales, servicios, gestos por categoría, En hardware + Detener + Registro.
5. El resto de páginas internas deja de ser noche porque usan los mismos tokens; su layout espera cortes 2–4.

## Non-goals

- Turno, `getActions`, `executeAction`, cola, JSON de secuencias, gateway de play/runtime.
- `pmas-web-motion-studio` (toolbar, modal de guardar, descripción ≥ 10, neutro inverso): corte 2.
- Sesión caducada, crear usuarios, roles: corte 3.
- Quitar Preview, objetos encima de cámaras, FPS: corte 4.
- Rediseñar layout de visión, chat, usuarios, roles, gestión, secuencias/iframe, perfil, login, registro, info, team, projects.
- Copiar paleta, rojo o marca Davivienda del `example/`.
- Gemma visión, `declarePoema`, reconectar el chat a OpenAI.

## Approach

Opción 1 aprobada: tokens nuevos + dashboard bandera. Un cambio de `@theme` en `pmas-web-main/src/styles.css` pinta el cascarón y las páginas internas. El panel se reescribe (estructura y copy). Las demás pantallas internas no se redibujan en este corte.

## Documentos de identidad

Viven en la raíz de `pba-launcher/`, no en un submódulo: son el acento de todo el proyecto.

| Archivo | Rol |
|---|---|
| `PRODUCT.md` | Verdad de producto (quién, para qué, principios). No describe pixeles. |
| `DESIGN.md` | Mundo visual (norte creativo, paleta, tipo, layout, reglas con nombre). |
| `example/PRODUCT.md` y `example/DESIGN.md` | Guía de gramática (cards, icono+label, densidad, dialogs). No se copian paleta ni marca. |

`PRODUCT.md` cubre: plataforma web Angular; usuarios = semillero Prometeo (Universidad Libre, Bogotá) que operan R-ONE; propósito = mesa de control del androide (gestos, visión, chat, estudio embebido, administración); voz = español de operador; el chat y el micrófono comparten el turno; `declarePoema` no es este producto visual.

`DESIGN.md` cubre el norte **«Mesa de control de R-ONE»**, tokens de la sección Paleta, tipografía Inter + Space Grotesk, gramática de card/KPI/sidebar tomada del `example/` sin el rojo bancario, y las reglas con nombre de más abajo.

La implementación crea esos dos archivos; este spec es el contrato, no los sustituye.

## Paleta y tokens

Norte: escritorio claro de gestión, no consola militar. Fondo gris-blanco de trabajo (no papel cálido). El cian `#38bdf8` se queda; no se cambia por el rojo de Universidad Libre.

En `pmas-web-main/src/styles.css` (`@theme`):

| Token | Hoy (noche) | Nuevo |
|---|---|---|
| `--color-background` | `#000f1d` | `#f4f7fb` |
| `--color-surface` | `#000f1d` | `#ffffff` |
| `--color-surface-container-lowest` | `#000a14` | `#f4f7fb` |
| `--color-surface-container-low` | `#001a2e` | `#f8fafc` |
| `--color-surface-container` | `#001525` | `#ffffff` |
| `--color-surface-container-high` | `#0d2133` | `#eef2f6` |
| `--color-surface-container-highest` | `#132c40` | `#e2e8f0` |
| `--color-on-surface` / `--color-on-background` | `#e1e2e5` | `#0f172a` |
| `--color-on-surface-variant` | `#c1c7ce` | `#475569` |
| `--color-outline` | `#8d919a` | `#cbd5e1` |
| `--color-outline-variant` | `#41484d` | `#e2e8f0` |
| `--color-primary` | `#38bdf8` | `#38bdf8` (sin cambio) |
| `--color-on-primary` | `#00354b` | `#0c4a6e` |
| `--color-primary-container` | `#004c6a` | `#e0f2fe` |
| `--color-secondary` | `#10b981` | `#10b981` (sin cambio) |
| `--color-error` | `#ffb4ab` | `#dc2626` |
| `--color-on-error` | `#690005` | `#ffffff` |
| `--color-inverse-surface` | `#e1e2e5` | `#0f172a` |
| `--color-inverse-on-surface` | `#2e3133` | `#f8fafc` |

Tipografía: `--font-headline: Space Grotesk`, `--font-body` / `--font-label: Inter`. Sin fuentes nuevas. Jerarquía por tamaño y peso, no por neón.

Radio: `--radius-DEFAULT: 0.375rem`, `--radius-lg: 0.5rem`, `--radius-xl: 0.75rem`, `--radius-full` sin cambio (chips/píldora).

Tokens `@theme` que no están en la tabla (`surface-dim`, `surface-bright`, `surface-variant`, `*-fixed`, `*-container`, `on-*` de primary/secondary/tertiary/error): todo contenedor que hoy es un relleno oscuro pasa a un tinte claro del mismo matiz; todo `on-*` que hoy es texto claro sobre oscuro pasa a texto oscuro sobre claro. No se deja `#93000a` ni `#004c6a` como bolsillo negro-rojo/cian.

`.industrial-grid` se restiliza a puntos muy tenues sobre el fondo claro (no se borra la clase). El panel puede seguir usándola; ninguna página interna puede seguir pintando la noche con ella.

**The Accent Chip Rule.** El cian ocupa chips, bordes activos, iconos y rellenos `primary/10`. El texto corrido es `#0f172a`. Prohibido párrafo o título largo en `#38bdf8` sobre blanco.

**The No Theater Rule.** Cero hex de consola, cero «System Override», cero Uptime/Signal inventados, cero `font-mono` como voz de marca. Mono solo en timestamps de registro.

**The Example Grammar Rule.** Del `example/` se toma: card con borde suave, icono + label, densidad de oficina, KPI en franja. No se toma oklch rojo, ni shadcn de banco, ni copy Davivienda.

**The Tonal Card Rule.** Tarjeta = blanco + borde `--color-outline` + radio xl. No `shadow-xl` teatral ni glow.

## Cascarón

Dueño: `pmas-web-main` layouts y `components/navbar`, `sidebar`, footer, drawer del `admin-shell`.

- Navbar: fondo claro opaco (no `bg-surface/60` sobre noche), marca **Prometeo**, texto oscuro. Rutas iguales.
- Etiqueta de sesión en la barra: **Panel** (antes «Control Panel»). Sin buscador «Search parameters...» (no busca nada real).
- Sidebar: mismos grupos (Robótica, Autenticación, Gestión) y mismos destinos (Movimientos, Visión, Chat, Creación de Secuencias, Panel Externo, Usuarios, Roles, …). Superficie clara; ítem activo con acento cian, no `bg-slate-950` ni `border-slate-800`.
- Health checks del lateral: se queda, restilizado al color claro. Título alineado a **Estado de servicios**.
- Cajón móvil: overlay no es `bg-black/60`; panel del menú claro.
- Footer interno: claro.
- Páginas públicas (login, registro, info, team, projects, r-one): heredan tokens. Layout público no se reescribe. Sesión y roles van al corte 3.

Rutas, guards y compact/bottom-nav no se rediseñan: solo color y copy visible.

## Panel de control (página bandera)

Dueño: `pmas-web-main/src/app/pages/control-panel/`.

Contrato de ejecución intacto (spec de neutro): Normal y Neutro mandan `mode`; `busy` bloquea esos botones; **Detener** siempre clicable; poll 500 ms / 3 s; runtime caído → «sin estado» y ejecutar bloqueado.

### Cabecera

Título **Panel de control**. Sin badge System Override, sin `0x4F22-ALPHA`, sin Uptime, sin Signal.

### Franja KPI (cuatro tarjetas, datos reales)

| KPI | Fuente | Valores |
|---|---|---|
| Estado | `GET /sequence/runtime` | **ocupado** si `busy`; **libre** si no; **sin estado** si el runtime no responde |
| Origen | `runtime.source` | `estudio` / `panel` / `turno` / **—** si null |
| Secuencias | catálogo ya cargado en el panel | entero = total de secuencias del catálogo **sin** aplicar buscador ni filtro de categoría; **—** si aún carga o hubo error de lista |
| Último evento | `commandLogs()` | hora + nombre de la última entrada; **—** si el registro está vacío |

Prohibido rellenar CPU, dBm, hex o uptime falso. El `uptime()` y el Signal actuales se eliminan.

### Cuerpo

1. **Estado de servicios** — el dropdown que ya existe, claro.
2. Escritorio xl, dos columnas:
   - Izquierda (~2/3): gestos por las seis categorías (Cara, Cuello, Brazo derecho, Brazo izquierdo, Torso, Cadera), buscador, filtro Todas + categoría, cada secuencia con nombre, descripción, **Normal** y **Neutro**.
   - Derecha (~1/3), sticky: **En hardware** (origen, fase `nombre · mode`, cola) + **Detener** + **Registro** (antes Execution Log) con Limpiar.
3. Carga / error / vacío: icono Material Symbols + frase en español. El vacío de filtro sigue siendo «Sin resultados para el filtro actual».

Copy de operador (mapa mínimo):

| Hoy | Nuevo |
|---|---|
| Robotic Control Interface | Panel de control |
| Execution Log | Registro |
| Control Panel (navbar) | Panel |
| Search parameters... | (se quita) |
| Cargando secuencias del robot... | Cargando secuencias… |

Se mantienen: Normal, Neutro, En hardware, Detener, Estado de servicios, etiquetas de categoría.

## Qué hereda y qué se deja

| Superficie | Este corte |
|---|---|
| Tokens CSS | Reescritura |
| Navbar, sidebar, drawer, footer interno | Color + copy; mismas rutas |
| `control-panel` | Reescritura de layout y copy |
| Visión, chat, usuarios, roles, gestión, secuencias, perfil | Solo paleta (pueden quedar `slate-*` sueltos; no es fallo de este corte salvo que el cascarón o el panel los pinten) |
| Login / públicas | Solo paleta |
| Motion studio (servicio propio) | Nada |
| Auth MS, robotics, gateway, mai-core | Nada |

## Fallos

| Situación | Resultado |
|---|---|
| Color fijo `slate-950` / `#000f1d` en cascarón o panel | Se corrige en este corte; bolsillo negro ahí = bug |
| `slate-*` en visión/chat/admin | Aceptable hasta su corte; no bloquea este |
| KPI con número inventado | Bug; las cuatro tarjetas salen de runtime, catálogo o log |
| Restilo rompe el candado | Bug; Normal/Neutro off si `busy` o runtime caído; Detener on |
| Título largo en cian sobre blanco | Bug (Accent Chip Rule) |
| Paleta Davivienda en tokens | Bug |
| PRODUCT.md / DESIGN.md dentro de `pmas-web-main` | Bug; van en la raíz del lanzador |

## Dueños del cambio

| Repositorio | Qué toca |
|---|---|
| `pba-launcher` (raíz) | `PRODUCT.md`, `DESIGN.md` |
| `pmas-web-main` | `styles.css`, cascarón, `control-panel`, copy de navbar/sidebar |
| `docs/` | este spec; el plan de implementación |

## Testing

- Tokens: fondo de `body` / shell no es `#000f1d`; `--color-on-surface` es oscuro.
- Navbar: existe «Panel»; no existe «Control Panel» ni el input Search parameters.
- Panel: no hay System Override, 0x4F22-ALPHA, Uptime ni Signal.
- Idle: Estado = libre, Origen = —, Detener clicable, Normal/Neutro enabled (salvo lista vacía).
- Con `busy` de runtime: Estado = ocupado, Origen = el `source` del snapshot, Normal/Neutro disabled, Detener enabled, En hardware muestra `current` y `queue`.
- Runtime 5xx / timeout: Estado = sin estado; ejecutar disabled; Detener enabled.
- Tras un play del panel: Último evento toma timestamp + nombre del log; Secuencias coincide con el conteo de la lista.
- Visión o chat: el cascarón y el `body` son claros. Un `slate-*` suelto dentro de esas páginas no bloquea el corte.
- Estudio en iframe: CSS propio, no obligado a la paleta nueva.

## Límites

Un corte. No se fusiona con estudio, auth ni visión. No se pide Arduino ni Compose para validar tokens; el candado sí se valida contra el runtime que ya existe. `feat/sequence-neutro-runtime` sigue siendo la base funcional del panel; este corte se apoya en ella, no la revert.
