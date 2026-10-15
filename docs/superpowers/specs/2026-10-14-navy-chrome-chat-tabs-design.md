# Marco navy y pestañas del chat — design

Date: 2026-10-14  
Status: approved by user on 2026-10-14  
Scope: moderar el verde del cascarón (navy del logo Prometeo), papel de trabajo frío, y hacer visibles las pestañas Chatbot IA / Decir oración. Solo `pmas-web-main` tokens + cascarón que ya usa `bg-rail` + `robotics-chat.html`. El layout del panel no se reabre.

Relación: el spec `2026-10-14-visual-identity-dashboard-design.md` sigue vigente para layout, tipo (≥ 14px cuerpo / ≥ 12px etiqueta), iconos y español de operador. Este corte **cambia la paleta** (marco y campo) y el contraste del chat. No es el corte de estudio, auth ni visión.

Cortes pendientes (specs propias, no este archivo):

1. Motion Studio: toolbar, modal de guardar (nombre + descripción ≥ 10 + categoría), neutro = mismos pasos en orden inverso y misma duración.
2. Autenticación: 401/expiración cierra la UI, crear usuarios, roles con efecto real.
3. Visión: más refresco, sin Preview, cámaras a tamaño útil, objetos observados arriba.

## Problem

El riel bosque `#065f46` pinta cabecera, menú, login izquierdo y la KPI Libre. El campo menta `#c5e6d4` sigue saturado. El operador ve «demasiado verde» aunque el layout y el contraste le gustan.

En Chat, las pestañas inactivas usan `text-slate-400` y `border-white/5` sobre el campo claro: no se leen. El logo de Prometeo es circuito navy, arco cian-azul y arco verde — el azul casi no aparece fuera del botón Normal.

## Goal

1. Marco (navbar, sidebar, barra inferior, panel izquierdo del login): navy del circuito `#0B2540` con tinta `#eef2f6` (contraste ≥ 7:1).
2. Campo de trabajo `#eef2f6`. Tarjetas `#f7fafc` (nunca `#ffffff`) y borde `#c5d4e0`.
3. Verde esmeralda `#059669` solo para Libre, Neutro y ok. Cian `#38bdf8` para Normal, Enviar y pestaña activa.
4. Pestañas Chatbot IA y Decir oración visibles: alto ≥ 44px, texto 14px, inactiva navy + borde; ambas activas en cian + tinta `#0c4a6e`.
5. Actualizar `DESIGN.md` y `PRODUCT.md` en la raíz (sin referencias a carpetas de guía ajenas).

## Non-goals

- Reubicar KPI, ejecución, En hardware o Registro.
- Rediseñar burbujas, frases rápidas o el compositor del chat más allá de quitar gris ilegible.
- Reconectar `chatService.chat` a OpenAI. Chatbot sigue el turno (`POST /chat/question`). Decir oración sigue en voz (`declarePoema` / speak).
- Motion Studio, auth, visión (cortes siguientes).
- Cambiar el contrato del turno, JSON de secuencias o robótica.

## Approach

Opción A aprobada: cambiar tokens y las clases del chat que aún llevan slate. Navbar, sidebar, bottom-nav y login izquierdo ya usan `bg-rail`: al pintar `--color-rail` de navy heredan el marco. La KPI Libre deja `bg-rail` y pasa a `bg-secondary` (esmeralda).

## Paleta

| Rol | Hex | Uso |
|---|---|---|
| Chrome / rail | `#0B2540` | Navbar, sidebar, bottom-nav, login izquierdo |
| On-chrome | `#eef2f6` | Texto e iconos del marco |
| Canvas | `#eef2f6` | Campo de páginas internas |
| Card | `#f7fafc` | Superficies elevadas |
| Border | `#c5d4e0` | Contornos |
| Ink | `#0B2540` | Títulos y cuerpo |
| Quiet ink | `#3d5a73` | Ayudas; no bosque `#2a5644` ni slate `#475569` |
| Action | `#38bdf8` + `#0c4a6e` | Normal, Enviar, pestaña activa |
| Rest / OK | `#059669` | Libre, Neutro, puntos de vida |
| Stop | `#dc2626` | Detener |
| Busy | `#b45309` | Estado ocupado |

`--color-rail` = navy (alias aceptable: `--color-chrome` apuntando al mismo hex). `--color-on-rail` = `#eef2f6`. `--color-background` = `#eef2f6`. `--color-surface` / container = `#f7fafc`. `--color-on-surface` = `#0B2540`. `--color-on-surface-variant` = `#3d5a73`. `--color-secondary` se queda `#059669`. `--color-primary` se queda `#38bdf8`.

## Cascarón

Sin cambio de estructura. Chip R-ONE: papel sobre navy. Login: marca navy a la izquierda, formulario en papel a la derecha. Selector de rol: tarjeta papel sobre velo navy (`bg-rail/80`), no overlay `#020617`.

Panel: misma malla. `estadoCardClass()` para `libre` = `bg-secondary-container text-on-secondary-container` (esmeralda pálida + tinta `#065f46`, AA en 12px y en 20px). No `bg-rail`. Ocupado y sin estado no cambian de semántica (ámbar / rojo).

## Chat

Archivo: `pmas-web-main/src/app/pages/robotics-chat/robotics-chat.html` (y spec de copy).

- Grid de dos pestañas, `min-h-11` o 44px, `text-sm` (14px), icono Material + etiqueta.
- Inactiva: `text-on-surface`, borde `border-outline`, fondo `bg-surface`. Prohibido `text-slate-400`, `text-slate-500`, `border-white/5` en pestañas.
- Activa (Chatbot y Decir): `bg-primary text-on-primary`.
- Limpiar, contadores y Enviar inactivo: ≥ 12px y tinta quieta `#3d5a73` u opacidad sobre navy; no gris pizarra que desaparezca.
- Contratos: `activeTab` `chatbot` | `decir`; `sendChat()` / `sendDecir()` sin cambio de API.

## Failures

| Fallo | Tratamiento |
|---|---|
| Pestaña inactiva ilegible (slate o borde blanco/5) | Bug |
| Libre pintado de navy | Bug |
| Campo o tarjeta `#ffffff` | Bug |
| Chatbot hablando con OpenAI en vez del turno | Bug de contrato; no se implementa |
| Tipo &lt; 12px en pestañas o limpia | Bug |

## Testing

- `styles.tokens.spec.ts`: background `#eef2f6`, rail/chrome `#0B2540`, on-surface-variant `#3d5a73`, secondary `#059669`, surface no `#ffffff`.
- Spec de chat: contiene `Chatbot` y `Decir`; no contiene `text-slate-400` en las pestañas; activa usa `bg-primary`.
- Spec de panel: `estadoCardClass` libre no usa `bg-rail` (usa secondary).
- Navegador: login navy + formulario; panel Libre esmeralda; Chat — las dos pestañas se leen y conmutan.

## Named rules

**The Navy Frame Rule.** Cabecera y menú son `#0B2540`. Un riel esmeralda en esos roles es un bug.

**The Green Reserve Rule.** `#059669` solo Libre, Neutro y ok.

**The Visible Tab Rule.** Una pestaña inactiva se lee igual de bien que una etiqueta de 14px navy sobre tarjeta. Slate sobre papel no.
