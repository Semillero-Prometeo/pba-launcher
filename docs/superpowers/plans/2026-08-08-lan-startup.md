# LAN Startup and Share QR Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One Ubuntu command starts Compose for LAN use, opens the frontend on the LAN IP, and the Angular app resolves the gateway from the page hostname and shares access via an in-app QR.

**Architecture:** Host script `scripts/lan-up.sh` detects LAN IPv4, opens UFW TCP 3000/4200, runs `docker compose up -d`, waits for port 4200, prints and opens the URL. Frontend `resolveGatewayUrl` builds `http://<hostname>:3000`. `LanShareService` + modal show a QR of `window.location.origin` on first AdminShell visit and from the navbar profile menu.

**Tech Stack:** Bash, Docker Compose, UFW (optional), Angular 21, Vitest, `qrcode` npm package.

## Global Constraints

- Primary target: native Ubuntu Linux; WSL2 is best-effort only (warn, do not claim full LAN support).
- Do not patch `environment.ts` with a LAN IP on each run.
- Do not add a reverse proxy in this work.
- Ports: web `4200`, gateway `3000`; UFW opens TCP only (no UDP).
- Launcher defaults to `docker compose up -d`, waits for `:4200`, then opens the browser.
- QR copy in UI: Spanish, matching the app (`Código QR de red`).
- `pmas-web-main` is a git submodule: commit frontend changes inside that repo, then update the parent submodule pointer.
- Keep existing `GATEWAY_URL` call sites working (export a session-resolved string plus a pure `resolveGatewayUrl` for tests).

## File Structure

| File | Responsibility |
|------|----------------|
| `pmas-web-main/src/app/core/constants/gateway.ts` | Pure `resolveGatewayUrl` + session `GATEWAY_URL` / `gatewayWsUrl` |
| `pmas-web-main/src/app/core/constants/gateway.spec.ts` | Unit tests for URL resolution |
| `pmas-web-main/src/environments/environment.ts` | Comment that `gatewayUrl` is fallback only (keep `http://localhost:3000`) |
| `pmas-web-main/src/app/core/services/lan-share.service.ts` | Share URL, localStorage first-show, modal open/close API |
| `pmas-web-main/src/app/core/services/lan-share.service.spec.ts` | First-show vs reopen unit tests |
| `pmas-web-main/src/app/components/lan-share-modal/*` | Modal UI + QR render via `qrcode` |
| `pmas-web-main/src/app/layouts/admin-shell/*` | Mount modal; call `maybeShowOnFirstAdminVisit` |
| `pmas-web-main/src/app/components/navbar/*` | Profile action to reopen modal |
| `scripts/lan-up.sh` | Ubuntu LAN start orchestration |
| `README.md` | Replace manual UFW/IP/`environment.ts` steps |

---

### Task 1: Runtime gateway URL helper

**Files:**
- Modify: `pmas-web-main/src/app/core/constants/gateway.ts`
- Create: `pmas-web-main/src/app/core/constants/gateway.spec.ts`
- Modify: `pmas-web-main/src/environments/environment.ts` (comment only)

**Interfaces:**
- Consumes: `environment.gatewayUrl` as fallback when `window` is unavailable
- Produces:
  - `export const GATEWAY_PORT = 3000`
  - `export function resolveGatewayUrl(hostname: string, port?: number): string`
  - `export const GATEWAY_URL: string` (resolved once for the browser session)
  - `export function gatewayWsUrl(path: string): string` (unchanged behavior, uses `GATEWAY_URL`)

- [ ] **Step 1: Write the failing test**

Create `pmas-web-main/src/app/core/constants/gateway.spec.ts`:

```typescript
import { describe, expect, it } from 'vitest';
import { resolveGatewayUrl, GATEWAY_PORT } from './gateway';

describe('resolveGatewayUrl', () => {
  it('builds http URL from hostname and default port', () => {
    expect(resolveGatewayUrl('10.211.14.115')).toBe('http://10.211.14.115:3000');
  });

  it('uses GATEWAY_PORT by default', () => {
    expect(GATEWAY_PORT).toBe(3000);
    expect(resolveGatewayUrl('192.168.1.10')).toBe(`http://192.168.1.10:${GATEWAY_PORT}`);
  });

  it('allows an explicit port override', () => {
    expect(resolveGatewayUrl('localhost', 3001)).toBe('http://localhost:3001');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `pmas-web-main`):

```bash
npx vitest run src/app/core/constants/gateway.spec.ts
```

Expected: FAIL (e.g. `resolveGatewayUrl` is not exported).

- [ ] **Step 3: Write minimal implementation**

Replace `pmas-web-main/src/app/core/constants/gateway.ts` with:

```typescript
import { environment } from '../../../environments/environment';

export const GATEWAY_PORT = 3000;

/** Pure helper: build gateway HTTP base from host + port. */
export function resolveGatewayUrl(hostname: string, port: number = GATEWAY_PORT): string {
  return `http://${hostname}:${port}`;
}

function browserOrFallbackHostname(): string {
  if (typeof window !== 'undefined' && window.location?.hostname) {
    return window.location.hostname;
  }
  try {
    return new URL(environment.gatewayUrl).hostname;
  } catch {
    return 'localhost';
  }
}

/**
 * Nest gateway HTTP base for this browser session.
 * Uses the page hostname so LAN devices hit the same host on port 3000.
 */
export const GATEWAY_URL = resolveGatewayUrl(browserOrFallbackHostname());

/** Build a WebSocket URL on the same host as ``GATEWAY_URL``. */
export function gatewayWsUrl(path: string): string {
  const base = GATEWAY_URL.replace(/^http/, 'ws');
  const p = path.startsWith('/') ? path : `/${path}`;
  return `${base}${p}`;
}
```

Update `environment.ts` comment above `gatewayUrl` to state it is a non-browser / test fallback only and must not be edited for LAN IPs.

- [ ] **Step 4: Run tests to verify they pass**

```bash
npx vitest run src/app/core/constants/gateway.spec.ts
```

Expected: PASS (all three tests).

- [ ] **Step 5: Commit (inside `pmas-web-main` submodule)**

```bash
cd pmas-web-main
git add src/app/core/constants/gateway.ts src/app/core/constants/gateway.spec.ts src/environments/environment.ts
git commit -m "$(cat <<'EOF'
Resolve gateway URL from page hostname at runtime.

Stop requiring operators to edit environment.ts when the LAN IP changes.
EOF
)"
cd ..
```

---

### Task 2: LanShareService (first-show + reopen)

**Files:**
- Create: `pmas-web-main/src/app/core/services/lan-share.service.ts`
- Create: `pmas-web-main/src/app/core/services/lan-share.service.spec.ts`

**Interfaces:**
- Consumes: `window.location.origin`, `localStorage`
- Produces (`LanShareService`, `providedIn: 'root'`):
  - `static readonly STORAGE_KEY = 'pmas.lanQrShown'`
  - `readonly modalOpen = signal(false)`
  - `shareUrl(): string` → `window.location.origin` (or `''` if no `window`)
  - `openModal(): void` → sets `modalOpen` true (does **not** clear storage)
  - `closeModal(): void` → sets `modalOpen` false and calls `markShown()`
  - `markShown(): void` → `localStorage.setItem(STORAGE_KEY, '1')`
  - `hasShown(): boolean` → storage key present
  - `maybeShowOnFirstAdminVisit(): void` → if `!hasShown()`, call `openModal()` then `markShown()`

- [ ] **Step 1: Write the failing test**

Create `pmas-web-main/src/app/core/services/lan-share.service.spec.ts`:

```typescript
import { describe, expect, it, beforeEach } from 'vitest';
import { LanShareService } from './lan-share.service';

describe('LanShareService', () => {
  let service: LanShareService;

  beforeEach(() => {
    localStorage.clear();
    service = new LanShareService();
  });

  it('opens modal and marks shown on first admin visit', () => {
    expect(service.hasShown()).toBe(false);
    service.maybeShowOnFirstAdminVisit();
    expect(service.modalOpen()).toBe(true);
    expect(service.hasShown()).toBe(true);
  });

  it('does not reopen automatically on a later admin visit', () => {
    service.maybeShowOnFirstAdminVisit();
    service.closeModal();
    expect(service.modalOpen()).toBe(false);
    service.maybeShowOnFirstAdminVisit();
    expect(service.modalOpen()).toBe(false);
    expect(service.hasShown()).toBe(true);
  });

  it('openModal reopens without clearing the shown flag', () => {
    service.maybeShowOnFirstAdminVisit();
    service.closeModal();
    service.openModal();
    expect(service.modalOpen()).toBe(true);
    expect(service.hasShown()).toBe(true);
  });

  it('closeModal marks shown even if mark was skipped', () => {
    service.openModal();
    localStorage.removeItem(LanShareService.STORAGE_KEY);
    service.closeModal();
    expect(service.modalOpen()).toBe(false);
    expect(service.hasShown()).toBe(true);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
npx vitest run src/app/core/services/lan-share.service.spec.ts
```

Expected: FAIL (module / class missing).

- [ ] **Step 3: Write minimal implementation**

Create `pmas-web-main/src/app/core/services/lan-share.service.ts`:

```typescript
import { Injectable, signal } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class LanShareService {
  static readonly STORAGE_KEY = 'pmas.lanQrShown';

  readonly modalOpen = signal(false);

  shareUrl(): string {
    if (typeof window === 'undefined' || !window.location?.origin) {
      return '';
    }
    return window.location.origin;
  }

  hasShown(): boolean {
    if (typeof localStorage === 'undefined') {
      return true;
    }
    return localStorage.getItem(LanShareService.STORAGE_KEY) !== null;
  }

  markShown(): void {
    if (typeof localStorage === 'undefined') {
      return;
    }
    localStorage.setItem(LanShareService.STORAGE_KEY, '1');
  }

  openModal(): void {
    this.modalOpen.set(true);
  }

  closeModal(): void {
    this.modalOpen.set(false);
    this.markShown();
  }

  maybeShowOnFirstAdminVisit(): void {
    if (this.hasShown()) {
      return;
    }
    this.openModal();
    this.markShown();
  }
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
npx vitest run src/app/core/services/lan-share.service.spec.ts
```

Expected: PASS.

- [ ] **Step 5: Commit (inside `pmas-web-main`)**

```bash
cd pmas-web-main
git add src/app/core/services/lan-share.service.ts src/app/core/services/lan-share.service.spec.ts
git commit -m "$(cat <<'EOF'
Add LanShareService for first-show and reopen QR modal state.

EOF
)"
cd ..
```

---

### Task 3: LAN share modal component + `qrcode` dependency

**Files:**
- Modify: `pmas-web-main/package.json` (add `qrcode` and `@types/qrcode`)
- Create: `pmas-web-main/src/app/components/lan-share-modal/lan-share-modal.ts`
- Create: `pmas-web-main/src/app/components/lan-share-modal/lan-share-modal.html`

**Interfaces:**
- Consumes: `LanShareService` (`modalOpen`, `shareUrl()`, `closeModal()`)
- Produces: standalone component `LanShareModal` selector `app-lan-share-modal`

- [ ] **Step 1: Install dependency**

From `pmas-web-main`:

```bash
npm install qrcode
npm install -D @types/qrcode
```

- [ ] **Step 2: Implement component**

`lan-share-modal.ts`:

```typescript
import { Component, effect, inject, signal } from '@angular/core';
import QRCode from 'qrcode';
import { LanShareService } from '../../core/services/lan-share.service';

@Component({
  selector: 'app-lan-share-modal',
  templateUrl: './lan-share-modal.html',
})
export class LanShareModal {
  readonly lanShare = inject(LanShareService);
  readonly qrDataUrl = signal<string | null>(null);
  readonly qrError = signal<string | null>(null);

  constructor() {
    effect(() => {
      if (!this.lanShare.modalOpen()) {
        return;
      }
      const url = this.lanShare.shareUrl();
      void this.renderQr(url);
    });
  }

  private async renderQr(url: string): Promise<void> {
    if (!url) {
      this.qrDataUrl.set(null);
      this.qrError.set('No hay URL para compartir.');
      return;
    }
    try {
      const dataUrl = await QRCode.toDataURL(url, { width: 240, margin: 2 });
      this.qrDataUrl.set(dataUrl);
      this.qrError.set(null);
    } catch {
      this.qrDataUrl.set(null);
      this.qrError.set('No se pudo generar el código QR.');
    }
  }

  close(): void {
    this.lanShare.closeModal();
  }
}
```

`lan-share-modal.html` (match users-modal overlay styling):

```html
@if (lanShare.modalOpen()) {
  <div class="fixed inset-0 z-[60] flex items-center justify-center p-4"
       style="background: rgba(2,6,23,0.85); backdrop-filter: blur(6px);"
       role="dialog"
       aria-modal="true"
       aria-label="Código QR de red">
    <div class="w-full max-w-sm bg-surface-container rounded-2xl border border-white/8 shadow-2xl overflow-hidden">
      <div class="flex items-center justify-between px-6 py-5 border-b border-white/5 bg-surface-container-high">
        <div class="flex items-center gap-3">
          <div class="w-9 h-9 rounded-xl bg-primary/15 border border-primary/25 flex items-center justify-center">
            <span class="material-symbols-outlined text-primary" style="font-size: 1.1rem; font-variation-settings: 'FILL' 1;">qr_code_2</span>
          </div>
          <h3 class="font-headline font-bold text-base tracking-tight text-on-surface">Código QR de red</h3>
        </div>
        <button type="button" (click)="close()" class="p-2 rounded-lg text-slate-500 hover:text-on-surface hover:bg-surface-container-highest transition-all cursor-pointer" aria-label="Cerrar">
          <span class="material-symbols-outlined" style="font-size: 1.1rem;">close</span>
        </button>
      </div>

      <div class="px-6 py-5 flex flex-col items-center gap-4">
        @if (qrError()) {
          <p class="text-sm text-error text-center">{{ qrError() }}</p>
        } @else if (qrDataUrl(); as src) {
          <img [src]="src" width="240" height="240" alt="Código QR para abrir la aplicación en la red local" class="rounded-lg bg-white p-2" />
        } @else {
          <p class="text-sm text-slate-500">Generando código…</p>
        }

        <p class="text-xs font-mono text-on-surface break-all text-center select-all">{{ lanShare.shareUrl() }}</p>
        <p class="text-[11px] text-outline text-center">Escanea este código desde un dispositivo en la misma red Wi‑Fi o LAN.</p>

        <button type="button" (click)="close()"
                class="w-full px-5 py-2.5 rounded-xl bg-primary text-on-primary font-headline font-bold text-sm tracking-tight hover:opacity-90 active:scale-95 transition-all cursor-pointer">
          Cerrar
        </button>
      </div>
    </div>
  </div>
}
```

- [ ] **Step 3: Smoke-check TypeScript compile for the new files**

From `pmas-web-main`:

```bash
npx ng build --configuration=development
```

Expected: build succeeds (or at least no errors in `lan-share-modal` / `qrcode` imports). If Docker-only builds are the norm, run the same check the team already uses; otherwise `npx tsc -p tsconfig.app.json --noEmit` if configured.

- [ ] **Step 4: Commit (inside `pmas-web-main`)**

```bash
cd pmas-web-main
git add package.json package-lock.json src/app/components/lan-share-modal
git commit -m "$(cat <<'EOF'
Add LAN share QR modal using the qrcode package.

EOF
)"
cd ..
```

---

### Task 4: Wire modal into AdminShell and navbar profile menu

**Files:**
- Modify: `pmas-web-main/src/app/layouts/admin-shell/admin-shell.ts`
- Modify: `pmas-web-main/src/app/layouts/admin-shell/admin-shell.html`
- Modify: `pmas-web-main/src/app/components/navbar/navbar.ts`
- Modify: `pmas-web-main/src/app/components/navbar/navbar.html`

**Interfaces:**
- Consumes: `LanShareService.maybeShowOnFirstAdminVisit`, `LanShareService.openModal`, `LanShareModal`
- Produces: first admin visit shows QR; profile item **Código QR de red** reopens it

- [ ] **Step 1: Update AdminShell**

In `admin-shell.ts`:

- Import `LanShareModal` and `LanShareService`.
- Add `LanShareModal` to `imports` array.
- Inject `LanShareService`.
- At end of `ngOnInit()`, call `this.lanShare.maybeShowOnFirstAdminVisit()`.

In `admin-shell.html`, add at the end of the template:

```html
<app-lan-share-modal />
```

- [ ] **Step 2: Update navbar profile dropdown**

In `navbar.ts`, inject `LanShareService` as `readonly lanShare = inject(LanShareService)`.

Add method:

```typescript
openLanQr(): void {
  this.closeProfileDropdown();
  this.lanShare.openModal();
}
```

In `navbar.html`, inside the profile dropdown options (after the “Ver perfil” link, before logout), add:

```html
<button
  type="button"
  (click)="openLanQr()"
  class="w-full flex items-center gap-3 px-4 py-3 text-sm text-on-surface-variant hover:bg-surface-container-highest
         hover:text-on-surface transition-colors cursor-pointer border-0 bg-transparent text-left">
  <span class="material-symbols-outlined text-slate-500" style="font-size: 1.1rem;">qr_code_2</span>
  Código QR de red
</button>
```

Note: `LanShareModal` lives in `AdminShell`. The profile menu is only used while authenticated inside that shell for admin routes; if the navbar also appears on login without the modal mounted, `openModal()` still sets the signal but nothing renders. That is acceptable for login. Do **not** mount the modal on the public login page.

- [ ] **Step 3: Manual UI check (dev)**

Start the web app (Compose or `npm start`), log in, confirm:

1. First admin load shows the QR modal once.
2. After close, reload admin still does not auto-show.
3. Profile → **Código QR de red** shows it again.

- [ ] **Step 4: Commit (inside `pmas-web-main`) + update parent submodule pointer**

```bash
cd pmas-web-main
git add src/app/layouts/admin-shell src/app/components/navbar
git commit -m "$(cat <<'EOF'
Show LAN QR on first admin visit and from the profile menu.

EOF
)"
cd ..
git add pmas-web-main
git commit -m "$(cat <<'EOF'
Bump pmas-web-main for LAN gateway resolution and share QR.

EOF
)"
```

---

### Task 5: `scripts/lan-up.sh`

**Files:**
- Create: `scripts/lan-up.sh` (executable)

**Interfaces:**
- Consumes: host network interfaces, optional `LAN_IFACE`, optional `.env` `WEB_MAIN_PORT` / `MS_GATEWAY_PORT`, `docker compose`, `ufw`, `xdg-open`
- Produces: detached stack on LAN; printed URL; browser open when possible

- [ ] **Step 1: Create the script**

Create `scripts/lan-up.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

WEB_PORT="${WEB_MAIN_PORT:-4200}"
GATEWAY_PORT="${MS_GATEWAY_PORT:-3000}"

if [[ -f .env ]]; then
  # shellcheck disable=SC1091
  set -a
  # Export only simple KEY=VALUE lines; ignore comments/blank
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ -z "${line//[[:space:]]/}" ]] && continue
    if [[ "$line" =~ ^(WEB_MAIN_PORT|MS_GATEWAY_PORT)= ]]; then
      export "$line"
    fi
  done < .env
  set +a
  WEB_PORT="${WEB_MAIN_PORT:-$WEB_PORT}"
  GATEWAY_PORT="${MS_GATEWAY_PORT:-$GATEWAY_PORT}"
fi

is_wsl() {
  grep -qi microsoft /proc/version 2>/dev/null || [[ -n "${WSL_DISTRO_NAME:-}" ]]
}

if is_wsl; then
  echo "WARNING: WSL detected. LAN exposure is supported on native Ubuntu; WSL is best-effort only." >&2
fi

iface_skipped() {
  local name="$1"
  [[ "$name" == lo ]] && return 0
  [[ "$name" == docker* ]] && return 0
  [[ "$name" == br-* ]] && return 0
  [[ "$name" == veth* ]] && return 0
  return 1
}

iface_preferred() {
  local name="$1"
  [[ "$name" == wlan* || "$name" == wlp* || "$name" == eth* || "$name" == en* ]]
}

detect_lan_ip() {
  local name addr
  if [[ -n "${LAN_IFACE:-}" ]]; then
    addr="$(ip -4 -o addr show dev "$LAN_IFACE" 2>/dev/null | awk '{print $4}' | cut -d/ -f1 | head -n1 || true)"
    if [[ -z "$addr" ]]; then
      echo "ERROR: No IPv4 on LAN_IFACE=$LAN_IFACE" >&2
      exit 1
    fi
    echo "$addr"
    return 0
  fi

  # Prefer wifi/ethernet
  while read -r name addr; do
    iface_skipped "$name" && continue
    iface_preferred "$name" || continue
    [[ -n "$addr" ]] || continue
    echo "$addr"
    return 0
  done < <(ip -4 -o addr show | awk '{gsub(/\/.*/, "", $4); print $2, $4}')

  # Fallback: any non-skipped interface
  while read -r name addr; do
    iface_skipped "$name" && continue
    [[ -n "$addr" ]] || continue
    echo "$addr"
    return 0
  done < <(ip -4 -o addr show | awk '{gsub(/\/.*/, "", $4); print $2, $4}')

  echo "ERROR: No usable LAN IPv4 found. Set LAN_IFACE=<interface> (e.g. wlp2s0) and retry." >&2
  exit 1
}

ensure_ufw() {
  if ! command -v ufw >/dev/null 2>&1; then
    echo "WARNING: ufw not found; skipping firewall rules for ${WEB_PORT}/tcp and ${GATEWAY_PORT}/tcp." >&2
    return 0
  fi
  if ! sudo -n ufw status >/dev/null 2>&1; then
    echo "Opening UFW TCP ${GATEWAY_PORT} and ${WEB_PORT} (may prompt for sudo)…"
  fi
  if ! sudo ufw allow "${GATEWAY_PORT}/tcp" >/dev/null; then
    echo "WARNING: failed to allow ${GATEWAY_PORT}/tcp via ufw; continuing." >&2
  fi
  if ! sudo ufw allow "${WEB_PORT}/tcp" >/dev/null; then
    echo "WARNING: failed to allow ${WEB_PORT}/tcp via ufw; continuing." >&2
  fi
}

wait_for_port() {
  local host="$1" port="$2" timeout="${3:-180}"
  local start
  start="$(date +%s)"
  echo "Waiting for TCP ${host}:${port} (timeout ${timeout}s)…"
  while true; do
    if (echo >/dev/tcp/"$host"/"$port") >/dev/null 2>&1; then
      echo "Port ${port} is open."
      return 0
    fi
    if command -v nc >/dev/null 2>&1 && nc -z "$host" "$port" >/dev/null 2>&1; then
      echo "Port ${port} is open."
      return 0
    fi
    if (( $(date +%s) - start >= timeout )); then
      echo "WARNING: timed out waiting for ${host}:${port}; opening the URL anyway." >&2
      return 1
    fi
    sleep 2
  done
}

LAN_IP="$(detect_lan_ip)"
FRONTEND_URL="http://${LAN_IP}:${WEB_PORT}"

ensure_ufw

DOCKER=(docker)
if ! docker info >/dev/null 2>&1; then
  if command -v sudo >/dev/null 2>&1; then
    DOCKER=(sudo docker)
  else
    echo "ERROR: cannot talk to Docker daemon. Add your user to the docker group or use sudo." >&2
    exit 1
  fi
fi

echo "Starting services: ${DOCKER[*]} compose up -d $*"
"${DOCKER[@]}" compose up -d "$@"

wait_for_port 127.0.0.1 "$WEB_PORT" 180 || true

echo
echo "Frontend (LAN): ${FRONTEND_URL}"
echo "Gateway (LAN):  http://${LAN_IP}:${GATEWAY_PORT}"
echo "Follow logs:    ${DOCKER[*]} compose logs -f"
echo

if command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$FRONTEND_URL" >/dev/null 2>&1 || echo "WARNING: xdg-open failed; open ${FRONTEND_URL} manually." >&2
else
  echo "xdg-open not found; open ${FRONTEND_URL} in your browser."
fi
```

- [ ] **Step 2: Make executable and dry-check syntax**

```bash
chmod +x scripts/lan-up.sh
bash -n scripts/lan-up.sh
```

Expected: no output from `bash -n` (syntax OK).

- [ ] **Step 3: Commit (parent repo)**

```bash
git add scripts/lan-up.sh
git commit -m "$(cat <<'EOF'
Add lan-up.sh to start Compose on the LAN and open the UI.

EOF
)"
```

---

### Task 6: README update + verification checklist

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Replace LAN / startup section**

Rewrite the startup portion of `README.md` so it covers:

1. Submodule init/update (keep existing).
2. Copy `.env.template` → `.env` if needed (one line if not already documented).
3. Primary LAN start:

```bash
./scripts/lan-up.sh
```

4. Optional: `LAN_IFACE=wlp2s0 ./scripts/lan-up.sh`
5. Note: script opens UFW TCP for gateway/web ports when possible, prints the LAN URL, opens the browser, and uses `docker compose up -d`.
6. Phones: use the printed URL or scan **Código QR de red** after login (first admin visit shows it automatically).
7. Keep login credentials block as-is.
8. Remove the manual `ufw allow`, `ip a` / `wlp2s0`, and `environment.ts` / `gatewayUrl` edit instructions.
9. Add a short **Verification** checklist:

```markdown
### Verificación (Ubuntu nativo)

- [ ] `./scripts/lan-up.sh` imprime `http://<LAN_IP>:4200` y abre el navegador
- [ ] Login funciona en el host
- [ ] El modal QR aparece en la primera visita al admin; el menú de perfil puede reabrirlo
- [ ] Un teléfono en la misma Wi‑Fi abre la URL/QR y puede iniciar sesión / llamar al API
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "$(cat <<'EOF'
Document lan-up.sh as the Ubuntu LAN startup path.

EOF
)"
```

- [ ] **Step 3: End-to-end verification on Ubuntu (manual)**

Run the checklist from Step 1 on a native Ubuntu machine on Wi‑Fi. Record pass/fail before claiming the feature complete.

---

## Spec coverage (self-review)

| Spec requirement | Task |
|------------------|------|
| Runtime gateway from page hostname | Task 1 |
| No `environment.ts` LAN edits | Task 1 + Task 6 |
| Lan share QR first AdminShell visit | Tasks 2–4 |
| Profile menu reopen | Task 4 |
| `lan-up.sh` IP / UFW TCP / `up -d` / wait / print / `xdg-open` | Task 5 |
| WSL warning | Task 5 |
| README replaces manual steps | Task 6 |
| Unit tests gateway + first-show | Tasks 1–2 |
| Manual Ubuntu verification | Task 6 |

No reverse proxy; ports remain 4200/3000; UDP not opened.
