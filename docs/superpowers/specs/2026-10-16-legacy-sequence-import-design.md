# Importar secuencias legacy originales — design

Date: 2026-10-16  
Status: approved by user on 2026-10-16  
Scope: un corte. El botón **Importar JSON** acepta el JSON-lista que escribe `interfaz_record9_5_1.py` y el origen nuevo. El neutro de un legacy se genera con el rebobinado del estudio. La categoría la elige el operador. La descripción queda vacía hasta el estudio. Dueños: `pmas-web-main` y `pba-ms-robotics`.

Relación: los specs `2026-10-14-motion-studio-integration-design.md` y `2026-10-14-sequence-neutro-runtime-design.md` siguen vigentes para iframe, `id`, cola Normal/Neutro y `is_complete_pair`. Este corte **corrige** el importador, que hoy rechaza las listas originales con «Falta categoría o neutro». No reabre el turno, el estudio de edición ni `declarePoema`.

## Problem

`interfaz_record9_5_1.py` guarda solo esto:

```json
[[1, 14, 0.0, 2, 650, 3, "P0_S1"], [1, 13, 1.99, 2, 900, 3, "P0_S2"]]
```

El neutro era **otro archivo** (`ABRAZOIZQ NEUTRO 7.1.json`). No hay `name`, `category`, `description` ni `blocks_neutro` en el mismo JSON.

El importador actual (`parseOriginText`) trata esa lista como error. Solo acepta el objeto de origen con categoría y ambas pistas. El texto del modal dice que acepta listas legacy, pero el test `rejects raw 7-tuple list` lo impide. Esas secuencias no llegan a robótica.

## Goal

1. Una lista de 7-tuplas válidas es un gesto. El neutro se genera con el mismo rebobinado de `generateNeutroFrom` / `generate_neutro`.
2. Un origen nuevo (`blocks` + `blocks_neutro`) se importa como hoy; no se regenera el neutro.
3. El operador elige categoría por fila. Sin categoría no se envía esa fila.
4. La descripción va vacía. El archivo queda en disco con `id`, categoría y ambas pistas. `is_complete_pair` sigue falso hasta que el estudio guarda una frase de al menos 10 caracteres.
5. Un archivo cuyo nombre contiene `NEUTRO` (sin distinguir mayúsculas) no se importa.
6. JSON que no es lista ni origen: se rechaza esa fila; las demás siguen.

## Non-goals

- Editar `interfaz_record9_5_1.py`.
- Emparejar el archivo `… NEUTRO …json` como pista neutra.
- Inferir la categoría del nombre del archivo.
- Copiar `generate_neutro` a `pba-ms-robotics`.
- Cambiar el turno, `getActions`, `executeAction`, `declarePoema` o `{ reply, fuente, movimientos }`.
- Cambiar el diálogo de guardar del estudio (sigue exigiendo descripción ≥ 10).

## Approach

Opción A aprobada: el importador en Angular lee la lista, genera el neutro con el rebobinado del estudio y POST al ingest. Robótica acepta descripción vacía. El catálogo no se abre hasta la frase.

## Formatos

### Legacy original (software Qt)

JSON-array. Cada fila tiene al menos 7 elementos: `[pca, servo, inicio, dur, pos, vel, nombre]`.  
Nombre de secuencia: el del archivo sin `.json` (editable en el modal).

### Origen nuevo

```json
{
  "name": "abrazoizq",
  "description": "Abrazo con el brazo izquierdo",
  "category": "brazo_izquierdo",
  "blocks": [[1, 14, 0.0, 2, 650, 3, "P0_S1"]],
  "blocks_neutro": [[1, 14, 0.0, 2, 900, 3, "P0_S1"]]
}
```

Si `blocks_neutro` tiene al menos una 7-tupla, se usa tal cual. Si el objeto trae `blocks` y `blocks_neutro` falta o está vacío, se genera el neutro. Si no hay `blocks` ni lista raíz: error de esa fila.

## Neutro generado

Misma regla que `pmas-web-motion-studio/src/static/editor.js` `generateNeutroFrom` y `src/neutro.py` `generate_neutro`: por cada `(pca, servo)`, deshacer el camino en orden inverso de tiempo. La función vive junto al parser (`origin-sequence.ts` o un módulo vecino). No se llama al iframe ni a un endpoint extra.

## Modal

Por fila: ruta del archivo, nombre editable, Arduino, **categoría** (select de las seis). Sin categoría no se envía. Descripción no se pide.

Un archivo con `NEUTRO` en el nombre se muestra como omitido (no es un gesto).

## Ingest

`ingest_save`:

- Categoría obligatoria (una de las seis).
- Ambas pistas no vacías.
- Descripción: `""` es válido. Si viene texto, se recorta a 280 y, si la longitud queda entre 1 y 9, se rechaza. ≥ 10 sigue válido.
- Overwrite del mismo `name` conserva `id`.

`is_complete_pair` no cambia: categoría + ambas pistas + descripción ≥ 10. Sin eso: `listSequences` sí; `getActions` y el panel de ejecución no.

El estudio ya lista `/sequence/files` y abre `/sequence/file`. Ahí se escribe la frase y el par queda listo.

## Error handling

| Caso | Resultado |
|---|---|
| Lista de 7-tuplas + categoría | Gesto + neutro generado; POST |
| Lista + sin categoría | Fila no se envía |
| Nombre contiene `NEUTRO` | Fila omitida |
| Origen con ambas pistas | Se guarda tal cual |
| Origen con `blocks` y sin neutro | Neutro generado |
| JSON ni lista ni origen | Error de esa fila |
| Descripción `""` | Archivo con `id`; no entra al catálogo |
| Descripción 1–9 | 400 |
| Descripción ≥ 10 | Par completo |

## Testing

`pmas-web-main` (Vitest, estilo `origin-sequence.spec.ts`):

- `ABRAZOIZQ 7.1.json` (lista) → `error` nulo, `blocks` = la lista, `blocksNeutro` no vacío y distinto del gesto.
- Nombre `ABRAZOIZQ NEUTRO 7.1` → no se importa (omitido).
- Origen con ambas pistas → `blocksNeutro` igual al del archivo.
- Objeto `{ foo: 1 }` → error.

`pba-ms-robotics` (pytest del ingest):

- Categoría + ambas pistas + `description=""` → archivo con `id`; `is_complete_pair` es falso.
- Misma fila con frase de 10+ → `is_complete_pair` es verdadero.
- Descripción de 5 caracteres → error.

## Decisions locked

- Un JSON-lista es un gesto; el neutro se genera; no se empareja el archivo `NEUTRO`.
- Categoría a mano; descripción vacía al importar.
- Rebobinado en Angular, copiado del estudio; no en robótica.
- Ingest acepta `""`; el catálogo sigue cerrado hasta la frase del estudio.
- mai-core, `declarePoema` y el contrato del turno no cambian.
