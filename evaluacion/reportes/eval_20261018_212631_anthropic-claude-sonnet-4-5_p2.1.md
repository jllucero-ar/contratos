# Evaluación — anthropic / claude-sonnet-4-5 (prompt 2.1)

_2026-10-18T21:26:31+00:00 · golden set ficticio · 5 casos_

| Métrica | Valor |
|---|---|
| Exactitud de campos | 100.0% |
| Respeto de nulos (no inventar) | 100.0% |
| Citas CCyCN inválidas | 0.0% de 47 |
| Riesgos esperados detectados (recall) | 84.6% (11/13) |
| Riesgos detectados con artículo anotado como correcto | 77.8% |
| Citas de riesgos a revisar a mano | 15 de 24 |
| Riesgos adicionales del modelo (sin anotar) | 14 |
| Valores no hallados en el texto (literalidad) | 1 |
| Casos con error | 0 |
| Reintentos | 0 |
| Tokens (entrada / salida) | 7401 / 6629 |

## Por caso

| Caso | Campos | Nulos | Citas inv. | Literalidad | Intentos |
|---|---|---|---|---|---|
| lc01_locacion_comercial | 14/14 | 0/0 | 0/11 | 0 | 1 |
| lv04_locacion_vivienda | 14/14 | 0/0 | 0/7 | 0 | 1 |
| mt05_mantenimiento_incompleto | 11/11 | 5/5 | 0/8 | 0 | 1 |
| sm03_suministro | 11/11 | 0/0 | 0/9 | 1 | 1 |
| sv02_servicios_profesionales | 13/13 | 3/3 | 0/12 | 0 | 1 |

## Riesgos

| Caso | Riesgo esperado | Detectado | Artículo respaldado | Citados | A revisar |
|---|---|---|---|---|---|
| lc01_locacion_comercial | R1 Mora automática sin interpelación con interés punitorio del 1,5% mensual | sí | sí | 9, 10, 768, 771, 886 | 9 (sin rubro en referencia), 10 (sin rubro en referencia) |
| lc01_locacion_comercial | R2 Exoneración de responsabilidad del locador por caso fortuito / fuerza mayor | sí | sí | 1204, 1730, 1743 | 1204 (sin rubro en referencia), 1730 (sin rubro en referencia) |
| lv04_locacion_vivienda | R1 Interés punitorio del 0,5% diario (desproporcionado) | sí | sí | 771, 1728 | 1728 (sin rubro en referencia) |
| lv04_locacion_vivienda | R2 Preaviso de 60 días para que la locataria resuelva (más gravoso que el régimen legal) | sí | sí | 1221 | — |
| lv04_locacion_vivienda | R3 Depósito en garantía sin plazo de devolución ni actualización | sí | n/a | 1196, 1197 | 1196 (Locación habitacional), 1197 (sin rubro en referencia) |
| mt05_mantenimiento_incompleto | R1 Plazo y precio indeterminados (a acordar por adenda / por orden de trabajo) | sí | no | 1010, 1011, 1012, 1133 | 1010 (sin rubro en referencia), 1011 (sin rubro en referencia), 1012 (sin rubro en referencia), 1133 (sin rubro en referencia) |
| mt05_mantenimiento_incompleto | R2 Responsabilidad de la contratista sin tope y exigencia de seguro | sí | no | 1749 | 1749 (sin rubro en referencia) |
| sm03_suministro | R1 Limitación de la responsabilidad del proveedor al valor de la partida no entregada | sí | sí | 1743 | — |
| sm03_suministro | R2 Precio fijo en dólares por 18 meses sin ajuste (riesgo de desequilibrio / imprevisión) | sí | sí | 765, 1091 | 765 (sin rubro en referencia) |
| sm03_suministro | R3 Plazo muy breve (48 horas) para rechazar partidas | NO | no | — | — |
| sv02_servicios_profesionales | R1 Rescisión sin causa con preaviso de 15 días y sin indemnización | sí | sí | 10, 1077 | 10 (sin rubro en referencia) |
| sv02_servicios_profesionales | R2 No hay cláusula de jurisdicción ni ley aplicable | sí | n/a | 2650 | 2650 (sin rubro en referencia) |
| sv02_servicios_profesionales | R3 Independencia / riesgo de recalificación de la relación como dependiente | NO | no | — | — |
