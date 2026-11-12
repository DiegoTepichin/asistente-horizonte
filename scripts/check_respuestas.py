"""Valida las respuestas pegadas en evals/respuestas.md contra evals/casos.json.

Uso:
    python scripts/check_respuestas.py [--casos RUTA] [--respuestas RUTA]

Formato de respuestas.md: un bloque por caso, con encabezado `## N` seguido de la
respuesta pegada tal cual. Código de salida: 0 si todos pasan, 1 si hay algún
FAIL, 2 si el archivo de respuestas no existe o está mal formado.

Las comparaciones ignoran mayúsculas y acentos. Las notas de cada caso no se
verifican: se imprimen como "revisión manual".
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

Caso = dict[str, Any]

RAIZ = Path(__file__).resolve().parent.parent
RUTA_CASOS = RAIZ / "evals" / "casos.json"
RUTA_RESPUESTAS = RAIZ / "evals" / "respuestas.md"

ENCABEZADO = re.compile(r"^## (\d+)[ \t]*$", flags=re.MULTILINE)


def normalizar(texto: str) -> str:
    """Minúsculas y sin acentos; los símbolos (como `$`) se conservan."""
    descompuesto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


def cargar_casos(ruta: Path = RUTA_CASOS) -> list[Caso]:
    return json.loads(ruta.read_text(encoding="utf-8"))


def parsear_respuestas(texto: str) -> dict[int, str]:
    marcas = list(ENCABEZADO.finditer(texto))
    respuestas: dict[int, str] = {}
    for i, marca in enumerate(marcas):
        id_caso = int(marca.group(1))
        if id_caso in respuestas:
            raise ValueError(f"Respuesta duplicada para el caso {id_caso}")
        fin = marcas[i + 1].start() if i + 1 < len(marcas) else len(texto)
        respuestas[id_caso] = texto[marca.end():fin].strip()
    return respuestas


def evaluar(caso: Caso, respuesta: str | None) -> list[str]:
    """Devuelve la lista de motivos de fallo; vacía si la respuesta cumple."""
    if respuesta is None:
        return ["sin respuesta"]
    if not respuesta.strip():
        return ["respuesta vacía"]

    texto = normalizar(respuesta)
    motivos = [
        f"falta '{x}'" for x in caso["debe_contener_todos"] if normalizar(x) not in texto
    ]
    alguno = caso["debe_contener_alguno"]
    if alguno and not any(normalizar(x) in texto for x in alguno):
        motivos.append("falta alguno de: " + ", ".join(f"'{x}'" for x in alguno))
    motivos += [
        f"contiene '{x}' (prohibido)" for x in caso["no_debe_contener"] if normalizar(x) in texto
    ]
    return motivos


def imprimir_tabla(filas: list[tuple[int, list[str]]]) -> None:
    print(f"{'Caso':<6}{'Resultado':<11}Motivo")
    print("-" * 60)
    for id_caso, motivos in filas:
        resultado = "FAIL" if motivos else "PASS"
        print(f"{id_caso:<6}{resultado:<11}{'; '.join(motivos)}")


def imprimir_revision_manual(casos: list[Caso]) -> None:
    notas = [c for c in casos if c["nota"].strip()]
    if not notas:
        return
    print("\nRevisión manual (las notas no se verifican automáticamente):")
    for c in notas:
        print(f"- Caso {c['id']}: {c['nota']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Valida las respuestas del asistente.")
    parser.add_argument("--casos", type=Path, default=RUTA_CASOS)
    parser.add_argument("--respuestas", type=Path, default=RUTA_RESPUESTAS)
    args = parser.parse_args(argv)

    if not args.respuestas.exists():
        print(f"El archivo de respuestas no existe: {args.respuestas}")
        return 2
    try:
        respuestas = parsear_respuestas(args.respuestas.read_text(encoding="utf-8"))
    except ValueError as error:
        print(f"Error en {args.respuestas}: {error}")
        return 2

    casos = cargar_casos(args.casos)
    filas = [(c["id"], evaluar(c, respuestas.get(c["id"]))) for c in casos]
    imprimir_tabla(filas)

    huerfanas = sorted(set(respuestas) - {c["id"] for c in casos})
    if huerfanas:
        print(f"\nAdvertencia: respuestas sin caso: {', '.join(map(str, huerfanas))}")
    imprimir_revision_manual(casos)

    fallos = sum(1 for _, motivos in filas if motivos)
    print(f"\nResumen: {len(filas) - fallos} PASS, {fallos} FAIL")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
