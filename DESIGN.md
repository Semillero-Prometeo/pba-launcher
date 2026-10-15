---
name: R-ONE Mesa de control
description: Escritorio claro de gestión para el androide R-ONE — cian Prometeo, tarjetas blancas, español de operador.
colors:
  primary: "#38bdf8"
  secondary: "#10b981"
  background: "#f4f7fb"
  foreground: "#0f172a"
  card: "#ffffff"
  muted: "#eef2f6"
  muted-foreground: "#475569"
  border: "#cbd5e1"
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

Escritorio claro de gestión para el semillero, no consola militar. Fondo gris-blanco de trabajo, tarjetas blancas con borde suave, texto oscuro. El cian Prometeo `#38bdf8` y la esmeralda `#10b981` son acento, no relleno.

**Key Characteristics:**

- Fondo `#f4f7fb`, tarjeta `#ffffff`, tinta `#0f172a`
- Acento en chips, bordes activos e iconos Material Symbols junto al texto
- Inter + Space Grotesk; jerarquía por tamaño, no por neón
- Gramática de card / KPI / sidebar tomada de `example/` sin el rojo bancario
- Panel de control como página bandera: KPI reales, gestos por categoría, En hardware, Registro

## Named Rules

**The Accent Chip Rule.** El cian ocupa chips, bordes, iconos y `primary/10`. El texto corrido es `#0f172a`. Prohibido un título largo en `#38bdf8` sobre blanco.

**The No Theater Rule.** Cero hex de consola, cero System Override, cero Uptime/Signal inventados. Mono solo en timestamps de registro.

**The Example Grammar Rule.** Del `example/` se toma card, icono+label, densidad y franja KPI. No se toma oklch rojo ni copy Davivienda.

**The Tonal Card Rule.** Tarjeta = blanco + borde `#cbd5e1` + radio xl. No `shadow-xl` ni glow.
