# Micrófono USB estable y visible en el chat — design

Date: 2026-10-27  
Status: approved by user on 2026-10-27  
Scope: un spec. Dueños: `pmai-mai-core`, `pmas-web-main`.  
`pba-ms-gateway` reenvía el JSON y no gana rutas. El turno, `POST /chat/question` y el dictado del navegador no cambian. Este trabajo se hace en el workspace; la Jetson no se modifica.

## Problem

El micrófono USB del robot escucha en `AudioService` con Vosk (`vosk-model-small-es-0.42`) y las frases `hey fede`, `fede` y `federico`. El reconocedor recibe también el silencio, y la frase cuenta si sus letras aparecen dentro del texto. Eso lo activa solo. El id es `mic_0`, `mic_1`, … y cambia al reenumerar el USB. El detector de voz solo es válido a 8, 16, 32 o 48 kHz; si el dispositivo abre a 44,1 kHz, un bloque inválido hoy cuenta como silencio y puede cortar la orden. `GET /audio/listening-status` no dice si hay señal. El chat no consulta ese endpoint.

Prioridad acordada: que no se active solo, que sí reconozca la frase, que sobreviva a desconectar el USB, y que no corte la orden ni se quede esperando.

## Goal

Misma pila Vosk. El silencio no entra al reconocedor de la frase. La frase coincide por palabras completas. El micrófono se recuerda por huella y se reabre al volver. El audio que ven Vosk y el detector de voz es 16 kHz. En el chat de R-ONE, una franja, una barra de nivel y un detalle muestran si el micrófono está conectado, si oye y si ya reconoció la frase.

## Non-goals

- Otro motor de activación (openWakeWord, Porcupine) u otro modelo Vosk.
- Cambiar las frases de `settings.toml`.
- Elegir el micrófono o pausar la escucha desde la pantalla.
- Cambiar el turno, el contrato de `POST /chat/question` o el botón de dictado del navegador.
- Desplegar o editar la Jetson.

## Approach

Opción 1 aprobada: reforzar el bucle actual. Compuerta de energía, coincidencia por palabras, huella estable, remuestreo a 16 kHz y un estado más rico que el chat consulta.

---

## 1. Arquitectura

`pmai-mai-core` es dueño de la escucha, la huella, el remuestreo y el estado. `pmas-web-main` es dueño de la franja en el chat de R-ONE. El gateway ya expone `GET /audio/listening-status` con JWT y reenvía el cuerpo NATS; los campos nuevos viajan en ese JSON.

La frase aceptada sigue entrando por el mismo `chat` que hoy dispara el turno. Este spec no abre el turno.

---

## 2. Reconocimiento

Valores nuevos en `[audio]` de `settings.toml`, junto a los que ya están (`chunk_ms = 30`, `long_silence_ms = 1600`, `post_wake_grace_ms = 2200`, `max_recording_seconds = 20`, `min_recording_seconds = 1`, `preroll_seconds = 0.4`, `wake_partial_match = true`):

| Clave | Valor | Uso |
|---|---|---|
| `wake_energy_rms` | `500` | RMS int16 mínimo para alimentar el reconocedor de la frase |
| `wake_energy_hangover_ms` | `300` | Tras bajar del umbral, se sigue alimentando este tiempo |
| `wake_confirm_chunks` | `2` | Parciales seguidos con la misma frase |
| `level_rms_full_scale` | `4000` | RMS que la barra muestra como 100 |
| `level_hold_ms` | `500` | Ventana del pico que ve la barra |

RMS de un bloque: raíz de la media de los cuadrados de las muestras int16.

**Compuerta.** Por debajo de `wake_energy_rms` el bloque no entra al reconocedor de la frase. Si la energía cae a mitad de la frase, los siguientes 300 ms sí entran. Durante ese hangover la fase de la franja ya puede ser silencio: la compuerta y la etiqueta no son el mismo temporizador.

**Coincidencia.** El texto se pasa a minúsculas. Se dejan letras (con tildes), números y espacios; el resto se quita. Luego se parte en palabras. Con `wake_partial_match = true`, la frase es el texto completo o un sufijo de palabras completas (`oye hey fede` cuenta). Con `false`, el texto tiene que ser igual a una frase. `fede` no coincide con `federico` ni con `confederación`. Hace falta la misma frase en 2 parciales seguidos, o una vez en el resultado final. Un solo parcial no abre la captura.

**Formato.** El dispositivo se abre a la primera tasa que acepte, con la lista de candidatos que ya existe. Antes de Vosk y de webrtcvad el audio es mono, 16 kHz, bloques de 30 ms (480 muestras). A 16 kHz se copia. A otra tasa, remuestreo lineal. Vosk y el VAD no ven 44,1 kHz.

**Fin de la orden.** Se conservan la gracia, el silencio de 1,6 s, el mínimo de 1 s y el máximo de 20 s. Una pausa menor a 1,6 s no cierra. Un bloque que el VAD no puede clasificar cuenta como voz y se anota una vez por flujo abierto. El preroll de 0,4 s se mantiene.

---

## 3. Identidad y reconexión

`microphone_id` pasa a ser la huella `sha1` de `nombre|api|canales`. La tasa de muestreo no entra en la huella. `device_index` solo sirve para abrir el flujo en ese instante. `preferred_microphone_id`, si se define, es esa huella. Vacío: se elige el primer dispositivo de nombre USB y, si no hay, la primera entrada; a partir de ahí se recuerda la huella.

Si el flujo falla o esa huella desaparece, se cierra el flujo, `phase` queda `disconnected`, se conservan id y nombre, y `last_error` dice que ese micrófono no está. No se salta a otro aunque haya otra entrada. Con la escucha activa, un fallo de PortAudio reintenta a los 2 s y el sondeo de dispositivos sigue cada 5 s. Cuando la huella vuelve, aunque el índice cambie, se abre el flujo sin otra llamada a `start-listening`.

`select-microphone` recibe la huella. `list-microphones` lista solo los presentes; el estado de escucha conserva el elegido ausente.

---

## 4. Estado y pantalla

`get_listening_status` mantiene los campos actuales y agrega `selected_microphone_name`, `stream_open`, `phase` e `input_level`.

`phase` es `disconnected`, `silent`, `hearing`, `capturing` o `error`.

| Situación | `phase` |
|---|---|
| Huella ausente o flujo cerrado por desconexión | `disconnected` |
| Modelo, biblioteca o tasa de apertura inutilizable | `error` |
| Desde la frase aceptada hasta cerrar la orden | `capturing` |
| Flujo abierto y el RMS del último bloque ≥ 500 | `hearing` |
| Flujo abierto y el RMS del último bloque es menor que 500 | `silent` |

`input_level` es el RMS máximo de los bloques de los últimos 500 ms, escalado con `min(100, round(rms * 100 / 4000))`. Mientras llegan bloques, no hay un decaimiento extra. Si el flujo deja de entregar audio, ese valor baja en línea a 0 en los 500 ms siguientes. La barra puede moverse en silencio de sala; `hearing` solo empieza en el umbral de la compuerta.

El chat de R-ONE, encima de las opciones rápidas, consulta `GET /audio/listening-status` cada 500 ms mientras la página está abierta y corta la consulta al salir. Usa el `HttpClient` y el token que ya tiene el chat. La primera regla que cumpla fija el texto:

| Orden | Condición | Texto |
|---|---|---|
| 1 | El GET falla | No se pudo consultar el micrófono |
| 2 | `running` es falso | Micrófono apagado |
| 3 | `listening_enabled` es falso | Escucha en pausa |
| 4 | `phase` es `error` | Error de audio |
| 5 | `phase` es `disconnected` | Desconectado |
| 6 | `phase` es `capturing` | Frase reconocida |
| 7 | `phase` es `hearing` | Oyendo |
| 8 | `phase` es `silent` | Conectado, en silencio |

Al lado va la barra 0–100. Si el GET falla, el nivel mostrado es 0 y el detalle guarda la última lectura buena con el texto "Sin lectura en vivo". Un 401 lo resuelve el interceptor de sesión que ya existe.

Al pulsar la franja se ve, solo lectura: micrófono elegido (o "Ninguno"), última frase (o "Ninguna") y último error (o "Ninguno"). No hay selector ni botón de escucha. El botón de dictado del navegador permanece.

---

## 5. Errores

El fallo de audio no detiene cámaras ni turno.

| Caso | Efecto |
|---|---|
| Sin dispositivo, o el elegido se fue | `disconnected`, nombre e id guardados, reintento |
| PortAudio con el flujo abierto | Se cierra el flujo, `disconnected`, reintento a los 2 s |
| Hay otra entrada y la huella elegida no | Se sigue esperando esa huella |
| Falta el modelo o falta `sounddevice`, `webrtcvad` o `vosk` | `error`, `last_error` con la causa, el proceso sigue |
| Ninguna tasa abre el dispositivo | `last_error` y reintento al cabo de 1 s |
| Bloque de VAD inválido | Cuenta como voz, un log por flujo |
| Excepción del reconocedor | `last_error`, vuelve a esperar la frase, el flujo sigue si el dispositivo está |
| El turno rechaza la frase | La frase ya está en el estado; la fase vuelve a `silent` o `hearing` |
| Overflow aislado | Se registra; la fase no cambia |
| Escucha apagada o audio deshabilitado | La franja usa las filas 2 y 3 de la tabla anterior |

---

## 6. Pruebas

En `pmai-mai-core`, pytest nuevo bajo `tests/`, sin tarjeta y sin el modelo Vosk:

- Un bloque bajo el umbral no entra al reconocedor; uno sobre el umbral sí; un bache dentro de los 300 ms también.
- `hey fede` y un sufijo `oye hey fede` coinciden. `confederación` no coincide con `fede`. `federico` no coincide con `fede`.
- Un parcial no abre la captura. Dos parciales iguales, o un resultado final, sí.
- 48 kHz y 44,1 kHz salen en bloques de 480 muestras a 16 kHz.
- La misma huella con otro índice sigue elegida. Al desaparecer, `phase` es `disconnected` y el nombre se conserva. Al volver, se vuelve a abrir.
- Un bloque de VAD inválido no suma silencio.
- El JSON de estado incluye `phase`, `input_level`, `selected_microphone_name` y `stream_open`.

En `pmas-web-main`, una función pura, al estilo de `gateway.spec.ts`, cubre las ocho filas de la tabla de textos, en ese orden. El gateway no cambia de ruta y no lleva prueba nueva.

La prueba con el USB real y la Jetson queda fuera de este cambio.

## Success criteria

- El silencio y una palabra que solo contiene las letras de la frase no abren la captura.
- Decir `hey fede`, `fede` o `federico` como palabras completas sí la abre, con dos parciales o un final.
- Desconectar y reconectar el mismo USB recupera la escucha sin reiniciar el servicio y sin cambiar de dispositivo.
- Una pausa menor a 1,6 s después de la gracia no cierra la orden; un bloque de VAD inválido tampoco.
- Con el chat abierto se ve la franja, la barra y, al pulsar, micrófono, última frase y último error.
