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
