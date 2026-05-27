# geoecon_map – On Topic Shift Hook

> Ejecutar cuando la conversación o el trabajo pivota a un archivo/sistema que no fue cargado por `session-start.md` al inicio de la sesión.

---

## Cuándo disparar

Ejemplos concretos de topic-shift en este repo:

- La conversación estaba sobre feature X (ej: OAuth2) y gira a `query.php`, `gea.php`, `GeaClient.php` u otro archivo legacy.
- Entra en escena un módulo Odoo que no estaba siendo tocado (ej: `geoecon_connector_api`, `a2_urban_intel`, `geoecon_gea`).
- Se menciona un subsistema frontend no tocado recientemente (ej: `geoeconol6-a2wiz`, `geaiq-layer-nav`, `geoeconol6-windowinfo`).
- El usuario menciona "la API", "el caché del server", "el wizard", "el visor" y no se ha revisado la doc correspondiente en esta sesión.

## Protocolo

```
1. ls .roots/docs/                         → ver qué docs existen
2. Matchear foco nuevo contra nombres:
     - query.php              → docs/query-php.md
     - geoeconol6-*.js        → docs/geoeconol6-js.md
     - arquitectura general   → docs/architecture.md
     - API remota GEA         → docs/api-geaiq.md
     - feature en curso       → docs/design-<feature>.md
     - glosario de términos   → docs/glossary.md
3. Leer las secciones relevantes ANTES de:
     - preguntar aclaraciones al usuario
     - proponer un diseño
     - empezar a implementar
4. Chequear también:
     - .roots/journal/notes.md   → observaciones técnicas previas
     - .roots/design/decisions.md → ADRs que puedan aplicar
5. Solo preguntar lo que quede no documentado.
6. Si al terminar descubriste algo que debería haber estado documentado
   → actualizar el doc correspondiente o proponer uno nuevo.
```

## Preguntas que sugieren que no ejecuté este hook

- "¿Cuál es la URL de X?"
- "¿Cómo se usa X desde el frontend?"
- "¿Dónde vive el caché de X?"
- "¿Qué endpoints expone X?"

Si estoy por hacer una de estas y no revisé `.roots/docs/` → volver al paso 1.

## Compatibilidad

Tool-agnostic. Vale para cualquier asistente de IA (Claude Code, Cursor, Copilot Workspace, Aider, Continue, etc.) o desarrollador humano. Cada herramienta puede tener su propio mecanismo para disparar el hook (hook nativo, slash command, o simplemente disciplina del operador).

---
