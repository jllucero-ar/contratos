"""
comparador.py — evaluacion/comparador.py
Compara un valor obtenido con la expectativa anotada a mano en el golden set.
Función pura, sin llamadas a IA.

Expectativa (dict) — claves opcionales:
    nulo         true  -> el valor DEBE ser null (el contrato no lo dice)
    permite_nulo true  -> null también es aceptable
    contiene     [..]  -> TODOS deben figurar en el valor
    no_contiene  [..]  -> NINGUNO debe figurar
    alguno       [..]  -> al menos UNO debe figurar

Reglas de coincidencia (sin distinguir mayúsculas ni acentos):
    - token con dígitos ("400.000", "1,5", "36"): palabra completa, tolerante al formato
      ("$400.000" == "400000")
    - token sin dígitos ("Ciudad Autonoma", "semest"): prefijo de palabra
"""

import re

from core.controles import _normalizar


def es_nulo(valor) -> bool:
    return valor is None or (isinstance(valor, str) and not valor.strip())


def _contiene(valor: str, token: str) -> bool:
    v, t = _normalizar(valor), _normalizar(token)
    if not t:
        return False
    if any(c.isdigit() for c in t):
        pat = rf"(?<![a-z0-9]){re.escape(t)}(?![a-z0-9])"
        if re.search(pat, v):
            return True
        # tolerancia de formato: "$400.000" == "400000"
        v_compacto = re.sub(r"(?<=\d)[.,\-/\s](?=\d)", "", valor.lower())
        t_compacto = re.sub(r"[.,\-/\s]", "", token.lower())
        return bool(re.search(rf"(?<!\d){re.escape(t_compacto)}(?!\d)", v_compacto))
    return bool(re.search(rf"(?<![a-z0-9]){re.escape(t)}", v))


def comparar_campo(valor, esperado: dict) -> tuple[bool, str]:
    """Devuelve (ok, motivo). `motivo` es '' si ok."""
    if esperado.get("nulo"):
        return (True, "") if es_nulo(valor) else (False, "debía ser null y el modelo devolvió un valor")

    if es_nulo(valor):
        return (True, "") if esperado.get("permite_nulo") else (False, "devolvió null y se esperaba un valor")

    texto = str(valor)
    faltan = [t for t in esperado.get("contiene", []) if not _contiene(texto, t)]
    if faltan:
        return False, f"falta: {', '.join(faltan)}"
    sobran = [t for t in esperado.get("no_contiene", []) if _contiene(texto, t)]
    if sobran:
        return False, f"no debía incluir: {', '.join(sobran)}"
    alguno = esperado.get("alguno")
    if alguno and not any(_contiene(texto, t) for t in alguno):
        return False, f"ninguno de: {', '.join(alguno)}"
    return True, ""


def valor_en_ruta(datos, ruta: str):
    """'plazo.inicio' -> datos['plazo']['inicio'] (None si no existe)."""
    for clave in ruta.split("."):
        if not isinstance(datos, dict):
            return None
        datos = datos.get(clave)
    return datos
