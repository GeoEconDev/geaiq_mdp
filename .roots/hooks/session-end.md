# geoecon_map – Session End Hook

> Ejecutar al cerrar cualquier sesión de desarrollo.

---

## Protocolo de Cierre

```
1. git status                              → verificar que no hay cambios sin commitear
2. git push origin claude/...              → asegurar que está pusheado
3. Actualizar .roots/journal/diary.md      → qué hice, reflexiones
4. Si hubo release → .roots/journal/changelog.md
5. Si hubo commits → .roots/docs/commits.md (agregar entradas nuevas)
6. Si arreglé bug → .roots/debug/fixes-log.md + marcar en errors-log.md
7. Si tomé decisión importante → .roots/design/decisions.md
8. Si hay ideas nuevas → .roots/journal/notes.md
9. Actualizar .roots/tasks/tasks.md (marcar completadas)
10. Actualizar .roots/_meta.json → bumping updated_at
```

## Checklist de calidad

- [ ] ¿El código nuevo tiene prefijo `glp-` en CSS nuevo?
- [ ] ¿No modifiqué firmas de funciones legacy?
- [ ] ¿Agregué `console.log('[GLNav]...')` en métodos nuevos para debugging?
- [ ] ¿El chat funciona con agente inactivo (graceful fallback)?
- [ ] ¿Los cambios en `_injectPanel()` son compatibles con el panel ya inyectado?

---
