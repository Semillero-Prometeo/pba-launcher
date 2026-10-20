# Decir oración parametrizable — design

Date: 2026-10-19  
Status: approved by user on 2026-10-19  
Scope: un spec. Dueños: `pba-ms-robotics`, `pba-ms-gateway`, `pmas-web-main`.  
El turno no se reabre. `declarePoema` y `POST /voice/speak` no cambian de contrato.

## Problem

Las frases rápidas de la pestaña **Decir oración** viven quemadas en `decirQuickOptions` (`pmas-web-main`). No se pueden crear, editar ni desactivar sin desplegar el front.

## Goal

Catálogo parametrizable desde la misma interfaz de chat. Crear, actualizar y desactivar. Quien está autenticado con chat puede gestionarlo. La grilla de hablar solo muestra frases activas. El recuadro libre para escribir y decir se queda.

## Non-goals

- Prisma u otro motor SQL.
- Borrar el registro o el archivo.
- Un JSON por frase.
- Reordenar.
- Subir íconos o emoji picker.
- Cambiar TTS, `declarePoema` o el turno.
- Sincronizar el catálogo en vivo entre pestañas.

## Approach

Opción B aprobada: **un solo JSON** en robótica (`data/phrases.json`) como fuente de verdad. Gateway expone HTTP. Angular deja el array quemado.

---

## 1. Arquitectura

El dueño es `pba-ms-robotics`. Archivo único, ruta por env `PHRASES_PATH`, por defecto `/usr/src/app/data/phrases.json`. Compose ya monta `./pba-ms-robotics:/usr/src/app`; el JSON sobrevive al reinicio. El archivo runtime no se commitea: la siembra vive en código.

Robótica expone NATS `phraseService.list|create|update|setActive`. El gateway traduce a HTTP bajo `JwtAuthGuard`. No se exige rol ADMIN.

Hablar sigue en `POST /voice/speak` → `ROBOTICS_MS.voiceService.speak`. El catálogo no habla por sí solo.

Angular, al abrir Decir oración, pide `GET /voice/phrases`. La grilla filtra `active: true`. El diálogo de gestión muestra todas.

---

## 2. Datos

```json
{
  "items": [
    {
      "id": 1,
      "title": "Saludo Patria",
      "text": "Saludos, Colegio Militar Patria…",
      "icon": "menu_book",
      "active": true
    }
  ]
}
```

| Campo | Regla |
|---|---|
| `id` | Entero. El siguiente es `max(id)+1` (si no hay ítems, 1). No se reutiliza. |
| `title` | Obligatorio. 1–80 caracteres tras trim. Es el texto del botón. |
| `text` | Obligatorio. 1–2000 caracteres. Es lo que se dice. |
| `icon` | Opcional. Vacío o `[a-z0-9_]+` (nombre Material, como hoy). Sin archivo. |
| `active` | Booleano. Por defecto `true` al crear. |

El orden del arreglo es el de la grilla. Crear agrega al final. Títulos no se exigen únicos. No hay `updatedAt` ni DELETE.

### Siembra

Si el archivo no existe o `items` es `[]`, el almacén escribe una vez las frases actuales de `decirQuickOptions`. El `label` pasa a `text`, el ícono se conserva, `active` es `true`, y cada una recibe el título de esta tabla (en el mismo orden que el array del front):

| # | title | icon |
|---|---|---|
| 1 | Saludo Patria | *(vacío)* |
| 2 | Patria en vivo | `menu_book` |
| 3 | Carreras Unilibre | `menu_book` |
| 4 | Invitación Facultad | `menu_book` |
| 5 | Soy R-One | `menu_book` |
| 6 | Interactúe conmigo | `menu_book` |
| 7 | Saludo corto | `waving_hand` |
| 8 | Sobre mí | `waving_hand` |
| 9 | Robot pasando | `directions_car` |
| 10 | Mis creadores | `groups` |
| 11 | Miren, padres | `star` |
| 12 | Hola Yohel | `code` |
| 13 | Hola Mauricio | `school` |
| 14 | Hola Marce | `psychology` |
| 15 | Hola Pablo | `science` |
| 16 | Hola Juan Manuel | `build` |
| 17 | Foto, sonrían | `photo_camera` |
| 18 | Hasta la vista | `waving_hand` |
| 19 | La familia | `favorite` |
| 20 | Stand Unilibre | `location_on` |
| 21 | Acérquense | `location_on` |
| 22 | ¿Quieren una foto? | `location_on` |
| 23 | Qué bonita | `location_on` |
| 24 | Hola guapos | `location_on` |
| 25 | Si puedo moverme | `location_on` |

El `text` de cada fila es el `label` de `decirQuickOptions` en `robotics-chat.ts` al escribir este spec, sin recortar. Tras sembrar, todas son editables. Una segunda carga no vuelve a sembrar. El array del front se elimina en el mismo cambio.

JSON corrupto: error 500; no se pisa el archivo ni se siembra encima.

---

## 3. Interfaz (`pmas-web-main`)

La pestaña Decir oración no cambia de sitio.

- Recuadro libre: tope 400 caracteres, Enter envía, Shift+Enter nueva línea. No pasa por el catálogo.
- Historial de lo hablado: igual.
- Grilla **Frases rápidas**: solo `active`. Tarjeta = ícono + **título**. Clic habla `phrase.text` completo (hasta 2000). El recuadro de 400 no es la fuente de ese envío: no se recorta el texto del catálogo.
- Búsqueda: filtra por título y por texto (minúsculas, substring).
- **Gestionar frases** (junto al título/búsqueda) abre un diálogo, no otra ruta:
  - Lista todas, con badge activa/inactiva.
  - Nueva: título, texto, ícono (nombre Material, opcional).
  - Editar: mismos campos; `id` no se toca.
  - Desactivar / Activar. Sin botón Eliminar.

Si `GET` falla: grilla vacía, aviso, recuadro libre usable. Tras crear, editar o cambiar `active`, se vuelve a pedir el listado.

---

## 4. Flujo, API y errores

### NATS (`pba-ms-robotics`)

| Subject | Cuerpo | Efecto |
|---|---|---|
| `phraseService.list` | — | Lee (y siembra si aplica). Devuelve `{ items }` |
| `phraseService.create` | `{ title, text, icon? }` | Valida, asigna `id`, `active: true`, append, escribe |
| `phraseService.update` | `{ id, title?, text?, icon? }` | Campos omitidos se conservan. `icon: ""` o `null` limpia el ícono |
| `phraseService.setActive` | `{ id, active }` | Solo cambia `active` |

Escritura: leer → mutar → temporal → `rename` sobre `phrases.json`. Sin candado: gana la última escritura.

### HTTP (`pba-ms-gateway`, JWT, autenticado)

| Método | Ruta | Cuerpo |
|---|---|---|
| `GET` | `/voice/phrases` | — |
| `POST` | `/voice/phrases` | `{ title, text, icon? }` |
| `PATCH` | `/voice/phrases/:id` | `{ title?, text?, icon? }` |
| `PATCH` | `/voice/phrases/:id/active` | `{ active: boolean }` |

### Errores

| Caso | Código |
|---|---|
| Título o texto fuera de rango; ícono que no cumple el patrón | 400 |
| `id` inexistente | 404 |
| Archivo ausente o `items: []` | 200 tras sembrar |
| JSON corrupto | 500; el archivo no se toca |
| Todas desactivadas | 200 con ítems inactivos; grilla vacía; recuadro libre intacto |

Pulsa una tarjeta → `POST /voice/speak` `{ message: text }`. El recuadro libre usa el mismo endpoint.

---

## 5. Pruebas

Pytest en `pba-ms-robotics/tests/` sobre el almacén (directorio temporal, sin NATS ni TTS):

1. Archivo ausente o `items: []` → siembra ≥ 1 ítem, todos `active`, con `title`, `text` e `id`.
2. Segunda lectura no duplica la siembra.
3. Crear, editar y `setActive` persisten en el mismo JSON.
4. Título o texto inválidos → error; `id` inexistente → no encontrado.
5. JSON corrupto → error; el archivo no se pisa.

Gateway: `tsc` (rutas nuevas). Angular: se elimina `decirQuickOptions`; no hace falta e2e del diálogo.

---

## Repos

| Repo | Cambio |
|---|---|
| `pba-ms-robotics` | Almacén, siembra, NATS `phraseService.*`, `PHRASES_PATH` |
| `pba-ms-gateway` | HTTP `/voice/phrases*` |
| `pmas-web-main` | Quitar array quemado; grilla + diálogo |
| Lanzador | Spec; `PHRASES_PATH` opcional en `.env.template` si el resto de rutas de robótica ya se documentan ahí |
