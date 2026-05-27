# geoecon_map – Session Start Hook

> Ejecutar al iniciar cualquier sesión de desarrollo en este repo.

---

## Protocolo de Inicio

```
1. Leer .roots/context.md                 → briefing de 30s
2. Leer .roots/journal/diary.md           → últimas 3 entradas
3. Leer .roots/tasks/tasks.md             → qué hay en progreso
4. Leer .roots/tasks/todo.md              → backlog priorizado
5. Leer .roots/debug/errors-log.md        → bugs activos
6. git log --oneline -10                  → contexto de commits recientes
7. git status                             → cambios pendientes
```

## Preguntas clave antes de empezar

- ¿Hay bugs activos en `errors-log.md` relacionados con la tarea de hoy?
- ¿Hay alguna decisión de diseño en `decisions.md` que afecte lo que voy a tocar?
- ¿La tarea pertenece al módulo `geaiq-layer-nav` o `geoeconol6-windowinfo`? (ambos tienen convenciones diferentes)

## Archivos que siempre hay que revisar antes de tocar CSS/JS

- `css/geaiq-layer-nav.css` — variables CSS y prefijos `glp-`
- `js/geaiq-layer-nav.js` — métodos públicos vs privados (`_` prefix)
- **Nunca modificar sin leer antes:** `GF.displayWindowInfo`, `GF.pickSelectionsFromShpId`, `GF.abrirCerrarClick` (backward compat crítica)

---
