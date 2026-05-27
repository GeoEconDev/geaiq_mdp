# geoecon_map – On Fix Protocol

> Qué hacer al commitear un fix.

---

## Protocolo

```
1. Actualizar .roots/debug/errors-log.md
   → Cambiar estado de "🔴 ACTIVO" a "✅ RESUELTO (fecha)"
   → Agregar la fecha del fix

2. Agregar entrada en .roots/debug/fixes-log.md:

## FIX-NNN – Descripción del fix

**Fecha:** DD Mes YYYY
**Error relacionado:** ERROR-NNN
**Cambio:** Descripción técnica de qué se cambió y por qué.

3. git commit con mensaje descriptivo:
   "[módulo]: fix breve descripción del problema"
   
4. git push origin claude/...

5. Si el fix afecta a otros módulos → notificar en .roots/journal/notes.md
```

## Convención de mensajes de commit para fixes

```
geaiq-layer-nav: fix período auto-selección cierra panel
geoeconol6-windowinfo: fix card primario no mostraba valor real
query.php: fix type=menu retorna null cuando no hay períodos
```

---
