"""Tests de escritura del log de auditoría. IA y extracción mockeadas; datos ficticios."""

import hashlib
import json
from unittest.mock import patch

from contratos import analizador
from core import audit_log

TEXTO = "Cliente Ejemplo, DNI 12.345.678, mail secreto@ficticio.example, Tel: 011 4444-5555. CLAUSULA_SECRETA_XYZ."
VALIDO = {
    "partes": {"parte_a": {"nombre": "Cliente Ejemplo", "identificacion": "[DNI_1]", "rol": "cliente"},
               "parte_b": {"nombre": None, "identificacion": None, "rol": None}},
    "objeto": None,
    "plazo": {"inicio": None, "vencimiento": None, "duracion": None, "observaciones": None},
    "canon": {"monto_inicial": None, "ajuste": None, "vencimiento_pago": None},
    "clausulas": {"rescision": None, "mora": None, "limitacion_responsabilidad": None,
                  "jurisdiccion": None, "notificaciones": None},
    "riesgos": ["Mora (art. 886 CCyCN) y art. 9999 CCyCN."],
    "observaciones_generales": None,
}


def _ia(texto, truncada=False, exito=True):
    return {"exito": exito, "respuesta": texto, "proveedor": "mock", "modelo": "mock-1", "truncada": truncada,
            "tokens": {"entrada": 100, "salida": 50}, "error": None if exito else "fallo con CLAUSULA_SECRETA_XYZ"}


def _correr(tmp_path, ia_side_effect, extraccion=None):
    pdf = tmp_path / "c.pdf"
    pdf.write_bytes(b"%PDF-contenido-ficticio")
    ext = extraccion or {"exito": True, "texto": TEXTO, "paginas": 1, "metodo": "pdfplumber", "error": None}
    logs = tmp_path / "logs"
    with patch.object(analizador, "extraer_texto", return_value=ext), \
         patch.object(analizador, "llamar_ia", side_effect=ia_side_effect):
        res = analizador.analizar_contrato(str(pdf), dir_logs=str(logs))
    lineas = [json.loads(l) for f in logs.glob("analisis_*.jsonl") for l in f.read_text(encoding="utf-8").splitlines()]
    return res, lineas, pdf


def test_una_linea_por_analisis_exitoso(tmp_path):
    res, lineas, pdf = _correr(tmp_path, [_ia(json.dumps(VALIDO))])
    assert res["exito"] and len(lineas) == 1
    r = lineas[0]
    assert r["proveedor"] == "mock" and r["modelo"] == "mock-1"
    assert r["prompt_version"] == analizador.PROMPT_VERSION
    assert r["pdf_sha256"] == hashlib.sha256(pdf.read_bytes()).hexdigest()
    assert r["tokens"] == {"entrada": 100, "salida": 50}
    assert r["intentos"] == 1 and r["exito"] is True and r["error_codigo"] is None
    c = r["controles"]
    assert c["esquema_valido"] is True and c["respuesta_completa"] is True
    assert c["citas_ccycn"] == {"paso": False, "encontradas": 2, "invalidas": 1}
    assert c["anonimizacion"]["por_tipo"] == {"DNI": 1, "EMAIL": 1, "TEL": 1}


def test_el_log_no_contiene_contrato_ni_datos_personales(tmp_path):
    _, _, _ = _correr(tmp_path, [_ia(json.dumps(VALIDO))])
    crudo = "".join(f.read_text(encoding="utf-8") for f in (tmp_path / "logs").glob("*.jsonl"))
    for prohibido in ("12.345.678", "secreto@ficticio.example", "011 4444-5555", "CLAUSULA_SECRETA_XYZ",
                      "Cliente Ejemplo"):
        assert prohibido not in crudo


def test_se_loguean_los_errores_sin_mensaje_libre(tmp_path):
    res, lineas, _ = _correr(tmp_path, [_ia("", exito=False)])
    assert not res["exito"]
    r = lineas[0]
    assert r["exito"] is False and r["error_codigo"] == "proveedor"
    assert "CLAUSULA_SECRETA_XYZ" not in json.dumps(r)


def test_log_de_truncada_y_esquema_invalido(tmp_path):
    _, lineas, _ = _correr(tmp_path, [_ia('{"a":', truncada=True)])
    assert lineas[0]["error_codigo"] == "truncada" and lineas[0]["controles"]["respuesta_completa"] is False
    (tmp_path / "otro").mkdir()
    _, lineas, _ = _correr(tmp_path / "otro", [_ia("x"), _ia("y")])
    assert lineas[0]["error_codigo"] == "esquema_invalido"
    assert lineas[0]["intentos"] == 2 and lineas[0]["tokens"]["entrada"] == 200


def test_error_de_extraccion_tambien_se_loguea(tmp_path):
    ext = {"exito": False, "texto": "", "paginas": 0, "metodo": None, "error": "no se pudo"}
    _, lineas, _ = _correr(tmp_path, [], extraccion=ext)
    assert lineas[0]["error_codigo"] == "extraccion" and lineas[0]["proveedor"] is None


def test_registrar_agrega_lineas_y_codigo_desconocido(tmp_path):
    base = dict(proveedor="p", modelo="m", prompt_version="x", pdf_sha256=None, tokens_entrada=None,
                tokens_salida=None, intentos=1, controles={}, exito=False)
    a = audit_log.registrar(audit_log.construir_registro(error_codigo="inventado", **base), tmp_path)
    audit_log.registrar(audit_log.construir_registro(**base), tmp_path)
    lineas = [json.loads(l) for l in a.read_text(encoding="utf-8").splitlines()]
    assert len(lineas) == 2 and lineas[0]["error_codigo"] == "desconocido"
