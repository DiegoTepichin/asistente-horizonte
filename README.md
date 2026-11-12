# asistente-horizonte

Asistente interno de "Despacho Contable Horizonte" (firma ficticia): indica a cada colaborador con quién ver cada asunto, sin revelar datos confidenciales.

El repositorio genera el system prompt del asistente a partir de un directorio y unas reglas, y verifica sus respuestas contra casos de evaluación.

## Estructura

- `data/directorio.json`, `data/reglas.md`: fuente única (datos ficticios).
- `scripts/build_prompt.py`: genera `dist/system_prompt.md` con la disponibilidad calculada por fecha. Nunca incluye sueldos ni teléfonos.
- `scripts/check_respuestas.py`: valida `evals/respuestas.md` contra `evals/casos.json`.
- `tests/`: pruebas con pytest.

## Uso

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest -q
.venv/bin/python scripts/build_prompt.py --hoy 2026-11-11
```

Pega `dist/system_prompt.md` como instrucciones del asistente. Para evaluarlo, pega sus respuestas en `evals/respuestas.md` (un bloque `## N` por caso) y corre:

```bash
.venv/bin/python scripts/check_respuestas.py
```

Código de salida: 0 si todo pasa, 1 si hay algún FAIL, 2 si falta el archivo de respuestas.

## Límites

- Todas las personas, sueldos y teléfonos de `data/` son inventados.
- El verificador compara texto; las notas de cada caso requieren revisión manual.
