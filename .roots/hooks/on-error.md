# geoecon_map – On Error Protocol

> Qué hacer al encontrar un error.

---

## Protocolo

```
1. Abrir .roots/debug/errors-log.md
2. Agregar entrada con formato:

## ERROR-NNN – Descripción breve

**Estado:** 🔴 ACTIVO
**Severidad:** Alta / Media / Baja
**Descripción:** Qué pasa exactamente, en qué condiciones.
**Causa raíz:** [completar al investigar]
**Fix propuesto:** [completar al investigar]
**Archivo:** archivo.js → función()

3. Si el error es en el wizard → verificar en la consola del browser
   los logs [GLNav] que aparecen en cada step
4. Si el error es en el chat IA → verificar /omr/agent/chat en Network tab
5. Si el error es en la carga de capa → verificar GF.LoadCluster callbacks
```

## Errores comunes y su diagnóstico

| Síntoma | Causa probable |
|---|---|
| Panel izquierdo no aparece | `GeaLayerNav.init()` no se llamó o `#gea-map-container` no existe |
| Leyenda vacía en items de capa | `GE.ClusterIndex` no tiene el cluster, o `_populateLegends` corrió antes de que OL cargara |
| Chat no responde | Agente `geoecon_gea` en estado `draft` o credenciales no configuradas en Odoo |
| Períodos no aparecen | `query.php?type=menu&field=period` falla — revisar parámetros en Network |
| Callback de capa no dispara | `GF.MapVisibleLayersToJson` no definido (ver ERROR-004 en errors-log.md) |

---
