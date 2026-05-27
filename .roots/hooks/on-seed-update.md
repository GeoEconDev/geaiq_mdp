# geoecon_map – On Seed Update Hook

> Ejecutar cuando se bumpea la versión del seed canonical, cuando un `session-start` detecta desync entre copia local y canonical, o cuando se crea un `.roots/` nuevo.

---

## Trigger

- Bump de versión en `geoecon_odoo/odoo_moldeo_roots/roots_seed.md` (campo `**Versión:**`).
- `session-start` detecta `diff` entre `.roots/roots_seed.md` (local) y el canonical.
- Se crea un `.roots/` nuevo para un módulo — falta poblar su `roots_seed.md`.
- Se trae un módulo externo que ya tiene `.roots/` — el seed embebido no coincide con el canonical del repo.

## Pasos

1. Identificar el canonical. En este repo: `geoecon_odoo/odoo_moldeo_roots/roots_seed.md`.
2. Listar todos los `.roots/` del repo con `find . -type d -name ".roots" -not -path "*/node_modules/*"`.
3. Para cada uno, escribir `<dir>/roots_seed.md` con el header de distribución seguido del contenido del canonical.
4. Si alguna copia local tenía modificaciones manuales (diff significativo contra canonical ignorando header) → preservarlas como nota al pie de la copia antes de sobrescribir, y avisar al humano que hay conflicto a resolver.
5. Registrar la re-distribución en `journal/notes.md` o `docs/commits.md` (indicando versión canonical y cantidad de copias actualizadas).

## Comando de referencia (one-shot)

```bash
set -e
SEED="geoecon_odoo/odoo_moldeo_roots/roots_seed.md"
HEADER='<!-- CANONICAL: '"$SEED"' -->
<!-- Esto es una COPIA distribuida del seed para que el módulo sea self-contained. -->
<!-- Para cambios permanentes: editar el canonical y re-distribuir a todos los .roots/. -->
<!-- Para cambios locales experimentales: agregar nota al pie de este archivo. -->

'
find . -type d -name ".roots" -not -path "*/node_modules/*" | while read -r dir; do
    { printf '%s' "$HEADER"; cat "$SEED"; } > "$dir/roots_seed.md"
done
```

## Output esperado

Todas las copias `.roots/roots_seed.md` alineadas con la versión canonical. Cada módulo vuelve a ser self-contained y reprocesable aisladamente.

## Compatibilidad

Tool-agnostic. Definido en `geoecon_odoo/odoo_moldeo_roots/roots_seed.md` (hook `on-seed-update`, desde v1.3).

---
