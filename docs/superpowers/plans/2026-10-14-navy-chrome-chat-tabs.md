# Navy chrome and visible chat tabs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Moderate the green shell to Prometeo navy (`#0B2540`), cool paper (`#eef2f6`), and make Chatbot IA / Decir oración tabs readable in cyan.

**Architecture:** `--color-rail` already paints navbar, sidebar, bottom-nav, and the login brand panel. Repaint rail to navy and the canvas to cool paper. Move the Libre KPI off `bg-rail` onto `bg-secondary-container`. Fix chat tab classes only. Do not reopen the control-panel layout.

**Tech Stack:** Markdown at launcher root; Angular 21, Tailwind v4 `@theme`, Vitest (`npx vitest run`).

## Global Constraints

- Spec: `docs/superpowers/specs/2026-10-14-navy-chrome-chat-tabs-design.md`. Visual-identity spec still governs layout, type ≥ 14px body / ≥ 12px labels, icons, Spanish operator copy.
- Chrome / rail `#0B2540`, on-chrome `#eef2f6`. Canvas `#eef2f6`. Card `#f7fafc` — never `#ffffff`. Border `#c5d4e0`. Ink `#0B2540`. Quiet ink `#3d5a73`.
- Primary `#38bdf8` + `#0c4a6e` for Normal, Enviar, and the active chat tab. Secondary `#059669` only for Libre, Neutro, ok.
- Libre KPI: `bg-secondary-container text-on-secondary-container`. Not `bg-rail`.
- Chat tabs: inactive navy + `border-outline`; both active `bg-primary text-on-primary`. No `text-slate-400` / `border-white/5` on tabs. `min-h-11`, `text-sm`.
- Chatbot stays `POST ${GATEWAY_URL}/chat/question`. Do not wire `chatService.chat` to OpenAI. `declarePoema` stays as it is.
- Do not edit motion-studio, auth services, robotics, mai-core, or vision layout/FPS.
- Do not mention `example/` or Davivienda in `PRODUCT.md` / `DESIGN.md`.
- Work on `feat/sequence-neutro-runtime`. Angular commits in `pmas-web-main`. Docs/plan commits in the launcher.

---

## File structure

| File | Responsibility |
|---|---|
| `PRODUCT.md` | Product truth: navy frame, emerald reserve, cyan action. |
| `DESIGN.md` | Visual world: tokens and named rules (Navy Frame, Green Reserve, Visible Tab). |
| `pmas-web-main/src/styles.css` | `@theme` hexes + cool-dot `.industrial-grid`. |
| `pmas-web-main/src/styles.tokens.spec.ts` | Token contract. |
| `pmas-web-main/src/app/pages/control-panel/control-panel.ts` | `estadoCardClass()` Libre off rail. |
| `pmas-web-main/src/app/pages/control-panel/control-panel.copy.spec.ts` | Assert Libre is secondary-container. |
| `pmas-web-main/src/app/pages/robotics-chat/robotics-chat.html` | Visible tabs, Limpiar, Enviar. |
| `pmas-web-main/src/app/pages/robotics-chat/robotics-chat.copy.spec.ts` | Tab contrast contract. |

Navbar, sidebar, bottom-nav, and login already use `bg-rail` / `text-on-rail`. Do not rewrite those templates unless a leftover forest class breaks the spec.

---

### Task 1: PRODUCT.md and DESIGN.md

**Files:**
- Modify: `PRODUCT.md`
- Modify: `DESIGN.md`

**Interfaces:**
- Consumes: spec sections Paleta, Named rules, Goal 5.
- Produces: launcher-root identity docs. Later tasks do not import these files.

- [ ] **Step 1: Confirm the current docs still describe forest chrome**

Run from the launcher root:

```bash
rg -n "065f46|c5e6d4|bosque|menta saturada" PRODUCT.md DESIGN.md
```

Expected: matches in both files.

- [ ] **Step 2: Write PRODUCT.md**

Replace `PRODUCT.md` with:

```markdown
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
- Tokens: `pmas-web-main/src/styles.css`

## Product Principles

1. **Operar, no decorar** — el panel sirve para mover el robot y ver qué va al hardware.
2. **Datos reales** — KPI de estado, origen, conteo de secuencias y último evento; nunca CPU/dBm/uptime falsos.
3. **Una identidad** — PRODUCT.md y DESIGN.md viven en la raíz del lanzador.
4. **El turno no se maquilla** — chat y micrófono siguen el mismo contrato; este corte no lo toca.
5. **Cortes siguientes** — estudio, auth y visión son otros ciclos.
6. **Marco navy** — cabecera y menú son `#0B2540`; el verde no ocupa el riel.
7. **Reserva verde** — Libre, Neutro y ok se leen en esmeralda.

## Accessibility & Inclusion

Texto de cuerpo ≥ 14px, etiquetas ≥ 12px. Contraste AA (4,5:1 cuerpo, 3:1 controles). El cian y el verde nunca son el único medio de un estado: van con palabra e icono. Foco visible en teclado. Pestañas inactivas se leen en navy sobre tarjeta.
```

- [ ] **Step 3: Write DESIGN.md**

Replace `DESIGN.md` with:

```markdown
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

## Named Rules

**The Navy Frame Rule.** Cabecera y menú son `#0B2540`. Un riel esmeralda en esos roles es un bug.

**The Green Reserve Rule.** `#059669` solo Libre, Neutro y ok.

**The Accent Chip Rule.** El cian ocupa Normal, Enviar, pestaña activa y el foco. Prohibido un título largo en `#38bdf8`.

**The No Theater Rule.** Cero hex de consola, cero System Override, cero Uptime/Signal. Mono solo en la hora del registro.

**The No Glare Rule.** Ninguna superficie de trabajo es `#ffffff`. El campo es `#eef2f6`; la tarjeta más clara es `#f7fafc`.

**The Visible Tab Rule.** Una pestaña inactiva se lee igual de bien que una etiqueta de 14px navy sobre tarjeta. Slate sobre papel no.

**The Speak With Icons Rule.** Cada control de ejecución, cada KPI y cada pestaña del chat lleva icono Material Symbols junto a la palabra.

**The Tonal Card Rule.** Tarjeta = `#f7fafc` + borde `#c5d4e0` + radio xl. Sin `shadow-xl` ni glow.
```

- [ ] **Step 4: Confirm no forest chrome and no guide-folder brand**

```bash
rg -n "065f46|c5e6d4|Davivienda|example/" PRODUCT.md DESIGN.md || true
```

Expected: no Davivienda / `example/`. No forest canvas hexes.

- [ ] **Step 5: Commit (launcher)**

```bash
git add PRODUCT.md DESIGN.md
git commit -m "$(cat <<'EOF'
Document navy chrome and emerald-reserved green.

The operator shell follows the Prometeo logo: navy frame, cool paper, cyan action.
EOF
)"
```

---

### Task 2: Tokens

**Files:**
- Modify: `pmas-web-main/src/styles.tokens.spec.ts`
- Modify: `pmas-web-main/src/styles.css`

**Interfaces:**
- Consumes: DESIGN.md hex table.
- Produces: `--color-rail: #0B2540`, `--color-on-rail: #eef2f6`, `--color-background: #eef2f6`, `--color-surface: #f7fafc`, `--color-on-surface: #0B2540`, `--color-on-surface-variant: #3d5a73`, `--color-outline: #c5d4e0`, `--color-chrome` alias of rail. Chrome templates that already use `bg-rail` inherit navy.

- [ ] **Step 1: Write the failing token spec**

Replace `pmas-web-main/src/styles.tokens.spec.ts` with:

```typescript
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const css = readFileSync(resolve(import.meta.dirname, 'styles.css'), 'utf8');
const html = readFileSync(resolve(import.meta.dirname, 'index.html'), 'utf8');

function token(name: string): string {
  const match = css.match(new RegExp(`${name}:\\s*(#[0-9a-fA-F]+)`));
  if (!match) throw new Error(`missing token ${name}`);
  return match[1].toLowerCase();
}

describe('navy chrome tokens', () => {
  it('uses cool paper and navy ink, never pure white or forest canvas', () => {
    expect(token('--color-background')).toBe('#eef2f6');
    expect(token('--color-surface')).toBe('#f7fafc');
    expect(token('--color-surface-container')).toBe('#f7fafc');
    expect(token('--color-on-surface')).toBe('#0b2540');
    expect(token('--color-on-surface-variant')).toBe('#3d5a73');
    expect(token('--color-outline')).toBe('#c5d4e0');
    expect(css).not.toMatch(/--color-background:\s*#ffffff/);
    expect(css).not.toMatch(/--color-surface:\s*#ffffff/);
    expect(css).not.toMatch(/--color-background:\s*#c5e6d4/);
    expect(css).not.toMatch(/--color-on-surface-variant:\s*#2a5644/);
    expect(css).not.toMatch(/--color-on-surface-variant:\s*#475569/);
  });

  it('keeps cyan action, emerald secondary, and a navy rail', () => {
    expect(token('--color-primary')).toBe('#38bdf8');
    expect(token('--color-secondary')).toBe('#059669');
    expect(token('--color-rail')).toBe('#0b2540');
    expect(token('--color-on-rail')).toBe('#eef2f6');
    expect(token('--color-chrome')).toBe('#0b2540');
    expect(token('--color-on-chrome')).toBe('#eef2f6');
    expect(token('--color-error')).toBe('#dc2626');
    expect(token('--color-warning')).toBe('#b45309');
    expect(css).not.toMatch(/--color-rail:\s*#065f46/);
    expect(css).not.toMatch(/--color-background:\s*#000f1d/);
  });

  it('restyles industrial-grid to faint cool dots', () => {
    expect(css).toMatch(/\.industrial-grid\s*\{[^}]*#c5d4e0/s);
    expect(css).not.toMatch(/\.industrial-grid\s*\{[^}]*#7fb59a/s);
    expect(css).not.toMatch(/\.industrial-grid\s*\{[^}]*#43474f/s);
  });

  it('drops the html dark class', () => {
    expect(html).toMatch(/<html lang="es">/);
    expect(html).not.toMatch(/class="dark"/);
  });
});
```

- [ ] **Step 2: Run the spec and confirm it fails**

```bash
cd pmas-web-main && npx vitest run src/styles.tokens.spec.ts
```

Expected: FAIL on `#c5e6d4` / `#065f46` vs expected navy/paper.

- [ ] **Step 3: Update `styles.css` `@theme` and helpers**

Replace the `@theme` block and the grid/focus/selection rules so the file is:

```css
@import 'tailwindcss';

@theme {
  --color-background: #eef2f6;
  --color-surface: #f7fafc;
  --color-surface-dim: #e2e8f0;
  --color-surface-bright: #f7fafc;
  --color-surface-container-lowest: #eef2f6;
  --color-surface-container-low: #f1f5f9;
  --color-surface-container: #f7fafc;
  --color-surface-container-high: #e8eef4;
  --color-surface-container-highest: #dce6ef;
  --color-surface-variant: #e8eef4;
  --color-surface-tint: #38bdf8;

  --color-primary: #38bdf8;
  --color-primary-fixed: #e0f2fe;
  --color-primary-fixed-dim: #38bdf8;
  --color-primary-container: #e0f2fe;
  --color-on-primary: #0c4a6e;
  --color-on-primary-fixed: #0c4a6e;
  --color-on-primary-fixed-variant: #0369a1;
  --color-on-primary-container: #0c4a6e;
  --color-inverse-primary: #38bdf8;

  --color-secondary: #059669;
  --color-secondary-fixed: #d1fae5;
  --color-secondary-fixed-dim: #10b981;
  --color-secondary-container: #d1fae5;
  --color-on-secondary: #ffffff;
  --color-on-secondary-fixed: #064e3b;
  --color-on-secondary-fixed-variant: #047857;
  --color-on-secondary-container: #065f46;

  --color-rail: #0B2540;
  --color-on-rail: #eef2f6;
  --color-rail-hover: #163a5c;
  --color-chrome: #0B2540;
  --color-on-chrome: #eef2f6;

  --color-tertiary: #047857;
  --color-tertiary-fixed: #d1fae5;
  --color-tertiary-fixed-dim: #34d399;
  --color-tertiary-container: #d1fae5;
  --color-on-tertiary: #ecfdf5;
  --color-on-tertiary-fixed: #064e3b;
  --color-on-tertiary-fixed-variant: #047857;
  --color-on-tertiary-container: #065f46;

  --color-error: #dc2626;
  --color-error-container: #fee2e2;
  --color-on-error: #ffffff;
  --color-on-error-container: #7f1d1d;

  --color-warning: #b45309;
  --color-warning-container: #ffedd5;
  --color-on-warning: #7c2d12;

  --color-outline: #c5d4e0;
  --color-outline-variant: #dce6ef;
  --color-on-surface: #0B2540;
  --color-on-surface-variant: #3d5a73;
  --color-on-background: #0B2540;
  --color-inverse-surface: #0B2540;
  --color-inverse-on-surface: #eef2f6;

  --font-headline: 'Space Grotesk', sans-serif;
  --font-body: 'Inter', sans-serif;
  --font-label: 'Inter', sans-serif;

  --radius-DEFAULT: 0.375rem;
  --radius-lg: 0.5rem;
  --radius-xl: 0.75rem;
  --radius-full: 0.75rem;
}

.material-symbols-outlined {
  font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;
}

.editorial-grid {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: 2rem;
}

.industrial-grid {
  background-image: radial-gradient(circle, #c5d4e0 1px, transparent 1px);
  background-size: 28px 28px;
}

:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

::selection {
  background: #bae6fd;
  color: #0c4a6e;
}

body {
  font-size: 0.875rem;
  line-height: 1.5;
}
```

- [ ] **Step 4: Run the token spec**

```bash
cd pmas-web-main && npx vitest run src/styles.tokens.spec.ts src/app/layouts/admin-shell/shell-copy.spec.ts
```

Expected: PASS (chrome templates still contain `bg-rail`).

- [ ] **Step 5: Commit (pmas-web-main)**

```bash
cd pmas-web-main
git add src/styles.css src/styles.tokens.spec.ts
git commit -m "$(cat <<'EOF'
Paint the operator chrome navy and the canvas cool paper.

Rail tokens now follow the Prometeo circuit navy so header and menu stop reading as a green room.
EOF
)"
```

---

### Task 3: Libre KPI off the rail

**Files:**
- Modify: `pmas-web-main/src/app/pages/control-panel/control-panel.copy.spec.ts`
- Modify: `pmas-web-main/src/app/pages/control-panel/control-panel.ts`

**Interfaces:**
- Consumes: `estadoCardClass(): string` on `ControlPanel`.
- Produces: `libre` → `'border-transparent bg-secondary-container text-on-secondary-container'`. Occupied/error strings unchanged.

- [ ] **Step 1: Extend the panel copy spec**

Add this test inside `describe('control panel dashboard copy'` in `control-panel.copy.spec.ts`:

```typescript
  it('paints Libre with emerald container, not the navy rail', () => {
    expect(ts).toMatch(
      /case 'libre':\s*return 'border-transparent bg-secondary-container text-on-secondary-container'/,
    );
    expect(ts).not.toMatch(/case 'libre':[\s\S]*bg-rail/);
  });
```

- [ ] **Step 2: Run it and confirm it fails**

```bash
cd pmas-web-main && npx vitest run src/app/pages/control-panel/control-panel.copy.spec.ts
```

Expected: FAIL because Libre still returns `bg-rail text-on-rail`.

- [ ] **Step 3: Change `estadoCardClass`**

In `pmas-web-main/src/app/pages/control-panel/control-panel.ts`, replace the `libre` branch:

```typescript
  estadoCardClass(): string {
    switch (this.kpis().estado) {
      case 'libre':
        return 'border-transparent bg-secondary-container text-on-secondary-container';
      case 'ocupado':
        return 'border-warning/40 bg-warning-container text-on-warning';
      default:
        return 'border-error/40 bg-error-container text-on-error-container';
    }
  }
```

Do not change `control-panel.html` layout.

- [ ] **Step 4: Run panel specs**

```bash
cd pmas-web-main && npx vitest run src/app/pages/control-panel/control-panel.copy.spec.ts src/app/pages/control-panel/panel-kpis.spec.ts
```

Expected: PASS.

- [ ] **Step 5: Commit (pmas-web-main)**

```bash
cd pmas-web-main
git add src/app/pages/control-panel/control-panel.ts src/app/pages/control-panel/control-panel.copy.spec.ts
git commit -m "$(cat <<'EOF'
Keep Libre on emerald instead of the navy rail.

Green stays reserved for rest/ok so the frame can be Prometeo navy.
EOF
)"
```

---

### Task 4: Chat tabs

**Files:**
- Create: `pmas-web-main/src/app/pages/robotics-chat/robotics-chat.copy.spec.ts`
- Modify: `pmas-web-main/src/app/pages/robotics-chat/robotics-chat.html`
- Do not modify: `robotics-chat.ts` (keep `POST /chat/question` and `sendDecir`).

**Interfaces:**
- Consumes: `activeTab` `'chatbot' | 'decir'`, `sendChat()`, `sendDecir()`, `clearChat()`, `clearDecir()`.
- Produces: two tabs with inactive `text-on-surface border-outline bg-surface` and active `bg-primary text-on-primary`; Limpiar ≥ 12px `text-on-surface-variant`; Enviar uses primary when enabled and `text-on-surface-variant` when disabled.

- [ ] **Step 1: Write the failing chat copy spec**

Create `pmas-web-main/src/app/pages/robotics-chat/robotics-chat.copy.spec.ts`:

```typescript
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const html = readFileSync(resolve(import.meta.dirname, 'robotics-chat.html'), 'utf8');
const ts = readFileSync(resolve(import.meta.dirname, 'robotics-chat.ts'), 'utf8');

describe('robotics chat tabs', () => {
  it('keeps both operator tabs and the turn contract', () => {
    expect(html).toContain('Chatbot IA');
    expect(html).toContain('Decir Oración');
    expect(html).toContain("activeTab.set('chatbot')");
    expect(html).toContain("activeTab.set('decir')");
    expect(ts).toContain('/chat/question');
    expect(ts).not.toContain('chatService.chat');
  });

  it('makes inactive tabs navy-on-card and active tabs cyan', () => {
    expect(html).toContain('min-h-11');
    expect(html).toMatch(/activeTab\(\) === 'chatbot'\s*\n\s*\? 'bg-primary text-on-primary/);
    expect(html).toMatch(/activeTab\(\) === 'decir'\s*\n\s*\? 'bg-primary text-on-primary/);
    expect(html).not.toMatch(/activeTab\(\) === 'chatbot'[\s\S]{0,80}bg-secondary/);
    const tabBlock = html.slice(0, html.indexOf('CHATBOT IA'));
    expect(tabBlock).not.toContain('text-slate-400');
    expect(tabBlock).not.toContain('border-white/5');
    expect(tabBlock).toContain('text-on-surface');
    expect(tabBlock).toContain('border-outline');
  });

  it('keeps Limpiar and Enviar readable', () => {
    expect(html).not.toMatch(/clearChat[\s\S]{0,400}text-\[10px\]/);
    expect(html).not.toMatch(/sendChat\(\)[\s\S]{0,500}text-slate-600/);
    expect(html).toMatch(/sendChat\(\)[\s\S]{0,400}bg-primary/);
  });
});
```

- [ ] **Step 2: Run it and confirm it fails**

```bash
cd pmas-web-main && npx vitest run src/app/pages/robotics-chat/robotics-chat.copy.spec.ts
```

Expected: FAIL (tabs still `text-slate-400` / chatbot active `bg-secondary`).

- [ ] **Step 3: Restyle the tab bar, Limpiar, and Enviar**

In `robotics-chat.html` replace the header block (from the tab bar comment through Limpiar) with:

```html
  <div class="flex flex-col gap-2 px-3 sm:px-4 py-3 border-b border-outline bg-surface flex-shrink-0">
    <div class="grid grid-cols-2 gap-2 w-full">
      <button
        type="button"
        (click)="activeTab.set('chatbot')"
        [class]="activeTab() === 'chatbot'
          ? 'bg-primary text-on-primary'
          : 'text-on-surface bg-surface hover:bg-surface-container-high'"
        class="flex items-center justify-center gap-1.5 min-h-11 sm:min-h-12 px-2 py-2.5 rounded-xl border border-outline
               font-headline font-bold text-sm tracking-tight transition-colors cursor-pointer">
        <span class="material-symbols-outlined shrink-0" style="font-size: 1.1rem; font-variation-settings: 'FILL' 1;">smart_toy</span>
        <span class="truncate">Chatbot IA</span>
      </button>
      <button
        type="button"
        (click)="activeTab.set('decir')"
        [class]="activeTab() === 'decir'
          ? 'bg-primary text-on-primary'
          : 'text-on-surface bg-surface hover:bg-surface-container-high'"
        class="flex items-center justify-center gap-1.5 min-h-11 sm:min-h-12 px-2 py-2.5 rounded-xl border border-outline
               font-headline font-bold text-sm tracking-tight transition-colors cursor-pointer">
        <span class="material-symbols-outlined shrink-0" style="font-size: 1.1rem; font-variation-settings: 'FILL' 1;">record_voice_over</span>
        <span class="truncate">Decir Oración</span>
      </button>
    </div>

    <div class="flex items-center justify-between gap-2 min-h-0">
      <div class="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-surface-container border border-outline text-xs">
        <span class="w-1.5 h-1.5 rounded-full bg-secondary shrink-0"></span>
        <span class="text-on-surface-variant">R-ONE en línea</span>
      </div>
      <div class="flex sm:flex-1 sm:justify-end">
        <button
          type="button"
          (click)="activeTab() === 'chatbot' ? clearChat() : clearDecir()"
          class="flex min-h-10 items-center gap-1.5 text-xs font-semibold text-on-surface-variant
                 hover:text-on-surface transition-colors cursor-pointer px-3 py-2 rounded-lg hover:bg-surface-container w-full sm:w-auto justify-center sm:justify-start">
          <span class="material-symbols-outlined" style="font-size: 0.9rem;">delete_sweep</span>
          <span>Limpiar</span>
        </button>
      </div>
    </div>
  </div>
```

Replace the Enviar button class binding (the `sendChat()` button, not Decir) so enabled is cyan and disabled is quiet ink:

```html
            <button
              (click)="sendChat()"
              [disabled]="chatBusy() || !chatInput().trim()"
              class="rounded-2xl flex items-center justify-center transition-colors
                     cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
              [class]="(chatBusy() || !chatInput().trim()
                ? 'bg-surface-container-highest'
                : 'bg-primary hover:opacity-90')
                + (compact() ? ' h-11 sm:w-12 sm:h-12' : ' h-14 w-14')">
              <span class="material-symbols-outlined"
                    [class]="chatBusy() || !chatInput().trim() ? 'text-on-surface-variant' : 'text-on-primary'"
                    style="font-size: 1.3rem; font-variation-settings: 'FILL' 1;">send</span>
            </button>
```

Bump the Enter hint under the composer from `text-[10px]` to `text-xs text-on-surface-variant`. Do not restyle message bubbles.

- [ ] **Step 4: Run chat + identity specs**

```bash
cd pmas-web-main && npx vitest run src/app/pages/robotics-chat/robotics-chat.copy.spec.ts src/styles.tokens.spec.ts src/app/pages/control-panel/control-panel.copy.spec.ts
```

Expected: PASS.

- [ ] **Step 5: Commit (pmas-web-main)**

```bash
cd pmas-web-main
git add src/app/pages/robotics-chat/robotics-chat.html src/app/pages/robotics-chat/robotics-chat.copy.spec.ts
git commit -m "$(cat <<'EOF'
Make Chatbot and Decir tabs readable on the cool paper.

Inactive tabs use navy ink; the active tab uses Prometeo cyan without hiding the other.
EOF
)"
```

---

### Task 5: Browser check

**Files:** none unless a class leftover fails the spec (then fix in the owning file from Tasks 2–4).

**Interfaces:**
- Consumes: Compose `pmas-web-main` on `:4200` with poll.
- Produces: evidence that login chrome is navy, Libre is emerald, both chat tabs read and switch.

- [ ] **Step 1: Confirm the app rebuilt**

If `docker compose up` is already running, wait for `pmas-web-main` “Application bundle generation complete”. Otherwise from the launcher root:

```bash
docker compose up -d pmas-web-main
```

- [ ] **Step 2: Login**

Open `http://localhost:4200/login`. Expected: left brand panel navy `#0B2540`, form on cool paper, no forest canvas. Sign in with the lab admin account, pick ADMIN.

- [ ] **Step 3: Control panel**

Open `http://localhost:4200/control-panel`. Expected: navy header and side/bottom nav; Estado Libre on pale emerald, not navy; layout unchanged (KPI strip, Ejecución, En hardware, Registro).

- [ ] **Step 4: Chat tabs**

Open Chat. Expected: both **Chatbot IA** and **Decir Oración** readable at rest; clicking each fills cyan and shows the matching pane. Send still posts to `/chat/question` (Network). Do not test OpenAI chat.

- [ ] **Step 5: If a leftover forest or slate class is visible on chrome/tabs, fix it and re-run the specs from Task 4. Commit that fix in `pmas-web-main` with a message that states why.**

---

## Self-review

| Spec requirement | Task |
|---|---|
| Navy chrome `#0B2540` / on `#eef2f6` | 2 (tokens; templates already `bg-rail`) |
| Canvas `#eef2f6`, card `#f7fafc`, no `#ffffff` | 1 + 2 |
| Quiet ink `#3d5a73` | 1 + 2 |
| Emerald only Libre/Neutro/ok; Libre not `bg-rail` | 3 |
| Chat tabs visible, both active cyan, no slate on tabs | 4 |
| Enviar cyan; Limpiar ≥ 12px | 4 |
| PRODUCT.md / DESIGN.md, no guide-folder brand | 1 |
| Turn contract untouched | 4 asserts `/chat/question`; 5 Network |
| Studio / auth / vision out of scope | no tasks edit those repos |
| Browser: login, panel Libre, chat tabs | 5 |
