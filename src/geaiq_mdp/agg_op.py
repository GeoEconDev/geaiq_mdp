import numpy as np
import pandas as pd

from .enums import MeasurementUnit

MEASUREMENTUNIT_AGG_MAP = {
    MeasurementUnit.HOGARES: "sum",
    MeasurementUnit.VIVIENDAS: "sum",
    MeasurementUnit.PERSONAS: "sum",
    MeasurementUnit.VOTOS: "sum",
    MeasurementUnit.ESTABLECIMIENTOS: "sum",
    MeasurementUnit.INSTALACION_INFRAESTRUCTURA: "count",  # Podría ser 'sum' dependiendo del contexto
    MeasurementUnit.SEDES: "sum",
    MeasurementUnit.MONEDA: "sum",
    MeasurementUnit.AREA: "sum",
    MeasurementUnit.VOLUMEN: "sum",
    MeasurementUnit.DISTANCIA: "sum",
    MeasurementUnit.IDENTIFICACION: None,  # Contar únicos para identificadores
    MeasurementUnit.TEMPERATURA: "mean",  # Promedio tiene más sentido para temperaturas
    MeasurementUnit.DENSIDAD: "mean",  # Puede ser promedio o ponderado
    MeasurementUnit.TASA: "mean",  # Usualmente se promedian
    MeasurementUnit.VARIACION: "mean",  # Puede ser promedio o calculada específicamente
    MeasurementUnit.TIEMPO: "sum",  # Sumar tiempos
    MeasurementUnit.PESO: "sum",
    MeasurementUnit.ENERGIA: "sum",
    MeasurementUnit.VELOCIDAD: "mean",  # Promedio es común para velocidades
    MeasurementUnit.PRESION: "mean",  # Promedio tiene sentido para presiones
    MeasurementUnit.FRECUENCIA: "mean",
    MeasurementUnit.ANGULO: "mean",  # Promedio de ángulos, pero podría necesitar manejo especial en algunos casos
    MeasurementUnit.CONCENTRACION: "mean",  # Promedio de concentraciones
    MeasurementUnit.INDICE: None,  # Promedio o cálculo específico dependiendo del índice
    MeasurementUnit.UNIDADES_ECONOMICAS: "sum",
    MeasurementUnit.TODO: "TODO"  # Pendiente de definir
}


def agg_empty_value(unit):
    """Valor neutro de agregar `unit` sobre un conjunto VACIO.

    Se usa para rellenar los observables HOJA que no tienen dato.

    Antes esto se resolvia con ``eval(f"{op}([])")``, y eso solo funcionaba con
    ``"sum"``, que es builtin. ``"mean"``, ``"count"`` y ``"TODO"`` no existen
    como nombres en el modulo y reventaban con
    ``NameError: name 'mean' is not defined``; ``None`` daba ``None([])``.
    En la practica eso hacia fallar el check/deploy de CUALQUIER source con una
    columna ``unit: tasa`` (y tambien densidad, temperatura, variacion,
    velocidad, indice...) que llegara a la auto-agregacion entre escalas.

    Pandas resuelve los tres casos con la misma semantica que se buscaba:
    ``sum -> 0.0`` (identico al ``sum([])`` de antes), ``mean -> NaN``
    (el promedio de un conjunto vacio no esta definido) y ``count -> 0``.
    """
    op = MEASUREMENTUNIT_AGG_MAP.get(unit)
    if not op or op == "TODO":
        return np.nan
    try:
        return pd.Series([], dtype="float64").agg(op)
    except (AttributeError, TypeError, ValueError):
        return np.nan
