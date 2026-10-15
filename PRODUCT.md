# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Integrantes del semillero Prometeo (Universidad Libre, Bogotá) que operan R-ONE: gestos del cuerpo, visión, chat, estudio de secuencias y administración.

## Product Purpose

Mesa de control del androide R-ONE. El éxito es ver el estado real del robot, lanzar un gesto con Normal o Neutro, hablar por el chat o el micrófono (el mismo turno) y administrar el semillero sin teatro de consola.

## Positioning

Herramienta operativa de un semillero de investigación, no un admin SaaS genérico ni una consola militar. Español de operador. El `example/` de Davivienda es gramática de layout, no la marca.

## Operating Context

- Lanzador `pba-launcher` con un repositorio por carpeta.
- Interfaz Angular en `pmas-web-main`, entrada HTTP en `pba-ms-gateway`.
- El chat de la interfaz y el micrófono usan el mismo turno (`pmai-mai-core`).
- `declarePoema` sigue en OpenAI y no es este producto visual.

## Capabilities and Constraints

- Un id de gesto válido es un par completo (`blocks` + `blocks_neutro` + categoría) con `id`.
- Mientras el hardware está ocupado, la UI no inicia otro movimiento; Detener sí.
- No copiar paleta ni marca Davivienda. Acento Prometeo: cian `#38bdf8` y esmeralda `#10b981`.

## Brand Commitments

- Nombre: Prometeo / R-ONE / Universidad Libre.
- Voz UI: español de operador (Ejecutar, Detener, En el robot, Registro).
- No hex de consola, no «System Override», no telemetría inventada.

## Evidence on Hand

- Spec: `docs/superpowers/specs/2026-10-14-visual-identity-dashboard-design.md`
- Tokens destino: `pmas-web-main/src/styles.css`
- Gramática (no marca): `example/DESIGN.md`

## Product Principles

1. **Operar, no decorar** — el panel sirve para mover el robot y ver qué va al hardware.
2. **Datos reales** — KPI de estado, origen, conteo de secuencias y último evento; nunca CPU/dBm/uptime falsos.
3. **Una identidad** — PRODUCT.md y DESIGN.md viven en la raíz del lanzador.
4. **El turno no se maquilla** — chat y micrófono siguen el mismo contrato; este corte no lo toca.
5. **Cortes siguientes** — estudio, auth y visión son otros ciclos.

## Accessibility & Inclusion

Labels con texto visible, foco en controles, contraste de texto oscuro sobre fondo claro. El cian no se usa como único medio para el estado ocupado/libre (va acompañado de la palabra).
