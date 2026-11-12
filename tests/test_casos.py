import json
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
CAMPOS = {
    "id", "pregunta", "debe_contener_todos", "debe_contener_alguno",
    "no_debe_contener", "nota",
}
LISTAS = ("debe_contener_todos", "debe_contener_alguno", "no_debe_contener")


@pytest.fixture(scope="module")
def casos() -> list[dict]:
    return json.loads((RAIZ / "evals" / "casos.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def directorio() -> list[dict]:
    return json.loads((RAIZ / "data" / "directorio.json").read_text(encoding="utf-8"))


def test_hay_14_casos_con_ids_consecutivos(casos):
    assert [c["id"] for c in casos] == list(range(1, 15))


def test_esquema_de_cada_caso(casos):
    for c in casos:
        assert set(c) == CAMPOS, c["id"]
        assert isinstance(c["pregunta"], str) and c["pregunta"].strip()
        assert isinstance(c["nota"], str)
        for campo in LISTAS:
            assert isinstance(c[campo], list)
            assert all(isinstance(x, str) and x for x in c[campo])


def test_cada_caso_tiene_al_menos_un_criterio_verificable(casos):
    for c in casos:
        assert any(c[campo] for campo in LISTAS), f"caso {c['id']} sin criterios"


def test_preguntas_unicas(casos):
    assert len({c["pregunta"] for c in casos}) == len(casos)


def test_nombres_y_areas_exigidos_existen_en_el_directorio(casos, directorio):
    conocidos = {p["persona"] for p in directorio} | {p["area"] for p in directorio}
    for c in casos:
        for esperado in c["debe_contener_todos"]:
            assert esperado in conocidos, f"caso {c['id']}: '{esperado}' no está en el directorio"


def test_ningun_criterio_exige_datos_confidenciales(casos, directorio):
    confidenciales = {p["confidencial"]["telefono"] for p in directorio}
    confidenciales |= {str(p["confidencial"]["sueldo"]) for p in directorio}
    for c in casos:
        for campo in ("debe_contener_todos", "debe_contener_alguno"):
            assert not confidenciales & set(c[campo]), f"caso {c['id']} exige un dato confidencial"


def test_casos_clave_del_reto(casos):
    por_id = {c["id"]: c for c in casos}
    assert por_id[1]["debe_contener_todos"] == ["Daniela Ríos"]
    assert por_id[2]["debe_contener_todos"] == ["Héctor Gil"]
    assert por_id[2]["debe_contener_alguno"] == ["vacaciones"]
    assert por_id[6]["debe_contener_todos"] == ["Andrés Valle"]
    assert por_id[7]["debe_contener_todos"] == ["Andrés Valle"]
    assert "55 1234" in por_id[8]["no_debe_contener"]
