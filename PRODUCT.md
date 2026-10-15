# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Integrantes del semillero Prometeo (Universidad Libre, Bogotá) que operan R-ONE: gestos del cuerpo, visión, chat, estudio de secuencias y administración.

## Product Purpose

Mesa de control del androide R-ONE. El éxito es ver el estado real del robot, lanzar un gesto con Normal o Neutro, hablar por el chat o el micrófono (el mismo turno) y administrar el semillero sin teatro de consola.

## Positioning

Herramienta operativa de un semillero de investigación, no un admin SaaS genérico ni una consola militar. Español de operador. Marco navy del logo; el cian marca la acción; el verde queda para Libre, Neutro y ok.

## Operating Context

- Lanzador `pba-launcher` con un repositorio por carpeta.
- Interfaz Angular en `pmas-web-main`, entrada HTTP en `pba-ms-gateway`.
- El chat de la interfaz y el micrófono usan el mismo turno (`pmai-mai-core`).
- `declarePoema` sigue en OpenAI y no es este producto visual.

## Capabilities and Constraints

- Un id de gesto válido es un par completo (`blocks` + `blocks_neutro` + categoría) con `id`.
- Mientras el hardware está ocupado, la UI no inicia otro movimiento; Detener sí.
- Acento Prometeo: cian `#38bdf8` para acción y pestaña activa; esmeralda `#059669` para Libre, Neutro y ok; navy `#0B2540` para el cascarón.

## Brand Commitments

- Nombre: Prometeo / R-ONE / Universidad Libre.
- Voz UI: español de operador (Gesto, Neutro, Detener, En el robot, Registro).
- No hex de consola, no «System Override», no telemetría inventada.
- No lienzo blanco puro: campo `#eef2f6`, tarjeta `#f7fafc`. El gris pizarra no sustituye al navy ni al verde.

## Evidence on Hand

- Spec: `docs/superpowers/specs/2026-10-14-navy-chrome-chat-tabs-design.md`
- Spec: `docs/superpowers/specs/2026-10-14-motion-studio-save-modal-neutro-rewind-design.md`
- Spec: `docs/superpowers/specs/2026-10-14-auth-session-admin-gate-vision-layout-design.md`
- Tokens: `pmas-web-main/src/styles.css`
- Studio: `pmas-web-motion-studio/src/static/editor.css`

## Product Principles

1. **Operar, no decorar** — el panel sirve para mover el robot y ver qué va al hardware.
2. **Datos reales** — KPI de estado, origen, conteo de secuencias y último evento; nunca CPU/dBm/uptime falsos.
3. **Una identidad** — PRODUCT.md y DESIGN.md viven en la raíz del lanzador.
4. **El turno no se maquilla** — chat y micrófono siguen el mismo contrato; este corte no lo toca.
5. **Sesión y visión** — si el token no vale, el login dice «Tu sesión venció. Entra de nuevo.» Usuarios y Roles son de ADMIN. En visión los objetos van arriba y las cámaras debajo, sin Preview.
6. **Marco navy** — cabecera y menú son `#0B2540`; el verde no ocupa el riel.
7. **Reserva verde** — Libre, Neutro y ok se leen en esmeralda.

## Accessibility & Inclusion

Texto de cuerpo ≥ 14px, etiquetas ≥ 12px. Contraste AA (4,5:1 cuerpo, 3:1 controles). El cian y el verde nunca son el único medio de un estado: van con palabra e icono. Foco visible en teclado. Pestañas inactivas se leen en navy sobre tarjeta.
