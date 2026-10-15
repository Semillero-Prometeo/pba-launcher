# Two-role user management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Leave only ADMIN and USER, create and edit a real person record with the account, stop the same-password update error, skip the login role picker when there is one role, and remove the Roles page and Gestión nav.

**Architecture:** Prisma enum and seed shrink to two roles; a SQL migration remaps STUDENT/TEACHER to USER. `POST`/`PUT /users` carry a nested `person` and write `person` + `user` + `user_role` in auth MS. Same current password is a no-op. Angular users page is the only admin people surface. Login uses `needsRoleSelection`.

**Tech Stack:** Angular 21 + Vitest file-read, NestJS gateway + auth MS, Prisma/Postgres, Markdown at launcher root.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-10-14-user-management-two-roles-design.md`.
- Do not change the turn, `chatService.chat`, `declarePoema`, `{ reply, fuente, movimientos }`, Motion Studio, robotics, management chat proxy, or vision pipeline.
- Edit only the owning repo. Do not mix files across repos in one commit.
- `X-Active-Role` stays the role UUID. Menu and `roleGuard` still key off active name `ADMIN`.
- Work on `feat/sequence-neutro-runtime` in each repo that already has it.
- Angular tests: `npx vitest run <file>` (not `ng test --include`, which typechecks every spec). Auth/gateway: `node --test test/<file>.cjs`.
- No `example/` or Davivienda. Spanish operator copy.

---

## File structure

| File | Responsibility |
|---|---|
| `pba-ms-auth/prisma/schema.prisma` | Enum `ADMIN`/`USER`; `person.email` VarChar(120). |
| `pba-ms-auth/prisma/migrations/20261015000000_two_roles_person_email/migration.sql` | Data remap + enum shrink + email width. |
| `pba-ms-auth/prisma/seed.ts` | Only seeds whatever `Roles` enum contains. |
| `pba-ms-gateway/prisma/schema.prisma` | Same enum and email width (client types). |
| `pba-ms-auth/src/person/dto/create-person.dto.ts` | Email MaxLength 120. |
| `pba-ms-gateway` + `pba-ms-auth` `create-user.dto.ts` / `update-user.dto.ts` | Nested `PersonInputDto`. |
| `pba-ms-auth/src/users/repositories/users.repository.ts` | Create person+user; `findAll` without `person_id` filter, with `deleted_at: null`. |
| `pba-ms-auth/src/users/users.service.ts` | No `FRONT_END_URL` on create; password no-op; person upsert; last ADMIN; no self-inactive. |
| `pmas-web-main/.../users.ts` + `users.html` | Person fields, `autocomplete="new-password"`, identity, dar de baja. |
| `pmas-web-main/.../sidebar.ts` | Autenticación = Usuarios only; drop Gestión. |
| `pmas-web-main/src/app/app.routes.ts` | Drop `/admin/roles` and `/admin/management`. |
| `pmas-web-main/.../admin/roles/*` | Delete. |
| `pmas-web-main/.../login.ts` | `needsRoleSelection`. |
| `PRODUCT.md` / `DESIGN.md` | This cut. |

---

### Task 1: Prisma two roles and person.email 120

**Files:**
- Modify: `pba-ms-auth/prisma/schema.prisma`
- Create: `pba-ms-auth/prisma/migrations/20261015000000_two_roles_person_email/migration.sql`
- Create: `pba-ms-auth/test/two-roles-schema.test.cjs`
- Modify: `pba-ms-gateway/prisma/schema.prisma`
- Create: `pba-ms-gateway/test/two-roles-schema.test.cjs`
- Modify: `pba-ms-auth/src/person/dto/create-person.dto.ts` (`MaxLength(40)` → `MaxLength(120)`)

**Interfaces:**
- Consumes: existing `Roles` enum with four values; `person.email` VarChar(40).
- Produces: `Roles = ADMIN | USER`. `person.email` VarChar(120). SQL remaps STUDENT/TEACHER `user_role` rows to USER then drops those role rows and enum values.

- [ ] **Step 1: Write the failing tests**

`pba-ms-auth/test/two-roles-schema.test.cjs`:

```js
const { readFileSync } = require('fs');
const { join } = require('path');
const { describe, it } = require('node:test');
const assert = require('node:assert/strict');

const schema = readFileSync(join(__dirname, '../prisma/schema.prisma'), 'utf8');
const dto = readFileSync(join(__dirname, '../src/person/dto/create-person.dto.ts'), 'utf8');
const sql = readFileSync(
  join(__dirname, '../prisma/migrations/20261015000000_two_roles_person_email/migration.sql'),
  'utf8',
);

describe('two-role schema', () => {
  it('enum has only ADMIN and USER', () => {
    const block = schema.slice(schema.indexOf('enum Roles'), schema.indexOf('enum DocumentTypes'));
    assert.match(block, /ADMIN/);
    assert.match(block, /USER/);
    assert.equal(block.includes('STUDENT'), false);
    assert.equal(block.includes('TEACHER'), false);
  });

  it('person.email is 120 chars', () => {
    assert.match(schema, /email\s+String\s+@unique\s+@db\.VarChar\(120\)/);
    assert.match(dto, /MaxLength\(120/);
  });

  it('migration remaps STUDENT/TEACHER then shrinks the enum', () => {
    assert.match(sql, /STUDENT/);
    assert.match(sql, /TEACHER/);
    assert.match(sql, /VARCHAR\(120\)/);
  });
});
```

`pba-ms-gateway/test/two-roles-schema.test.cjs`:

```js
const { readFileSync } = require('fs');
const { join } = require('path');
const { describe, it } = require('node:test');
const assert = require('node:assert/strict');

const schema = readFileSync(join(__dirname, '../prisma/schema.prisma'), 'utf8');

describe('gateway Roles enum', () => {
  it('has only ADMIN and USER and email 120', () => {
    const block = schema.slice(schema.indexOf('enum Roles'), schema.indexOf('enum DocumentTypes'));
    assert.equal(block.includes('STUDENT'), false);
    assert.equal(block.includes('TEACHER'), false);
    assert.match(schema, /email\s+String\s+@unique\s+@db\.VarChar\(120\)/);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd pba-ms-auth && node --test test/two-roles-schema.test.cjs
cd pba-ms-gateway && node --test test/two-roles-schema.test.cjs
```

Expected: FAIL (enum still has STUDENT/TEACHER; migration file missing).

- [ ] **Step 3: Schema, DTO, and SQL**

In both `prisma/schema.prisma` files:

```prisma
  email            String    @unique @db.VarChar(120)
```

```prisma
enum Roles {
  ADMIN
  USER

  @@schema("auth")
}
```

`create-person.dto.ts`: `@MaxLength(120, { message: 'El correo electrónico no puede tener más de 120 caracteres' })`.

`pba-ms-auth/prisma/migrations/20261015000000_two_roles_person_email/migration.sql` (table names match existing migrations, unquoted schema — `"person"`, `"role"`, `"user_role"`):

```sql
ALTER TABLE "person" ALTER COLUMN "email" SET DATA TYPE VARCHAR(120);

UPDATE "user_role" AS ur
SET "role_id" = (SELECT "id" FROM "role" WHERE "name" = 'USER')
WHERE "role_id" IN (SELECT "id" FROM "role" WHERE "name" IN ('STUDENT', 'TEACHER'))
  AND NOT EXISTS (
    SELECT 1 FROM "user_role" AS x
    WHERE x."user_id" = ur."user_id"
      AND x."role_id" = (SELECT "id" FROM "role" WHERE "name" = 'USER')
  );

DELETE FROM "user_role"
WHERE "role_id" IN (SELECT "id" FROM "role" WHERE "name" IN ('STUDENT', 'TEACHER'));

DELETE FROM "role" WHERE "name" IN ('STUDENT', 'TEACHER');

CREATE TYPE "Roles_new" AS ENUM ('ADMIN', 'USER');
ALTER TABLE "role" ALTER COLUMN "name" DROP DEFAULT;
ALTER TABLE "role" ALTER COLUMN "name" TYPE "Roles_new" USING ("name"::text::"Roles_new");
ALTER TABLE "role" ALTER COLUMN "name" SET DEFAULT 'USER';
DROP TYPE "Roles";
ALTER TYPE "Roles_new" RENAME TO "Roles";
```

Do not edit `seed.ts` beyond what the enum already drives (`Object.keys(Roles)`). After this, seed only creates ADMIN and USER.

- [ ] **Step 4: Run tests to verify they pass**

Same commands as Step 2. Expected: PASS.

- [ ] **Step 5: Commit in each owning repo**

```bash
cd pba-ms-auth
git add prisma/schema.prisma prisma/migrations/20261015000000_two_roles_person_email/migration.sql src/person/dto/create-person.dto.ts test/two-roles-schema.test.cjs
git commit -m "$(cat <<'EOF'
Keep only ADMIN and USER and widen person email.

EOF
)"

cd pba-ms-gateway
git add prisma/schema.prisma test/two-roles-schema.test.cjs
git commit -m "$(cat <<'EOF'
Align gateway Roles enum with ADMIN and USER.

EOF
)"
```

---

### Task 2: Nested `person` on create and update DTOs

**Files:**
- Modify: `pba-ms-gateway/src/auth-ms/users/dto/create-user.dto.ts`
- Modify: `pba-ms-gateway/src/auth-ms/users/dto/update-user.dto.ts`
- Modify: `pba-ms-auth/src/users/dto/create-user.dto.ts`
- Modify: `pba-ms-auth/src/users/dto/update-user.dto.ts`
- Modify: `pba-ms-gateway/test/create-user.dto.test.cjs`
- Create: `pba-ms-auth/test/person-input.dto.test.cjs`

**Interfaces:**
- Consumes: current `CreateUserDto` (`username`, `password`, `role_ids`) and `UpdateAuthUserDto` without person.
- Produces: `PersonInputDto { first_name, last_name, document_type_id, document_number, phone? }`. Create requires `person`. Update `person?`. Server sets `person.email = username`; the client does not send email.

- [ ] **Step 1: Extend the failing tests**

Replace `pba-ms-gateway/test/create-user.dto.test.cjs` with:

```js
const { readFileSync } = require('fs');
const { join } = require('path');
const { describe, it } = require('node:test');
const assert = require('node:assert/strict');

const create = readFileSync(join(__dirname, '../src/auth-ms/users/dto/create-user.dto.ts'), 'utf8');
const update = readFileSync(join(__dirname, '../src/auth-ms/users/dto/update-user.dto.ts'), 'utf8');

describe('gateway user DTOs', () => {
  it('requires password, role_ids and person on create', () => {
    assert.match(create, /class PersonInputDto/);
    assert.match(create, /first_name: string/);
    assert.match(create, /document_number: string/);
    assert.match(create, /person: PersonInputDto/);
    assert.match(create, /ArrayMinSize\(1\)/);
    assert.equal(create.includes('assign_student_role'), false);
  });

  it('allows optional person on update', () => {
    assert.match(update, /person\?: PersonInputDto/);
  });
});
```

`pba-ms-auth/test/person-input.dto.test.cjs`: same assertions against `src/users/dto/create-user.dto.ts` and `update-user.dto.ts`.

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd pba-ms-gateway && node --test test/create-user.dto.test.cjs
cd pba-ms-auth && node --test test/person-input.dto.test.cjs
```

Expected: FAIL (`PersonInputDto` missing).

- [ ] **Step 3: Add `PersonInputDto` in both repos**

Put this class in **each** `create-user.dto.ts` (gateway and auth). Auth already imports `ValidateNested`, `Type`, `IsObject`, `MaxLength`, `IsOptional`, `IsUUID`. Gateway: add `MaxLength` if missing.

```ts
export class PersonInputDto {
  @IsString()
  @IsNotEmpty()
  @MaxLength(50)
  first_name: string;

  @IsString()
  @IsNotEmpty()
  @MaxLength(50)
  last_name: string;

  @IsUUID('4')
  @IsNotEmpty()
  document_type_id: string;

  @IsString()
  @IsNotEmpty()
  @MaxLength(11)
  document_number: string;

  @IsString()
  @IsOptional()
  @MaxLength(15)
  phone?: string;
}
```

On `CreateUserDto` add (required) and **delete** `assign_student_role`:

```ts
  @IsObject()
  @ValidateNested()
  @Type(() => PersonInputDto)
  person: PersonInputDto;
```

On `UpdateAuthUserDto` add:

```ts
  @IsOptional()
  @IsObject()
  @ValidateNested()
  @Type(() => PersonInputDto)
  person?: PersonInputDto;
```

Import `PersonInputDto` from `./create-user.dto` in each `update-user.dto.ts`. Keep existing `username` / `password` / `role_ids` validators.

- [ ] **Step 4: Run tests to verify they pass**

Same commands as Step 2. Expected: PASS.

- [ ] **Step 5: Commit in each owning repo**

```bash
cd pba-ms-gateway
git add src/auth-ms/users/dto/create-user.dto.ts src/auth-ms/users/dto/update-user.dto.ts test/create-user.dto.test.cjs
git commit -m "$(cat <<'EOF'
Accept nested person on gateway user DTOs.

EOF
)"

cd pba-ms-auth
git add src/users/dto/create-user.dto.ts src/users/dto/update-user.dto.ts test/person-input.dto.test.cjs
git commit -m "$(cat <<'EOF'
Accept nested person on auth user DTOs.

EOF
)"
```

---

### Task 3: Create writes person; findAll lists them

**Files:**
- Modify: `pba-ms-auth/src/users/repositories/users.repository.ts`
- Modify: `pba-ms-auth/src/users/users.service.ts`
- Modify: `pba-ms-auth/test/admin-create-user.test.cjs`

**Interfaces:**
- Consumes: `CreateUserDto` with `person` from Task 2.
- Produces: `create` inserts `person` (email = username) + `user` + `user_role` in one `$transaction`. Does not read `FRONT_END_URL`. `findAll` where: existing search/roles, `deleted_at: null`, **no** `person_id: { not: null }`.

- [ ] **Step 1: Write the failing test additions**

Append to `pba-ms-auth/test/admin-create-user.test.cjs`:

```js
  it('creates a person and does not require FRONT_END_URL', () => {
    assert.match(src, /person.create/);
    assert.equal(svc.includes('FRONT_END_URL'), false);
  });

  it('lists users without requiring person_id and hides deleted', () => {
    const repo = readFileSync(join(root, 'src/users/repositories/users.repository.ts'), 'utf8');
    const findAll = repo.slice(repo.indexOf('async findAll'), repo.indexOf('async findOne'));
    assert.equal(findAll.includes('person_id: { not: null }'), false);
    assert.match(findAll, /deleted_at:\s*null/);
  });
```

Keep the existing plaintext-password and no-STUDENT cases.

- [ ] **Step 2: Run test to verify it fails**

```bash
cd pba-ms-auth && node --test test/admin-create-user.test.cjs
```

Expected: FAIL (`person.create` / `FRONT_END_URL` still present / `person_id` filter still there).

- [ ] **Step 3: Implement create + findAll**

`findAll` `baseWhere`:

```ts
    const baseWhere: Prisma.userWhereInput = {
      deleted_at: null,
      ...(roles && {
        user_role: {
          some: {
            role: { id: { in: roles } },
          },
        },
      }),
    };
```

Replace `create` so that after validating and hashing the password it runs:

```ts
    const personPayload = createUserDto.person;
    const hashedPassword = bcrypt.hashSync(createUserDto.password, 10);

    const user = await this.prismaService.$transaction(async (tx) => {
      const person = await tx.person.create({
        data: {
          first_name: personPayload.first_name,
          last_name: personPayload.last_name,
          email: createUserDto.username,
          document_number: personPayload.document_number,
          phone: personPayload.phone,
          document_type: { connect: { id: personPayload.document_type_id } },
        },
      });

      const created = await tx.user.create({
        data: {
          username: createUserDto.username,
          password: hashedPassword,
          person: { connect: { id: person.id } },
        },
      });

      const ids = [...(role_ids ?? []), ...(role_id ? [role_id] : [])];
      for (const rid of ids) {
        await tx.user_role.create({ data: { user_id: created.id, role_id: rid } });
      }
      return created;
    });
```

Keep `validatePassword` **before** `hashSync`. Catch Prisma unique violations (`P2002`) and throw `RpcException` 400: correo duplicado vs documento duplicado according to `meta.target`.

If `createUserDto.person` is missing, throw 400 `'Los datos de la persona son obligatorios'`.

If connecting `document_type` fails, throw 400 `'El tipo de documento no existe'`.

`users.service.create`: delete the `appSettingsService.findOne(AppSettings.FRONT_END_URL)` block and the 500 when missing. Keep the “usuario ya existe” check. Return the same `{ statusCode, message, data: { id, username } }`.

Prisma unique errors inside the transaction: wrap in try/catch around `$transaction`.

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd pba-ms-auth && node --test test/admin-create-user.test.cjs
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd pba-ms-auth
git add src/users/repositories/users.repository.ts src/users/users.service.ts test/admin-create-user.test.cjs
git commit -m "$(cat <<'EOF'
Create a person with the user and list accounts without a person filter.

EOF
)"
```

---

### Task 4: Update password no-op, person upsert, last ADMIN, no self-baja

**Files:**
- Modify: `pba-ms-auth/src/users/users.service.ts`
- Modify: `pba-ms-auth/src/users/repositories/users.repository.ts` (add `countActiveAdmins` and `upsertPerson`)
- Modify: `pba-ms-auth/test/update-auth-user.test.cjs`

**Interfaces:**
- Consumes: `UpdateAuthUserDto` with optional `person`, `password`, `username`, `role_ids`. `InactiveUserDto` + `RequestUserDto`.
- Produces:
  - Empty/omitted password: skip.
  - `bcrypt.compare(password, exists.password) === true`: skip, no throw.
  - New password: hash, `is_first_login: false`.
  - `person` present: update existing or create+connect.
  - `username` also writes `person.email`.
  - `role_ids: []` → 400 `'Elige al menos un rol.'`
  - Removing ADMIN from the last active ADMIN, or inactivating that user → 400 `'No puedes dejar el sistema sin un administrador'`.
  - `inactive` when `inactiveUserDto.user_id === requestUser.id` → 400 `'No puedes darte de baja a ti mismo'`.
  - Updating only `person` is valid (drop the “no se ha enviado ningún dato” check that required password/username/role_ids).

- [ ] **Step 1: Rewrite the failing update test**

Replace `pba-ms-auth/test/update-auth-user.test.cjs`:

```js
const { readFileSync } = require('fs');
const { join } = require('path');
const { describe, it } = require('node:test');
const assert = require('node:assert/strict');

const src = readFileSync(join(__dirname, '../src/users/users.service.ts'), 'utf8');

describe('updateAuthUser admin edit', () => {
  it('treats the current password as a no-op', () => {
    assert.match(src, /bcrypt\.compare/);
    assert.equal(src.includes('Esta contraseña ya ha sido utilizada'), false);
    assert.match(src, /is_first_login:\s*false/);
  });

  it('upserts person and blocks last admin / self inactive', () => {
    assert.match(src, /person/);
    assert.match(src, /No puedes dejar el sistema sin un administrador/);
    assert.match(src, /No puedes darte de baja a ti mismo/);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd pba-ms-auth && node --test test/update-auth-user.test.cjs
```

Expected: FAIL (old reuse message still present; no last-admin copy).

- [ ] **Step 3: Implement**

Import `PersonInputDto` from `../dto/create-user.dto` in the repository. Add:

```ts
  countActiveAdmins() {
    return this.prismaService.user.count({
      where: {
        deleted_at: null,
        user_role: { some: { role: { name: 'ADMIN' } } },
      },
    });
  }

  async upsertPerson(userId: string, username: string, person: PersonInputDto) {
    const existing = await this.prismaService.user.findUnique({
      where: { id: userId },
      select: { person_id: true },
    });
    if (existing?.person_id) {
      return this.prismaService.person.update({
        where: { id: existing.person_id },
        data: {
          first_name: person.first_name,
          last_name: person.last_name,
          email: username,
          document_number: person.document_number,
          phone: person.phone ?? null,
          document_type_id: person.document_type_id,
        },
      });
    }
    const created = await this.prismaService.person.create({
      data: {
        first_name: person.first_name,
        last_name: person.last_name,
        email: username,
        document_number: person.document_number,
        phone: person.phone,
        document_type: { connect: { id: person.document_type_id } },
      },
    });
    return this.prismaService.user.update({
      where: { id: userId },
      data: { person: { connect: { id: created.id } } },
    });
  }

  async syncPersonEmail(userId: string, email: string) {
    const existing = await this.prismaService.user.findUnique({
      where: { id: userId },
      select: { person_id: true },
    });
    if (!existing?.person_id) return;
    return this.prismaService.person.update({
      where: { id: existing.person_id },
      data: { email },
    });
  }
```

Rewrite `updateAuthUser` (keep `findOne(id, true)` for the hash):

```ts
    const { password, username, role_ids, person } = data;
    if (!password && !username && !role_ids && !person) {
      throw new RpcException({
        statusCode: HttpStatus.BAD_REQUEST,
        message: 'No se ha enviado ningún dato para actualizar',
      });
    }

    if (password) {
      const same = await bcrypt.compare(password, exists.password);
      if (!same) {
        await this.userRepository.update({ id }, { password, is_first_login: false });
      }
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
      await this.userRepository.syncPersonEmail(id, username);
    }

    if (person) {
      await this.userRepository.upsertPerson(id, username ?? exists.username, person);
    }
```

When `role_ids` is present:

```ts
    if (role_ids) {
      if (!role_ids.length) {
        throw new RpcException({ statusCode: HttpStatus.BAD_REQUEST, message: 'Elige al menos un rol.' });
      }
      await this.assertNotLastAdminLoss(id, role_ids);
      await this.rolesService.setRoles({ user_id: id, roles_id: role_ids });
    }
```

`assertNotLastAdminLoss` (private on `UsersService`):

```ts
  private async assertNotLastAdminLoss(userId: string, incomingRoleIds?: string[]) {
    const admin = await this.rolesService.findOne('ADMIN');
    const user = await this.userRepository.findOne(userId);
    const hasAdmin = user?.user_role?.some((ur) => ur.role.name === 'ADMIN');
    const wouldLose =
      hasAdmin && (incomingRoleIds ? !incomingRoleIds.includes(admin.id) : true);
    if (!wouldLose) return;
    const n = await this.userRepository.countActiveAdmins();
    if (n <= 1) {
      throw new RpcException({
        statusCode: HttpStatus.BAD_REQUEST,
        message: 'No puedes dejar el sistema sin un administrador',
      });
    }
  }
```

For `inactive`, call `assertNotLastAdminLoss(dto.user_id)` (no incoming ids ⇒ treating as losing ADMIN if they have it) **after**:

```ts
    if (inactiveUserDto.user_id === user.id) {
      throw new RpcException({
        statusCode: HttpStatus.BAD_REQUEST,
        message: 'No puedes darte de baja a ti mismo',
      });
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd pba-ms-auth && node --test test/update-auth-user.test.cjs
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd pba-ms-auth
git add src/users/users.service.ts src/users/repositories/users.repository.ts test/update-auth-user.test.cjs
git commit -m "$(cat <<'EOF'
Skip same-password updates and keep at least one admin.

EOF
)"
```

---

### Task 5: Users page — person fields, password, identity

**Files:**
- Modify: `pmas-web-main/src/app/pages/admin/users/users.ts`
- Modify: `pmas-web-main/src/app/pages/admin/users/users.html`
- Modify: `pmas-web-main/src/app/pages/admin/users/users.spec.ts`

**Interfaces:**
- Consumes: `POST/PUT /users` with `person`; `GET /document-types`; `GET /roles?take=50`; `GET /users?take=50`; `PATCH /users/inactive`.
- Produces: modal fields first_name, last_name, document_type_id, document_number, phone, username, password (`autocomplete="new-password"`), role_ids. Table: Nombre, Correo, Documento, Roles, Acciones. Copy «Dar de baja». No `industrial-grid`, `text-slate-*`, `text-[9px]`, `text-[10px]`, `border-white/5`.

- [ ] **Step 1: Write the failing test**

Replace `users.spec.ts`:

```ts
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const ts = readFileSync(resolve(import.meta.dirname, 'users.ts'), 'utf8');
const html = readFileSync(resolve(import.meta.dirname, 'users.html'), 'utf8');

describe('users admin CRUD', () => {
  it('sends person and never /auth/users', () => {
    expect(ts).toContain('${GATEWAY_URL}/users');
    expect(ts).toContain('/users/inactive');
    expect(ts).not.toContain('/auth/users');
    expect(ts).toContain('person:');
    expect(ts).toContain('first_name');
    expect(ts).toContain('document_number');
    expect(ts).toContain('/document-types');
    expect(ts).toContain('take=50');
    expect(html).toContain('first_name');
    expect(html).toContain('autocomplete="new-password"');
    expect(html).toContain('Dar de baja');
    expect(html).not.toContain('industrial-grid');
    expect(html).not.toContain('text-slate-');
    expect(html).not.toContain('text-[9px]');
    expect(html).not.toContain('text-[10px]');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd pmas-web-main && npx vitest run src/app/pages/admin/users/users.spec.ts
```

Expected: FAIL (`first_name` / `Dar de baja` missing).

- [ ] **Step 3: Implement `users.ts`**

Extend types and form:

```ts
export interface Person {
  first_name: string;
  last_name: string;
  document_number?: string;
  phone?: string;
  document_type_id?: string;
  document_type?: { id: string; name: string };
}

export interface User {
  id: string;
  username: string;
  person?: Person;
  user_role?: { role: { id: string; name: string } }[];
}

export interface Role { id: string; name: string; }
export interface DocumentType { id: string; name: string; }

form = signal({
  id: '',
  username: '',
  password: '',
  role_ids: [] as string[],
  first_name: '',
  last_name: '',
  document_type_id: '',
  document_number: '',
  phone: '',
});

documentTypes = signal<DocumentType[]>([]);
deleteError = signal<string | null>(null);
```

`loadAll`: `GET /users?skip=0&take=50`, `GET /roles?skip=0&take=50`, `GET /document-types` (unwrap array or `{ data }`).

`openCreate` / `openEdit` fill the new fields (`openEdit` from `user.person`). Password always `''` on open.

`save()` also requires `first_name`, `last_name`, `document_type_id`, `document_number`. Payload:

```ts
    const payload: {
      username: string;
      password?: string;
      role_ids: string[];
      person: {
        first_name: string;
        last_name: string;
        document_type_id: string;
        document_number: string;
        phone?: string;
      };
    } = {
      username: f.username,
      role_ids: f.role_ids,
      person: {
        first_name: f.first_name,
        last_name: f.last_name,
        document_type_id: f.document_type_id,
        document_number: f.document_number,
        ...(f.phone ? { phone: f.phone } : {}),
      },
    };
    if (f.password) payload.password = f.password;
```

Keep password regex checks. `doDelete`: on error set `deleteError` and do **not** close the dialog.

`displayDocument(user)`: `user.person?.document_number ?? '—'`.

- [ ] **Step 4: Implement `users.html`**

Replace the page shell `industrial-grid` with `bg-background`. Header: pozo navy + Space Grotesk 24px «Usuarios» + línea «Crea cuentas del semillero con nombre, documento y rol.». Search/input/table use `bg-surface`, `border-outline`, `text-on-surface` / `text-on-surface-variant`, `text-xs` labels (not 9px).

Columns (12-grid): Nombre 3, Correo 3, Documento 2, Roles 2, Acciones 2. Nombre = `displayName`. Correo = `username`. Do not render username twice.

Modal `max-w-lg`, scroll `max-h-[90vh] overflow-y-auto`. Fields in order: correo, nombres, apellidos, tipo (select of `documentTypes()`), número, teléfono, contraseña with `autocomplete="new-password"` and label «dejar vacío para no cambiar» in edit, role checkboxes.

Delete dialog title «Dar de baja», body without «no se puede deshacer», button «Dar de baja», `@if (deleteError())` error line.

- [ ] **Step 5: Run test to verify it passes**

Same command as Step 2. Expected: PASS.

- [ ] **Step 6: Commit**

```bash
cd pmas-web-main
git add src/app/pages/admin/users/users.ts src/app/pages/admin/users/users.html src/app/pages/admin/users/users.spec.ts
git commit -m "$(cat <<'EOF'
Edit person data on users and stop same-password dead ends.

EOF
)"
```

---

### Task 6: Drop Roles page and Gestión

**Files:**
- Modify: `pmas-web-main/src/app/components/sidebar/sidebar.ts`
- Modify: `pmas-web-main/src/app/components/sidebar/sidebar.spec.ts`
- Modify: `pmas-web-main/src/app/app.routes.ts`
- Modify: `pmas-web-main/src/app/core/guards/role.guard.spec.ts`
- Delete: `pmas-web-main/src/app/pages/admin/roles/roles.ts`
- Delete: `pmas-web-main/src/app/pages/admin/roles/roles.html`

**Interfaces:**
- Consumes: `SidebarGroup` with autenticacion + gestion.
- Produces: Autenticación items = Usuarios only. No `gestion` group. `visibleGroups` hides `autenticacion` unless ADMIN. No `/admin/roles` or `/admin/management`. `roleGuard` remains on `/admin/users`. Type `SidebarItem` drops `'roles' | 'management'` if unused.

- [ ] **Step 1: Write the failing tests**

`sidebar.spec.ts`:

```ts
describe('sidebar ADMIN gate', () => {
  it('shows only Usuarios under autenticacion and has no Gestión', () => {
    expect(ts).toContain("activeRoleName() === 'ADMIN'");
    expect(ts).toContain("g.id !== 'autenticacion'");
    expect(ts).not.toContain("id: 'gestion'");
    expect(ts).not.toContain("id: 'roles'");
    expect(ts).not.toContain('/admin/roles');
    expect(ts).not.toContain('/admin/management');
    expect(html).toContain('visibleGroups()');
  });
});
```

`role.guard.spec.ts` — remove the `/admin/roles` regex; keep `/admin/users` + `roleGuard`.

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd pmas-web-main && npx vitest run src/app/components/sidebar/sidebar.spec.ts src/app/core/guards/role.guard.spec.ts
```

Expected: FAIL (roles/gestion still present).

- [ ] **Step 3: Implement**

`sidebar.ts` groups: drop the entire `gestion` object; autenticacion items = only `{ id: 'users', label: 'Usuarios', icon: 'group', route: '/admin/users' }`. `openGroups = signal(['robotica', 'autenticacion'])`. `visibleGroups`: filter `g.id !== 'autenticacion'` when not ADMIN. Remove `'roles' | 'management'` from `SidebarItem`. `GroupHealthKey` may keep `'management'` unused or drop the case — if dropped, delete the `management` switch branch.

`app.routes.ts`: delete the `admin/roles` and `admin/management` route objects.

Delete `roles.ts` and `roles.html`.

- [ ] **Step 4: Run tests to verify they pass**

Same command as Step 2. Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd pmas-web-main
git add src/app/components/sidebar/sidebar.ts src/app/components/sidebar/sidebar.spec.ts src/app/app.routes.ts src/app/core/guards/role.guard.spec.ts
git add -u src/app/pages/admin/roles
git commit -m "$(cat <<'EOF'
Remove the Roles page and the empty Gestión group.

EOF
)"
```

---

### Task 7: Login picker only when there are two roles

**Files:**
- Modify: `pmas-web-main/src/app/pages/login/login.ts`
- Create: `pmas-web-main/src/app/pages/login/login-role-picker.spec.ts` (or extend `login.copy.spec.ts`)

**Interfaces:**
- Consumes: `AuthService.needsRoleSelection` (already `!_roleSelected && availableRoles().length > 1`) and auto-select on `roles.length === 1`.
- Produces: after login, `needsRoleSelection()` true → `loginDone.set(true)`; else `navigate(['/control-panel'])`.

- [ ] **Step 1: Write the failing test**

`pmas-web-main/src/app/pages/login/login-role-picker.spec.ts`:

```ts
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const ts = readFileSync(resolve(import.meta.dirname, 'login.ts'), 'utf8');

describe('login role picker', () => {
  it('opens the picker only when needsRoleSelection is true', () => {
    expect(ts).toContain('needsRoleSelection');
    expect(ts).not.toContain('availableRoles().length === 0');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd pmas-web-main && npx vitest run src/app/pages/login/login-role-picker.spec.ts
```

Expected: FAIL.

- [ ] **Step 3: Change `handleSubmit` next handler**

```ts
        next: () => {
          if (this.auth.needsRoleSelection()) {
            this.loginDone.set(true);
          } else {
            this.router.navigate(['/control-panel']);
          }
        },
```

In `login.html`, keep the role modal markup. Change the form subtitle to: «Usa el correo del semillero. Si tienes más de un rol, eliges con cuál entrar.»

- [ ] **Step 4: Run test to verify it passes**

Same command as Step 2. Expected: PASS. Also `npx vitest run src/app/pages/login/login.copy.spec.ts` still PASS.

- [ ] **Step 5: Commit**

```bash
cd pmas-web-main
git add src/app/pages/login/login.ts src/app/pages/login/login-role-picker.spec.ts src/app/pages/login/login.html
git commit -m "$(cat <<'EOF'
Skip the role picker when the account has a single role.

EOF
)"
```

---

### Task 8: PRODUCT.md and DESIGN.md

**Files:**
- Modify: `PRODUCT.md`
- Modify: `DESIGN.md`

**Interfaces:**
- Consumes: shipped Tasks 1–7.
- Produces: principle 5 names ADMIN/USER and person ficha; Evidence includes this spec; DESIGN Layout bullet for `/admin/users` and login picker.

- [ ] **Step 1: Edit PRODUCT.md**

Replace principle 5 with:

```
5. **Sesión, usuarios y visión** — si el token no vale, el login dice «Tu sesión venció. Entra de nuevo.» Los roles del producto son ADMIN y USER; Usuarios es de ADMIN y carga nombre y documento. En visión los objetos van arriba y las cámaras debajo, sin Preview.
```

Add Evidence:

```
- Spec: `docs/superpowers/specs/2026-10-14-user-management-two-roles-design.md`
```

- [ ] **Step 2: Edit DESIGN.md Layout**

Add:

```
- Login: el selector de rol solo aparece si hay más de un rol.
- Usuarios (`/admin/users`): tabla Nombre / Correo / Documento / Roles; modal con persona, contraseña y checkboxes ADMIN/USER. Sin Roles ni Gestión en el menú.
```

Do not change the palette table.

- [ ] **Step 3: Commit**

```bash
cd /home/personal/Projects/ulibre-prometeo/pba-launcher
git add PRODUCT.md DESIGN.md
git commit -m "$(cat <<'EOF'
Record two-role user management on PRODUCT and DESIGN.

EOF
)"
```

---

## Self-review (coverage)

| Spec requirement | Task |
|---|---|
| Enum + seed only ADMIN/USER | 1 |
| STUDENT/TEACHER → USER then delete | 1 (SQL) |
| `person.email` 120 | 1 |
| Nested person on POST/PUT | 2 |
| Create transaction person+user+roles; no FRONT_END_URL | 3 |
| findAll no person_id filter; deleted_at null; take=50 | 3, 5 |
| Same password no-op; new password `is_first_login false` | 4 |
| Person upsert on update; username syncs email | 4 |
| Last ADMIN + no self-baja; empty role_ids 400 | 4 |
| Angular person fields, autocomplete, identity, dar de baja | 5 |
| No Roles page, no Gestión | 6 |
| Login picker iff `needsRoleSelection` | 7 |
| PRODUCT/DESIGN | 8 |
| Turn / declarePoema / studio / vision untouched | Global Constraints |

No TBD. `PersonInputDto` is the same shape in gateway, auth, and Angular payload. `needsRoleSelection` is the existing `AuthService` computed. Messages `'No puedes dejar el sistema sin un administrador'` and `'No puedes darte de baja a ti mismo'` are stable across service and tests.

After code ships, apply the auth migration against the running DB (`npx prisma migrate deploy` in `pba-ms-auth` with `DATABASE_URL`, or the project's usual migrate path) so Compose picks up the enum. Human check: create a USER with cédula → appears in the list → login skips picker → edit without touching password saves.
