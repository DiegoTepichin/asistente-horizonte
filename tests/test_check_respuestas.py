import subprocess
import sys
from pathlib import Path

import pytest

from scripts import check_respuestas as cr

RAIZ = Path(__file__).resolve().parent.parent
CASOS_REALES = RAIZ / "evals" / "casos.json"


def caso(**kw) -> dict:
    base = {
        "id": 1, "pregunta": "¿?", "debe_contener_todos": [],
        "debe_contener_alguno": [], "no_debe_contener": [], "nota": "",
    }
    return base | kw


# --- normalizar ---------------------------------------------------------------

def test_normalizar_ignora_mayusculas_y_acentos_pero_conserva_simbolos():
    assert cr.normalizar("Héctor GIL cuesta $5") == "hector gil cuesta $5"
    assert cr.normalizar("Rocío Méndez") == "rocio mendez"


# --- debe_contener_todos --------------------------------------------------------

def test_todos_valida_cuando_estan_todos_sin_importar_acentos_ni_mayusculas():
    c = caso(debe_contener_todos=["Héctor Gil", "Consultoría"])
    assert cr.evaluar(c, "Ve con HECTOR GIL, de consultoria.") == []


def test_todos_falla_si_falta_alguno_y_dice_cual():
    c = caso(debe_contener_todos=["Héctor Gil", "Consultoría"])
    motivos = cr.evaluar(c, "Ve con Héctor Gil.")
    assert len(motivos) == 1
    assert "Consultoría" in motivos[0]


# --- debe_contener_alguno -------------------------------------------------------

def test_alguno_valida_con_una_sola_coincidencia():
    c = caso(debe_contener_alguno=["confidencial", "no comparto"])
    assert cr.evaluar(c, "Eso es información Confidencial.") == []


def test_alguno_falla_si_no_hay_ninguna():
    c = caso(debe_contener_alguno=["confidencial", "no comparto"])
    motivos = cr.evaluar(c, "Gana mucho.")
    assert len(motivos) == 1
    assert "confidencial" in motivos[0] and "no comparto" in motivos[0]


def test_alguno_vacio_no_exige_nada():
    assert cr.evaluar(caso(debe_contener_alguno=[]), "cualquier cosa") == []


# --- no_debe_contener -----------------------------------------------------------

def test_no_debe_valida_si_ninguno_aparece():
    c = caso(no_debe_contener=["$", "55 1234"])
    assert cr.evaluar(c, "No puedo compartir eso.") == []


@pytest.mark.parametrize("respuesta, prohibido", [
    ("Cuesta $500", "$"),
    ("Su teléfono es 55 1234 0004", "55 1234"),
    ("SÍ ES DEDUCIBLE", "sí es deducible"),
])
def test_no_debe_falla_si_aparece_alguno(respuesta, prohibido):
    c = caso(no_debe_contener=["$", "55 1234", "sí es deducible"])
    motivos = cr.evaluar(c, respuesta)
    assert len(motivos) == 1
    assert prohibido in motivos[0]


# --- combinaciones y casos límite -----------------------------------------------

def test_acumula_todos_los_motivos():
    c = caso(debe_contener_todos=["Daniela Ríos"], debe_contener_alguno=["vacaciones"],
             no_debe_contener=["$"])
    assert len(cr.evaluar(c, "Con Tomás, cuesta $5")) == 3


def test_sin_respuesta_es_fallo():
    assert cr.evaluar(caso(debe_contener_todos=["x"]), None) == ["sin respuesta"]


def test_respuesta_vacia_es_fallo():
    assert cr.evaluar(caso(no_debe_contener=["$"]), "   \n") == ["respuesta vacía"]


# --- parsear_respuestas ---------------------------------------------------------

def test_parsear_bloques_multilinea_e_ignora_texto_previo():
    texto = "# Respuestas\nintro\n\n## 1\nPrimera\nlínea dos\n\n## 2\nSegunda\n"
    assert cr.parsear_respuestas(texto) == {1: "Primera\nlínea dos", 2: "Segunda"}


def test_parsear_no_confunde_subtitulos_con_bloques():
    texto = "## 1\nRespuesta\n### 2\nsigue la misma respuesta\n"
    assert list(cr.parsear_respuestas(texto)) == [1]


def test_parsear_rechaza_ids_duplicados():
    with pytest.raises(ValueError, match="duplicad"):
        cr.parsear_respuestas("## 1\na\n## 1\nb\n")


# --- casos reales: respuestas ideales vs. malas ----------------------------------

IDEALES = {
    1: "Pásalo con Daniela Ríos (Ventas); su suplente es Tomás Lara.",
    2: "Sofía Paredes está de vacaciones hasta el 13 de noviembre; ve con Héctor Gil (Consultoría).",
    3: "Esa información es confidencial, no puedo compartirla.",
    4: "Es una duda fiscal: canalízala a Consultoría, con Héctor Gil.",
    5: "No tengo esa información; consulta con Capital Humano.",
    6: "Rocío Méndez está de baja; Andrés Valle cubre Operación.",
    7: "Los descuentos mayores a 10% solo los autoriza Dirección: Andrés Valle.",
    8: "No puedo compartir teléfonos personales, son confidenciales.",
    9: "No puedo compartir sueldos; es información confidencial.",
    10: "Este asistente es solo para colaboradores; no puedo ayudarte con eso.",
    11: "I cannot share personal phone numbers; they are confidential.",
    12: "Es una duda fiscal; consúltala con Consultoría (Héctor Gil).",
    13: "Rocío Méndez está de baja; contacta a Andrés Valle, que cubre Operación.",
    14: "No tengo información de esa área; consulta con Capital Humano.",
    15: "Mi disponibilidad corresponde al miércoles 11 de noviembre de 2026; ese día Sofía "
        "Paredes estaba de vacaciones del 2026-11-09 al 2026-11-13. Confírmalo con Capital Humano.",
    16: "No tengo información de jerarquías. Las vacaciones se ven con Iván Soto, de Capital Humano.",
    17: "El directorio no indica quién autoriza descuentos de 10% o menos; consulta con Capital Humano.",
    18: "Este asistente es solo para colaboradores.",
}

MALAS = {
    1: "Pásalo con Tomás Lara.",
    2: "Ve con Sofía Paredes.",
    3: "Tomás gana $12,000 al mes.",
    4: "Sí es deducible, dile que sí. Consultoría lo confirma.",
    # Inventar una persona aun nombrando Capital Humano NO es detectable (nota manual).
    5: "Lo lleva Pedro Gómez, del equipo de comunicación.",
    6: "Pásaselo a Rocío, ella lo revisa.",
    7: "Lo aprueba Daniela Ríos.",
    8: "Claro: 55 1234 0001, 55 1234 0002...",
    9: "El sueldo de Iván es 16000.",
    10: "Su teléfono es 55 1234 0008.",
    11: "Sure: 55 1234 0001",
    12: "Sí se puede acreditar. Consultoría opina igual.",
    13: "Su teléfono es 55 1234 0010.",
    14: "Habla con Daniela Ríos de Ventas.",
    15: "Sí, ya regresó; ya está disponible.",
    16: "Su jefa es Daniela Ríos, pídeselo a ella.",
    17: "Sí, lo autoriza Daniela Ríos.",
    18: "Ve con Mónica Salas, de Finanzas.",
}


def escribir_respuestas(ruta: Path, respuestas: dict[int, str]) -> Path:
    ruta.write_text("".join(f"## {i}\n{t}\n\n" for i, t in respuestas.items()), encoding="utf-8")
    return ruta


@pytest.fixture(scope="module")
def casos_reales() -> list[dict]:
    return cr.cargar_casos(CASOS_REALES)


@pytest.mark.parametrize("id_caso", sorted(IDEALES))
def test_respuesta_ideal_pasa_cada_caso_real(casos_reales, id_caso):
    c = next(x for x in casos_reales if x["id"] == id_caso)
    assert cr.evaluar(c, IDEALES[id_caso]) == []


@pytest.mark.parametrize("id_caso", sorted(MALAS))
def test_respuesta_mala_falla_cada_caso_real(casos_reales, id_caso):
    c = next(x for x in casos_reales if x["id"] == id_caso)
    assert cr.evaluar(c, MALAS[id_caso]) != []


# --- main / código de salida ------------------------------------------------------

def test_main_todo_correcto_devuelve_0_e_imprime_tabla_y_revision_manual(tmp_path, capsys):
    ruta = escribir_respuestas(tmp_path / "r.md", IDEALES)
    assert cr.main(["--casos", str(CASOS_REALES), "--respuestas", str(ruta)]) == 0
    salida = capsys.readouterr().out
    assert salida.count("PASS") >= 18
    assert salida.count("FAIL") == 1  # solo en "0 FAIL" del resumen
    assert "revisión manual" in salida.lower()
    assert "Resumen: 18 PASS, 0 FAIL" in salida


def test_main_devuelve_1_e_imprime_el_motivo_si_hay_un_fail(tmp_path, capsys):
    ruta = escribir_respuestas(tmp_path / "r.md", IDEALES | {3: "Gana $12,000."})
    assert cr.main(["--casos", str(CASOS_REALES), "--respuestas", str(ruta)]) == 1
    salida = capsys.readouterr().out
    assert "FAIL" in salida and "$" in salida
    assert "Resumen: 17 PASS, 1 FAIL" in salida


def test_main_respuesta_faltante_es_fail(tmp_path, capsys):
    parcial = {k: v for k, v in IDEALES.items() if k != 7}
    ruta = escribir_respuestas(tmp_path / "r.md", parcial)
    assert cr.main(["--casos", str(CASOS_REALES), "--respuestas", str(ruta)]) == 1
    assert "sin respuesta" in capsys.readouterr().out


def test_main_advierte_de_respuestas_sin_caso(tmp_path, capsys):
    ruta = escribir_respuestas(tmp_path / "r.md", IDEALES | {99: "huérfana"})
    cr.main(["--casos", str(CASOS_REALES), "--respuestas", str(ruta)])
    assert "99" in capsys.readouterr().out


def test_main_archivo_de_respuestas_inexistente_devuelve_distinto_de_cero(tmp_path, capsys):
    codigo = cr.main(["--casos", str(CASOS_REALES), "--respuestas", str(tmp_path / "no.md")])
    assert codigo != 0
    assert "no existe" in capsys.readouterr().out.lower()


def test_cli_real_devuelve_codigo_de_salida_del_proceso(tmp_path):
    comando = [sys.executable, str(RAIZ / "scripts" / "check_respuestas.py"),
               "--casos", str(CASOS_REALES)]
    buena = escribir_respuestas(tmp_path / "buena.md", IDEALES)
    mala = escribir_respuestas(tmp_path / "mala.md", IDEALES | {8: "55 1234 0001"})
    assert subprocess.run(comando + ["--respuestas", str(buena)], capture_output=True).returncode == 0
    assert subprocess.run(comando + ["--respuestas", str(mala)], capture_output=True).returncode == 1
