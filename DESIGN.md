---
name: R-ONE Mesa de control
description: Escritorio de gestión para el androide R-ONE — marco navy del logo, cian de acción, esmeralda de Libre/Neutro.
colors:
  primary: "#38bdf8"
  secondary: "#059669"
  background: "#eef2f6"
  foreground: "#0B2540"
  card: "#f7fafc"
  muted: "#e8eef4"
  muted-foreground: "#3d5a73"
  border: "#c5d4e0"
  rail: "#0B2540"
  on-rail: "#eef2f6"
  destructive: "#dc2626"
typography:
  title:
    fontFamily: "Space Grotesk, sans-serif"
    fontSize: "1.5rem"
    fontWeight: 700
  body:
    fontFamily: "Inter, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
  label:
    fontFamily: "Inter, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 600
rounded:
  lg: "0.5rem"
  xl: "0.75rem"
---

# Design System: R-ONE Mesa de control

## Overview

**Creative North Star: "Mesa de control de R-ONE"**

Escritorio de gestión para el semillero. El marco es el navy del circuito del logo `#0B2540`. El campo es papel frío `#eef2f6`. Las tarjetas son `#f7fafc`, no blanco puro. El cian `#38bdf8` es acción (Normal, Enviar, pestaña activa). La esmeralda `#059669` es Libre, Neutro y ok.

**Key Characteristics:**

- Marco navy, campo frío, tarjeta papel, tinta `#0B2540`
- Texto quieto `#3d5a73`, nunca gris pizarra ni bosque
- Icono Material Symbols a la izquierda de cada etiqueta útil
- Inter 14px cuerpo / 12px etiqueta; Space Grotesk en títulos de página
- Panel bandera: KPI Libre en contenedor esmeralda; chat con pestañas cian

## Color roles

| Rol | Color | Uso |
|---|---|---|
| Chrome / rail | `#0B2540` + tinta `#eef2f6` | Navbar, sidebar, bottom-nav, login izquierdo |
| Canvas | `#eef2f6` | Campo de trabajo |
| Card | `#f7fafc` | Superficie elevada |
| Action | `#38bdf8` + tinta `#0c4a6e` | Normal, Enviar, pestaña activa |
| Rest / OK | `#059669` | Neutro, Libre (contenedor), puntos de vida |
| Ink | `#0B2540` | Títulos y cuerpo |
| Quiet ink | `#3d5a73` | Ayudas, metadatos |
| Stop | `#dc2626` | Detener |
| Busy | `#b45309` | Estado ocupado |

## Type scale

| Rol | Size | Weight | Face |
|---|---|---|---|
| Page title | 1.5rem / 24px | 700 | Space Grotesk |
| Section | 1.125rem / 18px | 700 | Space Grotesk |
| Body | 0.875rem / 14px | 400 | Inter |
| Label | 0.75rem / 12px | 600 | Inter |
| Button | 0.875rem / 14px | 600 | Inter |
| Meta | 0.75rem / 12px | 400 | Inter |

Prohibido `text-[8px]`, `text-[9px]`, `text-[10px]` en UI. Mayúsculas sostenidas solo en chips de una palabra (Cara, ACK). Tracking extremo no.

## Layout

- Cabecera de página: icono en pozo + título + una línea de guía. El pozo puede ser navy o esmeralda; no reabrir la malla del panel.
- KPI Libre: contenedor esmeralda, no riel navy.
- Chat: dos pestañas a ancho completo, alto mínimo 44px, texto 14px.
- Motion Studio (iframe): cabecera navy; barra Play / Stop / Agregar / Gesto|Neutro / Generar neutro / Guardar / Actualizar; Guardar abre diálogo (nombre, descripción ≥ 10, categoría, Arduino); escenario en papel frío; barras de gesto cian y de neutro esmeralda. No reabrir la gramática de la regla.
- Login: aviso de sesión vencida sobre el formulario (icono `schedule`, 14 px, borde error). No toast. El selector de rol solo aparece si hay más de un rol.
- Visión: cabecera con pozo navy; objetos observados en tarjetas grandes (recorte ≥ 128 px) a ancho completo; cámaras debajo en cuadrícula a ~480 px; sin Preview.
- Usuarios (`/admin/users`): tabla Nombre / Correo / Documento / Roles; modal con persona, contraseña y checkboxes ADMIN/USER. Sin Roles ni Gestión en el menú.

## Named Rules

**The Navy Frame Rule.** Cabecera y menú son `#0B2540`. Un riel esmeralda en esos roles es un bug.

**The Green Reserve Rule.** `#059669` solo Libre, Neutro y ok.

**The Accent Chip Rule.** El cian ocupa Normal, Enviar, pestaña activa, Play, Guardar, pista Gesto activa y el foco. Prohibido un título largo en `#38bdf8`.

**The No Theater Rule.** Cero hex de consola, cero System Override, cero Uptime/Signal. Mono solo en la hora del registro.

**The No Glare Rule.** Ninguna superficie de trabajo es `#ffffff`. El campo es `#eef2f6`; la tarjeta más clara es `#f7fafc`.

**The Visible Tab Rule.** Una pestaña inactiva se lee igual de bien que una etiqueta de 14px navy sobre tarjeta. Slate sobre papel no.

**The Speak With Icons Rule.** Cada control de ejecución, cada KPI y cada pestaña del chat lleva icono Material Symbols junto a la palabra.

**The Tonal Card Rule.** Tarjeta = `#f7fafc` + borde `#c5d4e0` + radio xl. Sin `shadow-xl` ni glow.
