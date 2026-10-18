"""
esquema.py — contratos/esquema.py
Esquema de salida del análisis de contratos (Pydantic).
Genérico: sirve para cualquier tipo de contrato (locación, servicios, suministro, etc.).
"""

import json
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class _Base(BaseModel):
    # Claves desconocidas = error de validación (el modelo no puede inventar campos)
    model_config = ConfigDict(extra="forbid")


class Parte(_Base):
    nombre: Optional[str] = Field(description="nombre o razón social")
    identificacion: Optional[str] = Field(description="CUIT/CUIL/DNI u otra identificación")
    rol: Optional[str] = Field(
        description="rol en el contrato (ej: locador, locatario, prestador, cliente, vendedor, comprador)"
    )


class Partes(_Base):
    parte_a: Parte = Field(description="primera parte nombrada en el encabezamiento del contrato (por orden de aparición, sin importar su rol)")
    parte_b: Parte = Field(description="segunda parte nombrada en el encabezamiento del contrato (por orden de aparición, sin importar su rol)")


class Plazo(_Base):
    inicio: Optional[str] = Field(description="fecha de inicio")
    vencimiento: Optional[str] = Field(description="fecha de vencimiento")
    duracion: Optional[str] = Field(description="duración expresada en años/meses")
    observaciones: Optional[str] = Field(description="condiciones de renovación o preaviso si las hay")


class Canon(_Base):
    monto_inicial: Optional[str] = Field(description="monto y moneda del precio o canon inicial")
    ajuste: Optional[str] = Field(description="mecanismo de ajuste si lo hay (IPC, dólar, etc.)")
    vencimiento_pago: Optional[str] = Field(description="plazo o fecha de pago")


class Clausulas(_Base):
    rescision: Optional[str] = Field(description="condiciones y penalidades por rescisión anticipada")
    mora: Optional[str] = Field(description="intereses y condiciones de mora")
    limitacion_responsabilidad: Optional[str] = Field(
        description="límites a la responsabilidad de las partes si los hay"
    )
    jurisdiccion: Optional[str] = Field(description="tribunales competentes pactados")
    notificaciones: Optional[str] = Field(description="medios y plazos para notificaciones entre partes")


class AnalisisContrato(_Base):
    partes: Partes
    objeto: Optional[str] = Field(
        description="descripción del bien, servicio u obligación principal del contrato"
    )
    plazo: Plazo
    canon: Canon
    clausulas: Clausulas
    riesgos: list[str] = Field(
        description="lista de cláusulas o condiciones que representan un riesgo para alguna de las partes, "
                    "cada una con su fundamento normativo"
    )
    observaciones_generales: Optional[str] = Field(
        description="resumen ejecutivo del contrato y recomendaciones principales"
    )


def plantilla(modelo: type[BaseModel] = AnalisisContrato) -> dict:
    """Estructura de ejemplo (campo -> descripción) derivada del modelo, para el prompt."""
    resultado = {}
    for nombre, campo in modelo.model_fields.items():
        anotacion = campo.annotation
        if isinstance(anotacion, type) and issubclass(anotacion, BaseModel):
            resultado[nombre] = plantilla(anotacion)
        elif getattr(anotacion, "__origin__", None) is list:
            resultado[nombre] = [campo.description]
        else:
            resultado[nombre] = campo.description
    return resultado


def plantilla_json() -> str:
    return json.dumps(plantilla(), ensure_ascii=False, indent=2)


def resumir_errores(error) -> str:
    """Resume un ValidationError como 'ruta: mensaje' SIN incluir los valores recibidos."""
    lineas = []
    for e in error.errors():
        ruta = ".".join(str(x) for x in e["loc"]) or "(raíz)"
        lineas.append(f"- {ruta}: {e['msg']}")
    return "\n".join(lineas)
