# Hook: On Seed Process

> Protocolo maestro al procesar/reprocesar el seed. Consolida sync
> upstream, distribución, y verificación de CLAUDE.md.

---

## Pasos

0. **Detectar modo de trabajo (solo en bootstrap inicial):**
   - Si `_meta.json` ya existe y tiene `working_mode` → usar ese modo, no preguntar
   - Si no existe `_meta.json` o no tiene `working_mode` → preguntar al usuario:
     - Client branch → pedir versión y nombre de cliente → crear `.roots/{version}.{client}/`
     - Source → crear `.roots/{module}/` directamente
   - Persistir la respuesta en `_meta.json.working_mode`
   - Este paso NO se repite en sesiones posteriores
   - **En este repo (`geoecon_map.claude.local`) el modo es siempre `source`** —
     ya pre-fijado en todos los `_meta.json`. No volver a preguntar.

1. **Sync con upstream público:**
   - Fetch `https://raw.githubusercontent.com/ctmil/roots_seed/main/roots_seed.md`
   - Comparar versión upstream vs versión del canonical local
   - Si local < upstream → avisar al humano, proponer aplicar cambios
   - Si local > upstream → evaluar si hay mejoras genéricas para PR
   - Si no hay acceso al upstream → anotar en `journal/notes.md`, continuar

2. **Verificar canonical del repo:**
   - Leer `geoecon_odoo/odoo_moldeo_roots/roots_seed.md` (canonical local de este repo)
   - Confirmar que el campo `**Versión:**` coincide con lo esperado
   - Si hay ediciones locales no bumpeadas → avisar al humano

3. **Distribuir a todas las copias:**
   - Ejecutar `hooks/on-seed-update.md`
   - Cada `.roots/roots_seed.md` queda alineado con el canonical
   - Verificar con diff que no quedaron copias desincronizadas

4. **Verificar/crear CLAUDE.md:**
   - Si no existe `CLAUDE.md` en la raíz → crearlo con el template
     definido en § "Integración con CLAUDE.md"
   - Si existe → verificar que la lista de módulos con `.roots/`
     está actualizada (agregar nuevos, marcar removidos)
   - Si existe `.claude/` → verificar que sus hooks referencian
     `.roots/` sin duplicar lógica

5. **Verificar workbench/:**
   - Para cada `.roots/{module}/` que no tenga `workbench/` → crearla
   - No agregar contenido — es espacio del usuario

6. **Registrar:**
   - Agregar entrada en `journal/diary.md` o `docs/commits.md`
     documentando el procesamiento del seed, versión, y acciones tomadas

---

## Output esperado

- Canonical local alineado (o con delta documentado) con upstream
- Todas las copias `.roots/roots_seed.md` sincronizadas
- `CLAUDE.md` actualizado con índice de módulos
- Carpetas `workbench/` existentes en todos los módulos
- Registro del procesamiento en journal o commits

---
