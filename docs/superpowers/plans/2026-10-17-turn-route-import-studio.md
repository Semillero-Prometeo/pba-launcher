# Turn route, paired import, and studio Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Management routes chat and microphone to OpenAI básico + speak or to the mai-core turn; Angular imports Qt gesture+NEUTRO pairs; the panel hides Neutro without a track and shows Arduino; Motion Studio groups the library, drops list Play, shows full block params, and warns that generated neutro needs a human.

**Architecture:** One router in `pba-ms-management` (`ChatRouteStore` JSON + `ChatService.chat`). Mic calls `MANAGEMENT_MS.chatService.chat`. Import pairing lives in Angular. Panel and studio poll `GET /sequence/arduinos`. Studio helpers live in `library-view.js`.

**Tech Stack:** NestJS 11 + Jest (`pba-ms-management/test`); Nest gateway; Python 3.12 + pytest (`pmai-mai-core`); Angular 21 + Vitest; Motion Studio static JS + `node --test`.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-10-17-turn-route-import-studio-design.md`.
- Defaults: `{ "automationEnabled": true, "selectedModel": "complejo" }`.
- `selectedModel` is only `basico` | `complejo`.
- Básico: `chatStructured` + `speak`, `{ reply, fuente: "OpenAI", movimientos: [] }`. Never fall through to the turn on OpenAI 502.
- Complejo: `maiCore.ask` only. No extra `speak`.
- `declarePoema` stays OpenAI + speak. Do not read the route JSON.
- Do not change `responder()`, BLIP, Milvus, Gemma, `getActions`, or the Normal → 1 s → neutro queue.
- Import does not call `generateNeutroFrom`. Companion `NEUTRO` files are the neutro track.
- Pair key: lowercase, strip `\bneutro\b`, collapse spaces. Version stays in the key.
- Edit only the owning repo. Commits: management, gateway, mai-core, web-main, motion-studio, then launcher docs.
- No Prisma settings table. No websocket for the picker.

---

## File structure

| File | Responsibility |
|---|---|
| `pba-ms-management/src/chat/chat-route.store.ts` | Read/write `chat-route.json` |
| `pba-ms-management/src/chat/chat.service.ts` | Route `chat()`; get/set automation and model |
| `pba-ms-management/src/chat/chat.controller.ts` | NATS `getRoute`, `setAutomation`, `setModel` |
| `pba-ms-management/test/chat-route.spec.ts` | Store + router tests |
| `pba-ms-gateway/src/management-ms/chat/chat.controller.ts` | HTTP GET/PATCH route |
| `pmai-mai-core/src/pmai_core/resources/audio/service.py` | Mic → management.chat |
| `pmai-mai-core/src/pmai_core/app.py` | `bind_chat` |
| `pmai-mai-core/tests/test_audio_dispatch.py` | Dispatch does not call `ask_async` |
| `pmas-web-main/src/app/pages/robotics-chat/*` | Toggle + picker |
| `pmas-web-main/src/app/pages/sequences/origin-sequence.ts` | Parse without generated neutro |
| `pmas-web-main/src/app/pages/sequences/origin-pair.ts` | Pair key + suggest pairs |
| `pmas-web-main/src/app/pages/sequences/sequences.ts` / `.html` | Large pairing dialog |
| `pmas-web-main/src/app/pages/control-panel/*` | Hide Neutro; Arduino chip; playable without neutro |
| `pmas-web-main/src/app/pages/control-panel/arduino-status.ts` | Chip label |
| `pmas-web-motion-studio/src/static/library-view.js` | Groups, card text, Arduino, warning copy |
| `pmas-web-motion-studio/src/static/editor.js` / `index.html` / `editor.css` | Use helpers; drop list Play |
| `AGENTS.md`, `.cursor/rules/rone-overview.mdc` | Chat/mic go through `chatService.chat` |

---

### Task 1: Chat route JSON store

**Files:**
- Create: `pba-ms-management/src/chat/chat-route.store.ts`
- Create: `pba-ms-management/test/chat-route.spec.ts`
- Modify: `pba-ms-management/.gitignore` (add `/data/chat-route.json`)
- Modify: `pba-ms-management/.env.template` (optional `MS_MANAGEMENT_CHAT_ROUTE_PATH=`)
- Modify: `pba-ms-management/src/core/settings/app.setting.ts` (optional Joi key)
- Modify: `docker-compose.yml` (`pba-ms-management` volume `./pba-ms-management/data:/usr/src/app/data`)

**Interfaces:**
- Consumes: `process.env.MS_MANAGEMENT_CHAT_ROUTE_PATH` or `path.join(process.cwd(), 'data', 'chat-route.json')`.
- Produces: `ChatRouteState { automationEnabled: boolean; selectedModel: 'basico' | 'complejo' }`. `ChatRouteStore.read(): ChatRouteState`. `ChatRouteStore.write(next: ChatRouteState): ChatRouteState`.

- [ ] **Step 1: Write the failing store tests**

Create `pba-ms-management/test/chat-route.spec.ts`:

```typescript
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import { ChatRouteStore } from '../src/chat/chat-route.store';

describe('ChatRouteStore', () => {
  let filePath: string;

  beforeEach(() => {
    filePath = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'chat-route-')), 'chat-route.json');
    process.env.MS_MANAGEMENT_CHAT_ROUTE_PATH = filePath;
  });

  it('creates defaults when the file is missing', () => {
    const store = new ChatRouteStore();
    expect(store.read()).toEqual({ automationEnabled: true, selectedModel: 'complejo' });
    expect(fs.existsSync(filePath)).toBe(true);
  });

  it('recreates defaults when the file is corrupt', () => {
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    fs.writeFileSync(filePath, '{nope');
    const store = new ChatRouteStore();
    expect(store.read()).toEqual({ automationEnabled: true, selectedModel: 'complejo' });
  });

  it('persists a write', () => {
    const store = new ChatRouteStore();
    store.write({ automationEnabled: false, selectedModel: 'basico' });
    expect(new ChatRouteStore().read()).toEqual({ automationEnabled: false, selectedModel: 'basico' });
  });
});
```

- [ ] **Step 2: Run the store tests to verify they fail**

From `pba-ms-management`:

```bash
npm test -- --testPathPattern=chat-route.spec
```

Expected: FAIL. `Cannot find module '../src/chat/chat-route.store'`.

- [ ] **Step 3: Implement the store**

Create `pba-ms-management/src/chat/chat-route.store.ts`:

```typescript
import { Injectable } from '@nestjs/common';
import * as fs from 'fs';
import * as path from 'path';

export type ChatModel = 'basico' | 'complejo';

export interface ChatRouteState {
  automationEnabled: boolean;
  selectedModel: ChatModel;
}

export const DEFAULT_CHAT_ROUTE: ChatRouteState = {
  automationEnabled: true,
  selectedModel: 'complejo',
};

@Injectable()
export class ChatRouteStore {
  private readonly filePath: string;

  constructor() {
    this.filePath =
      process.env.MS_MANAGEMENT_CHAT_ROUTE_PATH?.trim() ||
      path.join(process.cwd(), 'data', 'chat-route.json');
  }

  read(): ChatRouteState {
    try {
      const raw = fs.readFileSync(this.filePath, 'utf8');
      const parsed = JSON.parse(raw) as Partial<ChatRouteState>;
      const selectedModel = parsed.selectedModel === 'basico' ? 'basico' : 'complejo';
      const automationEnabled = parsed.automationEnabled === false ? false : true;
      const state: ChatRouteState = { automationEnabled, selectedModel };
      if (!fs.existsSync(this.filePath)) {
        return this.write(state);
      }
      return state;
    } catch {
      return this.write(DEFAULT_CHAT_ROUTE);
    }
  }

  write(next: ChatRouteState): ChatRouteState {
    fs.mkdirSync(path.dirname(this.filePath), { recursive: true });
    fs.writeFileSync(this.filePath, `${JSON.stringify(next, null, 2)}\n`, 'utf8');
    return next;
  }
}
```

Add `/data/chat-route.json` to `pba-ms-management/.gitignore`. Keep the `data/` directory mountable.

In `app.setting.ts` Joi object add:

```typescript
MS_MANAGEMENT_CHAT_ROUTE_PATH: Joi.string().optional().allow(''),
```

In `docker-compose.yml` under `pba-ms-management.volumes` add:

```yaml
      - ./pba-ms-management/data:/usr/src/app/data
```

In `.env.template` add `MS_MANAGEMENT_CHAT_ROUTE_PATH=`.

- [ ] **Step 4: Run the store tests to verify they pass**

```bash
npm test -- --testPathPattern=chat-route.spec
```

Expected: PASS (3 tests). The later ChatService tests are not in this file yet.

- [ ] **Step 5: Commit in `pba-ms-management` and the launcher compose/template**

```bash
cd pba-ms-management
git add src/chat/chat-route.store.ts test/chat-route.spec.ts .gitignore .env.template src/core/settings/app.setting.ts
git commit -m "$(cat <<'EOF'
Add persistent chat route JSON store.

EOF
)"
```

Launcher: add only the compose volume and any template line that lives in the launcher `.env.template` if you mirrored it. Do not commit secrets.

---

### Task 2: `ChatService` routes básico vs complejo

**Files:**
- Modify: `pba-ms-management/src/chat/chat.service.ts`
- Modify: `pba-ms-management/src/chat/chat.controller.ts`
- Modify: `pba-ms-management/src/chat/chat.module.ts`
- Modify: `pba-ms-management/test/chat-route.spec.ts`

**Interfaces:**
- Consumes: `ChatRouteStore.read/write`. `OpenaiIntegrationService.chatStructured`. `MsRoboticsService.speak`. `MsMaiCoreService.ask`.
- Produces: `getRoute(): ChatRouteState`. `setAutomation(enabled: boolean): ChatRouteState` (off forces `basico`). `setModel(model: ChatModel): ChatRouteState` (complejo + off → `RpcException` 409). `chat()` as spec table.

- [ ] **Step 1: Append failing router tests**

Append to `pba-ms-management/test/chat-route.spec.ts`:

```typescript
import { RpcException } from '@nestjs/microservices';
import { ChatService } from '../src/chat/chat.service';

function serviceWith(state: { automationEnabled: boolean; selectedModel: 'basico' | 'complejo' }) {
  const store = {
    read: () => ({ ...state }),
    write: (next: typeof state) => {
      Object.assign(state, next);
      return { ...state };
    },
  };
  const openai = { chatStructured: jest.fn().mockResolvedValue({ reply: 'hola' }) };
  const robotics = { speak: jest.fn().mockResolvedValue(undefined) };
  const maiCore = { ask: jest.fn().mockResolvedValue({ reply: 'turno', fuente: 'caché', movimientos: [] }) };
  const service = new ChatService(openai as never, robotics as never, maiCore as never, store as never);
  return { service, openai, robotics, maiCore, store };
}

describe('ChatService route', () => {
  it('uses OpenAI and speak when automation is off', async () => {
    const { service, openai, robotics, maiCore } = serviceWith({
      automationEnabled: false,
      selectedModel: 'basico',
    });
    const res = await service.chat({ message: 'hola' });
    expect(openai.chatStructured).toHaveBeenCalledWith({ message: 'hola' });
    expect(robotics.speak).toHaveBeenCalledWith({ message: 'hola' });
    expect(maiCore.ask).not.toHaveBeenCalled();
    expect(res).toEqual({ reply: 'hola', fuente: 'OpenAI', movimientos: [] });
  });

  it('uses OpenAI when automation is on and model is basico', async () => {
    const { service, maiCore } = serviceWith({ automationEnabled: true, selectedModel: 'basico' });
    await service.chat({ message: 'hola' });
    expect(maiCore.ask).not.toHaveBeenCalled();
  });

  it('uses mai-core when automation is on and model is complejo', async () => {
    const { service, openai, robotics, maiCore } = serviceWith({
      automationEnabled: true,
      selectedModel: 'complejo',
    });
    const res = await service.chat({ message: 'hola' });
    expect(maiCore.ask).toHaveBeenCalledWith('hola');
    expect(openai.chatStructured).not.toHaveBeenCalled();
    expect(robotics.speak).not.toHaveBeenCalled();
    expect(res.fuente).toBe('caché');
  });

  it('forces basico when automation is turned off', () => {
    const state = { automationEnabled: true, selectedModel: 'complejo' as const };
    const { service } = serviceWith(state);
    expect(service.setAutomation(false)).toEqual({ automationEnabled: false, selectedModel: 'basico' });
  });

  it('rejects complejo while automation is off', () => {
    const { service } = serviceWith({ automationEnabled: false, selectedModel: 'basico' });
    try {
      service.setModel('complejo');
      throw new Error('expected RpcException');
    } catch (err) {
      expect(err).toBeInstanceOf(RpcException);
      expect((err as RpcException).getError()).toEqual({
        statusCode: 409,
        message: 'Los turnos automáticos están apagados',
      });
    }
  });
});
```

- [ ] **Step 2: Run the new tests to verify they fail**

```bash
npm test -- --testPathPattern=chat-route.spec
```

Expected: FAIL on `ChatService` constructor arity or missing methods.

- [ ] **Step 3: Route chat and expose get/set**

Replace `pba-ms-management/src/chat/chat.service.ts` with:

```typescript
import { Injectable, Logger } from '@nestjs/common';
import { RpcException } from '@nestjs/microservices';
import { MsMaiCoreService } from 'src/ms-mai-core-integration/ms-mai-core.service';
import { MsRoboticsService } from 'src/ms-robotics-integration/ms-robotics.service';
import { ChatStructuredRequestDto } from 'src/openai-integration/dto/chat-structured-request.dto';
import { ChatStructuredResponseDto } from 'src/openai-integration/dto/chat-structured-response.dto';
import { OpenaiIntegrationService } from 'src/openai-integration/openai-integration.service';
import { ChatModel, ChatRouteState, ChatRouteStore } from './chat-route.store';

@Injectable()
export class ChatService {
  private readonly logger = new Logger(ChatService.name);

  constructor(
    private readonly openaiIntegrationService: OpenaiIntegrationService,
    private readonly msRoboticsService: MsRoboticsService,
    private readonly maiCore: MsMaiCoreService,
    private readonly routeStore: ChatRouteStore,
  ) {}

  getRoute(): ChatRouteState {
    return this.routeStore.read();
  }

  setAutomation(enabled: boolean): ChatRouteState {
    const current = this.routeStore.read();
    const selectedModel: ChatModel = enabled ? current.selectedModel : 'basico';
    return this.routeStore.write({ automationEnabled: enabled, selectedModel });
  }

  setModel(model: ChatModel): ChatRouteState {
    const current = this.routeStore.read();
    if (model === 'complejo' && !current.automationEnabled) {
      throw new RpcException({
        statusCode: 409,
        message: 'Los turnos automáticos están apagados',
      });
    }
    return this.routeStore.write({ ...current, selectedModel: model });
  }

  async chat(chatStructuredRequestDto: ChatStructuredRequestDto): Promise<ChatStructuredResponseDto> {
    const route = this.routeStore.read();
    const useTurn = route.automationEnabled && route.selectedModel === 'complejo';
    if (useTurn) {
      this.logger.log(`Asking mai-core: ${chatStructuredRequestDto.message}`);
      const response = await this.maiCore.ask(chatStructuredRequestDto.message);
      this.logger.log(`mai-core replied fuente=${response.fuente ?? ''}`);
      return response;
    }
    this.logger.log(`Asking OpenAI básico: ${chatStructuredRequestDto.message}`);
    const dto = await this.openaiIntegrationService.chatStructured({
      message: chatStructuredRequestDto.message,
    });
    await this.msRoboticsService.speak({ message: dto.reply });
    return { reply: dto.reply, fuente: 'OpenAI', movimientos: [] };
  }

  async declarePoema(): Promise<ChatStructuredResponseDto> {
    const poema = await this.openaiIntegrationService.chatStructured({
      message: 'Declara un poema para Diana Serrano, con un tono romantico y amoroso',
    });
    await this.msRoboticsService.speak({ message: poema.reply });
    return poema;
  }
}
```

Register `ChatRouteStore` in `chat.module.ts` `providers`.

Add to `chat.controller.ts`:

```typescript
import { ChatModel, ChatRouteState } from './chat-route.store';

  @MessagePattern(`${MANAGEMENT_MS}.chatService.getRoute`)
  getRoute(): ChatRouteState {
    return this.chatService.getRoute();
  }

  @MessagePattern(`${MANAGEMENT_MS}.chatService.setAutomation`)
  setAutomation(@Payload() body: { enabled: boolean }): ChatRouteState {
    return this.chatService.setAutomation(Boolean(body?.enabled));
  }

  @MessagePattern(`${MANAGEMENT_MS}.chatService.setModel`)
  setModel(@Payload() body: { model: ChatModel }): ChatRouteState {
    return this.chatService.setModel(body.model);
  }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
npm test -- --testPathPattern=chat-route.spec
```

Expected: PASS.

- [ ] **Step 5: Commit in `pba-ms-management`**

```bash
git add src/chat/chat.service.ts src/chat/chat.controller.ts src/chat/chat.module.ts test/chat-route.spec.ts
git commit -m "$(cat <<'EOF'
Route chat through stored basic or turn model.

EOF
)"
```

---

### Task 3: Gateway HTTP for the route

**Files:**
- Modify: `pba-ms-gateway/src/management-ms/chat/chat.controller.ts`
- Create: `pba-ms-gateway/src/management-ms/chat/dto/set-automation.dto.ts`
- Create: `pba-ms-gateway/src/management-ms/chat/dto/set-model.dto.ts`

**Interfaces:**
- Consumes: NATS subjects from Task 2.
- Produces: `GET /chat/route` (JWT). `PATCH /chat/route/automation` (JWT + `HasRoles(Roles.ADMIN)`). `PATCH /chat/route/model` (JWT). `POST /chat/question` unchanged.

- [ ] **Step 1: Add DTOs**

`set-automation.dto.ts`:

```typescript
import { IsBoolean } from 'class-validator';

export class SetAutomationDto {
  @IsBoolean()
  enabled: boolean;
}
```

`set-model.dto.ts`:

```typescript
import { IsIn, IsString } from 'class-validator';

export class SetModelDto {
  @IsString()
  @IsIn(['basico', 'complejo'])
  model: 'basico' | 'complejo';
}
```

- [ ] **Step 2: Add HTTP handlers**

Update imports on `chat.controller.ts` and add methods. Class already has `@UseGuards(JwtAuthGuard)`. Method-level RolesGuard for automation:

```typescript
import { Body, Controller, Get, Inject, Patch, Post, UseGuards } from '@nestjs/common';
import { Roles } from '@prisma/client';
import { JwtAuthGuard, RolesGuard } from 'src/auth/guards';
import { HasRoles } from 'src/core/decorators/roles.decorator';
import { SetAutomationDto } from './dto/set-automation.dto';
import { SetModelDto } from './dto/set-model.dto';

  @Get('route')
  getRoute() {
    return this.client.send(`${MANAGEMENT_MS}.chatService.getRoute`, {}).pipe(
      catchError((error) => {
        throw new RpcException(error);
      }),
    );
  }

  @Patch('route/automation')
  @UseGuards(RolesGuard)
  @HasRoles(Roles.ADMIN)
  setAutomation(@Body() body: SetAutomationDto) {
    return this.client.send(`${MANAGEMENT_MS}.chatService.setAutomation`, body).pipe(
      catchError((error) => {
        throw new RpcException(error);
      }),
    );
  }

  @Patch('route/model')
  setModel(@Body() body: SetModelDto) {
    return this.client.send(`${MANAGEMENT_MS}.chatService.setModel`, body).pipe(
      catchError((error) => {
        throw new RpcException(error);
      }),
    );
  }
```

Keep existing `question` and `poema` posts.

- [ ] **Step 3: Typecheck gateway**

From `pba-ms-gateway`:

```bash
npx tsc --noEmit -p tsconfig.json
```

Expected: exit 0.

- [ ] **Step 4: Commit in `pba-ms-gateway`**

```bash
git add src/management-ms/chat
git commit -m "$(cat <<'EOF'
Expose chat route get and patch over HTTP.

EOF
)"
```

---

### Task 4: Microphone uses `chatService.chat`

**Files:**
- Modify: `pmai-mai-core/src/pmai_core/resources/audio/service.py`
- Modify: `pmai-mai-core/src/pmai_core/app.py`
- Create: `pmai-mai-core/tests/test_audio_dispatch.py`

**Interfaces:**
- Consumes: `ManagementMsService.chat(message: str) -> None` (already sync NATS).
- Produces: `AudioService.bind_chat(chat)`. `_dispatch_transcript` calls `chat(transcript)` and never `turn.ask_async`.

- [ ] **Step 1: Write the failing dispatch test**

Create `pmai-mai-core/tests/test_audio_dispatch.py`:

```python
from pmai_core.resources.audio.service import AudioService
from pmai_core.settings import Settings


def test_dispatch_transcript_calls_bound_chat_not_turn() -> None:
    calls: list[str] = []
    turn_calls: list[str] = []

    class FakeTurn:
        def ask_async(self, transcript: str, source: str) -> None:
            turn_calls.append(f"{source}:{transcript}")

    service = AudioService(Settings())
    service.bind_chat(calls.append)
    service.bind_turn(FakeTurn())
    service._dispatch_transcript("hey fede hola")
    assert calls == ["hey fede hola"]
    assert turn_calls == []
```

- [ ] **Step 2: Run the test to verify it fails**

From `pmai-mai-core`:

```bash
python3 -m pytest tests/test_audio_dispatch.py -v
```

Expected: FAIL. `bind_chat` missing or `_dispatch_transcript` still calls `ask_async`.

- [ ] **Step 3: Bind chat and dispatch to it**

In `AudioService.__init__` add `self._chat: Any | None = None`.

Add:

```python
    def bind_chat(self, chat: Any) -> None:
        self._chat = chat
```

Replace `_dispatch_transcript` with:

```python
    def _dispatch_transcript(self, transcript: str) -> None:
        chat = self._chat
        if chat is None:
            logger.error("audio_chat_unbound")
            return
        try:
            chat(transcript)
        except Exception as exc:
            logger.error("audio_voice_chat_failed", error=str(exc), exc_info=exc)
```

Remove the `run_coroutine_threadsafe` / `_log_voice_turn_failure` path from this method. Keep `_log_voice_turn_failure` only if something else uses it; if unused, delete it.

In `app.py` after creating `audio_service`:

```python
    from pmai_core.api.management_ms.management_ms_service import ManagementMsService

    management = ManagementMsService()
    audio_service.bind_chat(management.chat)
```

Leave `audio_service.bind_turn(turn)` in place so other code can still inspect the turn. Dispatch must not use it.

- [ ] **Step 4: Run the test to verify it passes**

```bash
python3 -m pytest tests/test_audio_dispatch.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit in `pmai-mai-core`**

```bash
git add src/pmai_core/resources/audio/service.py src/pmai_core/app.py tests/test_audio_dispatch.py
git commit -m "$(cat <<'EOF'
Send microphone transcripts through management chat.

EOF
)"
```

---

### Task 5: Chat UI toggle and picker

**Files:**
- Modify: `pmas-web-main/src/app/pages/robotics-chat/robotics-chat.ts`
- Modify: `pmas-web-main/src/app/pages/robotics-chat/robotics-chat.html`
- Modify: `AGENTS.md`
- Modify: `.cursor/rules/rone-overview.mdc`

**Interfaces:**
- Consumes: `GET /chat/route` → `{ automationEnabled, selectedModel }`. `PATCH /chat/route/automation` `{ enabled }`. `PATCH /chat/route/model` `{ model }`. `auth.activeRoleName() === 'ADMIN'`.
- Produces: ADMIN sees **Turnos automáticos**. Picker `Básico (OpenAI)` always; `Complejo (turno)` only if `automationEnabled`. `sendChat` still `POST /chat/question` with `{ message }` only.

- [ ] **Step 1: Load and mutate route on the chat page**

In `robotics-chat.ts` add:

```typescript
type ChatModel = 'basico' | 'complejo';

interface ChatRouteState {
  automationEnabled: boolean;
  selectedModel: ChatModel;
}
```

Signals: `route = signal<ChatRouteState | null>(null)`, `routeBusy = signal(false)`.

`readonly isAdmin = computed(() => this.auth.activeRoleName() === 'ADMIN');`

In `ngOnInit` call `this.loadRoute()`.

```typescript
  loadRoute() {
    this.http.get<ChatRouteState>(`${GATEWAY_URL}/chat/route`).subscribe({
      next: (state) => this.route.set(state),
      error: () => this.route.set({ automationEnabled: true, selectedModel: 'complejo' }),
    });
  }

  setAutomation(enabled: boolean) {
    if (!this.isAdmin() || this.routeBusy()) return;
    this.routeBusy.set(true);
    this.http.patch<ChatRouteState>(`${GATEWAY_URL}/chat/route/automation`, { enabled }).subscribe({
      next: (state) => {
        this.route.set(state);
        this.routeBusy.set(false);
      },
      error: () => this.routeBusy.set(false),
    });
  }

  setModel(model: ChatModel) {
    if (this.routeBusy()) return;
    this.routeBusy.set(true);
    this.http.patch<ChatRouteState>(`${GATEWAY_URL}/chat/route/model`, { model }).subscribe({
      next: (state) => {
        this.route.set(state);
        this.routeBusy.set(false);
      },
      error: () => this.routeBusy.set(false),
    });
  }
```

Do not send `selectedModel` on `POST /chat/question`.

- [ ] **Step 2: Render toggle and picker**

In `robotics-chat.html`, inside the chatbot header row (right of the tabs, only when `activeTab() === 'chatbot'` is already the surrounding block — put the toggle in the header that is shared, but **hide it unless** `activeTab() === 'chatbot'`):

```html
      @if (activeTab() === 'chatbot' && isAdmin()) {
        <label class="flex items-center gap-2 text-xs font-semibold text-on-surface">
          <input
            type="checkbox"
            [ngModel]="route()?.automationEnabled ?? true"
            (ngModelChange)="setAutomation($event)"
            [disabled]="routeBusy()" />
          Turnos automáticos
        </label>
      }
```

Above the textarea (chatbot composer), add:

```html
          @if (route(); as currentRoute) {
            <label class="mb-2 block text-xs font-semibold text-on-surface">
              Modelo
              <select
                class="mt-1 w-full min-h-10 rounded-lg border border-outline bg-surface-container-low px-3 py-2 text-sm"
                [ngModel]="currentRoute.selectedModel"
                (ngModelChange)="setModel($event)"
                [disabled]="routeBusy()">
                <option value="basico">Básico (OpenAI)</option>
                @if (currentRoute.automationEnabled) {
                  <option value="complejo">Complejo (turno)</option>
                }
              </select>
            </label>
          }
```

Do not add this to the Decir tab.

- [ ] **Step 3: Update the turn map**

In `AGENTS.md`, after “Una pregunta a la vez. Entra por el micrófono o por `POST /chat/question`.” insert:

```
La pregunta llega a `MANAGEMENT_MS.chatService.chat`. Si los turnos están apagados o el modelo del sistema es `basico`, management usa OpenAI `chatStructured`, llama a `voiceService.speak` y responde `{ reply, fuente: "OpenAI", movimientos: [] }`. Si los turnos están encendidos y el modelo es `complejo`, reenvía a `MAI_CORE_MS.interactionService.ask` (pasos 1–6). El picker del chat es la elección del sistema; el micrófono usa la misma ruta.
```

Renumber is not required; keep steps 1–6 as the **complejo** path.

Replace the sentence that forbids reconnecting chat to OpenAI in `.cursor/rules/rone-overview.mdc` with:

```
El chat HTTP y el micrófono pasan por `MANAGEMENT_MS.chatService.chat`. OpenAI básico + hablar solo si la ruta es `basico` o los turnos están apagados. `declarePoema` sigue en OpenAI.
```

Also change the management bullet from “reenvía a `MAI_CORE_MS.interactionService.ask`” to “enruta Básico (`chatStructured` + speak) o Complejo (`interactionService.ask`)”.

- [ ] **Step 4: Commit**

`pmas-web-main`:

```bash
git add src/app/pages/robotics-chat/robotics-chat.ts src/app/pages/robotics-chat/robotics-chat.html
git commit -m "$(cat <<'EOF'
Add chat route toggle and model picker.

EOF
)"
```

Launcher:

```bash
git add AGENTS.md .cursor/rules/rone-overview.mdc
git commit -m "$(cat <<'EOF'
Document management chat routing for mic and UI.

EOF
)"
```

---

### Task 6: Pair by filename, stop generating neutro on parse

**Files:**
- Create: `pmas-web-main/src/app/pages/sequences/origin-pair.ts`
- Create: `pmas-web-main/src/app/pages/sequences/origin-pair.spec.ts`
- Modify: `pmas-web-main/src/app/pages/sequences/origin-sequence.ts`
- Modify: `pmas-web-main/src/app/pages/sequences/origin-sequence.spec.ts`

**Interfaces:**
- Consumes: `OriginParseResult` from `origin-sequence.ts`.
- Produces: `isNeutroFileName(name: string): boolean` (same `\bneutro\b` as today). `pairKey(fileBaseName: string): string`. `suggestNeutroPath(gestureBase: string, neutroBases: string[]): string | null`. `parseOriginText` returns `blocksNeutro` from the file only (never `generateNeutroFrom`).

- [ ] **Step 1: Write failing pair + parse tests**

Create `origin-pair.spec.ts`:

```typescript
import { describe, expect, it } from 'vitest';
import { isNeutroFileName, pairKey, suggestNeutroPath } from './origin-pair';

describe('origin-pair', () => {
  it('matches ABRAZOIZQ 7.1 with ABRAZOIZQ NEUTRO 7.1', () => {
    expect(pairKey('ABRAZOIZQ 7.1')).toBe(pairKey('ABRAZOIZQ NEUTRO 7.1'));
    expect(suggestNeutroPath('ABRAZOIZQ 7.1', ['ABRAZOIZQ NEUTRO 7.1'])).toBe('ABRAZOIZQ NEUTRO 7.1');
  });

  it('does not match 7.3 with NEUTRO 7.0', () => {
    expect(pairKey('BRAZOIZQ CON GUINO 7.3')).not.toBe(pairKey('BRAZOIZQ CON GUINO NEUTRO 7.0'));
    expect(suggestNeutroPath('BRAZOIZQ CON GUINO 7.3', ['BRAZOIZQ CON GUINO NEUTRO 7.0'])).toBeNull();
  });

  it('detects NEUTRO names', () => {
    expect(isNeutroFileName('ABRAZOIZQ NEUTRO 7.1')).toBe(true);
    expect(isNeutroFileName('ABRAZOIZQ 7.1')).toBe(false);
  });
});
```

Replace the Qt list test and the “generates neutro when origin has no track” test in `origin-sequence.spec.ts`:

```typescript
  it('reads a Qt 7-tuple list without generating neutro', () => {
    const parsed = parseOriginText(JSON.stringify(ABRAZOIZQ), 'ABRAZOIZQ 7.1', 0);
    expect(parsed.error).toBeNull();
    expect(parsed.blocks).toEqual(ABRAZOIZQ);
    expect(parsed.blocksNeutro).toEqual([]);
  });

  it('leaves origin without neutro track empty', () => {
    const parsed = parseOriginText(
      JSON.stringify({ name: 'saludo', blocks: [[0, 0, 0.0, 2, 850, 5, 'P0_S0']] }),
      'archivo',
      1,
    );
    expect(parsed.blocksNeutro).toEqual([]);
  });
```

Delete `describe('shouldSkipLegacyNeutroFile')`. Keep `generateNeutroFrom` unit tests (studio rewind still exists in this file for now; unused by parse).

- [ ] **Step 2: Run tests to verify they fail**

From `pmas-web-main`:

```bash
npx vitest run src/app/pages/sequences/origin-pair.spec.ts src/app/pages/sequences/origin-sequence.spec.ts
```

Expected: FAIL. Missing `origin-pair` and list still generates neutro.

- [ ] **Step 3: Implement pair helpers and stop generating**

Create `origin-pair.ts`:

```typescript
export function isNeutroFileName(fileBaseName: string): boolean {
  return /\bneutro\b/i.test(fileBaseName);
}

export function pairKey(fileBaseName: string): string {
  return fileBaseName
    .replace(/\.json$/i, '')
    .toLowerCase()
    .replace(/\bneutro\b/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

export function suggestNeutroPath(gestureBase: string, neutroBases: string[]): string | null {
  const key = pairKey(gestureBase);
  return neutroBases.find((name) => pairKey(name) === key) ?? null;
}
```

In `parseOriginText`:
- For a list: `blocksNeutro: []` (do not call `generateNeutroFrom`).
- For an origin object: if `blocks_neutro` has tuples, map them; else `[]`.

Keep `shouldSkipLegacyNeutroFile` as a deprecated alias of `isNeutroFileName` **or** delete it and update imports. Delete it.

- [ ] **Step 4: Run tests to verify they pass**

```bash
npx vitest run src/app/pages/sequences/origin-pair.spec.ts src/app/pages/sequences/origin-sequence.spec.ts
```

Expected: PASS.

- [ ] **Step 5: Commit in `pmas-web-main`**

```bash
git add src/app/pages/sequences/origin-pair.ts src/app/pages/sequences/origin-pair.spec.ts src/app/pages/sequences/origin-sequence.ts src/app/pages/sequences/origin-sequence.spec.ts
git commit -m "$(cat <<'EOF'
Pair import names and stop generating neutro on parse.

EOF
)"
```

---

### Task 7: Large import dialog with neutro selector

**Files:**
- Modify: `pmas-web-main/src/app/pages/sequences/sequences.ts`
- Modify: `pmas-web-main/src/app/pages/sequences/sequences.html`

**Interfaces:**
- Consumes: `parseOriginText`, `isNeutroFileName`, `pairKey`, `suggestNeutroPath`. `POST /sequence/file` with `blocks` + `blocks_neutro` (possibly `[]`).
- Produces: Full-viewport dialog. Neutro files are a pool, not omitted rows. One neutro path per gesture. Operator can add more files without closing. No `generateNeutroFrom`.

- [ ] **Step 1: Change the in-memory model**

Replace `omitted` with a split:

```typescript
interface OriginImportItem {
  sourceFileName: string;
  sourceRelativePath: string;
  fileBaseName: string;
  kind: 'gesture' | 'neutro' | 'error';
  targetName: string;
  description: string;
  category: string | null;
  arduino_id: number | null;
  tupleBlocks: OriginTuple[];
  embeddedNeutro: OriginTuple[];
  neutroSourcePath: string | null;
  error: string | null;
}
```

`parseOriginFile`:
- Always parse.
- If `isNeutroFileName(fileBaseName)` and parse ok → `kind: 'neutro'`, `tupleBlocks` = parsed.blocks (the companion file **is** the neutro track).
- If parse error → `kind: 'error'`.
- Else → `kind: 'gesture'`, `embeddedNeutro = parsed.blocksNeutro`.

After `Promise.all`, run `applySuggestedPairs(items)`:

```typescript
  private applySuggestedPairs(items: OriginImportItem[]): OriginImportItem[] {
    const neutros = items.filter((item) => item.kind === 'neutro');
    const used = new Set<string>();
    return items.map((item) => {
      if (item.kind !== 'gesture') return item;
      const suggested = suggestNeutroPath(
        item.fileBaseName,
        neutros.map((n) => n.fileBaseName).filter((name) => !used.has(name)),
      );
      if (!suggested) {
        return { ...item, neutroSourcePath: null };
      }
      used.add(suggested);
      const match = neutros.find((n) => n.fileBaseName === suggested);
      return { ...item, neutroSourcePath: match?.sourceRelativePath ?? null };
    });
  }
```

`updateLegacyItemNeutro(index, path: string | null)`: if `path` is already used by another gesture, ignore the change (keep previous).

`importLegacyItems` valid rows: `kind === 'gesture'`, no error, category, arduino, name. `blocks_neutro` =
- tuples of the neutro item whose `sourceRelativePath === neutroSourcePath`, or
- `embeddedNeutro` if `neutroSourcePath === '__embedded__'`, or
- `[]`.

Selecting more files **appends** (concat + re-suggest only for gestures that still have `neutroSourcePath === null`). Do not wipe confirmed pairs.

Remove `shouldSkipLegacyNeutroFile` usage.

- [ ] **Step 2: Replace the sheet with a large dialog**

Replace the bottom sheet in `sequences.html` with a centered overlay: `fixed inset-4 z-50` (or `inset-2 md:inset-8`), `max-h-[92vh] overflow-auto`, not `bottom-0 max-h-[60vh]`.

Copy:

```
Listas del software original o origen nuevo. Los archivos NEUTRO se emparejan por nombre. Puedes cambiar el par o dejar el gesto sin neutro. Sigue eligiendo archivos sin cerrar.
```

Per gesture row: name, Arduino, category, select Neutro:

```html
                <label class="text-[11px] text-slate-400">
                  Neutro
                  <select
                    [ngModel]="item.neutroSourcePath"
                    (ngModelChange)="updateLegacyItemNeutro(i, $event)"
                    class="w-full mt-1 rounded bg-surface-container-high border border-white/10 px-2 py-1 text-sm">
                    <option [ngValue]="null">Sin neutro</option>
                    @if (item.embeddedNeutro.length) {
                      <option [ngValue]="'__embedded__'">Neutro del archivo origen</option>
                    }
                    @for (neutro of availableNeutrosFor(i); track neutro.sourceRelativePath) {
                      <option [ngValue]="neutro.sourceRelativePath">{{ neutro.sourceRelativePath }}</option>
                    }
                  </select>
                </label>
```

`availableNeutrosFor(index)`: all `kind === 'neutro'` whose path is unused or already selected on this row.

Show neutro-only files in a short list “Neutros en el lote (N)” so the operator sees they were loaded, not omitted.

Keep the file input `multiple` + `webkitdirectory`. Do not close the dialog after import; set status and keep rows so they can import again. Clear only on Cerrar.

- [ ] **Step 3: Manual check**

Open Seq. → Importar JSON → load `ABRAZOIZQ 7.1.json` and `ABRAZOIZQ NEUTRO 7.1.json` together. The gesture row must show the NEUTRO file selected. Import. Confirm robotics JSON has both tracks.

- [ ] **Step 4: Commit in `pmas-web-main`**

```bash
git add src/app/pages/sequences/sequences.ts src/app/pages/sequences/sequences.html
git commit -m "$(cat <<'EOF'
Import gesture and companion neutro in a full dialog.

EOF
)"
```

---

### Task 8: Panel Neutro button and Arduino chip

**Files:**
- Create: `pmas-web-main/src/app/pages/control-panel/arduino-status.ts`
- Create: `pmas-web-main/src/app/pages/control-panel/arduino-status.spec.ts`
- Modify: `pmas-web-main/src/app/pages/control-panel/sequence-groups.ts`
- Create: `pmas-web-main/src/app/pages/control-panel/sequence-groups.spec.ts`
- Modify: `pmas-web-main/src/app/pages/control-panel/control-panel.ts`
- Modify: `pmas-web-main/src/app/pages/control-panel/control-panel.html`

**Interfaces:**
- Consumes: `GET /sequence/arduinos` → `{ arduino_id, port, hardware_fingerprint }[]`. `PlayableSequence.blocks_neutro`.
- Produces: `formatArduinoStatus(list): { connected: boolean; label: string }`. `hasNeutroTrack(sequence): boolean`. `isPlayableSequence` true with empty neutro if category + `blocks.length > 0`.

- [ ] **Step 1: Write failing tests**

`arduino-status.spec.ts`:

```typescript
import { describe, expect, it } from 'vitest';
import { formatArduinoStatus } from './arduino-status';

describe('formatArduinoStatus', () => {
  it('reports none', () => {
    expect(formatArduinoStatus([])).toEqual({ connected: false, label: 'Sin Arduino' });
  });

  it('reports one', () => {
    expect(formatArduinoStatus([{ arduino_id: 1, port: '/dev/ttyUSB0' }])).toEqual({
      connected: true,
      label: 'Arduino #1 · /dev/ttyUSB0',
    });
  });

  it('reports many', () => {
    expect(
      formatArduinoStatus([
        { arduino_id: 1, port: 'a' },
        { arduino_id: 2, port: 'b' },
      ]),
    ).toEqual({ connected: true, label: '2 conectados' });
  });
});
```

`sequence-groups.spec.ts`:

```typescript
import { describe, expect, it } from 'vitest';
import { hasNeutroTrack, isPlayableSequence } from './sequence-groups';

const base = {
  name: 'abrazo',
  description: '',
  category: 'brazo_izquierdo' as const,
  blocks: [{}],
  blocks_neutro: [],
};

describe('panel sequences', () => {
  it('is playable without neutro', () => {
    expect(isPlayableSequence(base)).toBe(true);
    expect(hasNeutroTrack(base)).toBe(false);
  });

  it('has neutro when the track is not empty', () => {
    expect(hasNeutroTrack({ ...base, blocks_neutro: [{}] })).toBe(true);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
npx vitest run src/app/pages/control-panel/arduino-status.spec.ts src/app/pages/control-panel/sequence-groups.spec.ts
```

Expected: FAIL. Missing modules; `isPlayableSequence` still requires neutro.

- [ ] **Step 3: Implement helpers and panel UI**

`arduino-status.ts`:

```typescript
export interface ArduinoDevice {
  arduino_id: number;
  port: string;
  hardware_fingerprint?: string | null;
}

export function formatArduinoStatus(list: ArduinoDevice[]): { connected: boolean; label: string } {
  if (!list.length) return { connected: false, label: 'Sin Arduino' };
  if (list.length === 1) {
    return { connected: true, label: `Arduino #${list[0].arduino_id} · ${list[0].port}` };
  }
  return { connected: true, label: `${list.length} conectados` };
}
```

In `sequence-groups.ts` change `isPlayableSequence` to:

```typescript
export function isPlayableSequence(sequence: PlayableSequence): boolean {
  return (
    CATEGORY_ORDER.includes(sequence.category as SequenceCategory) &&
    Array.isArray(sequence.blocks) &&
    sequence.blocks.length > 0
  );
}

export function hasNeutroTrack(sequence: { blocks_neutro?: unknown[] }): boolean {
  return Array.isArray(sequence.blocks_neutro) && sequence.blocks_neutro.length > 0;
}
```

In `control-panel.ts`: `arduinoStatus = signal({ connected: false, label: 'Sin Arduino' })`, private timer. In `ngOnInit` start `pollArduinos()` every 5000 ms (`GET ${GATEWAY_URL}/sequence/arduinos`). On error or empty, `formatArduinoStatus([])`. Clear timer in `ngOnDestroy`.

Export `hasNeutroTrack` to the template (component method or public import — add `readonly hasNeutroTrack = hasNeutroTrack` on the class).

In `control-panel.html` header, next to the title:

```html
    <p class="ml-auto flex items-center gap-2 rounded-full border border-outline px-3 py-1 text-xs font-semibold">
      <span class="size-2 rounded-full" [class]="arduinoStatus().connected ? 'bg-secondary' : 'bg-on-surface-variant'"></span>
      {{ arduinoStatus().label }}
    </p>
```

Replace the two-button grid:

```html
                        <div class="grid gap-2 sm:w-64 shrink-0" [class]="hasNeutroTrack(sequence) ? 'grid-cols-2' : 'grid-cols-1'">
                          <button type="button" (click)="executePhase(sequence.name, 'normal')" ...>Normal</button>
                          @if (hasNeutroTrack(sequence)) {
                            <button type="button" (click)="executePhase(sequence.name, 'neutro')" ...>Neutro</button>
                          }
                        </div>
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
npx vitest run src/app/pages/control-panel/arduino-status.spec.ts src/app/pages/control-panel/sequence-groups.spec.ts
```

Expected: PASS.

- [ ] **Step 5: Commit in `pmas-web-main`**

```bash
git add src/app/pages/control-panel
git commit -m "$(cat <<'EOF'
Show Arduino chip and hide empty Neutro on the panel.

EOF
)"
```

---

### Task 9: Motion Studio library, cards, warning, Arduino

**Files:**
- Create: `pmas-web-motion-studio/src/static/library-view.js`
- Create: `pmas-web-motion-studio/tests/library-view.test.cjs`
- Modify: `pmas-web-motion-studio/src/static/editor.js`
- Modify: `pmas-web-motion-studio/src/static/index.html`
- Modify: `pmas-web-motion-studio/src/static/editor.css`

**Interfaces:**
- Consumes: `libraryItems[].category`, `libraryItems[].name`. Block `{ nombre, pca, servo, inicio, dur, pos, vel, arduino_id }`. `GET ${gatewayUrl}/sequence/arduinos`.
- Produces: `groupLibraryItems(items)` groups by category, unknown → `Sin categoría`. `blockCardText(block)` includes all fields. `NEUTRO_REVIEW_WARNING` exact spec sentence. `formatArduinoStatus(list)` same labels as the panel. Library rows have no Play button. `.lib-open strong` wraps.

- [ ] **Step 1: Write failing Node tests**

Create `library-view.js` as an empty `module.exports = {}` first if needed, then tests in `tests/library-view.test.cjs`:

```javascript
const test = require("node:test");
const assert = require("node:assert/strict");
const {
  groupLibraryItems,
  blockCardText,
  formatArduinoStatus,
  NEUTRO_REVIEW_WARNING,
} = require("../src/static/library-view.js");

test("groups by category and wraps unknown", () => {
  const groups = groupLibraryItems([
    { name: "largo-nombre-de-abrazo-izquierdo", category: "brazo_izquierdo" },
    { name: "sin", category: null },
  ]);
  assert.equal(groups[0].label, "brazo_izquierdo");
  assert.equal(groups[0].items[0].name, "largo-nombre-de-abrazo-izquierdo");
  assert.equal(groups.at(-1).label, "Sin categoría");
});

test("card text lists every block field", () => {
  const text = blockCardText({
    nombre: "P0_S1",
    pca: 1,
    servo: 14,
    inicio: 0,
    dur: 2,
    pos: 650,
    vel: 3,
    arduino_id: 1,
  });
  for (const token of ["P0_S1", "pca:1", "s:14", "t:0", "d:2", "pos:650", "v:3", "ard:1"]) {
    assert.match(text, new RegExp(token.replace(":", "\\:")));
  }
});

test("card omits arduino when 0", () => {
  const text = blockCardText({
    nombre: "P0_S1",
    pca: 0,
    servo: 1,
    inicio: 1,
    dur: 1,
    pos: 1,
    vel: 1,
    arduino_id: 0,
  });
  assert.doesNotMatch(text, /ard:/);
});

test("warning copy is locked", () => {
  assert.equal(
    NEUTRO_REVIEW_WARNING,
    "El neutro generado debe revisarlo una persona. En el androide no es fiable.",
  );
});

test("arduino status matches the panel", () => {
  assert.deepEqual(formatArduinoStatus([]), { connected: false, label: "Sin Arduino" });
  assert.deepEqual(formatArduinoStatus([{ arduino_id: 1, port: "/dev/ttyUSB0" }]), {
    connected: true,
    label: "Arduino #1 · /dev/ttyUSB0",
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

From `pmas-web-motion-studio`:

```bash
node --test tests/library-view.test.cjs
```

Expected: FAIL. Missing exports.

- [ ] **Step 3: Implement helpers and wire the editor**

`library-view.js` (CJS + browser global):

```javascript
(function (root, factory) {
  const api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.StudioLibrary = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  const NEUTRO_REVIEW_WARNING =
    "El neutro generado debe revisarlo una persona. En el androide no es fiable.";

  function formatArduinoStatus(list) {
    if (!list || !list.length) return { connected: false, label: "Sin Arduino" };
    if (list.length === 1) {
      return { connected: true, label: `Arduino #${list[0].arduino_id} · ${list[0].port}` };
    }
    return { connected: true, label: `${list.length} conectados` };
  }

  function blockCardText(block) {
    const parts = [
      block.nombre,
      `pca:${block.pca}`,
      `s:${block.servo}`,
      `t:${block.inicio}`,
      `d:${block.dur}`,
      `pos:${block.pos}`,
      `v:${block.vel}`,
    ];
    if (Number(block.arduino_id) !== 0) parts.push(`ard:${block.arduino_id}`);
    return parts.join(" ");
  }

  function groupLibraryItems(items) {
    const buckets = new Map();
    for (const item of items) {
      const key = item.category && String(item.category).trim() ? String(item.category) : "Sin categoría";
      if (!buckets.has(key)) buckets.set(key, []);
      buckets.get(key).push(item);
    }
    const named = [...buckets.keys()].filter((key) => key !== "Sin categoría").sort();
    const order = named.concat(buckets.has("Sin categoría") ? ["Sin categoría"] : []);
    return order.map((label) => ({ label, items: buckets.get(label) }));
  }

  return { NEUTRO_REVIEW_WARNING, formatArduinoStatus, blockCardText, groupLibraryItems };
});
```

In `index.html` before `editor.js`:

```html
    <script src="/static/library-view.js?v=identity"></script>
```

After `#mode`, add `<span id="arduino-chip" class="mode">Sin Arduino</span>`.

After `#generate-neutro` add:

```html
        <p id="neutro-warning" class="status" role="note"></p>
```

Set its text in `editor.js` on load:

```javascript
const neutroWarning = document.getElementById("neutro-warning");
if (neutroWarning) neutroWarning.textContent = StudioLibrary.NEUTRO_REVIEW_WARNING;
```

`renderLibrary`: use `StudioLibrary.groupLibraryItems(libraryItems)`. For each group, append an `<li class="lib-group">` with the label, then one `lib-item` per sequence. **Do not** create the Play button. `row.append(open)` only. `title.textContent = item.name` (full name).

Block innerHTML:

```javascript
        el.innerHTML = `<span>${StudioLibrary.blockCardText(block)}</span><button type="button" class="kill" aria-label="Eliminar">×</button><span class="resize"></span>`;
```

Poll arduinos every 5s when `gatewayUrl` and `token` exist (`authorizedFetch("/sequence/arduinos")`). On fail or `[]`, `formatArduinoStatus([])`. Write label onto `#arduino-chip`.

CSS:

```css
.lib-open strong {
  white-space: normal;
  overflow: visible;
  text-overflow: unset;
  word-break: break-word;
}

.lib-item {
  grid-template-columns: minmax(0, 1fr);
}

.lib-group {
  padding: 0.45rem 0.7rem 0.15rem;
  font-size: 0.7rem;
  font-weight: 700;
  color: var(--muted);
  text-transform: uppercase;
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
node --test tests/library-view.test.cjs
```

Expected: PASS.

- [ ] **Step 5: Commit in `pmas-web-motion-studio`**

```bash
git add src/static/library-view.js src/static/editor.js src/static/index.html src/static/editor.css tests/library-view.test.cjs
git commit -m "$(cat <<'EOF'
Group studio library and show full block cards.

EOF
)"
```

---

### Task 10: Launcher pointer and spec note

**Files:**
- Modify: launcher submodule pointers after the five repo commits
- Modify: `docs/superpowers/specs/2026-10-17-turn-route-import-studio-design.md` only if a locked sentence drifted during implementation (do not rewrite the spec for style)

**Interfaces:**
- Consumes: commits from Tasks 1–9.
- Produces: launcher commit that records submodule SHAs + this plan if not already committed.

- [ ] **Step 1: Confirm every spec row has a commit**

Walk the spec Goal list: route, import pairs, panel Neutro/Arduino, studio groups/Play/cards/warning/Arduino.

- [ ] **Step 2: Commit the plan and submodule pointers on the launcher**

```bash
git add docs/superpowers/plans/2026-10-17-turn-route-import-studio.md
git add pba-ms-management pba-ms-gateway pmai-mai-core pmas-web-main pmas-web-motion-studio
git commit -m "$(cat <<'EOF'
Point submodules at route, import, and studio work.

EOF
)"
```

Do not commit `.env` or `data/chat-route.json` if it contains runtime state you do not want in git.

---

## Self-review

1. Spec coverage: route store + chat table (T1–T2), HTTP (T3), mic (T4), picker/ADMIN (T5), pair key / no generate (T6), dialog (T7), panel Neutro + Arduino + playable without neutro (T8), studio (T9), docs (T5 + T10). `declarePoema` untouched. 409 covered. Corrupt JSON covered.
2. Placeholders: none.
3. Names: `ChatRouteState`, `automationEnabled`, `selectedModel`, `basico` / `complejo`, `hasNeutroTrack`, `formatArduinoStatus`, `pairKey`, `NEUTRO_REVIEW_WARNING` are the same in later tasks as in earlier ones.
