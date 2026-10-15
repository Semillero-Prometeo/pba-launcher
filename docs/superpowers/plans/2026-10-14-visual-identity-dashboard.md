# Light dashboard identity and flagship control panel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give R-ONE a light operational identity (`PRODUCT.md` + `DESIGN.md` at the launcher root) and restyle the logged-in chrome plus the control panel into a Spanish operator dashboard with four real KPIs.

**Architecture:** New CSS tokens in `pmas-web-main` paint the shell and every page that already uses `bg-background` / `text-on-surface`. The control panel is the only page whose layout is rewritten. KPI values come from a pure helper over runtime, catalog, and logs — never invented telemetry. Motion studio, auth, robotics, gateway, and mai-core are not edited.

**Tech Stack:** Markdown at launcher root; Angular 21, Tailwind v4 `@theme`, Vitest (`npx vitest run`).

## Global Constraints

- Spec: `docs/superpowers/specs/2026-10-14-visual-identity-dashboard-design.md`. Neutro/runtime spec still governs Normal/Neutro, `busy`, En hardware, and poll 500 ms / 3 s.
- `PRODUCT.md` and `DESIGN.md` live at the **launcher root**, not inside `pmas-web-main`.
- Primary accent stays `#38bdf8`. Secondary stays `#10b981`. Do not copy Davivienda red / oklch from `example/`.
- Background `#f4f7fb`, cards `#ffffff`, text `#0f172a`. Cyan is for chips, borders, icons, `primary/10` fills — not long titles.
- Spanish operator copy. No `System Override`, `0x4F22-ALPHA`, fake Uptime/Signal, `Execution Log`, `Control Panel`, or `Search parameters...`.
- Do not change the turn, `getActions`, `executeAction`, sequence JSON, gateway play/runtime, or `pmas-web-motion-studio`.
- Do not redesign vision, chat, users, roles, management, sequences iframe, profile, or public layouts. Token inheritance is enough.
- Work on top of `feat/sequence-neutro-runtime`. Do not revert pair playback.
- Commits for Angular go in `pmas-web-main`. `PRODUCT.md`, `DESIGN.md`, and this plan commit in the launcher.
- `.industrial-grid` is restyled to faint light dots, not deleted.

---

## File structure

| File | Responsibility |
|---|---|
| `PRODUCT.md` | Product truth (users, purpose, principles). No pixels. |
| `DESIGN.md` | Visual world, tokens, named rules. |
| `pmas-web-main/src/styles.css` | Light `@theme` tokens + restyled `.industrial-grid`. |
| `pmas-web-main/src/index.html` | `lang="es"`, no `class="dark"`. |
| `pmas-web-main/src/app/layouts/admin-shell/` | Drawer overlay and search flag. |
| `pmas-web-main/src/app/components/navbar/` | Light bar, **Panel**, no fake search. |
| `pmas-web-main/src/app/components/sidebar/` | Light docked/drawer nav. |
| `pmas-web-main/src/app/components/footer/` | Light internal footer. |
| `pmas-web-main/src/app/components/health-status-dropdown/` | Light service dropdown. |
| `pmas-web-main/src/app/components/robotics-bottom-nav/` | Light compact nav. |
| `pmas-web-main/src/app/pages/control-panel/panel-kpis.ts` | Pure KPI mapping. |
| `pmas-web-main/src/app/pages/control-panel/control-panel.ts` | Drop fake telemetry; expose `kpis()`. |
| `pmas-web-main/src/app/pages/control-panel/control-panel.html` | Dashboard layout. |

---

### Task 1: PRODUCT.md and DESIGN.md at the launcher root

**Files:**
- Create: `PRODUCT.md`
- Create: `DESIGN.md`

**Interfaces:**
- Consumes: spec sections Documentos de identidad, Paleta y tokens, named rules.
- Produces: launcher-root `PRODUCT.md` (product truth) and `DESIGN.md` (visual world with `#38bdf8`, no Davivienda). Later tasks do not import these files; they exist for humans and Impeccable.

- [ ] **Step 1: Confirm the files are missing**

Run from the launcher root:

```bash
test ! -f PRODUCT.md && test ! -f DESIGN.md && echo MISSING
```

Expected: `MISSING`

- [ ] **Step 2: Write PRODUCT.md**

Create `PRODUCT.md` at the launcher root with exactly this content:

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
```

- [ ] **Step 3: Write DESIGN.md**

Create `DESIGN.md` at the launcher root with exactly this content:

```markdown
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
```

- [ ] **Step 4: Verify identity files**

Run from the launcher root:

```bash
test -f PRODUCT.md && test -f DESIGN.md
grep -q "semillero Prometeo" PRODUCT.md
grep -q "Mesa de control de R-ONE" DESIGN.md
grep -q "#38bdf8" DESIGN.md
grep -q "oklch(0.577" PRODUCT.md DESIGN.md && echo FAIL_RED || echo OK_PALETTE
grep -qi "portal-web-dav" PRODUCT.md DESIGN.md && echo FAIL_SICV || echo OK_BRAND
```

Expected: files exist; heading greps succeed; last two lines `OK_PALETTE` and `OK_BRAND` (no Davivienda oklch / portal-web-dav copied as brand).

- [ ] **Step 5: Commit (launcher)**

```bash
git add PRODUCT.md DESIGN.md
git commit -m "Document R-ONE product truth and the light dashboard visual world."
```

---

### Task 2: Light CSS tokens and industrial grid

**Files:**
- Modify: `pmas-web-main/src/styles.css`
- Modify: `pmas-web-main/src/index.html`
- Create: `pmas-web-main/src/styles.tokens.spec.ts`

**Interfaces:**
- Consumes: token table in the spec.
- Produces: `@theme` light tokens listed below; `.industrial-grid` faint `#cbd5e1` dots; `<html lang="es">` without `class="dark"`.

- [ ] **Step 1: Write the failing test**

Create `pmas-web-main/src/styles.tokens.spec.ts`:

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

describe('light dashboard tokens', () => {
  it('uses the approved light surfaces and ink', () => {
    expect(token('--color-background')).toBe('#f4f7fb');
    expect(token('--color-surface')).toBe('#ffffff');
    expect(token('--color-surface-container')).toBe('#ffffff');
    expect(token('--color-surface-container-high')).toBe('#eef2f6');
    expect(token('--color-on-surface')).toBe('#0f172a');
    expect(token('--color-on-surface-variant')).toBe('#475569');
    expect(token('--color-outline')).toBe('#cbd5e1');
  });

  it('keeps Prometeo cyan and emerald and uses a light error', () => {
    expect(token('--color-primary')).toBe('#38bdf8');
    expect(token('--color-secondary')).toBe('#10b981');
    expect(token('--color-error')).toBe('#dc2626');
    expect(token('--color-error-container')).toBe('#fee2e2');
    expect(token('--color-primary-container')).toBe('#e0f2fe');
    expect(css).not.toMatch(/--color-error-container:\s*#93000a/);
    expect(css).not.toMatch(/--color-background:\s*#000f1d/);
  });

  it('restyles industrial-grid to faint light dots', () => {
    expect(css).toMatch(/\.industrial-grid\s*\{[^}]*#cbd5e1/s);
    expect(css).not.toMatch(/\.industrial-grid\s*\{[^}]*#43474f/s);
  });

  it('drops the html dark class', () => {
    expect(html).toMatch(/<html lang="es">/);
    expect(html).not.toMatch(/class="dark"/);
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
cd pmas-web-main && npx vitest run src/styles.tokens.spec.ts
```

Expected: FAIL (`#000f1d` or missing `#f4f7fb`, and `class="dark"` still present).

- [ ] **Step 3: Replace `@theme` and `.industrial-grid`; fix index.html**

Replace the `@theme { ... }` block in `pmas-web-main/src/styles.css` with:

```css
@theme {
  --color-background: #f4f7fb;
  --color-surface: #ffffff;
  --color-surface-dim: #eef2f6;
  --color-surface-bright: #ffffff;
  --color-surface-container-lowest: #f4f7fb;
  --color-surface-container-low: #f8fafc;
  --color-surface-container: #ffffff;
  --color-surface-container-high: #eef2f6;
  --color-surface-container-highest: #e2e8f0;
  --color-surface-variant: #e2e8f0;
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

  --color-secondary: #10b981;
  --color-secondary-fixed: #d1fae5;
  --color-secondary-fixed-dim: #10b981;
  --color-secondary-container: #d1fae5;
  --color-on-secondary: #064e3b;
  --color-on-secondary-fixed: #064e3b;
  --color-on-secondary-fixed-variant: #047857;
  --color-on-secondary-container: #064e3b;

  --color-tertiary: #059669;
  --color-tertiary-fixed: #d1fae5;
  --color-tertiary-fixed-dim: #34d399;
  --color-tertiary-container: #d1fae5;
  --color-on-tertiary: #064e3b;
  --color-on-tertiary-fixed: #064e3b;
  --color-on-tertiary-fixed-variant: #047857;
  --color-on-tertiary-container: #064e3b;

  --color-error: #dc2626;
  --color-error-container: #fee2e2;
  --color-on-error: #ffffff;
  --color-on-error-container: #7f1d1d;

  --color-outline: #cbd5e1;
  --color-outline-variant: #e2e8f0;
  --color-on-surface: #0f172a;
  --color-on-surface-variant: #475569;
  --color-on-background: #0f172a;
  --color-inverse-surface: #0f172a;
  --color-inverse-on-surface: #f8fafc;

  --font-headline: 'Space Grotesk', sans-serif;
  --font-body: 'Inter', sans-serif;
  --font-label: 'Inter', sans-serif;

  --radius-DEFAULT: 0.375rem;
  --radius-lg: 0.5rem;
  --radius-xl: 0.75rem;
  --radius-full: 0.75rem;
}
```

Replace `.industrial-grid` with:

```css
.industrial-grid {
  background-image: radial-gradient(circle, #cbd5e1 1px, transparent 1px);
  background-size: 24px 24px;
}
```

In `pmas-web-main/src/index.html` change the root element to:

```html
<html lang="es">
```

Do not leave `class="dark"`.

- [ ] **Step 4: Run the test to verify it passes**

Run:

```bash
cd pmas-web-main && npx vitest run src/styles.tokens.spec.ts
```

Expected: PASS

- [ ] **Step 5: Commit (pmas-web-main)**

```bash
cd pmas-web-main
git add src/styles.css src/index.html src/styles.tokens.spec.ts
git commit -m "Switch Angular tokens to the light Prometeo dashboard palette."
```

---

### Task 3: Light admin chrome (navbar, sidebar, drawer, footer, health, compact nav)

**Files:**
- Modify: `pmas-web-main/src/app/components/navbar/navbar.html`
- Modify: `pmas-web-main/src/app/layouts/admin-shell/admin-shell.html`
- Modify: `pmas-web-main/src/app/layouts/admin-shell/admin-shell.ts`
- Modify: `pmas-web-main/src/app/components/sidebar/sidebar.html`
- Modify: `pmas-web-main/src/app/components/footer/footer.html`
- Modify: `pmas-web-main/src/app/components/health-status-dropdown/health-status-dropdown.html`
- Modify: `pmas-web-main/src/app/components/robotics-bottom-nav/robotics-bottom-nav.html`
- Create: `pmas-web-main/src/app/layouts/admin-shell/shell-copy.spec.ts`

**Interfaces:**
- Consumes: light tokens from Task 2.
- Produces: chrome without `slate-950` / `#000f1d`; navbar label **Panel**; no Search parameters input; `showSearchForRoute()` always `false`; health dropdown default title (sidebar stops passing `Health checks`).

- [ ] **Step 1: Write the failing test**

Create `pmas-web-main/src/app/layouts/admin-shell/shell-copy.spec.ts`:

```typescript
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const here = import.meta.dirname;

function read(rel: string): string {
  return readFileSync(resolve(here, rel), 'utf8');
}

describe('admin chrome copy and light surfaces', () => {
  const navbar = read('../../components/navbar/navbar.html');
  const sidebar = read('../../components/sidebar/sidebar.html');
  const shell = read('admin-shell.html');
  const shellTs = read('admin-shell.ts');
  const footer = read('../../components/footer/footer.html');
  const health = read('../../components/health-status-dropdown/health-status-dropdown.html');
  const bottom = read('../../components/robotics-bottom-nav/robotics-bottom-nav.html');

  it('uses Panel and drops theater search', () => {
    expect(navbar).toMatch(/>\s*Panel\s*</);
    expect(navbar).not.toContain('Control Panel');
    expect(navbar).not.toContain('Search parameters');
    expect(shellTs).toMatch(/showSearchForRoute\(\)[^{]*\{\s*return false;/);
  });

  it('does not paint the chrome night-industrial', () => {
    for (const file of [navbar, sidebar, shell, footer, bottom]) {
      expect(file).not.toContain('slate-950');
      expect(file).not.toContain('#000f1d');
      expect(file).not.toContain('bg-black/60');
    }
  });

  it('keeps health and footer in operator Spanish', () => {
    expect(sidebar).not.toContain('Health checks');
    expect(health).toContain('border-outline');
    expect(footer).not.toContain('Unit Status: Nominal');
    expect(footer).not.toContain('bg-slate-950');
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
cd pmas-web-main && npx vitest run src/app/layouts/admin-shell/shell-copy.spec.ts
```

Expected: FAIL (`Control Panel` / `slate-950` still present).

- [ ] **Step 3: Apply chrome edits**

In `pmas-web-main/src/app/layouts/admin-shell/admin-shell.ts` replace `showSearchForRoute` with:

```typescript
  showSearchForRoute(): boolean {
    return false;
  }
```

In `pmas-web-main/src/app/components/navbar/navbar.html`:

1. Change the `<nav>` class from `bg-surface/60 backdrop-blur-xl` to `bg-surface border-b border-outline`.
2. Change the Prometeo wordmark from `text-blue-400` to `text-on-surface`.
3. Replace the authenticated (non-fullSite) desktop link text `Control Panel` with `Panel`.
4. Replace the authenticated mobile link text `Control Panel` with `Panel`.
5. Delete the entire `@if (showSearch && auth.isAuthenticated()) { ... }` search block (the `Search parameters...` input).
6. Replace remaining `text-slate-500` in this file with `text-on-surface-variant`.
7. Replace `shadow-2xl` on the profile dropdown with `shadow-sm`.

In `pmas-web-main/src/app/layouts/admin-shell/admin-shell.html` replace the drawer overlay and panel classes:

```html
    <div class="absolute inset-0 bg-on-surface/20" (click)="closeDrawer()"></div>
    <div
      class="relative z-10 flex flex-col w-[min(22rem,92vw)] max-w-full h-full bg-surface border-r border-outline shadow-sm">
      <div class="flex items-center justify-between px-3 py-3 border-b border-outline shrink-0">
        <span class="font-label text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">Navegación</span>
        <button
          type="button"
          (click)="closeDrawer()"
          class="p-2 rounded-lg text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high cursor-pointer"
          aria-label="Cerrar menú">
```

Replace the whole `pmas-web-main/src/app/components/sidebar/sidebar.html` with:

```html
<aside
  class="flex-col border-r border-outline bg-surface py-4 z-40 overflow-y-auto transition-[width] duration-200 ease-out"
  [class.hidden]="variant === 'docked'"
  [class.md:flex]="variant === 'docked'"
  [class.flex]="variant === 'drawer'"
  [class.fixed]="variant === 'docked'"
  [class.left-0]="variant === 'docked'"
  [class.top-16]="variant === 'docked'"
  [class.h-\[calc\(100vh-64px\)\]]="variant === 'docked'"
  [class.relative]="variant === 'drawer'"
  [class.h-full]="variant === 'drawer'"
  [class.min-h-0]="variant === 'drawer'"
  [class.w-full]="variant === 'drawer'"
  [class.w-64]="variant === 'docked' && expandedUi()"
  [class.w-\[4.5rem\]]="variant === 'docked' && !expandedUi()">

  @if (variant === 'docked') {
    <div class="px-2 mb-3 flex justify-end">
      <button
        type="button"
        (click)="chrome.toggleSidebarCollapsed()"
        class="p-2 rounded-lg text-on-surface-variant hover:text-secondary hover:bg-surface-container-high transition-colors cursor-pointer"
        [attr.aria-label]="chrome.sidebarCollapsed() ? 'Expandir menú' : 'Contraer menú'">
        <span class="material-symbols-outlined" style="font-size: 1.1rem;">
          {{ chrome.sidebarCollapsed() ? 'chevron_right' : 'chevron_left' }}
        </span>
      </button>
    </div>
  }

  <div class="px-4 mb-4" [class.px-2]="variant === 'docked' && !expandedUi()" [class.text-center]="variant === 'docked' && !expandedUi()">
    @if (expandedUi()) {
      <div class="flex items-center gap-3 mb-1">
        <div class="w-2 h-2 rounded-full bg-secondary shrink-0"></div>
        <h2 class="text-on-surface font-black font-label text-xs uppercase tracking-[0.1em] leading-tight">
          Panel de Administración
        </h2>
      </div>
      <p class="text-on-surface-variant text-[10px] uppercase font-bold tracking-widest">Prometeo · R-ONE</p>
    } @else {
      <div class="flex justify-center">
        <div class="w-2 h-2 rounded-full bg-secondary"></div>
      </div>
    }
  </div>

  <div class="px-3 mb-4" [class.px-2]="variant === 'docked' && !expandedUi()">
    <app-health-status-dropdown title="Estado de servicios"></app-health-status-dropdown>
  </div>

  <nav class="flex-1 space-y-1 px-2 min-h-0">
    @for (group of groups; track group.id) {
      <button
        type="button"
        (click)="toggleGroup(group.id)"
        [class.px-2]="variant === 'docked' && !expandedUi()"
        class="w-full flex items-center justify-between px-2 py-2 rounded-lg text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high transition-all duration-200 cursor-pointer">
        <div class="flex items-center gap-2 min-w-0" [class.justify-center]="variant === 'docked' && !expandedUi()" [class.w-full]="variant === 'docked' && !expandedUi()">
          <span class="material-symbols-outlined shrink-0" style="font-size: 1rem; font-variation-settings: 'FILL' 1;">
            {{ group.icon }}
          </span>
          @if (expandedUi()) {
            <span class="font-label text-[10px] font-bold uppercase tracking-[0.15em] truncate">{{ group.label }}</span>
            <div class="w-1.5 h-1.5 rounded-full shrink-0" [class]="statusColor(groupStatus(group))"></div>
          }
        </div>
        @if (expandedUi()) {
          <span class="material-symbols-outlined text-outline transition-transform duration-200 shrink-0"
                style="font-size: 0.9rem;"
                [class.rotate-180]="isGroupOpen(group.id)">
            expand_more
          </span>
        }
      </button>

      @if (isGroupOpen(group.id) && expandedUi()) {
        <div class="ml-2 border-l border-outline pl-2 space-y-0.5 pb-1">
          @for (item of group.items; track item.id) {
            <a [routerLink]="item.route"
               [queryParams]="item.queryParams ?? {}"
               [class]="activeItem === item.id
                 ? 'bg-primary/10 text-on-surface border-l-2 border-primary -ml-px'
                 : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high'"
               class="px-3 py-2.5 flex items-center gap-3 rounded-r-lg transition-colors no-underline">
              <span class="material-symbols-outlined" style="font-size: 0.95rem;">{{ item.icon }}</span>
              <span class="font-label text-[10px] font-bold uppercase tracking-[0.1em]">{{ item.label }}</span>
            </a>
          }
        </div>
      }

      @if (variant === 'docked' && !expandedUi() && isGroupOpen(group.id)) {
        <div class="flex flex-col items-center gap-1 pb-2">
          @for (item of group.items; track item.id) {
            <a [routerLink]="item.route"
               [queryParams]="item.queryParams ?? {}"
               [title]="item.label"
               [class]="activeItem === item.id ? 'text-on-surface bg-primary/10' : 'text-on-surface-variant hover:text-on-surface'"
               class="p-2.5 rounded-lg transition-colors no-underline">
              <span class="material-symbols-outlined" style="font-size: 1rem;">{{ item.icon }}</span>
            </a>
          }
        </div>
      }
    }
  </nav>

  <div class="px-2 mt-3 shrink-0">
    <button
      type="button"
      (click)="health.checkAll()"
      [class.px-2]="variant === 'docked' && !expandedUi()"
      class="w-full flex items-center justify-center gap-2 py-2 rounded-lg text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high transition-colors text-[10px] font-label uppercase tracking-wider cursor-pointer border border-outline">
      <span class="material-symbols-outlined" style="font-size: 0.85rem;">refresh</span>
      @if (expandedUi()) {
        <span>Actualizar estado</span>
      }
    </button>
  </div>
</aside>
```

Replace `pmas-web-main/src/app/components/health-status-dropdown/health-status-dropdown.html` with:

```html
<details class="rounded-xl border border-outline bg-surface-container overflow-hidden">
  <summary class="list-none cursor-pointer px-3 py-2.5 bg-surface-container-high border-b border-outline">
    <div class="flex items-center justify-between gap-2">
      <div class="flex items-center gap-2 min-w-0">
        <span class="material-symbols-outlined text-secondary" style="font-size: 1rem;">monitor_heart</span>
        <span class="font-label uppercase tracking-wider text-[10px] text-on-surface-variant truncate">{{ title }}</span>
      </div>
      <span class="text-[10px] text-on-surface-variant">{{ onlineCount() }}/{{ entries().length }} en línea</span>
    </div>
  </summary>

  <div class="p-2.5 space-y-1.5">
    @for (item of entries(); track item.label) {
      <div class="rounded-lg border border-outline bg-surface-container-low px-2.5 py-2 flex items-center justify-between gap-2">
        <div class="flex items-center gap-2 min-w-0">
          <span class="w-1.5 h-1.5 rounded-full flex-shrink-0" [class]="statusDot(item.status)"></span>
          <span class="text-[10px] font-label uppercase tracking-wide text-on-surface truncate">{{ item.label }}</span>
        </div>
        <span class="text-[9px] text-on-surface-variant">{{ statusText(item.status) }}</span>
      </div>
    }
    <button
      type="button"
      (click)="health.checkAll()"
      class="w-full mt-1 px-3 py-2 rounded-lg text-[10px] font-label uppercase tracking-wider
             bg-surface-container-high text-on-surface hover:bg-surface-container-highest
             transition-colors cursor-pointer">
      Actualizar estado
    </button>
  </div>
</details>
```

Replace `pmas-web-main/src/app/components/footer/footer.html` with:

```html
<footer class="w-full border-t border-outline bg-surface flex flex-col sm:flex-row justify-between items-center gap-6 px-6 md:px-12 py-6 md:py-8">
  <div class="flex flex-col gap-2">
    <p class="font-label text-[10px] uppercase tracking-widest text-on-surface-variant">
      &copy; 2026 Prometeo Universidad Libre.
    </p>
  </div>

  <div class="flex gap-6 items-center">
    <div class="flex -space-x-2">
      <div class="w-6 h-6 rounded-full bg-primary/20 border border-primary/30 flex items-center justify-center">
        <span class="material-symbols-outlined text-primary" style="font-size: 12px;">science</span>
      </div>
      <div class="w-6 h-6 rounded-full bg-secondary/20 border border-secondary/30 flex items-center justify-center">
        <span class="material-symbols-outlined text-secondary" style="font-size: 12px;">memory</span>
      </div>
      <div class="w-6 h-6 rounded-full bg-tertiary/20 border border-tertiary/30 flex items-center justify-center">
        <span class="material-symbols-outlined text-tertiary" style="font-size: 12px;">precision_manufacturing</span>
      </div>
    </div>
    <span class="text-[10px] font-label uppercase tracking-[0.3em] text-on-surface-variant">R-ONE</span>
  </div>
</footer>
```

Replace the `<nav>` classes in `pmas-web-main/src/app/components/robotics-bottom-nav/robotics-bottom-nav.html` so the night fills are gone:

```html
<nav
  class="fixed bottom-0 left-0 right-0 z-50
         flex flex-row justify-around items-center gap-1 px-2 py-2
         border-t border-outline bg-surface
         pb-[max(0.5rem,env(safe-area-inset-bottom))]
         md:right-auto md:top-16 md:bottom-0 md:w-16
         md:flex-col md:justify-start md:items-center md:gap-1
         md:py-4 md:px-0
         md:border-t-0 md:border-r md:border-outline"
  aria-label="Navegación robótica">
  @for (link of links; track link.route) {
    <a
      [routerLink]="link.route"
      routerLinkActive="text-on-surface bg-primary/10"
      [routerLinkActiveOptions]="{ exact: true }"
      class="flex flex-col items-center justify-center min-w-0 flex-1 py-2 rounded-lg text-on-surface-variant
             hover:text-on-surface hover:bg-surface-container-high transition-colors no-underline max-w-[5rem]
             md:flex-none md:w-12 md:h-12 md:py-0 md:rounded-xl md:max-w-none">
      <span class="material-symbols-outlined" style="font-size: 1.35rem; font-variation-settings: 'FILL' 1;">
        {{ link.icon }}
      </span>
      <span class="font-label text-[8px] font-bold uppercase tracking-wide mt-0.5 truncate w-full text-center
                   md:hidden">
        {{ link.label }}
      </span>
    </a>
  }
</nav>
```

Do not change sidebar routes or group ids.

- [ ] **Step 4: Run the test to verify it passes**

Run:

```bash
cd pmas-web-main && npx vitest run src/app/layouts/admin-shell/shell-copy.spec.ts
```

Expected: PASS

- [ ] **Step 5: Commit (pmas-web-main)**

```bash
cd pmas-web-main
git add src/app/components/navbar/navbar.html \
  src/app/layouts/admin-shell/admin-shell.html \
  src/app/layouts/admin-shell/admin-shell.ts \
  src/app/layouts/admin-shell/shell-copy.spec.ts \
  src/app/components/sidebar/sidebar.html \
  src/app/components/footer/footer.html \
  src/app/components/health-status-dropdown/health-status-dropdown.html \
  src/app/components/robotics-bottom-nav/robotics-bottom-nav.html
git commit -m "Restyle the logged-in chrome as a light Spanish operator shell."
```

---

### Task 4: Pure KPI helper (no fake telemetry)

**Files:**
- Create: `pmas-web-main/src/app/pages/control-panel/panel-kpis.ts`
- Create: `pmas-web-main/src/app/pages/control-panel/panel-kpis.spec.ts`

**Interfaces:**
- Consumes: `RuntimeSnapshot` fields `busy` and `source`; unfiltered catalog count; newest log `{ timestamp, sequenceName }`.
- Produces:

```typescript
export type RuntimeSource = 'turno' | 'panel' | 'estudio' | null;

export interface PanelKpiInput {
  runtimeUnreachable: boolean;
  busy: boolean;
  source: RuntimeSource;
  sequenceLoading: boolean;
  sequenceError: string | null;
  sequenceCount: number;
  lastLog: { timestamp: string; sequenceName: string } | null;
}

export interface PanelKpis {
  estado: 'ocupado' | 'libre' | 'sin estado';
  origen: 'estudio' | 'panel' | 'turno' | '—';
  secuencias: string;
  ultimoEvento: string;
}

export function catalogSequenceCount(groups: { sequences: unknown[] }[]): number;
export function panelKpis(input: PanelKpiInput): PanelKpis;
```

`catalogSequenceCount` sums `groups[i].sequences.length` (the six category groups, **not** the search-filtered view). `secuencias` is `String(count)` or `'—'` while loading or on list error. `ultimoEvento` is `` `${timestamp} · ${sequenceName}` `` or `'—'`.

- [ ] **Step 1: Write the failing tests**

Create `pmas-web-main/src/app/pages/control-panel/panel-kpis.spec.ts`:

```typescript
import { describe, expect, it } from 'vitest';
import { catalogSequenceCount, panelKpis, PanelKpiInput } from './panel-kpis';

const base: PanelKpiInput = {
  runtimeUnreachable: false,
  busy: false,
  source: null,
  sequenceLoading: false,
  sequenceError: null,
  sequenceCount: 4,
  lastLog: null,
};

describe('panelKpis', () => {
  it('shows idle values', () => {
    expect(panelKpis(base)).toEqual({
      estado: 'libre',
      origen: '—',
      secuencias: '4',
      ultimoEvento: '—',
    });
  });

  it('shows busy source from runtime', () => {
    expect(
      panelKpis({ ...base, busy: true, source: 'turno' }),
    ).toEqual({
      estado: 'ocupado',
      origen: 'turno',
      secuencias: '4',
      ultimoEvento: '—',
    });
  });

  it('shows sin estado when runtime is down', () => {
    expect(
      panelKpis({ ...base, runtimeUnreachable: true, busy: true, source: 'panel' }),
    ).toEqual({
      estado: 'sin estado',
      origen: '—',
      secuencias: '4',
      ultimoEvento: '—',
    });
  });

  it('hides the count while loading or on error', () => {
    expect(panelKpis({ ...base, sequenceLoading: true }).secuencias).toBe('—');
    expect(panelKpis({ ...base, sequenceError: 'falló' }).secuencias).toBe('—');
  });

  it('formats the newest log as last event', () => {
    expect(
      panelKpis({
        ...base,
        lastLog: { timestamp: '18:01:02', sequenceName: 'saludo normal' },
      }).ultimoEvento,
    ).toBe('18:01:02 · saludo normal');
  });
});

describe('catalogSequenceCount', () => {
  it('sums every category group and ignores later UI filters', () => {
    expect(
      catalogSequenceCount([
        { sequences: [{}, {}] },
        { sequences: [] },
        { sequences: [{}] },
      ]),
    ).toBe(3);
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
cd pmas-web-main && npx vitest run src/app/pages/control-panel/panel-kpis.spec.ts
```

Expected: FAIL (`Cannot find module './panel-kpis'`).

- [ ] **Step 3: Write the helper**

Create `pmas-web-main/src/app/pages/control-panel/panel-kpis.ts`:

```typescript
export type RuntimeSource = 'turno' | 'panel' | 'estudio' | null;

export interface PanelKpiInput {
  runtimeUnreachable: boolean;
  busy: boolean;
  source: RuntimeSource;
  sequenceLoading: boolean;
  sequenceError: string | null;
  sequenceCount: number;
  lastLog: { timestamp: string; sequenceName: string } | null;
}

export interface PanelKpis {
  estado: 'ocupado' | 'libre' | 'sin estado';
  origen: 'estudio' | 'panel' | 'turno' | '—';
  secuencias: string;
  ultimoEvento: string;
}

export function catalogSequenceCount(groups: { sequences: unknown[] }[]): number {
  return groups.reduce((total, group) => total + group.sequences.length, 0);
}

export function panelKpis(input: PanelKpiInput): PanelKpis {
  const estado: PanelKpis['estado'] = input.runtimeUnreachable
    ? 'sin estado'
    : input.busy
      ? 'ocupado'
      : 'libre';
  const origen: PanelKpis['origen'] = input.runtimeUnreachable
    ? '—'
    : input.source ?? '—';
  const secuencias =
    input.sequenceLoading || input.sequenceError ? '—' : String(input.sequenceCount);
  const ultimoEvento = input.lastLog
    ? `${input.lastLog.timestamp} · ${input.lastLog.sequenceName}`
    : '—';
  return { estado, origen, secuencias, ultimoEvento };
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run:

```bash
cd pmas-web-main && npx vitest run src/app/pages/control-panel/panel-kpis.spec.ts
```

Expected: PASS

- [ ] **Step 5: Commit (pmas-web-main)**

```bash
cd pmas-web-main
git add src/app/pages/control-panel/panel-kpis.ts src/app/pages/control-panel/panel-kpis.spec.ts
git commit -m "Map control-panel KPIs from runtime, catalog, and logs."
```

---

### Task 5: Flagship control-panel dashboard

**Files:**
- Modify: `pmas-web-main/src/app/pages/control-panel/control-panel.ts`
- Modify: `pmas-web-main/src/app/pages/control-panel/control-panel.html`
- Create: `pmas-web-main/src/app/pages/control-panel/control-panel.copy.spec.ts`

**Interfaces:**
- Consumes: `panelKpis` and `catalogSequenceCount` from Task 4; existing `runtime()`, `playLocked()`, `executePhase`, `stopHardware`, `filteredSequenceGroups()`, poll.
- Produces: header **Panel de control**; four KPI cards bound to `kpis()`; **Registro**; no fake telemetry signals (`uptime`, `cpuLoad`, `memAlloc`, `temperature`, `velocity` deleted); Normal/Neutro still `[disabled]="playLocked()"`; Detener never disabled; no `shadow-xl`, no `border-white/`, no `slate-950`.

- [ ] **Step 1: Write the failing copy test**

Create `pmas-web-main/src/app/pages/control-panel/control-panel.copy.spec.ts`:

```typescript
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const html = readFileSync(resolve(import.meta.dirname, 'control-panel.html'), 'utf8');
const ts = readFileSync(resolve(import.meta.dirname, 'control-panel.ts'), 'utf8');

describe('control panel dashboard copy', () => {
  it('is a Spanish operator dashboard', () => {
    expect(html).toContain('Panel de control');
    expect(html).toContain('Registro');
    expect(html).toContain('En hardware');
    expect(html).toContain('kpis().estado');
    expect(html).toContain('kpis().origen');
    expect(html).toContain('kpis().secuencias');
    expect(html).toContain('kpis().ultimoEvento');
    expect(html).not.toContain('System Override');
    expect(html).not.toContain('0x4F22-ALPHA');
    expect(html).not.toContain('Robotic Control');
    expect(html).not.toContain('Execution Log');
    expect(html).not.toContain('Uptime');
    expect(html).not.toContain('Signal');
  });

  it('keeps the busy lock and always offers Detener', () => {
    expect(html).toMatch(/executePhase\(sequence\.name, 'normal'\)[\s\S]*\[disabled\]="playLocked\(\)"/);
    expect(html).toMatch(/executePhase\(sequence\.name, 'neutro'\)[\s\S]*\[disabled\]="playLocked\(\)"/);
    expect(html).toContain('stopHardware()');
    expect(html).not.toMatch(/stopHardware\(\)"[\s\S]*disabled/);
  });

  it('drops invented telemetry and night cards', () => {
    expect(ts).not.toContain('uptime = signal');
    expect(ts).not.toContain('cpuLoad');
    expect(ts).toContain('panelKpis');
    expect(html).not.toContain('shadow-xl');
    expect(html).not.toContain('border-white/');
    expect(html).not.toContain('slate-950');
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
cd pmas-web-main && npx vitest run src/app/pages/control-panel/control-panel.copy.spec.ts
```

Expected: FAIL (`System Override` still in the template).

- [ ] **Step 3: Wire KPIs in control-panel.ts**

Add this import next to the `sequence-groups` import:

```typescript
import { catalogSequenceCount, panelKpis } from './panel-kpis';
```

Delete these four (five) fake signals:

```typescript
  uptime = signal('14:02:55');
  cpuLoad = signal(64);
  memAlloc = signal(30);
  temperature = signal(42);
  velocity = signal(0.85);
```

After `playLocked`, add:

```typescript
  sequenceCount = computed(() => catalogSequenceCount(this.sequenceGroups()));
  kpis = computed(() =>
    panelKpis({
      runtimeUnreachable: this.runtimeUnreachable(),
      busy: this.runtime().busy,
      source: this.runtime().source,
      sequenceLoading: this.sequenceLoading(),
      sequenceError: this.sequenceError(),
      sequenceCount: this.sequenceCount(),
      lastLog: this.commandLogs()[0] ?? null,
    }),
  );
```

Do not change `executePhase`, `stopHardware`, `pollRuntime`, `playLocked`, or `filteredSequenceGroups`.

- [ ] **Step 4: Replace control-panel.html**

Replace the entire file `pmas-web-main/src/app/pages/control-panel/control-panel.html` with:

```html
<div class="industrial-grid min-h-[calc(100vh-6rem)]">

  <header class="mb-6">
    <h1 class="font-headline text-xl md:text-3xl font-bold tracking-tight text-on-surface">
      Panel de control
    </h1>
  </header>

  <section class="mb-6 grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3">
    <article class="rounded-xl border border-outline bg-surface p-4">
      <div class="flex items-center gap-2 mb-1">
        <span class="material-symbols-outlined text-primary" style="font-size: 1.1rem;">sensors</span>
        <p class="text-[10px] font-label uppercase tracking-wider text-on-surface-variant">Estado</p>
      </div>
      <p class="font-headline text-lg font-bold text-on-surface">{{ kpis().estado }}</p>
    </article>
    <article class="rounded-xl border border-outline bg-surface p-4">
      <div class="flex items-center gap-2 mb-1">
        <span class="material-symbols-outlined text-primary" style="font-size: 1.1rem;">origin</span>
        <p class="text-[10px] font-label uppercase tracking-wider text-on-surface-variant">Origen</p>
      </div>
      <p class="font-headline text-lg font-bold text-on-surface">{{ kpis().origen }}</p>
    </article>
    <article class="rounded-xl border border-outline bg-surface p-4">
      <div class="flex items-center gap-2 mb-1">
        <span class="material-symbols-outlined text-primary" style="font-size: 1.1rem;">animation</span>
        <p class="text-[10px] font-label uppercase tracking-wider text-on-surface-variant">Secuencias</p>
      </div>
      <p class="font-headline text-lg font-bold text-on-surface">{{ kpis().secuencias }}</p>
    </article>
    <article class="rounded-xl border border-outline bg-surface p-4">
      <div class="flex items-center gap-2 mb-1">
        <span class="material-symbols-outlined text-primary" style="font-size: 1.1rem;">event</span>
        <p class="text-[10px] font-label uppercase tracking-wider text-on-surface-variant">Último evento</p>
      </div>
      <p class="font-headline text-sm font-bold text-on-surface break-words">{{ kpis().ultimoEvento }}</p>
    </article>
  </section>

  <section class="mb-8">
    <app-health-status-dropdown title="Estado de servicios"></app-health-status-dropdown>
  </section>

  <section class="mt-2">
    <div class="flex items-center justify-between mb-4">
      <div class="min-w-0">
        <span class="font-label text-[10px] uppercase tracking-[0.3em] text-secondary mb-1 block">Secuencias</span>
        <h2 class="font-headline text-lg sm:text-xl font-bold tracking-tight text-on-surface">Ejecución</h2>
      </div>
      <div class="hidden sm:flex items-center gap-2 text-[10px] text-outline">
        <span class="w-1.5 h-1.5 rounded-full bg-secondary"></span>
        {{ commandLogs().length }} eventos
      </div>
    </div>

    <div class="mb-4 grid grid-cols-1 sm:grid-cols-[1fr_220px] gap-2">
      <input
        [ngModel]="movementSearch()"
        (ngModelChange)="updateMovementSearch($event)"
        placeholder="Buscar movimiento o secuencia..."
        class="w-full rounded-lg bg-surface border border-outline px-3 py-2 text-sm text-on-surface placeholder:text-on-surface-variant" />
      <select
        [ngModel]="selectedGroupFilter()"
        (ngModelChange)="updateGroupFilter($event)"
        class="w-full rounded-lg bg-surface border border-outline px-3 py-2 text-sm text-on-surface">
        @for (opt of groupFilterOptions(); track opt.value) {
          <option [ngValue]="opt.value">{{ opt.label }}</option>
        }
      </select>
    </div>

    <div class="grid grid-cols-1 xl:grid-cols-3 gap-6">

      <div class="xl:col-span-2 space-y-4">

        @if (sequenceLoading()) {
          <div class="flex flex-col items-center justify-center py-16 gap-3 text-on-surface-variant">
            <span class="material-symbols-outlined animate-spin" style="font-size: 2rem;">progress_activity</span>
            <p class="text-[10px] font-label uppercase tracking-wider">Cargando secuencias…</p>
          </div>
        } @else if (sequenceError()) {
          <div class="flex flex-col items-center justify-center py-16 gap-3 text-on-surface-variant">
            <span class="material-symbols-outlined text-error" style="font-size: 2rem;">error_outline</span>
            <p class="text-[10px] font-label uppercase tracking-wider text-error">{{ sequenceError() }}</p>
            <button
              (click)="loadSequences()"
              class="flex items-center gap-2 px-4 py-2 rounded-lg bg-surface-container-high border border-outline
                     text-[10px] font-label uppercase tracking-wider text-on-surface
                     hover:bg-surface-container-highest transition-colors cursor-pointer">
              <span class="material-symbols-outlined" style="font-size: 0.9rem;">refresh</span>
              Reintentar
            </button>
          </div>
        } @else if (filteredSequenceGroups().length === 0) {
          <div class="flex flex-col items-center justify-center py-16 gap-3 text-on-surface-variant">
            <span class="material-symbols-outlined" style="font-size: 2rem;">robot_2</span>
            <p class="text-[10px] font-label uppercase tracking-wider">Sin resultados para el filtro actual</p>
          </div>
        } @else {
          @for (group of filteredSequenceGroups(); track group.key) {
            <div class="bg-surface rounded-xl border border-outline overflow-hidden">
              <div class="flex items-center justify-between px-4 py-2.5 sm:px-5 sm:py-3 bg-surface-container-high border-b border-outline">
                <div class="flex items-center gap-3">
                  <div class="px-2 py-0.5 rounded bg-primary/15 border border-primary/25">
                    <span class="text-[9px] font-bold tracking-widest text-on-surface">{{ group.key }}</span>
                  </div>
                  <h3 class="font-headline text-sm font-bold tracking-tight text-on-surface">{{ group.label }}</h3>
                </div>
                <span class="text-[10px] font-label text-outline">{{ group.sequences.length }} secuencias</span>
              </div>

              <div class="p-3 sm:p-4">
                @if (group.sequences.length === 0) {
                  <p class="text-[10px] text-on-surface-variant">Sin secuencias en esta categoría</p>
                } @else {
                  <div [class]="group.sequences.length >= 2 ? 'grid grid-cols-2 gap-2' : 'grid grid-cols-1 gap-2'">
                  @for (sequence of group.sequences; track sequence.name) {
                    <div class="rounded-lg border border-outline bg-surface-container-low p-2.5 sm:p-3 space-y-2">
                      <div class="text-center space-y-1 min-h-[3rem]">
                        <p class="text-[11px] sm:text-xs text-on-surface leading-snug break-words">
                          {{ displaySequenceName(sequence.name) }}
                        </p>
                        @if (sequence.description) {
                          <p class="text-[10px] text-outline leading-snug break-words">{{ sequence.description }}</p>
                        }
                      </div>
                      <div class="grid grid-cols-2 gap-2">
                        <button
                          (click)="executePhase(sequence.name, 'normal')"
                          [disabled]="playLocked()"
                          class="rounded-lg border border-primary/20 bg-primary/10 hover:bg-primary/20 transition-colors py-2 cursor-pointer disabled:opacity-50 text-[10px] font-label uppercase tracking-wide text-on-surface">
                          Normal
                        </button>
                        <button
                          (click)="executePhase(sequence.name, 'neutro')"
                          [disabled]="playLocked()"
                          class="rounded-lg border border-outline bg-surface-container-high hover:bg-surface-container-highest transition-colors py-2 cursor-pointer disabled:opacity-50 text-[10px] font-label uppercase tracking-wide text-on-surface">
                          Neutro
                        </button>
                      </div>
                    </div>
                  }
                  </div>
                }
              </div>
            </div>
          }
        }
      </div>

      <div class="xl:col-span-1">
        <div class="space-y-4 xl:sticky xl:top-24">
          <div class="bg-surface rounded-xl border border-outline overflow-hidden">
            <div class="px-5 py-3 bg-surface-container-high border-b border-outline flex items-center justify-between">
              <h3 class="font-headline text-sm font-bold tracking-tight text-on-surface">En hardware</h3>
              <button (click)="stopHardware()" class="py-2 px-3 rounded bg-error text-on-error text-[10px] font-semibold cursor-pointer">
                Detener
              </button>
            </div>
            <div class="p-4 space-y-2 text-[10px] text-on-surface-variant">
              @if (runtimeUnreachable()) {
                <p class="text-error">sin estado</p>
              } @else {
                <p>Origen: {{ runtime().source || '—' }}</p>
                <p>Fase: {{ runtime().current ? (runtime().current!.name + ' · ' + runtime().current!.mode) : 'idle' }}</p>
                <p>Cola:</p>
                @if (runtime().queue.length === 0) {
                  <p>—</p>
                } @else {
                  @for (step of runtime().queue; track $index) {
                    <p>{{ step.name }} · {{ step.mode }}</p>
                  }
                }
              }
            </div>
          </div>

          <div class="bg-surface rounded-xl border border-outline overflow-hidden">
            <div class="flex items-center justify-between px-5 py-3 bg-surface-container-high border-b border-outline">
              <div class="flex items-center gap-2">
                <span class="material-symbols-outlined text-secondary" style="font-size: 1rem;">receipt_long</span>
                <h3 class="font-headline text-sm font-bold tracking-tight text-on-surface">Registro</h3>
              </div>
              <button
                (click)="clearLogs()"
                class="text-[9px] font-label uppercase tracking-wider text-on-surface-variant hover:text-on-surface
                       transition-colors cursor-pointer px-2 py-1 rounded hover:bg-surface-container-highest flex items-center gap-1">
                <span class="material-symbols-outlined" style="font-size: 0.8rem;">delete_sweep</span>
                Limpiar
              </button>
            </div>

            <div
              #logScroll
              class="h-[260px] md:h-[350px] overflow-y-auto px-3 py-2 space-y-1 font-mono text-[10px]"
              style="scrollbar-width: thin; scrollbar-color: #cbd5e1 transparent;">

              @if (commandLogs().length === 0) {
                <div class="flex flex-col items-center justify-center h-full gap-3 text-on-surface-variant">
                  <span class="material-symbols-outlined" style="font-size: 2rem;">terminal</span>
                  <p class="text-[10px] font-label uppercase tracking-wider">Sin ejecuciones</p>
                </div>
              }

              @for (log of commandLogs(); track trackLog($index, log)) {
                <div class="py-1.5 px-2 rounded hover:bg-surface-container-highest transition-colors">
                  <div class="flex items-start gap-2">
                    <span class="material-symbols-outlined flex-shrink-0 mt-0.5" [class]="logStatusColor(log.status)" style="font-size: 0.8rem;">
                      {{ logStatusIcon(log.status) }}
                    </span>
                    <div class="flex-1 min-w-0">
                      <div class="flex items-center gap-1.5 flex-wrap">
                        <span class="text-on-surface-variant">{{ log.timestamp }}</span>
                        <span class="px-1 py-0.5 rounded bg-primary/10 text-on-surface text-[8px]">{{ log.group }}</span>
                      </div>
                      <div class="text-on-surface-variant mt-0.5 truncate">{{ log.sequenceName }}</div>
                      @if (log.message) {
                        <div class="text-on-surface-variant mt-0.5 truncate">{{ log.message }}</div>
                      }
                    </div>
                  </div>
                </div>
              }
            </div>

            <div class="px-4 py-2 border-t border-outline bg-surface-container-high">
              <div class="flex justify-between text-[9px] text-on-surface-variant">
                <span>Total: {{ commandLogs().length }}</span>
                <span>ACK: {{ ackCount() }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>

</div>
```

Material icon `origin` is valid in Material Symbols. If the font build lacks it, use `alt_route` instead — do not invent a glyph.

- [ ] **Step 5: Run the tests**

Run:

```bash
cd pmas-web-main && npx vitest run src/app/pages/control-panel/control-panel.copy.spec.ts src/app/pages/control-panel/panel-kpis.spec.ts src/app/pages/control-panel/sequence-groups.spec.ts src/styles.tokens.spec.ts src/app/layouts/admin-shell/shell-copy.spec.ts
```

Expected: PASS all five files.

- [ ] **Step 6: Commit (pmas-web-main)**

```bash
cd pmas-web-main
git add src/app/pages/control-panel/control-panel.ts \
  src/app/pages/control-panel/control-panel.html \
  src/app/pages/control-panel/control-panel.copy.spec.ts
git commit -m "Rebuild the control panel as a light dashboard with real KPIs."
```

---

## Self-review notes (for the implementer)

- Do not edit `pmas-web-motion-studio`, robotics, gateway, mai-core, or vision/chat templates.
- After Task 5, leftover `slate-*` inside visión/chat/admin pages is allowed.
- `sequences.html` may still have `bg-[#000f1d]` around the iframe; leave it.
- Point the launcher submodule at the new `pmas-web-main` commit only if you are updating the launcher index; that is a separate launcher commit (`git add pmas-web-main`).
