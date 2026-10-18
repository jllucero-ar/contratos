"""
controles.py — core/controles.py
Controles determinísticos sobre la respuesta del modelo.

Verificación de citas del CCyCN: solo EXISTENCIA y FORMATO (el artículo está entre 1 y 2671
y está escrito de forma reconocible). NO verifica que el contenido del artículo respalde
lo que afirma el análisis.
"""

import re
import unicodedata

ART_MIN = 1
ART_MAX = 2671  # último artículo del CCyCN (Ley 26.994)

# "art.", "arts.", "artículo(s)" + lista de números: "765", "765, 766 y 767", "765 a 767"
_RE_ARTICULOS = re.compile(
    r"\b(?:arts?(?:\.\s*|\s+)|art[ií]culos?\s+)"
    r"(?P<lista>[\w.º°]+(?:\s*(?:,|\by\b|\be\b|\bal?\b|-|–)\s*\d[\w.º°]*)*)",
    re.IGNORECASE,
)
_RE_SEPARADOR = re.compile(r"\s*(?P<sep>,|\by\b|\be\b|\bal?\b|-|–)\s*", re.IGNORECASE)
_RE_NUMERO = re.compile(r"^\d{1,3}(?:\.\d{3})+$|^\d+$")

_RE_CCYCN = re.compile(
    r"\bCCyCN\b|\bCCCN\b|\bCC\s?y\s?C\b|\bC\.?\s?C\.?\s?y\s?C\.?\s?N\.?|C[óo]digo\s+Civil\s+y\s+Comercial",
    re.IGNORECASE,
)
_RE_OTRA_NORMA = re.compile(
    r"\b(?:ley|leyes|decreto|dnu|resoluci[óo]n|c[óo]digo\s+(?:procesal|penal|de\s+comercio|aduanero)|"
    r"cpccn|constituci[óo]n|c\.?n\.?)\b",
    re.IGNORECASE,
)
_RE_SUFIJO = re.compile(r"\s*(?:bis|ter|quater)\b", re.IGNORECASE)  # el CCyCN no tiene artículos "bis"/"ter"

_VENTANA_ANTES = 30
_VENTANA_DESPUES = 60
_GAP_HEREDA = 8  # "arts. 1198 y art. 1199 CCyCN": el 1° hereda la norma del 2°


def extraer_strings(obj) -> list[str]:
    """Todos los strings de un dict/lista anidado."""
    if isinstance(obj, str):
        return [obj]
    if isinstance(obj, dict):
        return [s for v in obj.values() for s in extraer_strings(v)]
    if isinstance(obj, (list, tuple)):
        return [s for v in obj for s in extraer_strings(v)]
    return []


def verificar_citas_ccycn(datos) -> dict:
    """
    Extrae las citas de artículos del CCyCN de todos los strings de `datos` y marca las inválidas.

    Solo se validan las citas atribuibles al CCyCN (mencionan "CCyCN" o "Código Civil y Comercial"
    junto a la cita). Las de otras normas (Ley 24.240, etc.) se cuentan sin validar.

    Returns:
        {"encontradas": [str], "invalidas": [{"cita": str, "motivo": str}],
         "otras_normas_no_verificadas": int, "paso": bool}
    """
    encontradas: list[str] = []
    invalidas: list[dict] = []
    otras = 0

    for texto in extraer_strings(datos):
        for cita in _extraer_citas(texto):
            if cita["norma"] != "ccycn":
                otras += 1
                continue
            if cita["valor"] not in encontradas:
                encontradas.append(cita["valor"])
            if cita["motivo"] and not any(i["cita"] == cita["valor"] for i in invalidas):
                invalidas.append({"cita": cita["valor"], "motivo": cita["motivo"]})

    return {
        "encontradas": encontradas,
        "invalidas": invalidas,
        "otras_normas_no_verificadas": otras,
        "paso": not invalidas,
    }


def _extraer_citas(texto: str) -> list[dict]:
    """Devuelve [{"valor", "motivo", "norma"}] para cada artículo citado en `texto`."""
    matches = list(_RE_ARTICULOS.finditer(texto))
    normas: list[str] = [""] * len(matches)

    # De atrás hacia adelante, para que una cita pueda heredar la norma de la siguiente
    for i in range(len(matches) - 1, -1, -1):
        m = matches[i]
        fin_ventana = matches[i + 1].start() if i + 1 < len(matches) else len(texto)
        despues = texto[m.end():min(fin_ventana, m.end() + _VENTANA_DESPUES)]
        ini_antes = matches[i - 1].end() if i > 0 else 0
        antes = texto[max(ini_antes, m.start() - _VENTANA_ANTES):m.start()]

        if _RE_CCYCN.search(despues):
            normas[i] = "ccycn"
        elif _RE_OTRA_NORMA.search(despues):
            normas[i] = "otra"
        elif i + 1 < len(matches) and len(despues.strip(" ,;y")) <= _GAP_HEREDA:
            normas[i] = normas[i + 1]
        elif _RE_CCYCN.search(antes):
            normas[i] = "ccycn"
        else:
            normas[i] = "otra"

    citas = []
    for m, norma in zip(matches, normas):
        items = _analizar_lista(m.group("lista"))
        if items and _RE_SUFIJO.match(texto, m.end()):
            items[-1] = (items[-1][0], "formato_irreconocible")
        for valor, motivo in items:
            citas.append({"valor": valor, "motivo": motivo, "norma": norma})
    return citas


def _analizar_lista(lista: str) -> list[tuple[str, str | None]]:
    """Convierte '765, 766 y 767' en [(valor_normalizado, motivo_o_None), ...]."""
    tokens = re.split(_RE_SEPARADOR, lista)  # [tok, sep, tok, sep, ...]
    resultado = []

    for idx in range(0, len(tokens), 2):
        tok = tokens[idx].strip().rstrip(".")
        tok = tok.replace("º", "").replace("°", "")

        if not any(c.isdigit() for c in tok):
            if idx > 0 or (tok.isalpha() and tok.islower()):
                break  # palabra común ("siguientes", "pertinentes", ...): no es una cita

        if not _RE_NUMERO.match(tok):
            resultado.append((tok, "formato_irreconocible"))
            continue

        numero = int(tok.replace(".", ""))
        motivo = None if ART_MIN <= numero <= ART_MAX else "fuera_de_rango"
        resultado.append((str(numero), motivo))

    return resultado


# --- Control de literalidad -------------------------------------------------------------------
#
# Verifica que ciertos valores "extraídos" aparezcan en el texto del contrato. Detecta valores
# inventados o alterados; NO verifica que estén bien interpretados. Solo mira campos que deberían
# copiarse del contrato (nombres, identificaciones, fechas, plazos, montos). Los campos de texto
# libre (objeto, cláusulas, riesgos) son paráfrasis y no se controlan.

CAMPOS_NOMBRE = (
    ("partes", "parte_a", "nombre"),
    ("partes", "parte_b", "nombre"),
)
CAMPOS_NUMERICOS = (
    ("partes", "parte_a", "identificacion"),
    ("partes", "parte_b", "identificacion"),
    ("plazo", "inicio"),
    ("plazo", "vencimiento"),
    ("plazo", "duracion"),
    ("canon", "monto_inicial"),
    ("canon", "vencimiento_pago"),
)
_RE_NUM_VALOR = re.compile(r"\d+(?:[.,\-/]\d+)*")
_MIN_DIGITOS = 2  # los números de 1 dígito ("3 años") se ignoran: coinciden con casi cualquier texto
_STOP_NOMBRE = {"sa", "srl", "sas", "s", "a", "l", "r", "de", "del", "la", "el", "y", "e", "los", "las"}


def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c)).lower()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", texto).split())


def _valor(datos: dict, ruta: tuple):
    for clave in ruta:
        if not isinstance(datos, dict):
            return None
        datos = datos.get(clave)
    return datos if isinstance(datos, str) and datos.strip() else None


def verificar_literalidad(datos: dict, texto_fuente: str) -> dict:
    """
    Returns:
        {"verificados": int, "no_verificables": int,
         "no_encontrados": [{"campo": "plazo.inicio", "motivo": "numero_no_encontrado"|"nombre_no_encontrado"}],
         "paso": bool}
    """
    # Texto con los separadores entre dígitos eliminados: "1.250.000" -> "1250000", "30-71234567-8" -> "30712345678"
    compacto = re.sub(r"(?<=\d)[.,\-/\s](?=\d)", "", texto_fuente)
    normalizado = _normalizar(texto_fuente)
    palabras_texto = set(normalizado.split())

    verificados = 0
    no_verificables = 0
    no_encontrados = []

    for ruta in CAMPOS_NOMBRE:
        valor = _valor(datos, ruta)
        if valor is None:
            continue
        verificados += 1
        n = _normalizar(valor)
        palabras = [p for p in n.split() if p not in _STOP_NOMBRE and len(p) >= 2]
        if n not in normalizado and not (palabras and all(p in palabras_texto for p in palabras)):
            no_encontrados.append({"campo": ".".join(ruta), "motivo": "nombre_no_encontrado"})

    for ruta in CAMPOS_NUMERICOS:
        valor = _valor(datos, ruta)
        if valor is None:
            continue
        numeros = [re.sub(r"\D", "", t) for t in _RE_NUM_VALOR.findall(valor)]
        numeros = [n for n in numeros if len(n) >= _MIN_DIGITOS]
        if not numeros:
            no_verificables += 1
            continue
        verificados += 1
        if not all(re.search(rf"(?<!\d){n}(?!\d)", compacto) for n in numeros):
            no_encontrados.append({"campo": ".".join(ruta), "motivo": "numero_no_encontrado"})

    return {
        "verificados": verificados,
        "no_verificables": no_verificables,
        "no_encontrados": no_encontrados,
        "paso": not no_encontrados,
    }


def citas_ccycn_en(texto: str) -> list[str]:
    """Artículos del CCyCN citados en `texto` con formato válido y dentro de rango (sin duplicados)."""
    vistos: list[str] = []
    for c in _extraer_citas(texto):
        if c["norma"] == "ccycn" and not c["motivo"] and c["valor"] not in vistos:
            vistos.append(c["valor"])
    return vistos
