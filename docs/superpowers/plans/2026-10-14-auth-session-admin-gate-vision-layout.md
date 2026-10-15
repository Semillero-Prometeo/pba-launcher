# Session expiry, ADMIN gate, and vision layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the operator shell on any expired or forbidden session with a clear login message, let ADMIN create users against the real `/users` API, hide Usuarios/Roles from everyone else, and show vision objects above full-size cameras at 1 s with no Preview.

**Architecture:** Angular owns session UX (`isAuthenticated` = token + unexpired JWT, interceptor 401/403 → `logout('expired')`, `roleGuard` on `/admin/*`). Gateway `HasRoles(ADMIN)` + `RolesGuard` keyed to `X-Active-Role`. Auth MS create validates plaintext password and assigns `role_ids`. mai-core pipeline interval 1.0 s and a single JPEG per camera. PRODUCT/DESIGN at the launcher root record the cut.

**Tech Stack:** Angular 21 + Vitest file-read (and one pure JWT helper), NestJS gateway + auth MS, Python mai-core, Markdown at launcher root.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-10-14-auth-session-admin-gate-vision-layout-design.md`.
- Do not change the turn, `chatService.chat`, `declarePoema`, `{ reply, fuente, movimientos }`, Motion Studio, robotics ingest, or management chat proxy.
- Edit only the owning repo: session/ADMIN UI in `pmas-web-main`; HTTP guards/DTOs in `pba-ms-gateway`; create/update persistence in `pba-ms-auth`; pipeline/encode in `pmai-mai-core`; PRODUCT/DESIGN in the launcher.
- Login copy: «Tu sesión venció. Entra de nuevo.» POST `/auth/login` 401 stays «Credenciales incorrectas.»
- Active role name `ADMIN` (not the UUID) gates the menu and `roleGuard`. Gateway `HasRoles` uses the same name on the **active** role.
- Vision: no `Preview`, no `previewSrc`, no `text-slate-*`, no `text-[8px]`–`text-[10px]`. Thumb ~480 px. Pipeline 1.0 s.
- Work on `feat/sequence-neutro-runtime` in each repo that already has it; otherwise the repo's current branch. Do not mix files across repos in one commit.

---

## File structure

| File | Responsibility |
|---|---|
| `pmas-web-main/src/app/core/services/jwt-exp.ts` | Pure `tokenIsUnexpired`. |
| `pmas-web-main/src/app/core/services/auth.service.ts` | `isAuthenticated`, `logout('expired')`, flash key, `loadProfile` reason. |
| `pmas-web-main/src/app/core/interceptors/auth.interceptor.ts` | Any 401/403 except public auth URLs. |
| `pmas-web-main/src/app/core/guards/auth.guard.ts` | Expired token → logout flash. |
| `pmas-web-main/src/app/core/guards/role.guard.ts` | ADMIN-only routes. |
| `pmas-web-main/src/app/pages/login/login.ts` + `login.html` | Flash banner. |
| `pmas-web-main/src/app/layouts/admin-shell/admin-shell.ts` | `loadProfile` on refresh. |
| `pmas-web-main/src/app/pages/robotics-vision/vision-websocket.service.ts` | Close 4001 → logout; thumb 480. |
| `pmas-web-main/src/app/pages/admin/users/users.ts` + `users.html` | POST/PUT `/users`, PATCH inactive. |
| `pmas-web-main/src/app/components/sidebar/sidebar.ts` | Hide Autenticación/Gestión unless ADMIN. |
| `pmas-web-main/src/app/app.routes.ts` | `roleGuard` on `/admin/users` and `/admin/roles`. |
| `pba-ms-gateway/src/auth-ms/users/dto/create-user.dto.ts` | `password` + `role_ids`. |
| `pba-ms-gateway/src/auth-ms/users/dto/update-user.dto.ts` | optional `role_ids`. |
| `pba-ms-gateway/src/auth-ms/users/users.controller.ts` | Not public; `HasRoles(ADMIN)`. |
| `pba-ms-gateway/src/auth-ms/roles/roles.controller.ts` | `HasRoles(ADMIN)`. |
| `pba-ms-gateway/src/auth/guards/roles.guard.ts` | Active role name must be in `HasRoles`. |
| `pba-ms-gateway/src/mai-core-ms/vision/vision.gateway.ts` | Default thumb 480; clamp 960. |
| `pba-ms-auth/src/users/dto/create-user.dto.ts` | Same password + `role_ids`. |
| `pba-ms-auth/src/users/dto/update-user.dto.ts` | optional `role_ids`. |
| `pba-ms-auth/src/users/repositories/users.repository.ts` | Validate plaintext, hash, assign `role_ids`. |
| `pba-ms-auth/src/users/users.service.ts` | Create without forced STUDENT; update applies username + password + roles. |
| `pmai-mai-core/settings.toml` + `src/pmai_core/settings.py` | `result_interval_seconds = 1.0`. |
| `pmai-mai-core/src/pmai_core/api/vision/vision_controller.py` | One JPEG; preview always null. |
| `pmai-mai-core/src/pmai_core/api/vision/schemas.py` | `thumb_max_width` default 480, `le=960`. |
| `pmas-web-main/.../robotics-vision.html` + `.ts` | Objects first, cameras below, no Preview. |
| `PRODUCT.md` / `DESIGN.md` | This cut is no longer pending. |

---

### Task 1: JWT expiry helper and `isAuthenticated`

**Files:**
- Create: `pmas-web-main/src/app/core/services/jwt-exp.ts`
- Create: `pmas-web-main/src/app/core/services/jwt-exp.spec.ts`
- Modify: `pmas-web-main/src/app/core/services/auth.service.ts`

**Interfaces:**
- Consumes: raw JWT string (three base64url segments).
- Produces: `tokenIsUnexpired(token: string, nowMs?: number): boolean`. `AuthService.isAuthenticated` is true only when `token()` is set **and** `tokenIsUnexpired(token())`.

- [ ] **Step 1: Write the failing test**

Create `pmas-web-main/src/app/core/services/jwt-exp.spec.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { tokenIsUnexpired } from './jwt-exp';

function jwtWithExp(expSeconds: number): string {
  const payload = btoa(JSON.stringify({ exp: expSeconds }))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/g, '');
  return `hdr.${payload}.sig`;
}

describe('tokenIsUnexpired', () => {
  it('is true when exp is in the future', () => {
    expect(tokenIsUnexpired(jwtWithExp(2_000_000_000), 1_700_000_000_000)).toBe(true);
  });

  it('is false when exp is in the past', () => {
    expect(tokenIsUnexpired(jwtWithExp(1_000_000_000), 1_700_000_000_000)).toBe(false);
  });

  it('is false for malformed tokens', () => {
    expect(tokenIsUnexpired('not-a-jwt')).toBe(false);
    expect(tokenIsUnexpired('a.b')).toBe(false);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd pmas-web-main && npx ng test --watch=false --include='**/jwt-exp.spec.ts'`

Expected: FAIL (cannot find `./jwt-exp` or `tokenIsUnexpired` is not a function).

- [ ] **Step 3: Implement `jwt-exp.ts` and wire `isAuthenticated`**

`jwt-exp.ts`:

```ts
export function tokenIsUnexpired(token: string, nowMs: number = Date.now()): boolean {
  try {
    const parts = token.split('.');
    if (parts.length < 2) return false;
    const payload = parts[1].replace(/-/g, '+').replace(/_/g, '/');
    const padded = payload + '='.repeat((4 - (payload.length % 4)) % 4);
    const json = JSON.parse(atob(padded)) as { exp?: unknown };
    if (typeof json.exp !== 'number') return false;
    return json.exp * 1000 > nowMs;
  } catch {
    return false;
  }
}
```

In `auth.service.ts` import `tokenIsUnexpired` and replace:

```ts
readonly isAuthenticated = computed(() => {
  const t = this._token();
  return !!t && tokenIsUnexpired(t);
});
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd pmas-web-main && npx ng test --watch=false --include='**/jwt-exp.spec.ts'`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd pmas-web-main
git add src/app/core/services/jwt-exp.ts src/app/core/services/jwt-exp.spec.ts src/app/core/services/auth.service.ts
git commit -m "$(cat <<'EOF'
Treat a JWT past exp as logged out.

EOF
)"
```

---

### Task 2: Expired-session flash on `/login`

**Files:**
- Modify: `pmas-web-main/src/app/core/services/auth.service.ts`
- Modify: `pmas-web-main/src/app/pages/login/login.ts`
- Modify: `pmas-web-main/src/app/pages/login/login.html`
- Modify: `pmas-web-main/src/app/pages/login/login.copy.spec.ts`

**Interfaces:**
- Consumes: `tokenIsUnexpired` from Task 1.
- Produces: `export const LOGIN_FLASH_KEY = 'prometeo_login_flash'`. `logout(reason?: 'expired'): void` writes `'expired'` to `sessionStorage` when `reason === 'expired'`. Login shows «Tu sesión venció. Entra de nuevo.»

- [ ] **Step 1: Extend `login.copy.spec.ts` so it fails**

Add:

```ts
it('tells the operator when the session expired', () => {
  expect(html).toContain('Tu sesión venció. Entra de nuevo.');
  expect(html).toContain('sessionExpired');
  expect(html).toContain('schedule');
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd pmas-web-main && npx ng test --watch=false --include='**/login.copy.spec.ts'`

Expected: FAIL (`Tu sesión venció` not found).

- [ ] **Step 3: Implement flash**

In `auth.service.ts`:

```ts
export const LOGIN_FLASH_KEY = 'prometeo_login_flash';
```

Replace `logout()`:

```ts
logout(reason?: 'expired') {
  if (reason === 'expired') {
    sessionStorage.setItem(LOGIN_FLASH_KEY, 'expired');
  }
  this._token.set(null);
  this._profile.set(null);
  this._roleSelected.set(false);
  this._activeRoleId.set('');
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(ROLE_KEY);
  this.router.navigate(['/login']);
}
```

In `loadProfile` `catchError`, call `this.logout('expired')` instead of `this.logout()`.

In `login.ts` add:

```ts
import { LOGIN_FLASH_KEY } from '../../core/services/auth.service';

sessionExpired = signal(false);

constructor() {
  if (this.auth.token() && !this.auth.isAuthenticated()) {
    this.auth.logout('expired');
  }
  this.sessionExpired.set(sessionStorage.getItem(LOGIN_FLASH_KEY) === 'expired');
  sessionStorage.removeItem(LOGIN_FLASH_KEY);
}
```

In `login.html`, **above** the `<form>`, after the “Iniciar sesión” block:

```html
@if (sessionExpired()) {
  <div class="mb-6 flex items-start gap-3 p-4 bg-error-container rounded-lg border border-error/30" role="alert">
    <span class="material-symbols-outlined text-error mt-0.5" style="font-size: 1.1rem;">schedule</span>
    <p class="text-sm text-on-error-container leading-relaxed">
      Tu sesión venció. Entra de nuevo.
    </p>
  </div>
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd pmas-web-main && npx ng test --watch=false --include='**/login.copy.spec.ts'`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd pmas-web-main
git add src/app/core/services/auth.service.ts src/app/pages/login/login.ts src/app/pages/login/login.html src/app/pages/login/login.copy.spec.ts
git commit -m "$(cat <<'EOF'
Show expired-session copy on the login form.

EOF
)"
```

---

### Task 3: Interceptor logs out on any 401/403 except public auth

**Files:**
- Modify: `pmas-web-main/src/app/core/interceptors/auth.interceptor.ts`
- Create: `pmas-web-main/src/app/core/interceptors/auth.interceptor.spec.ts`

**Interfaces:**
- Consumes: `AuthService.logout('expired')` from Task 2.
- Produces: public auth URLs (`/auth/login`, `/auth/restore-password`, `/auth/set-password`) never call logout. Every other HTTP 401 or 403 calls `logout('expired')`. Delete `INACTIVE_SESSION_MESSAGE` / `shouldLogoutOn401`.

- [ ] **Step 1: Write the failing file-read test**

```ts
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const src = readFileSync(resolve(import.meta.dirname, 'auth.interceptor.ts'), 'utf8');

describe('auth interceptor session close', () => {
  it('closes on any 401 or 403 except public auth URLs', () => {
    expect(src).toContain("logout('expired')");
    expect(src).toContain('/auth/login');
    expect(src).toContain('/auth/restore-password');
    expect(src).toContain('/auth/set-password');
    expect(src).not.toContain('INACTIVE_SESSION_MESSAGE');
    expect(src).not.toContain('shouldLogoutOn401');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd pmas-web-main && npx ng test --watch=false --include='**/auth.interceptor.spec.ts'`

Expected: FAIL (`INACTIVE_SESSION_MESSAGE` still present).

- [ ] **Step 3: Replace interceptor body**

```ts
import { HttpErrorResponse, HttpInterceptorFn, HttpRequest } from '@angular/common/http';
import { inject } from '@angular/core';
import { tap } from 'rxjs';
import { AuthService } from '../services/auth.service';

const TOKEN_KEY = 'prometeo_token';

function isPublicAuthRequest(req: HttpRequest<unknown>): boolean {
  return (
    req.url.includes('/auth/login') ||
    req.url.includes('/auth/restore-password') ||
    req.url.includes('/auth/set-password')
  );
}

function shouldLogout(err: unknown, req: HttpRequest<unknown>): boolean {
  if (isPublicAuthRequest(req)) return false;
  return err instanceof HttpErrorResponse && (err.status === 401 || err.status === 403);
}

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const authService = inject(AuthService);
  const token = authService.token() ?? localStorage.getItem(TOKEN_KEY);

  if (!token) {
    return next(req).pipe(
      tap({
        error: (err) => {
          if (shouldLogout(err, req)) authService.logout('expired');
        },
      }),
    );
  }

  const cloned = req.clone({
    setHeaders: {
      Authorization: `Bearer ${token}`,
      'X-Active-Role': authService.activeRole(),
    },
  });

  return next(cloned).pipe(
    tap({
      error: (err) => {
        if (shouldLogout(err, req)) authService.logout('expired');
      },
    }),
  );
};
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd pmas-web-main && npx ng test --watch=false --include='**/auth.interceptor.spec.ts'`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd pmas-web-main
git add src/app/core/interceptors/auth.interceptor.ts src/app/core/interceptors/auth.interceptor.spec.ts
git commit -m "$(cat <<'EOF'
Log out on any authenticated 401 or 403.

EOF
)"
```

---

### Task 4: Guards, shell profile, vision WS 4001

**Files:**
- Modify: `pmas-web-main/src/app/core/guards/auth.guard.ts`
- Modify: `pmas-web-main/src/app/layouts/admin-shell/admin-shell.ts`
- Modify: `pmas-web-main/src/app/pages/robotics-vision/vision-websocket.service.ts`
- Create: `pmas-web-main/src/app/core/guards/auth.guard.spec.ts`
- Create: `pmas-web-main/src/app/pages/robotics-vision/vision-websocket.spec.ts`

**Interfaces:**
- Consumes: `logout('expired')`, `isAuthenticated`, `loadProfile`.
- Produces: expired token hitting `authGuard` flashes login. Shell loads `/me` after refresh. Vision WS close code `4001` calls `logout('expired')` and does not reconnect.

- [ ] **Step 1: Write failing file-read tests**

`auth.guard.spec.ts`:

```ts
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const src = readFileSync(resolve(import.meta.dirname, 'auth.guard.ts'), 'utf8');
const shell = readFileSync(resolve(import.meta.dirname, '../../layouts/admin-shell/admin-shell.ts'), 'utf8');

describe('authGuard expired session', () => {
  it('logs out expired tokens instead of keeping the shell', () => {
    expect(src).toContain("logout('expired')");
    expect(src).toContain('isAuthenticated');
  });

  it('loads the profile in the admin shell after refresh', () => {
    expect(shell).toContain('loadProfile');
    expect(shell).toContain('AuthService');
  });
});
```

`vision-websocket.spec.ts`:

```ts
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const src = readFileSync(resolve(import.meta.dirname, 'vision-websocket.service.ts'), 'utf8');

describe('vision websocket auth close', () => {
  it('closes the Angular session on 4001', () => {
    expect(src).toContain('4001');
    expect(src).toContain("logout('expired')");
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd pmas-web-main && npx ng test --watch=false --include='**/auth.guard.spec.ts' --include='**/vision-websocket.spec.ts'`

Expected: FAIL.

- [ ] **Step 3: Implement**

`auth.guard.ts`:

```ts
import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

export const authGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);

  if (auth.isAuthenticated()) return true;
  if (auth.token()) auth.logout('expired');
  return router.createUrlTree(['/login']);
};
```

`admin-shell.ts`: inject `AuthService`. At the start of `ngOnInit`:

```ts
private readonly auth = inject(AuthService);

ngOnInit(): void {
  if (this.auth.token() && !this.auth.profile()) {
    this.auth.loadProfile().subscribe();
  }
  // existing router + lanShare code unchanged
}
```

In `vision-websocket.service.ts` replace `ws.onclose`:

```ts
ws.onclose = (ev: CloseEvent) => {
  if (this.socket === ws) {
    this.socket = null;
  }
  if (ev.code === 4001) {
    this.auth.logout('expired');
    return;
  }
  if (this.connectionState() === 'connected') {
    this.connectionState.set('idle');
  }
};
```

- [ ] **Step 4: Run tests to verify they pass**

Run: same command as Step 2.

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd pmas-web-main
git add src/app/core/guards/auth.guard.ts src/app/core/guards/auth.guard.spec.ts src/app/layouts/admin-shell/admin-shell.ts src/app/pages/robotics-vision/vision-websocket.service.ts src/app/pages/robotics-vision/vision-websocket.spec.ts
git commit -m "$(cat <<'EOF'
Close the shell and vision socket when the session is dead.

EOF
)"
```

---

### Task 5: Create-user DTO and plaintext password (auth MS + gateway)

**Files:**
- Modify: `pba-ms-auth/src/users/dto/create-user.dto.ts`
- Modify: `pba-ms-auth/src/users/dto/update-user.dto.ts`
- Modify: `pba-ms-auth/src/users/repositories/users.repository.ts`
- Modify: `pba-ms-auth/src/users/users.service.ts`
- Create: `pba-ms-auth/src/users/repositories/users.repository.create.spec.ts`
- Modify: `pba-ms-gateway/src/auth-ms/users/dto/create-user.dto.ts`
- Modify: `pba-ms-gateway/src/auth-ms/users/dto/update-user.dto.ts`
- Create: `pba-ms-gateway/src/auth-ms/users/dto/create-user.dto.spec.ts`

**Interfaces:**
- Consumes: existing `PasswordGeneratorService.validatePassword(plaintext)`.
- Produces: `CreateUserDto` fields `{ username: string; password: string; role_ids: string[]; person_id?: string }`. Repository validates **plaintext** then hashes. `users.service.create` does **not** force STUDENT; it passes `role_ids`. `UpdateAuthUserDto.role_ids?: string[]`.

Password rules (copy onto both Create DTOs, already on Update):

```ts
@IsString()
@IsNotEmpty()
@MinLength(8)
@Matches(/^(?=.*[a-z])(?=.*[A-Z])(?=.*(?:\d|[^\w\s]))(?!.*[.\n]).*$/, {
  message:
    'La contraseña debe contener al menos una letra mayúscula, una letra minúscula, un número o un caracter especial',
})
password: string;
```

`role_ids`:

```ts
@IsArray()
@ArrayMinSize(1)
@IsUUID('4', { each: true })
role_ids: string[];
```

On update, `role_ids` is `@IsOptional()` `@IsArray()` `@IsUUID('4', { each: true })`.

`person_id` on create: `@IsOptional()` `@IsUUID('4')` — drop `@IsNotEmpty()`.

- [ ] **Step 1: Write failing tests**

`pba-ms-auth/src/users/repositories/users.repository.create.spec.ts` (file-read):

```ts
import { readFileSync } from 'fs';
import { join } from 'path';

const src = readFileSync(join(__dirname, 'users.repository.ts'), 'utf8');
const dto = readFileSync(join(__dirname, '../dto/create-user.dto.ts'), 'utf8');
const svc = readFileSync(join(__dirname, '../users.service.ts'), 'utf8');

describe('admin create user', () => {
  it('validates plaintext password before hashing', () => {
    expect(dto).toContain('password: string');
    expect(dto).toContain('role_ids');
    const validateAt = src.indexOf('validatePassword(');
    const hashAt = src.indexOf('hashSync');
    expect(validateAt).toBeGreaterThan(-1);
    expect(hashAt).toBeGreaterThan(validateAt);
    expect(src).toContain('createUserDto.password');
    expect(src).not.toContain('generateTemporaryPassword');
  });

  it('does not assign STUDENT by default', () => {
    expect(svc).not.toContain('assignStudentRole');
    expect(svc).not.toContain('Roles.STUDENT');
  });
});
```

`pba-ms-gateway/src/auth-ms/users/dto/create-user.dto.spec.ts`:

```ts
import { readFileSync } from 'fs';
import { join } from 'path';

const dto = readFileSync(join(__dirname, 'create-user.dto.ts'), 'utf8');

describe('gateway CreateUserDto', () => {
  it('requires password and role_ids', () => {
    expect(dto).toContain('password: string');
    expect(dto).toContain('role_ids');
    expect(dto).toContain("ArrayMinSize(1)");
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
cd pba-ms-auth && npx jest src/users/repositories/users.repository.create.spec.ts --no-coverage
cd pba-ms-gateway && npx jest src/auth-ms/users/dto/create-user.dto.spec.ts --no-coverage
```

Expected: FAIL (no `password: string` / still `generateTemporaryPassword`).

- [ ] **Step 3: Implement DTOs, repository, create service**

**Both** `CreateUserDto` classes (auth MS and gateway): keep `username` email; add `password` and `role_ids` as above; `person_id` optional; keep optional `assign_student_role` unused by the mesa path (do not read it in `create`).

**Both** `UpdateAuthUserDto`: add optional `role_ids`.

`users.repository.create` in auth MS — replace the password block:

```ts
async create(createUserDto: CreateUserDto) {
  const { role_id, assign_student_role, person_id, role_ids, password, ...data } = createUserDto;
  const { isValid, errors } = this.passwordGeneratorService.validatePassword(password);
  if (!isValid) {
    throw new RpcException({
      message: errors.join(', '),
      statusCode: HttpStatus.BAD_REQUEST,
    });
  }
  const hashedPassword = bcrypt.hashSync(password, 10);
  // existing person_id lookup unchanged
  const user = await this.prismaService.user.create({
    data: {
      ...data,
      password: hashedPassword,
      ...(person_id ? { person: { connect: { id: person_id } } } : {}),
    },
  });
  const ids = [...(role_ids ?? []), ...(role_id ? [role_id] : [])];
  for (const rid of ids) {
    await this.prismaService.user_role.create({
      data: { user_id: user.id, role_id: rid },
    });
  }
  const resetToken = this.passwordGeneratorService.generatePasswordResetToken(user.id);
  return { id: user.id, username: user.username, resetToken };
}
```

`users.service.create` — remove STUDENT assignment:

```ts
async create(data: CreateUserDto) {
  const user: UserResponse | null = await this.userRepository.findOne(data.username);
  if (user) {
    throw new RpcException({
      statusCode: HttpStatus.BAD_REQUEST,
      message: 'El usuario ya existe',
    });
  }
  const result = await this.userRepository.create(data);
  const newUser: UserResponse | null = await this.userRepository.findOne(result.username);
  const [frontendUrl]: [app_settings] = await Promise.all([
    this.appSettingsService.findOne(AppSettings.FRONT_END_URL),
  ]);
  if (!frontendUrl) {
    throw new RpcException({
      message: 'No se encontró la URL de frontend',
      statusCode: HttpStatus.INTERNAL_SERVER_ERROR,
    });
  }
  return {
    statusCode: HttpStatus.CREATED,
    message: 'Usuario creado correctamente',
    data: { id: newUser.id, username: result.username },
  };
}
```

Unused imports (`Roles`, `role`) in `users.service.ts` — remove if the compiler complains.

- [ ] **Step 4: Run tests to verify they pass**

Same commands as Step 2. Expected: PASS.

- [ ] **Step 5: Commit in each owning repo**

```bash
cd pba-ms-auth
git add src/users/dto/create-user.dto.ts src/users/dto/update-user.dto.ts src/users/repositories/users.repository.ts src/users/users.service.ts src/users/repositories/users.repository.create.spec.ts
git commit -m "$(cat <<'EOF'
Create users with a real password and assigned roles.

EOF
)"

cd pba-ms-gateway
git add src/auth-ms/users/dto/create-user.dto.ts src/auth-ms/users/dto/update-user.dto.ts src/auth-ms/users/dto/create-user.dto.spec.ts
git commit -m "$(cat <<'EOF'
Accept password and role_ids on POST /users.

EOF
)"
```

---

### Task 6: `HasRoles(ADMIN)` and active-role `RolesGuard`

**Files:**
- Modify: `pba-ms-gateway/src/auth/guards/roles.guard.ts`
- Modify: `pba-ms-gateway/src/auth-ms/users/users.controller.ts`
- Modify: `pba-ms-gateway/src/auth-ms/roles/roles.controller.ts`
- Create: `pba-ms-gateway/src/auth/guards/roles.guard.spec.ts`
- Create: `pba-ms-gateway/src/auth-ms/users/users.controller.spec.ts`

**Interfaces:**
- Consumes: `HasRoles` (`ROLES_KEY`), `X-Active-Role` UUID already validated by `JwtAuthGuard`.
- Produces: if `HasRoles` is set, the **active** role's `role.name` must be in that list. `UsersController` and `RolesController` use `@UseGuards(JwtAuthGuard, RolesGuard)` and `@HasRoles(Roles.ADMIN)`. `POST /users` is **not** `@Public()`.

- [ ] **Step 1: Write failing file-read tests**

`roles.guard.spec.ts`:

```ts
import { readFileSync } from 'fs';
import { join } from 'path';

const src = readFileSync(join(__dirname, 'roles.guard.ts'), 'utf8');

describe('RolesGuard active role', () => {
  it('checks the active role name, not any assigned role', () => {
    expect(src).toContain("headers['x-active-role']");
    expect(src).toContain('role.id');
    expect(src).toContain('role.name');
    expect(src).not.toContain('userRoleNames.includes');
  });
});
```

`users.controller.spec.ts`:

```ts
import { readFileSync } from 'fs';
import { join } from 'path';

const users = readFileSync(join(__dirname, 'users.controller.ts'), 'utf8');
const roles = readFileSync(join(__dirname, '../roles/roles.controller.ts'), 'utf8');

describe('admin HTTP gate', () => {
  it('protects users and roles with ADMIN', () => {
    expect(users).toContain('HasRoles');
    expect(users).toContain('Roles.ADMIN');
    expect(users).toContain('RolesGuard');
    expect(users).not.toContain('@Public()');
    expect(roles).toContain('HasRoles');
    expect(roles).toContain('Roles.ADMIN');
    expect(roles).toContain('RolesGuard');
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd pba-ms-gateway && npx jest src/auth/guards/roles.guard.spec.ts src/auth-ms/users/users.controller.spec.ts --no-coverage
```

Expected: FAIL (`@Public()` still on create; guard still uses `userRoleNames.includes`).

- [ ] **Step 3: Implement**

Replace the role check in `roles.guard.ts` (keep public / empty-roles early returns and the `findOneUser` call):

```ts
const request = context.switchToHttp().getRequest<ExtendedRequest>();
const userId = request.user?.id;
if (!userId) {
  throw new ForbiddenException('Usuario no autenticado');
}

const user: UserResponse = await this.usersService.findOneUser(userId);
if (!user || !user.user_role?.length) {
  throw new ForbiddenException('Acceso no autorizado, sin roles asignados');
}

const raw = request.headers['x-active-role'];
const activeRoleId = Array.isArray(raw) ? raw[0] : raw;
const active = user.user_role.find((ur: UserRoleResponse) => ur.role?.id === activeRoleId);
if (!active?.role?.name || !requiredRoles.includes(active.role.name as Roles)) {
  throw new ForbiddenException('No tiene permisos para acceder a este recurso');
}
return true;
```

`users.controller.ts` class:

```ts
import { Roles } from '@prisma/client';
import { HasRoles } from 'src/core/decorators/roles.decorator';
import { JwtAuthGuard, RolesGuard } from 'src/auth/guards';

@Controller('users')
@UseGuards(JwtAuthGuard, RolesGuard)
@HasRoles(Roles.ADMIN)
export class UsersController {
```

Delete `@Public()` and `import { Public } ...` from this file.

`roles.controller.ts` class: same `@UseGuards(JwtAuthGuard, RolesGuard)` and `@HasRoles(Roles.ADMIN)` (JwtAuthGuard is already there — add RolesGuard).

- [ ] **Step 4: Run tests to verify they pass**

Same command as Step 2. Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd pba-ms-gateway
git add src/auth/guards/roles.guard.ts src/auth/guards/roles.guard.spec.ts src/auth-ms/users/users.controller.ts src/auth-ms/users/users.controller.spec.ts src/auth-ms/roles/roles.controller.ts
git commit -m "$(cat <<'EOF'
Restrict users and roles APIs to the active ADMIN role.

EOF
)"
```

---

### Task 7: PUT `/users/:id` applies username, password, and `role_ids`

**Files:**
- Modify: `pba-ms-auth/src/users/users.service.ts`
- Create: `pba-ms-auth/src/users/users.service.update.spec.ts`

**Interfaces:**
- Consumes: `UpdateAuthUserDto` with optional `username`, `password`, `role_ids` from Task 5. `RolesService.setRoles({ user_id, roles_id })`.
- Produces: `updateAuthUser` applies every provided field in one call. Username update does **not** require `person`. Empty body still 400.

- [ ] **Step 1: Write the failing test**

```ts
import { readFileSync } from 'fs';
import { join } from 'path';

const src = readFileSync(join(__dirname, 'users.service.ts'), 'utf8');

describe('updateAuthUser admin edit', () => {
  it('can set roles and username without a person row', () => {
    expect(src).toContain('setRoles');
    expect(src).toContain('role_ids');
    expect(src).not.toContain('person_id: exists.person.id');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd pba-ms-auth && npx jest src/users/users.service.update.spec.ts --no-coverage
```

Expected: FAIL (`person_id: exists.person.id` still there).

- [ ] **Step 3: Replace `updateAuthUser`**

```ts
async updateAuthUser(id: string, data: UpdateAuthUserDto) {
  const exists = await this.userRepository.findOne(id, true);
  if (!exists) {
    throw new RpcException({
      statusCode: HttpStatus.BAD_REQUEST,
      message: `El usuario con id ${id} no existe`,
    });
  }

  const { password, username, role_ids } = data;
  if (!password && !username && !role_ids?.length) {
    throw new RpcException({
      statusCode: HttpStatus.BAD_REQUEST,
      message: 'No se ha enviado ningún dato para actualizar',
    });
  }

  if (password) {
    const isOldPassword = await bcrypt.compare(password, exists.password);
    if (isOldPassword) {
      throw new RpcException({
        statusCode: HttpStatus.BAD_REQUEST,
        message: 'Esta contraseña ya ha sido utilizada anteriormente, por favor elige una nueva',
      });
    }
    await this.userRepository.update({ id }, { password, is_first_login: true });
  }

  if (username) {
    const other = await this.userRepository.findOne(username);
    if (other && other.id !== id) {
      throw new RpcException({
        statusCode: HttpStatus.BAD_REQUEST,
        message: `El nombre de usuario ${username} ya existe`,
      });
    }
    await this.userRepository.update({ id }, { username });
  }

  if (role_ids?.length) {
    await this.rolesService.setRoles({ user_id: id, roles_id: role_ids });
  }

  return this.userRepository.findOne(id);
}
```

- [ ] **Step 4: Run test to verify it passes**

Same command. Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd pba-ms-auth
git add src/users/users.service.ts src/users/users.service.update.spec.ts
git commit -m "$(cat <<'EOF'
Update a user email, password, and roles in one PUT.

EOF
)"
```

---

### Task 8: Angular users CRUD, `roleGuard`, sidebar

**Files:**
- Create: `pmas-web-main/src/app/core/guards/role.guard.ts`
- Create: `pmas-web-main/src/app/core/guards/role.guard.spec.ts`
- Modify: `pmas-web-main/src/app/app.routes.ts`
- Modify: `pmas-web-main/src/app/components/sidebar/sidebar.ts`
- Modify: `pmas-web-main/src/app/components/sidebar/sidebar.html`
- Create: `pmas-web-main/src/app/components/sidebar/sidebar.spec.ts`
- Modify: `pmas-web-main/src/app/pages/admin/users/users.ts`
- Modify: `pmas-web-main/src/app/pages/admin/users/users.html`
- Create: `pmas-web-main/src/app/pages/admin/users/users.spec.ts`

**Interfaces:**
- Consumes: `activeRoleName === 'ADMIN'`, `POST/PUT ${GATEWAY_URL}/users`, `PATCH ${GATEWAY_URL}/users/inactive`.
- Produces: `roleGuard: CanActivateFn`. `User.id` / `Role.id` are `string`. Form: correo (`username`), password (required on create), `role_ids`. No `first_name` / `last_name` / extra email field.

- [ ] **Step 1: Write failing tests**

`role.guard.spec.ts`:

```ts
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const guard = readFileSync(resolve(import.meta.dirname, 'role.guard.ts'), 'utf8');
const routes = readFileSync(resolve(import.meta.dirname, '../../app.routes.ts'), 'utf8');

describe('roleGuard ADMIN', () => {
  it('is on users and roles routes and checks ADMIN', () => {
    expect(guard).toContain("activeRoleName() === 'ADMIN'");
    expect(guard).toContain('/control-panel');
    expect(routes).toContain('roleGuard');
    expect(routes).toMatch(/admin\/users[\s\S]{0,400}roleGuard/);
    expect(routes).toMatch(/admin\/roles[\s\S]{0,400}roleGuard/);
  });
});
```

`sidebar.spec.ts`:

```ts
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const ts = readFileSync(resolve(import.meta.dirname, 'sidebar.ts'), 'utf8');
const html = readFileSync(resolve(import.meta.dirname, 'sidebar.html'), 'utf8');

describe('sidebar ADMIN gate', () => {
  it('hides autenticacion and gestion unless ADMIN', () => {
    expect(ts).toContain('visibleGroups');
    expect(ts).toContain("activeRoleName() === 'ADMIN'");
    expect(html).toContain('visibleGroups()');
  });
});
```

`users.spec.ts`:

```ts
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const ts = readFileSync(resolve(import.meta.dirname, 'users.ts'), 'utf8');
const html = readFileSync(resolve(import.meta.dirname, 'users.html'), 'utf8');

describe('users admin CRUD', () => {
  it('calls gateway /users and never /auth/users', () => {
    expect(ts).toContain('${GATEWAY_URL}/users');
    expect(ts).toContain("http.put");
    expect(ts).toContain('/users/inactive');
    expect(ts).not.toContain('/auth/users');
    expect(ts).toContain('role_ids');
    expect(html).not.toContain('first_name');
    expect(html).not.toContain('last_name');
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd pmas-web-main && npx ng test --watch=false --include='**/role.guard.spec.ts' --include='**/sidebar.spec.ts' --include='**/admin/users/users.spec.ts'
```

Expected: FAIL (no `role.guard.ts`).

- [ ] **Step 3: Implement**

`role.guard.ts`:

```ts
import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { catchError, map, of } from 'rxjs';
import { AuthService } from '../services/auth.service';

export const roleGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  const allow = () =>
    auth.activeRoleName() === 'ADMIN' ? true : router.createUrlTree(['/control-panel']);

  if (auth.profile()) return allow();
  return auth.loadProfile().pipe(
    map(() => allow()),
    catchError(() => of(router.createUrlTree(['/login']))),
  );
};
```

`app.routes.ts`: import `roleGuard`. On `admin/users` and `admin/roles`:

```ts
canActivate: [roleGuard],
```

(parent already has `authGuard`.)

`sidebar.ts`: inject `AuthService`. Add:

```ts
private readonly auth = inject(AuthService);

visibleGroups(): SidebarGroup[] {
  if (this.auth.activeRoleName() === 'ADMIN') return this.groups;
  return this.groups.filter((g) => g.id !== 'autenticacion' && g.id !== 'gestion');
}
```

`sidebar.html`: change `@for (group of groups;` to `@for (group of visibleGroups();`.

`users.ts` — replace interfaces and save/delete (keep search/load/roles list):

```ts
export interface User {
  id: string;
  username: string;
  person?: { first_name: string; last_name: string };
  user_role?: { role: { id: string; name: string } }[];
  is_active?: boolean;
}

export interface Role {
  id: string;
  name: string;
}

form = signal({
  id: '',
  username: '',
  password: '',
  role_ids: [] as string[],
});

openCreate() {
  this.form.set({
    id: '',
    username: '',
    password: '',
    role_ids: this.roles()[0] ? [this.roles()[0].id] : [],
  });
  this.modalMode.set('create');
  this.modalError.set(null);
  this.modalOpen.set(true);
}

openEdit(user: User) {
  this.form.set({
    id: user.id,
    username: user.username,
    password: '',
    role_ids: user.user_role?.map((ur) => ur.role.id) ?? [],
  });
  this.modalMode.set('edit');
  this.modalError.set(null);
  this.modalOpen.set(true);
}

isRoleSelected(roleId: string): boolean {
  return this.form().role_ids.includes(roleId);
}

toggleRole(roleId: string) {
  this.form.update((f) => {
    const ids = f.role_ids.includes(roleId)
      ? f.role_ids.filter((id) => id !== roleId)
      : [...f.role_ids, roleId];
    return { ...f, role_ids: ids };
  });
}

save() {
  const f = this.form();
  const passwordOk = /^(?=.*[a-z])(?=.*[A-Z])(?=.*(?:\d|[^\w\s]))(?!.*[.\n]).*$/;
  if (!f.username) {
    this.modalError.set('El correo es obligatorio.');
    return;
  }
  if (!f.role_ids.length) {
    this.modalError.set('Elige al menos un rol.');
    return;
  }
  if (this.modalMode() === 'create') {
    if (!f.password || f.password.length < 8 || !passwordOk.test(f.password)) {
      this.modalError.set(
        'La contraseña debe tener al menos 8 caracteres, mayúscula, minúscula y un número o carácter especial.',
      );
      return;
    }
  } else if (f.password && (f.password.length < 8 || !passwordOk.test(f.password))) {
    this.modalError.set(
      'La contraseña debe tener al menos 8 caracteres, mayúscula, minúscula y un número o carácter especial.',
    );
    return;
  }
  this.saving.set(true);
  this.modalError.set(null);
  const payload: { username: string; password?: string; role_ids: string[] } = {
    username: f.username,
    role_ids: f.role_ids,
  };
  if (f.password) payload.password = f.password;
  const req =
    this.modalMode() === 'create'
      ? this.http.post(`${GATEWAY_URL}/users`, payload)
      : this.http.put(`${GATEWAY_URL}/users/${f.id}`, payload);
  req.subscribe({
    next: () => {
      this.saving.set(false);
      this.modalOpen.set(false);
      this.loadAll();
    },
    error: (err) => {
      this.saving.set(false);
      const msg = err.error?.message;
      this.modalError.set(Array.isArray(msg) ? msg[0] : (msg ?? 'Error al guardar.'));
    },
  });
}

doDelete() {
  const u = this.deleteTarget();
  if (!u) return;
  this.deleting.set(true);
  this.http
    .patch(`${GATEWAY_URL}/users/inactive`, {
      user_id: u.id,
      reason: 'Baja desde mesa de control',
    })
    .subscribe({
      next: () => {
        this.deleting.set(false);
        this.deleteTarget.set(null);
        this.loadAll();
      },
      error: () => {
        this.deleting.set(false);
        this.deleteTarget.set(null);
      },
    });
}
```

`users.html` modal body: delete the Nombre/Apellido grid and the extra Correo field. Relabel «Usuario *» to «Correo *» bound to `form().username` (`type="email"`). Keep password and role checkboxes. Table may keep `displayName(user)` (falls back to username).

- [ ] **Step 4: Run tests to verify they pass**

Same command as Step 2. Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd pmas-web-main
git add src/app/core/guards/role.guard.ts src/app/core/guards/role.guard.spec.ts src/app/app.routes.ts src/app/components/sidebar/sidebar.ts src/app/components/sidebar/sidebar.html src/app/components/sidebar/sidebar.spec.ts src/app/pages/admin/users/users.ts src/app/pages/admin/users/users.html src/app/pages/admin/users/users.spec.ts
git commit -m "$(cat <<'EOF'
Gate Usuarios to ADMIN and call the real /users API.

EOF
)"
```

---

### Task 9: Pipeline 1 s and one JPEG per camera

**Files:**
- Modify: `pmai-mai-core/settings.toml`
- Modify: `pmai-mai-core/src/pmai_core/settings.py`
- Modify: `pmai-mai-core/src/pmai_core/api/vision/schemas.py`
- Modify: `pmai-mai-core/src/pmai_core/api/vision/vision_controller.py`
- Create: `pmai-mai-core/tests/test_vision_pipeline_contract.py`

**Interfaces:**
- Consumes: existing `frame_to_jpeg_base64`.
- Produces: `result_interval_seconds = 1.0`. `thumb_max_width` default 480, `le=960`. `get_snapshot` calls `frame_to_jpeg_base64` once per camera with a frame; `preview_jpeg_base64=None`.

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_pipeline_interval_is_one_second():
    toml = (ROOT / "settings.toml").read_text()
    settings = (ROOT / "src/pmai_core/settings.py").read_text()
    assert "result_interval_seconds = 1.0" in toml
    assert "result_interval_seconds: float = 1.0" in settings
    assert "result_interval_seconds = 5.0" not in toml
    assert "result_interval_seconds: float = 5.0" not in settings


def test_snapshot_encodes_one_jpeg_and_null_preview():
    src = (ROOT / "src/pmai_core/api/vision/vision_controller.py").read_text()
    assert src.count("frame_to_jpeg_base64") == 1
    assert "preview_jpeg_base64=None" in src or "preview_jpeg_base64=None," in src
    schema = (ROOT / "src/pmai_core/api/vision/schemas.py").read_text()
    assert "default=480" in schema
    assert "le=960" in schema
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd pmai-mai-core && python3 -m pytest tests/test_vision_pipeline_contract.py -v
```

Expected: FAIL (still 5.0; two `frame_to_jpeg_base64`).

- [ ] **Step 3: Implement**

`settings.toml`: `result_interval_seconds = 1.0`

`settings.py` `PipelineSettings`: `result_interval_seconds: float = 1.0`

`schemas.py` `thumb_max_width`:

```python
thumb_max_width: int = Field(
    default=480,
    ge=32,
    le=960,
    validation_alias=AliasChoices("thumb_max_width", "thumbMaxWidth"),
)
```

In `vision_controller.py` replace the preview block with:

```python
thumb_b64 = frame_to_jpeg_base64(
    annotated_frame,
    max_width=req.thumb_max_width,
    jpeg_quality=82,
)
tiles.append(
    CameraStreamTile(
        camera_id=info.camera_id,
        source_type=info.source_type.value,
        device_path=info.device_path,
        name=info.name,
        resolution=list(info.resolution),
        fps=info.fps,
        status=info.status.value,
        has_frame=True,
        thumbnail_jpeg_base64=thumb_b64,
        preview_jpeg_base64=None,
    )
)
```

Keep `preview_jpeg_base64=None` on the no-frame branch too.

- [ ] **Step 4: Run test to verify it passes**

Same pytest command. Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd pmai-mai-core
git add settings.toml src/pmai_core/settings.py src/pmai_core/api/vision/schemas.py src/pmai_core/api/vision/vision_controller.py tests/test_vision_pipeline_contract.py
git commit -m "$(cat <<'EOF'
Emit vision results every second with a single camera JPEG.

EOF
)"
```

---

### Task 10: Vision page — objects first, no Preview, thumbs 480

**Files:**
- Modify: `pba-ms-gateway/src/mai-core-ms/vision/vision.gateway.ts`
- Create: `pba-ms-gateway/src/mai-core-ms/vision/vision.gateway.spec.ts`
- Modify: `pmas-web-main/src/app/pages/robotics-vision/vision-websocket.service.ts`
- Modify: `pmas-web-main/src/app/pages/robotics-vision/robotics-vision.ts`
- Modify: `pmas-web-main/src/app/pages/robotics-vision/robotics-vision.html`
- Create: `pmas-web-main/src/app/pages/robotics-vision/robotics-vision.spec.ts`

**Interfaces:**
- Consumes: Task 9 snapshot (`thumbnailJpegBase64`, `previewJpegBase64` always null, `globalObjects`).
- Produces: WS default `thumbMaxWidth: 480`, clamp max 960. Angular `setQuality` only `{ type: 'setQuality', thumbMaxWidth: 480 }` — if the client type still requires `previewMaxWidth`, send `previewMaxWidth: 480` as a ignored leftover **or** make it optional; do **not** send `setSelection`. Page order: header → objects cards → cameras grid. No `previewSrc`, no word `Preview`.

- [ ] **Step 1: Write failing tests**

Gateway `vision.gateway.spec.ts`:

```ts
import { readFileSync } from 'fs';
import { join } from 'path';

const src = readFileSync(join(__dirname, 'vision.gateway.ts'), 'utf8');

describe('vision gateway thumb size', () => {
  it('defaults thumbs to 480 and allows 960', () => {
    expect(src).toContain('thumbMaxWidth: 480');
    expect(src).toContain('Math.min(960');
  });
});
```

`robotics-vision.spec.ts`:

```ts
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const html = readFileSync(resolve(import.meta.dirname, 'robotics-vision.html'), 'utf8');
const ts = readFileSync(resolve(import.meta.dirname, 'robotics-vision.ts'), 'utf8');
const ws = readFileSync(resolve(import.meta.dirname, 'vision-websocket.service.ts'), 'utf8');

describe('vision objects-first layout', () => {
  it('shows objects before cameras and drops Preview', () => {
    const objectsAt = html.indexOf('Objetos observados');
    const camerasAt = html.indexOf('Cámaras');
    expect(objectsAt).toBeGreaterThan(-1);
    expect(camerasAt).toBeGreaterThan(objectsAt);
    expect(html).not.toContain('Preview');
    expect(html).not.toContain('text-slate-');
    expect(html).not.toContain('text-[9px]');
    expect(html).not.toContain('text-[10px]');
    expect(html).not.toContain('industrial-grid');
    expect(ts).not.toContain('previewSrc');
    expect(ws).toContain('thumbMaxWidth: 480');
    expect(ws).not.toContain('setSelection');
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd pba-ms-gateway && npx jest src/mai-core-ms/vision/vision.gateway.spec.ts --no-coverage
cd pmas-web-main && npx ng test --watch=false --include='**/robotics-vision.spec.ts'
```

Expected: FAIL (`Preview` still in HTML; gateway still `thumbMaxWidth: 160`).

- [ ] **Step 3: Implement**

`vision.gateway.ts` initial state: `thumbMaxWidth: 480`. In `setQuality`:

```ts
state.thumbMaxWidth = Math.min(960, Math.max(32, Math.floor(msg.thumbMaxWidth)));
```

`vision-websocket.service.ts` `onopen`:

```ts
this.sendClientMessage({ type: 'setQuality', thumbMaxWidth: 480, previewMaxWidth: 480 });
```

Delete `selectCamera` (or leave unused but **do not call it**). Remove `setSelection` from this file.

Replace `robotics-vision.ts` with:

```ts
import { Component, inject, OnDestroy, OnInit } from '@angular/core';
import { VisionWebSocketService } from './vision-websocket.service';
import type { VisionCameraTile } from './vision.types';

@Component({
  selector: 'app-robotics-vision',
  templateUrl: './robotics-vision.html',
})
export class RoboticsVision implements OnInit, OnDestroy {
  readonly vision = inject(VisionWebSocketService);

  ngOnInit(): void {
    this.vision.connect();
  }

  ngOnDestroy(): void {
    this.vision.disconnect();
  }

  thumbDataUrl(tile: VisionCameraTile): string | null {
    if (!tile.hasFrame || !tile.thumbnailJpegBase64) return null;
    return `data:image/jpeg;base64,${tile.thumbnailJpegBase64}`;
  }

  objectImageSrc(base64: string | null): string | null {
    if (!base64) return null;
    return `data:image/jpeg;base64,${base64}`;
  }

  formatPct(conf: number): string {
    return `${Math.round(conf * 100)}%`;
  }
}
```

Replace `robotics-vision.html` with:

```html
<div class="min-h-[calc(100vh-6rem)]">

  <header class="mb-8 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
    <div class="flex items-start gap-4">
      <div class="flex size-12 shrink-0 items-center justify-center rounded-xl bg-rail text-on-rail">
        <span class="material-symbols-outlined" style="font-size: 1.5rem; font-variation-settings: 'FILL' 1;">videocam</span>
      </div>
      <div>
        <h1 class="font-headline text-2xl font-bold tracking-tight text-on-surface">Visión</h1>
        <p class="mt-1 max-w-xl text-sm text-on-surface-variant">
          Objetos que el detector ya identificó, y las cámaras a tamaño útil.
        </p>
      </div>
    </div>
    <p class="text-xs font-semibold text-on-surface-variant">
      <span [class.text-primary]="vision.connectionState() === 'connected'"
            [class.text-error]="vision.connectionState() === 'error'">
        WS: {{ vision.connectionState() }}
      </span>
      @if (vision.snapshot(); as snap) {
        <span class="ml-2 tabular-nums">v{{ snap.version }}</span>
      }
    </p>
  </header>

  @if (vision.lastError(); as err) {
    <div class="mb-6 rounded-xl border border-error/40 bg-error-container px-4 py-3 text-sm text-on-error-container">
      {{ err }}
    </div>
  }

  <section class="mb-8" aria-label="Objetos observados">
    <div class="mb-4 flex flex-wrap items-end justify-between gap-2">
      <h2 class="font-headline text-lg font-bold text-on-surface">Objetos observados</h2>
      @if (vision.snapshot(); as snap) {
        <p class="text-xs text-on-surface-variant">
          ReID: {{ snap.reidSummary.crossCameraIdentities }} / {{ snap.reidSummary.totalIdentities }} cross-cámara
        </p>
      }
    </div>
    <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      @for (obj of vision.snapshot()?.globalObjects ?? []; track obj.id_global) {
        <article class="rounded-xl border border-outline bg-surface p-4">
          <div class="flex items-start gap-4">
            @if (objectImageSrc(obj.image_base64); as imgSrc) {
              <img [src]="imgSrc" alt="" class="size-32 shrink-0 rounded-lg object-cover border border-outline" />
            } @else {
              <div class="size-32 shrink-0 rounded-lg border border-dashed border-outline flex items-center justify-center text-xs text-on-surface-variant">Sin img</div>
            }
            <div class="min-w-0">
              <p class="font-headline text-lg font-bold text-on-surface truncate">{{ obj.etiqueta }}</p>
              <p class="mt-1 text-sm text-on-surface">{{ formatPct(obj.confianza) }}</p>
              <p class="mt-2 text-xs text-on-surface-variant truncate">{{ obj.id_global }}</p>
              <p class="mt-1 text-xs text-on-surface-variant">{{ obj.cameras_seen.join(', ') || '—' }}</p>
            </div>
          </div>
        </article>
      } @empty {
        <p class="col-span-full text-sm text-on-surface-variant">No hay objetos en este snapshot.</p>
      }
    </div>
  </section>

  <section aria-label="Cámaras">
    <h2 class="font-headline text-lg font-bold text-on-surface mb-4">Cámaras</h2>
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      @for (cam of vision.snapshot()?.cameras ?? []; track cam.cameraId) {
        <article class="rounded-xl overflow-hidden border border-outline bg-surface">
          <div class="aspect-video bg-rail/10">
            @if (thumbDataUrl(cam); as src) {
              <img [src]="src" [alt]="cam.name || cam.cameraId" class="w-full h-full object-cover" />
            } @else {
              <div class="w-full h-full flex items-center justify-center text-sm text-on-surface-variant">Sin frame</div>
            }
          </div>
          <div class="px-3 py-2 border-t border-outline">
            <p class="text-sm font-semibold text-on-surface truncate">{{ cam.name || cam.cameraId }}</p>
            <p class="text-xs text-on-surface-variant">{{ cam.status }} · {{ cam.fps }} fps</p>
          </div>
        </article>
      } @empty {
        <p class="col-span-full text-sm text-on-surface-variant">Sin cámaras en el snapshot.</p>
      }
    </div>
  </section>
</div>
```

Empty-cameras message sits **under** the objects block (in the Cámaras section), as the spec asks.

- [ ] **Step 4: Run tests to verify they pass**

Same commands as Step 2. Expected: PASS. If `ws.not.toContain('setSelection')` fails because `vision.types.ts` still declares the type, that is fine — the test reads the **service** file only.

- [ ] **Step 5: Commit in each owning repo**

```bash
cd pba-ms-gateway
git add src/mai-core-ms/vision/vision.gateway.ts src/mai-core-ms/vision/vision.gateway.spec.ts
git commit -m "$(cat <<'EOF'
Default vision thumbs to 480 pixels.

EOF
)"

cd pmas-web-main
git add src/app/pages/robotics-vision/vision-websocket.service.ts src/app/pages/robotics-vision/robotics-vision.ts src/app/pages/robotics-vision/robotics-vision.html src/app/pages/robotics-vision/robotics-vision.spec.ts
git commit -m "$(cat <<'EOF'
Put observed objects above full-size cameras and drop Preview.

EOF
)"
```

---

### Task 11: PRODUCT.md and DESIGN.md

**Files:**
- Modify: `PRODUCT.md`
- Modify: `DESIGN.md`

**Interfaces:**
- Consumes: shipped Tasks 1–10.
- Produces: principle 5 no longer lists auth/visión as pending. Evidence includes this spec. DESIGN Layout bullets for login flash and visión.

- [ ] **Step 1: Edit PRODUCT.md**

Replace principle 5 with:

```
5. **Sesión y visión** — si el token no vale, el login dice «Tu sesión venció. Entra de nuevo.» Usuarios y Roles son de ADMIN. En visión los objetos van arriba y las cámaras debajo, sin Preview.
```

Add to Evidence:

```
- Spec: `docs/superpowers/specs/2026-10-14-auth-session-admin-gate-vision-layout-design.md`
```

In Product Purpose, keep operating as success; do not mention Davivienda or `example/`.

- [ ] **Step 2: Edit DESIGN.md Layout**

After the Motion Studio bullet, add:

```
- Login: aviso de sesión vencida sobre el formulario (icono `schedule`, 14 px, borde error). No toast.
- Visión: cabecera con pozo navy; objetos observados en tarjetas grandes (recorte ≥ 128 px) a ancho completo; cámaras debajo en cuadrícula a ~480 px; sin Preview.
```

Do not change the palette table.

- [ ] **Step 3: Commit**

```bash
cd /home/personal/Projects/ulibre-prometeo/pba-launcher
git add PRODUCT.md DESIGN.md
git commit -m "$(cat <<'EOF'
Record session expiry and vision layout on PRODUCT and DESIGN.

EOF
)"
```

---

## Self-review (coverage)

| Spec requirement | Task |
|---|---|
| 401/403 → logout + login copy | 2, 3 |
| POST login not that path | 3 |
| JWT `exp` + guest/auth guards | 1, 4 |
| `loadProfile` flash + shell refresh | 2, 4 |
| WS 4001 | 4 |
| POST/PUT `/users` password + `role_ids`, not public | 5, 6 |
| Validate plaintext then hash | 5 |
| PUT applies username/password/roles | 7 |
| PATCH inactive | 8 |
| `HasRoles(ADMIN)` + active role | 6 |
| `roleGuard` + sidebar | 8 |
| Pipeline 1.0, one JPEG, thumb 480 | 9, 10 |
| Objects first, no Preview, identity | 10 |
| PRODUCT/DESIGN | 11 |
| Turn / declarePoema / studio untouched | Global Constraints |

No TBD. `logout('expired')` and `LOGIN_FLASH_KEY` names are stable across Tasks 2–4. `role_ids` is the same field in DTOs, repository, Angular form, and `setRoles({ roles_id })`.
