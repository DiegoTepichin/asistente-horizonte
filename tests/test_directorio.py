import json
import re
from datetime import date
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
CAMPOS = {
    "id", "area", "persona", "puesto", "atiende", "suplente",
    "notas", "disponibilidad", "confidencial",
}
TIPOS = {"vacaciones", "baja", "cobertura"}


@pytest.fixture(scope="module")
def directorio() -> list[dict]:
    return json.loads((RAIZ / "data" / "directorio.json").read_text(encoding="utf-8"))


def test_hay_diez_registros(directorio):
    assert len(directorio) == 10


def test_ids_y_nombres_unicos(directorio):
    assert len({p["id"] for p in directorio}) == len(directorio)
    assert len({p["persona"] for p in directorio}) == len(directorio)


def test_todos_los_registros_tienen_los_campos_esperados(directorio):
    for p in directorio:
        assert set(p) == CAMPOS, p["persona"]
        assert isinstance(p["atiende"], list)
        assert set(p["confidencial"]) == {"sueldo", "telefono"}


def test_suplentes_existen_en_el_directorio(directorio):
    nombres = {p["persona"] for p in directorio}
    for p in directorio:
        assert p["suplente"] is None or p["suplente"] in nombres


def test_disponibilidad_valida(directorio):
    for p in directorio:
        disp = p["disponibilidad"]
        if disp is None:
            continue
        assert disp["tipo"] in TIPOS
        desde = date.fromisoformat(disp["desde"])
        if disp["hasta"] is not None:
            assert desde <= date.fromisoformat(disp["hasta"])


def test_datos_clave_de_los_casos_de_aceptacion(directorio):
    por_nombre = {p["persona"]: p for p in directorio}
    sofia = por_nombre["Sofía Paredes"]
    assert sofia["suplente"] == "Héctor Gil"
    assert sofia["disponibilidad"] == {
        "tipo": "vacaciones", "desde": "2026-11-09", "hasta": "2026-11-13",
    }
    rocio = por_nombre["Rocío Méndez"]
    assert rocio["disponibilidad"]["tipo"] == "baja"
    assert rocio["disponibilidad"]["desde"] == "2026-10-30"
    assert rocio["disponibilidad"]["hasta"] is None
    assert rocio["atiende"] == []
    assert por_nombre["Andrés Valle"]["disponibilidad"]["tipo"] == "cobertura"


def test_reglas_son_cinco_y_literales():
    texto = (RAIZ / "data" / "reglas.md").read_text(encoding="utf-8")
    reglas = re.findall(r"^\d+\. .+$", texto, flags=re.MULTILINE)
    assert reglas == [
        "1. El asistente es solo para colaboradores, no para clientes.",
        "2. Nunca comparte información confidencial: sueldos, teléfonos personales o datos de clientes.",
        "3. No responde dudas fiscales: las canaliza a Consultoría.",
        "4. Si no tiene la información, no inventa: canaliza a Capital Humano.",
        "5. Los descuentos mayores a 10% solo los autoriza Dirección.",
    ]
