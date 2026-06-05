from enum import Enum


class Environments(str, Enum):
    PROD = "prod"
    DEV = "dev"
    LOCAL = "local"
    TEST = "test"


class ColumnStatus(str, Enum):
    DRAFT = "draft"  # Not ready to check
    READY = "ready"  # Ready to check
    ERROR = "error"  # Have some errors on check, requires revision
    VALID = "valid"  # Is valid and is ready to deploy
    DEPLOYED  = "deployed" # Is in the data warehouse
    FAILED = "failed" # Can't upload to data warehouse, requires revision
    DONE = "done"  # Just deployed


class SourceStatus(str, Enum):
    DRAFT = "draft"  # Not ready to check
    READY = "ready"  # Ready to check
    ERROR = "error"  # Have some errors on check, requires revision
    VALID = "valid"  # Is valid and is ready to deploy
    DEPLOYED  = "deployed" # Is in the data warehouse
    FAILED = "failed" # Can't upload to data warehouse, requires revision 
    DONE = "done"  # Deployed and checked


class SourceType(str, Enum):
    TODO = "TODO"  # To be defined
    QUERY = "query"  # Source as query
    SHAPE = "shape"  # Shape file as input


class SourcePlatform(str, Enum):
    BIGQUERY = "bigquery"
    POSTGRESQL = "postgresql"
    GOOGLEDRIVE = "googledrive"


class ReliabilityType(str, Enum):
    TODO = "TODO"  # To be defined
    TRUST = "trust"  # Datos confiables, probablemente verificados o de alta calidad
    RAW = "raw"  # Datos en su forma original, sin procesar
    COMPUTED = "computed"  # Datos derivados de cálculos o procesos
    SYNTHETIC = "synthetic"  # Datos generados artificialmente
    VERIFIED = "verified"  # Datos que han sido verificados
    ESTIMATED = "estimated"  # Datos que han sido estimados
    AGGREGATED = "aggregated"  # Datos agrupados o resumidos
    IMPUTED = "imputed"  # Datos inferidos o rellenados
    SIMULATED = "simulated"  # Datos generados por simulación
    UNTRUST = "untrust"  # Datos que no logran ser validados desde su fuente


class MeasurementUnit(str, Enum):
    TODO = "TODO"  # To be defined
    HOGARES = "hogares"  # Número de hogares, entendido como el espacio de una familia (orgánico)
    VIVIENDAS = "viviendas"  # Número de viviendas, entendido como la estructura física (inorgánico)
    PERSONAS = "personas"  # Número de personas
    VOTOS = "votos"  # Número de votos
    ESTABLECIMIENTOS = "establecimientos"  # Número de establecimientos
    INSTALACION_INFRAESTRUCTURA = "instalación de infraestructura"  # Instalaciones que proporcionan servicios de conectividad e intercambio de bienes
    SEDES = "sedes"  # Número de sedes (oficinas, locales, etc.)
    MONEDA = "moneda"  # Cantidad de dinero
    AREA = "área"  # Medida de superficie (metros cuadrados, hectáreas, etc.)
    VOLUMEN = "volumen"  # Medida de volumen (litros, metros cúbicos, etc.)
    DISTANCIA = "distancia"  # Medida de distancia (metros, kilómetros, etc.)
    IDENTIFICACION = "identificación"  # Identificadores únicos (códigos, números de identificación, etc.)
    TEMPERATURA = (
        "temperatura"  # Medida de temperatura (grados Celsius, Fahrenheit, etc.)
    )
    DENSIDAD = "densidad"  # Medida de densidad (personas por kilómetro cuadrado, etc.)
    TASA = "tasa"  # Medida de tasa (porcentaje, tasa de interés, etc.)
    VARIACION = (
        "variación"  # Medida de variación (cambio porcentual, diferencias, etc.)
    )
    TIEMPO = "tiempo"  # Medida de tiempo (segundos, minutos, horas, etc.)
    PESO = "peso"  # Medida de peso (gramos, kilogramos, toneladas, etc.)
    ENERGIA = "energía"  # Medida de energía (joules, kilovatios-hora, etc.)
    VELOCIDAD = "velocidad"  # Medida de velocidad (metros por segundo, kilómetros por hora, etc.)
    PRESION = "presión"  # Medida de presión (pascales, bares, etc.)
    FRECUENCIA = "frecuencia"  # Medida de frecuencia (hercios)
    ANGULO = "ángulo"  # Medida de ángulo (grados, radianes)
    CONCENTRACION = "concentración"  # Medida de concentración (moles por litro, partes por millón, etc.)
    INDICE = "índice"  # Medida que determinar un orden o distancia entre entidades.
    UNIDADES_ECONOMICAS = "unidades económicas"  # Unidades económicas pueden ser establecimientos, locales, otros.


class Encodings(Enum):
    ASCII = "ascii"
    BASE64_CODEC = "base64_codec"
    BIG5 = "big5"
    BIG5HKSCS = "big5hkscs"
    BZ2_CODEC = "bz2_codec"
    CHARMAP = "charmap"
    CP037 = "cp037"
    CP1006 = "cp1006"
    CP1026 = "cp1026"
    CP1125 = "cp1125"
    CP1140 = "cp1140"
    CP1250 = "cp1250"
    CP1251 = "cp1251"
    CP1252 = "cp1252"
    CP1253 = "cp1253"
    CP1254 = "cp1254"
    CP1255 = "cp1255"
    CP1256 = "cp1256"
    CP1257 = "cp1257"
    CP1258 = "cp1258"
    CP273 = "cp273"
    CP424 = "cp424"
    CP437 = "cp437"
    CP500 = "cp500"
    CP720 = "cp720"
    CP737 = "cp737"
    CP775 = "cp775"
    CP850 = "cp850"
    CP852 = "cp852"
    CP855 = "cp855"
    CP856 = "cp856"
    CP857 = "cp857"
    CP858 = "cp858"
    CP860 = "cp860"
    CP861 = "cp861"
    CP862 = "cp862"
    CP863 = "cp863"
    CP864 = "cp864"
    CP865 = "cp865"
    CP866 = "cp866"
    CP869 = "cp869"
    CP874 = "cp874"
    CP875 = "cp875"
    CP932 = "cp932"
    CP949 = "cp949"
    CP950 = "cp950"
    EUC_JISX0213 = "euc_jisx0213"
    EUC_JIS_2004 = "euc_jis_2004"
    EUC_JP = "euc_jp"
    EUC_KR = "euc_kr"
    GB18030 = "gb18030"
    GB2312 = "gb2312"
    GBK = "gbk"
    HEX_CODEC = "hex_codec"
    HP_ROMAN8 = "hp_roman8"
    HZ = "hz"
    IDNA = "idna"
    ISO2022_JP = "iso2022_jp"
    ISO2022_JP_1 = "iso2022_jp_1"
    ISO2022_JP_2 = "iso2022_jp_2"
    ISO2022_JP_2004 = "iso2022_jp_2004"
    ISO2022_JP_3 = "iso2022_jp_3"
    ISO2022_JP_EXT = "iso2022_jp_ext"
    ISO2022_KR = "iso2022_kr"
    ISO8859_1 = "iso8859_1"
    ISO8859_10 = "iso8859_10"
    ISO8859_11 = "iso8859_11"
    ISO8859_13 = "iso8859_13"
    ISO8859_14 = "iso8859_14"
    ISO8859_15 = "iso8859_15"
    ISO8859_16 = "iso8859_16"
    ISO8859_2 = "iso8859_2"
    ISO8859_3 = "iso8859_3"
    ISO8859_4 = "iso8859_4"
    ISO8859_5 = "iso8859_5"
    ISO8859_6 = "iso8859_6"
    ISO8859_7 = "iso8859_7"
    ISO8859_8 = "iso8859_8"
    ISO8859_9 = "iso8859_9"
    JOHAB = "johab"
    KOI8_R = "koi8_r"
    KOI8_T = "koi8_t"
    KOI8_U = "koi8_u"
    KZ1048 = "kz1048"
    LATIN_1 = "latin_1"
    MAC_ARABIC = "mac_arabic"
    MAC_CROATIAN = "mac_croatian"
    MAC_CYRILLIC = "mac_cyrillic"
    MAC_FARSI = "mac_farsi"
    MAC_GREEK = "mac_greek"
    MAC_ICELAND = "mac_iceland"
    MAC_LATIN2 = "mac_latin2"
    MAC_ROMAN = "mac_roman"
    MAC_ROMANIAN = "mac_romanian"
    MAC_TURKISH = "mac_turkish"
    MBCS = "mbcs"
    OEM = "oem"
    PALMOS = "palmos"
    PTCP154 = "ptcp154"
    PUNYCODE = "punycode"
    QUOPRI_CODEC = "quopri_codec"
    RAW_UNICODE_ESCAPE = "raw_unicode_escape"
    ROT_13 = "rot_13"
    SHIFT_JIS = "shift_jis"
    SHIFT_JISX0213 = "shift_jisx0213"
    SHIFT_JIS_2004 = "shift_jis_2004"
    TIS_620 = "tis_620"
    UNDEFINED = "undefined"
    UNICODE_ESCAPE = "unicode_escape"
    UTF_16 = "utf_16"
    UTF_16_BE = "utf_16_be"
    UTF_16_LE = "utf_16_le"
    UTF_32 = "utf_32"
    UTF_32_BE = "utf_32_be"
    UTF_32_LE = "utf_32_le"
    UTF_7 = "utf_7"
    UTF_8 = "utf_8"
    UTF_8_SIG = "utf_8_sig"
    UU_CODEC = "uu_codec"
    ZLIB_CODEC = "zlib_codec"


class ObservableClassEnum(str, Enum):
    UNIDADES_TERRITORIALES_ADMINISTRATIVAS = "Unidades Territoriales y Administrativas"
    UNIDADES_ECONOMICAS = "Unidades Económicas"
    UNIDADES_EDUCATIVAS = "Unidades Educativas"
    UNIDADES = "Unidades Inespecíficas"
    ZONAS_INDUSTRIALES = "Zonas Industriales"
    INFRAESTRUCTURAS_EQUIPAMIENTOS = "Infraestructuras y Equipamientos"
    SERVICIOS_PUBLICOS = "Servicios Públicos y Establecimientos"
    INSTALACIONES_DE_SALUD = "Instalaciones de salud"
    SERVICIOS_DE_SEGURIDAD_Y_EMERGENCIA = "Servicios de seguridad y emergencia"
    SEDES_DE_ADMINISTRACIONES_PUBLICAS = "Sedes de administraciones públicas"
    INSTALACIONES_COMERCIALES_RECREATIVAS = "Instalaciones Comerciales y Recreativas"
    INSTALACIONES_PUBLICAS_DE_SERVICIOS_COMUNITARIOS = (
        "Instalaciones públicas de servicios comunitarios"
    )
    SITIOS_CULTURALES_PATRIMONIALES = "Sitios Culturales y Patrimoniales"
    CENTROS_DE_TRANSPORTE = "Centros de Transporte"
    PARQUES_Y_AREAS_NATURALES = "Parques y Áreas Naturales"


class ObservableWithoutObservationActions(str, Enum):
    ERROR = "error"
    USE_DEFAULTS = "use_defaults"


class ObservableScaleEnum(str, Enum):
    PAIS = "país"
    DEPARTAMENTO = "departamento"
    PARTIDO = "partido"
    DISTRITO = "distrito"
    PROVINCIA = "provincia"
    MUNICIPIO = "municipio"
    ISLA = "isla"
    CANTON = "cantón"
    AREA_NO_MUNICIPALIZADA = "área no municipalizada"
    POINT = "point"
    CORREGIMIENTO = "corregimiento"
    UNIDAD_FEDERATIVA = "unidad federativa"


class ObservableScaleTypeEnum(str, Enum):
    ABSTRACT = "abstract"
    UTA = "UTA"  # Unidad Territorial Administrativa
    NUTS = "UTS"  # Unidad Territorial Estadística
    LOCATION = "location"
    CLUSTER = "cluster"
    FUNCTIONALREGION = "functional region"


SCALE_TO_CLASS_TYPE = {
    ObservableScaleEnum.PAIS: ObservableScaleTypeEnum.UTA,
    ObservableScaleEnum.DEPARTAMENTO: ObservableScaleTypeEnum.UTA,
    ObservableScaleEnum.PARTIDO: ObservableScaleTypeEnum.UTA,
    ObservableScaleEnum.DISTRITO: ObservableScaleTypeEnum.UTA,
    ObservableScaleEnum.PROVINCIA: ObservableScaleTypeEnum.UTA,
    ObservableScaleEnum.MUNICIPIO: ObservableScaleTypeEnum.UTA,
    ObservableScaleEnum.ISLA: ObservableScaleTypeEnum.UTA,
    ObservableScaleEnum.CANTON: ObservableScaleTypeEnum.UTA,
    ObservableScaleEnum.AREA_NO_MUNICIPALIZADA: ObservableScaleTypeEnum.UTA,
    ObservableScaleEnum.POINT: ObservableScaleTypeEnum.UTA,
    ObservableScaleEnum.CORREGIMIENTO: ObservableScaleTypeEnum.UTA,
    ObservableScaleEnum.UNIDAD_FEDERATIVA: ObservableScaleTypeEnum.UTA,
}

SCALE_TO_DETAILS = {
    ObservableScaleEnum.PAIS: {
        "administrative_level": 0,
        "description": "Entidad política soberana reconocida internacionalmente.",
        "type": ObservableClassEnum.UNIDADES_TERRITORIALES_ADMINISTRATIVAS.value,
    },
    ObservableScaleEnum.DEPARTAMENTO: {
        "administrative_level": 2,
        "description": "División administrativa dentro de un país, generalmente de nivel superior.",
        "type": ObservableClassEnum.UNIDADES_TERRITORIALES_ADMINISTRATIVAS.value,
    },
    ObservableScaleEnum.PARTIDO: {
        "administrative_level": 2,
        "description": "División administrativa dentro de un país, generalmente de nivel superior.",
        "type": ObservableClassEnum.UNIDADES_TERRITORIALES_ADMINISTRATIVAS.value,
    },
    ObservableScaleEnum.DISTRITO: {
        "administrative_level": 2,
        "description": "Subdivisión territorial dentro de un departamento o provincia.",
        "type": ObservableClassEnum.UNIDADES_TERRITORIALES_ADMINISTRATIVAS.value,
    },
    ObservableScaleEnum.PROVINCIA: {
        "administrative_level": 1,
        "description": "Unidad administrativa que agrupa varios distritos o municipios.",
        "type": ObservableClassEnum.UNIDADES_TERRITORIALES_ADMINISTRATIVAS.value,
    },
    ObservableScaleEnum.MUNICIPIO: {
        "administrative_level": 2,
        "description": "Entidad local con autonomía administrativa, que puede incluir varias localidades.",
        "type": ObservableClassEnum.UNIDADES_TERRITORIALES_ADMINISTRATIVAS.value,
    },
    ObservableScaleEnum.ISLA: {
        "administrative_level": None,
        "description": "Porción de tierra rodeada de agua, habitada o no.",
        "type": ObservableClassEnum.UNIDADES_TERRITORIALES_ADMINISTRATIVAS.value,
    },
    ObservableScaleEnum.CANTON: {
        "administrative_level": 2,
        "description": "División administrativa en ciertos países, generalmente intermedia.",
        "type": ObservableClassEnum.UNIDADES_TERRITORIALES_ADMINISTRATIVAS.value,
    },
    ObservableScaleEnum.AREA_NO_MUNICIPALIZADA: {
        "administrative_level": 2,
        "description": "Territorio sin organización municipal autónoma.",
        "type": ObservableClassEnum.UNIDADES_TERRITORIALES_ADMINISTRATIVAS.value,
    },
    ObservableScaleEnum.POINT: {
        "administrative_level": None,
        "description": "Punto geográfico específico sin división administrativa.",
        "type": ObservableClassEnum.UNIDADES.value,
    },
    ObservableScaleEnum.CORREGIMIENTO: {
        "administrative_level": 3,
        "description": "Unidad territorial menor dentro de ciertos países, similar a un distrito.",
        "type": ObservableClassEnum.UNIDADES_TERRITORIALES_ADMINISTRATIVAS.value,
    },
    ObservableScaleEnum.UNIDAD_FEDERATIVA: {
        "administrative_level": 0,
        "description": "Entidad administrativa que forma parte de una federación, con cierto grado de autonomía.",
        "type": ObservableClassEnum.UNIDADES_TERRITORIALES_ADMINISTRATIVAS.value,
    },
}


class GroupScaleEnum(str, Enum):
    CONCRETE_SCALE = "concrete_scale"
    ABSTRACT_SCALE = "abstract_scale"


class ExitCode(int, Enum):
    info = 0
    ok = 0
    warning = 1
    error = 2


class ShapeOperationEnum(str, Enum):
    DISSOLVE = "dissolve"
