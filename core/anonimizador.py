"""
anonimizador.py — core/anonimizador.py
Reemplaza DNI, CUIT, CUIL, emails y teléfonos por marcadores ([DNI_1], [CUIT_1], ...) ANTES de
enviar el texto al proveedor de IA, y restaura los valores reales en el resultado final.

- El mapeo marcador -> valor real vive solo en memoria (en la instancia). Nunca se loguea,
  se serializa ni se devuelve.
- Alcance: SOLO estos cinco tipos de dato. Nombres, domicilios, montos y demás texto del
  contrato NO se anonimizan.
- Detección por regex, conservadora: prefiere no tocar un número ambiguo antes que alterar
  montos, fechas o matrículas. Puede haber falsos negativos (formatos atípicos).
"""

import re

TIPOS = ("DNI", "CUIT", "CUIL", "EMAIL", "TEL")

_RE_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

# CUIT/CUIL: 11 dígitos, prefijo válido, guiones/espacios opcionales
_RE_CUIT = re.compile(r"(?<![\d.-])(?:20|23|24|25|26|27|30|33|34)[-\s]?\d{8}[-\s]?\d(?![\d])")
_RE_ETIQUETA_CUIL = re.compile(r"CUIL\W{0,3}(?:N[°º]\W{0,3})?$", re.IGNORECASE)

# DNI: solo con etiqueta explícita; se reemplaza únicamente el número
_RE_DNI = re.compile(
    r"(?P<etiqueta>\b(?:D\.?N\.?I\.?|Documento\s+Nacional\s+de\s+Identidad|Documento\s+de\s+Identidad)"
    r"\s*(?:N[°º.o]*\s*)?:?\s*)(?P<num>\d{1,2}\.?\d{3}\.?\d{3})(?![\d])",
    re.IGNORECASE,
)

# Teléfonos: (A) con +54, (B) con etiqueta, (C) con característica 0xx(xx)
_NUM_TEL = r"\+?\(?\d[\d()\s-]{6,16}\d"
_RE_TEL_INTERNACIONAL = re.compile(r"(?<![\d\w])\+54[\s\d()-]{8,16}\d")
_RE_TEL_ETIQUETA = re.compile(
    r"(?P<etiqueta>\b(?:tel(?:[eé]fono)?|cel(?:ular)?|m[oó]vil|whats\s?app|fax)\b\.?\s*(?:N[°º]\s*)?:?\s*)"
    rf"(?P<num>{_NUM_TEL})",
    re.IGNORECASE,
)
_RE_TEL_CARACTERISTICA = re.compile(r"(?<![\d.,$/\w-])\(?0\d{2,4}\)?[\s-]?(?:15[\s-]?)?\d{3,4}[\s-]?\d{4}(?!\d|[.,]\d|/)")

_RE_MARCADOR = re.compile(r"\[(?:%s)_\d+\]" % "|".join(TIPOS))


class Anonimizador:
    """Una instancia por análisis: el mapeo no se comparte entre contratos."""

    def __init__(self):
        self._mapa: dict[str, str] = {}      # marcador -> valor real (solo en memoria)
        self._inverso: dict[tuple, str] = {}  # (tipo, valor) -> marcador
        self._conteo: dict[str, int] = {}

    def __repr__(self):
        return f"Anonimizador(conteo={self._conteo})"

    # --- API pública ---

    @property
    def conteo(self) -> dict:
        """Cantidad de valores distintos anonimizados por tipo (sin los valores)."""
        return dict(self._conteo)

    def anonimizar(self, texto: str) -> str:
        texto = _RE_EMAIL.sub(lambda m: self._marcador("EMAIL", m.group(0)), texto)
        texto = self._sub_cuit(texto)
        texto = _RE_DNI.sub(lambda m: m.group("etiqueta") + self._marcador("DNI", m.group("num")), texto)
        texto = _RE_TEL_ETIQUETA.sub(lambda m: m.group("etiqueta") + self._marcador("TEL", m.group("num").strip()), texto)
        texto = _RE_TEL_INTERNACIONAL.sub(lambda m: self._marcador("TEL", m.group(0).strip()), texto)
        texto = _RE_TEL_CARACTERISTICA.sub(lambda m: self._marcador("TEL", m.group(0).strip()), texto)
        return texto

    def restaurar(self, obj):
        """Restituye los valores reales en todos los strings de un dict/lista anidado."""
        if isinstance(obj, str):
            return _RE_MARCADOR.sub(lambda m: self._mapa.get(m.group(0), m.group(0)), obj)
        if isinstance(obj, dict):
            return {k: self.restaurar(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self.restaurar(v) for v in obj]
        return obj

    @staticmethod
    def contar_marcadores(obj) -> int:
        """Cuenta marcadores que siguen presentes en `obj` (útil tras restaurar)."""
        if isinstance(obj, str):
            return len(_RE_MARCADOR.findall(obj))
        if isinstance(obj, dict):
            return sum(Anonimizador.contar_marcadores(v) for v in obj.values())
        if isinstance(obj, list):
            return sum(Anonimizador.contar_marcadores(v) for v in obj)
        return 0

    # --- Internos ---

    def _sub_cuit(self, texto: str) -> str:
        def reemplazo(m):
            previo = texto[max(0, m.start() - 12):m.start()]
            tipo = "CUIL" if _RE_ETIQUETA_CUIL.search(previo) else "CUIT"
            return self._marcador(tipo, m.group(0))

        return _RE_CUIT.sub(reemplazo, texto)

    def _marcador(self, tipo: str, valor: str) -> str:
        clave = (tipo, valor)
        if clave not in self._inverso:
            self._conteo[tipo] = self._conteo.get(tipo, 0) + 1
            marcador = f"[{tipo}_{self._conteo[tipo]}]"
            self._inverso[clave] = marcador
            self._mapa[marcador] = valor
        return self._inverso[clave]
