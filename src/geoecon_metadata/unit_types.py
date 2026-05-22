from typing import Any
import pandas as pd
from .enums import MeasurementUnit


MEASUREMENTUNIT_TYPE_MAP = {
    MeasurementUnit.HOGARES: pd.Int64Dtype(),
    MeasurementUnit.VIVIENDAS: pd.Int64Dtype(),
    MeasurementUnit.PERSONAS: pd.Int64Dtype(),
    MeasurementUnit.VOTOS: pd.Int64Dtype(),
    MeasurementUnit.ESTABLECIMIENTOS: pd.Int64Dtype(),
    MeasurementUnit.INSTALACION_INFRAESTRUCTURA: pd.Int64Dtype(),
    MeasurementUnit.SEDES: pd.Int64Dtype(),
    MeasurementUnit.MONEDA: pd.Float64Dtype(),
    MeasurementUnit.AREA: pd.Float64Dtype(),
    MeasurementUnit.VOLUMEN: pd.Float64Dtype(),
    MeasurementUnit.DISTANCIA: pd.Float64Dtype(),
    MeasurementUnit.IDENTIFICACION: str,
    MeasurementUnit.TEMPERATURA: pd.Float64Dtype(),
    MeasurementUnit.DENSIDAD: pd.Float64Dtype(),
    MeasurementUnit.TASA: pd.Float64Dtype(),
    MeasurementUnit.VARIACION: pd.Float64Dtype(),
    MeasurementUnit.TIEMPO: str,
    MeasurementUnit.PESO: pd.Float64Dtype(),
    MeasurementUnit.ENERGIA: pd.Float64Dtype(),
    MeasurementUnit.VELOCIDAD: pd.Float64Dtype(),
    MeasurementUnit.PRESION: pd.Float64Dtype(),
    MeasurementUnit.FRECUENCIA: pd.Float64Dtype(),
    MeasurementUnit.ANGULO: pd.Float64Dtype(),
    MeasurementUnit.CONCENTRACION: pd.Float64Dtype(),
    MeasurementUnit.INDICE: pd.Float64Dtype(),
    MeasurementUnit.UNIDADES_ECONOMICAS: pd.Int64Dtype(),
    MeasurementUnit.TODO: str,
}
