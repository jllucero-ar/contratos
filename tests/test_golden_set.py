"""Consistencia del golden set: archivos completos, bien formados y expectativas coherentes con el texto."""

import json
import re
from pathlib import Path

import pytest

from core.controles import _normalizar
from core.extractor import extraer_texto

GOLDEN = Path(__file__).parent.parent / "evaluacion" / "golden"
CLAVES_VALIDAS = {"nulo", "permite_nulo", "contiene", "no_contiene", "alguno"}
CAMPOS_VALIDOS = {
    "partes.parte_a.nombre", "partes.parte_a.identificacion", "partes.parte_a.rol",
    "partes.parte_b.nombre", "partes.parte_b.identificacion", "partes.parte_b.rol",
    "plazo.inicio", "plazo.vencimiento", "plazo.duracion", "plazo.observaciones",
    "canon.monto_inicial", "canon.ajuste", "canon.vencimiento_pago",
    "clausulas.rescision", "clausulas.mora", "clausulas.limitacion_responsabilidad",
    "clausulas.jurisdiccion", "clausulas.notificaciones",
}
CASOS = sorted(p.name.removesuffix(".esperado.json") for p in GOLDEN.glob("*.esperado.json"))


def test_hay_al_menos_cinco_casos():
    assert len(CASOS) >= 5


@pytest.mark.parametrize("caso", CASOS)
def test_caso_completo_y_bien_formado(caso):
    assert (GOLDEN / f"{caso}.txt").exists() and (GOLDEN / f"{caso}.pdf").exists()
    esperado = json.loads((GOLDEN / f"{caso}.esperado.json").read_text(encoding="utf-8"))
    assert esperado["id"] == caso and esperado["trampa"]
    assert esperado["campos"]
    for campo, spec in esperado["campos"].items():
        assert campo in CAMPOS_VALIDOS, campo
        assert set(spec) <= CLAVES_VALIDAS, (campo, spec)
        assert not ("nulo" in spec and len(spec) > 1), f"{campo}: 'nulo' no se combina con otras condiciones"


@pytest.mark.parametrize("caso", CASOS)
def test_lo_esperado_figura_en_el_contrato(caso):
    """Lo que 'contiene' debe estar en el texto fuente (si no, la expectativa estaría mal anotada)."""
    texto = _normalizar((GOLDEN / f"{caso}.txt").read_text(encoding="utf-8"))
    esperado = json.loads((GOLDEN / f"{caso}.esperado.json").read_text(encoding="utf-8"))
    for campo, spec in esperado["campos"].items():
        for token in spec.get("contiene", []):
            assert _normalizar(token) in texto, f"{caso} · {campo}: '{token}' no está en el contrato"


@pytest.mark.parametrize("caso", CASOS)
def test_pdf_extraible_y_sin_datos_reales(caso):
    ext = extraer_texto(str(GOLDEN / f"{caso}.pdf"))
    assert ext["exito"] and ext["metodo"] == "pdfplumber"
    fuente = (GOLDEN / f"{caso}.txt").read_text(encoding="utf-8")
    # el PDF debe contener el mismo contenido que el .txt (comparando palabras largas)
    palabras = {p for p in re.findall(r"[A-Za-zÁÉÍÓÚáéíóúñÑ]{8,}", fuente)}
    assert all(p in ext["texto"] for p in list(palabras)[:25])


def test_datos_ficticios():
    """Solo dominios .example y CUIT 30-7000000x: nada que parezca un dato real."""
    for txt in GOLDEN.glob("*.txt"):
        contenido = txt.read_text(encoding="utf-8")
        for mail in re.findall(r"[\w.]+@[\w.]+", contenido):
            assert mail.endswith(".example"), mail
        for cuit in re.findall(r"\b30-\d{8}-\d\b", contenido):
            assert cuit.startswith("30-7000000"), cuit


@pytest.mark.parametrize("caso", CASOS)
def test_parte_a_aparece_antes_que_parte_b(caso):
    """Convención: parte_a/parte_b van por orden de aparición en el contrato (no por rol)."""
    texto = _normalizar((GOLDEN / f"{caso}.txt").read_text(encoding="utf-8"))
    esperado = json.loads((GOLDEN / f"{caso}.esperado.json").read_text(encoding="utf-8"))["campos"]

    def posicion(campo):
        spec = esperado[campo]
        tokens = spec.get("contiene") or spec.get("alguno")
        return min(texto.find(_normalizar(t)) for t in tokens)

    assert 0 <= posicion("partes.parte_a.nombre") < posicion("partes.parte_b.nombre")
