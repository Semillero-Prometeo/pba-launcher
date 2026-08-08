# LAN startup and share QR — design

Date: 2026-08-08  
Status: approved for implementation planning  
Primary target: native Ubuntu Linux  
Secondary: WSL2 (best-effort; do not treat as LAN source of truth)

## Problem

Operators start the stack with `sudo docker compose up`, then do manual steps:

1. Open UFW for ports 3000 and 4200.
2. Find the LAN IP (for example on `wlp2s0`).
3. Edit `pmas-web-main/src/environments/environment.ts` (`gatewayUrl`).
4. Open `http://<LAN_IP>:4200` on the host and on other devices.

These steps break when the Wi‑Fi IP changes. They also dirty the frontend submodule.

## Goal

One Ubuntu command must:

- Start Compose services for LAN use.
- Configure host firewall rules for the web and gateway ports (when UFW is available).
- Print the LAN frontend URL to the console.
- Open that URL in the default browser on the host.

The Angular app must call the gateway without a manual IP edit.  
After login, the admin UI must show a QR code for the share URL on first visit, and again from the profile menu when the user asks.

## Non-goals

- Reverse proxy / single public port (possible later).
- Full WSL2 LAN networking (mirrored mode, Windows firewall, portproxy).
- Changing microservice ports or credentials.
- Rewriting the README beyond startup / LAN steps needed for this flow.

## Approach (chosen)

**Runtime gateway host + Ubuntu launcher script + in-app LAN QR.**

Do not patch `environment.ts` on each run.  
Do not add a reverse proxy in this change.

Gateway CORS already allows `origin: '*'`, so LAN origins can call the gateway.

## Architecture

| Piece | Responsibility |
|--------|----------------|
| `scripts/lan-up.sh` | Detect LAN IPv4, ensure UFW TCP 3000/4200, `docker compose up -d`, wait for :4200, print URL, open browser |
| Frontend gateway helper | Build API base as `http://<page-hostname>:3000` |
| LAN share service + modal | Share URL = `window.location.origin`; QR; first-show flag; profile menu action |
| README | Document `./scripts/lan-up.sh` as the Ubuntu LAN start path |

```text
Operator
  -> lan-up.sh (IP, UFW, compose, print, xdg-open)
  -> Browser http://LAN_IP:4200
  -> Angular uses http://LAN_IP:3000 for API
  -> Phone scans QR (same origin URL) -> same flow
```

## Components

### 1. Host script: `scripts/lan-up.sh`

Behavior:

1. Resolve LAN IPv4.
   - Prefer interfaces that match `wlan*`, `wlp*`, `eth*`, `en*`.
   - Skip `lo`, `docker*`, `br-*`, `veth*`.
   - Allow override: `LAN_IFACE=<name>`.
2. Ensure UFW allows TCP 3000 and TCP 4200 (idempotent). If `ufw` is missing or the command fails, print a warning and continue.
3. Start services in detached mode by default: `docker compose up -d` from the repo root (pass through extra args after `-d` if useful). Foreground-only `docker compose up` cannot open the browser until Compose exits, so it is not the default for this script.
4. Wait until TCP port 4200 accepts connections (reasonable timeout, then warn and still print the URL).
5. Print `http://$LAN_IP:4200` (and note that the gateway is on port 3000).
6. Open that URL with `xdg-open` when available.
7. Tell the operator how to follow logs (for example `docker compose logs -f`).

Constraints:

- If no usable LAN IP is found, exit with a clear error. Do not open `http://localhost:4200` as if it were a LAN URL.
- If the environment looks like WSL, print a warning that native Ubuntu is the supported LAN path.
- Prefer not requiring `sudo docker compose` if the user is already in the `docker` group; document both cases in the README. UFW still needs elevated rights when rules are applied.
- Only TCP is required for HTTP; do not open UDP 3000/4200 unless a later need appears.

### 2. Gateway URL resolution (`pmas-web-main`)

Today `GATEWAY_URL` is a compile-time string from `environment.gatewayUrl` (`http://localhost:3000`).

Change:

- Resolve the gateway base URL at runtime from `window.location.hostname` and gateway port `3000` (constant; optional future override).
- Keep `environment.gatewayUrl` only as a documented fallback for non-browser contexts (tests), not as an operator-edited LAN setting.
- Update `gateway.ts` (and any thin helper) so all existing `GATEWAY_URL` call sites keep working.

Success criterion: open the UI as `http://<any-host>:4200` and API calls go to `http://<same-host>:3000`.

### 3. LAN share QR UI (`pmas-web-main`)

Share URL: `window.location.origin` (the URL the browser used, including port 4200).

QR rendering: add a small client dependency (for example `qrcode`) and render to canvas or image. No backend endpoint.

First show:

- Trigger when the authenticated user enters `AdminShell` for the first time in that browser.
- Key example: `localStorage['pmas.lanQrShown']`.
- If the key is missing, open the modal, then set the key.
- Closing the modal must still set the key so the modal does not loop.

Manual show:

- In the navbar profile dropdown (next to “Ver perfil”), add an action such as **“Código QR de red”**.
- This opens the same modal and does not clear the first-show flag.

Modal content:

- QR image
- Share URL as text (copy-friendly)
- Short hint: device must use the same network
- Dismiss control

Use the existing lightweight signal-modal pattern (same style as admin users/roles modals). Do not add Angular Material only for this dialog.

## Data flow

1. `lan-up.sh` opens `http://<LAN_IP>:4200` (not localhost).
2. Angular loads; gateway helper uses that hostname for port 3000.
3. User logs in; `AdminShell` loads; first-show logic may open the QR modal.
4. Phone scans QR → opens the same origin → same runtime gateway host.
5. Profile menu can reopen the modal at any time.

## Error handling

| Case | Behavior |
|------|----------|
| No LAN IPv4 | Script fails with a clear message; suggest `LAN_IFACE` |
| UFW unavailable / no sudo | Warn; continue Compose + print URL |
| No `xdg-open` | Print URL only |
| Page opened as localhost | API works on the host only; QR is localhost — avoid this by opening the LAN URL from the script |
| WSL | Warn; do not claim full LAN support |

## Testing

- Manual on Ubuntu: start script → host browser opens LAN URL → phone on same Wi‑Fi scans QR → login and a gateway call succeed.
- Unit: gateway URL helper (hostname → base URL).
- Unit: first-show flag vs profile-menu reopen.
- README checklist for script dry runs (IP selection, ports, printed URL).

## README changes

Replace the manual `ufw` / `ip a` / `environment.ts` LAN instructions with:

- Prerequisites (Docker, optional UFW).
- `./scripts/lan-up.sh` as the primary LAN start command.
- Note that phones use the printed URL or the in-app QR.
- Keep login credentials and submodule notes elsewhere as they are today.

## Implementation order (for the later plan)

1. Gateway runtime helper + keep call sites working.
2. LAN share service, QR modal, AdminShell first-show, profile menu action.
3. `scripts/lan-up.sh`.
4. README update.
5. Manual Ubuntu verification checklist.

## Decisions locked

- Target of truth: native Ubuntu.
- Browser: auto-open on host; also print URL to console.
- Gateway: runtime hostname (not file patch; not reverse proxy in this work).
- QR: first AdminShell visit per browser + profile dropdown action.
- Ports stay 4200 (web) and 3000 (gateway); UFW opens TCP only.
- Launcher defaults to `docker compose up -d`, then waits for port 4200 before opening the browser.
