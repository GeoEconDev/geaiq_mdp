# geoecon_map – On Task Done Hook

> Ejecutar al completar cada tarea individual, ANTES de reportarla al humano. Distinto de `session-end.md` — aplica aunque la sesión continúe con otra tarea.

---

## Pasos mínimos (siempre, en orden)

1. **`.roots/tasks/todo.md`** — marcar la tarea como `[x]` o moverla a "Completadas".
2. **`.roots/tasks/tasks.md`** — mover la entrada de "En Progreso" a "Completadas Recientemente" con fecha.
3. **`.roots/docs/commits.md`** — si hubo commit, agregar entrada con formato:
   ```
   ### `<hash>` – <mensaje>
   - **Motivación:** …
   - **Cambios:** …
   ```

## Pasos condicionales

- **Error encontrado** → `.roots/debug/errors-log.md` (ID `ERROR-XXX` secuencial)
- **Fix aplicado** → `.roots/debug/fixes-log.md` (ID `FIX-XXX`); si cierra un `ERROR-XXX` existente, marcar como "Resuelto" en `errors-log.md`
- **Decisión arquitectónica** → `.roots/design/decisions.md` (ID `ADR-XXX`)
- **Idea / observación técnica** → `.roots/journal/notes.md`
- **Término nuevo del dominio** → `.roots/docs/glossary.md`
- **Cambio de schema / datos** → `.roots/debug/migrations.md`

## Antes de reportar al humano

Un humano leyendo sólo `.roots/` debería poder reconstruir qué se hizo y por qué. Si después de aplicar el hook alguien no puede:

- saber qué tarea se completó,
- encontrar el commit relevante en `commits.md`,
- entender la motivación detrás del cambio,

entonces el hook no se ejecutó correctamente — volver al paso 1.

## Compatibilidad

Tool-agnostic. Aplica a cualquier asistente de IA o desarrollador humano. Formalizado en `geoecon_odoo/odoo_moldeo_roots/roots_seed.md` (hook `on-task-done`, desde v1.2).

---
