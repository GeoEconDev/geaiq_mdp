from .utils import ColumnRef, IncludeOptions
from .dimension import Dimension
from .menu import MenuOption
from .wh import ObservableGroup, ObservableScale, Period, Class_, Attribute, ObservableClass
from .ui import IndicatorInstanceGenerators, Indicator
from .source import Column, Processing, Source, Shape, SourceDefinition

yaml_classes = [
    ObservableGroup,
    ObservableScale,
    Period,
    Class_,
    Attribute,
    Column,
    Shape,
    Source,
    MenuOption,
    Dimension,
    Column,
    ColumnRef,
    IncludeOptions,
    Processing,
    IndicatorInstanceGenerators,
    Indicator,
    ObservableClass
]

def register(registrable):
    for cls_ in yaml_classes:
        registrable.register_class(cls_)
    return registrable

__all__ = [
    "ColumnRef",
    "IncludeOptions",
    "Dimension",
    "MenuOption",
    "ObservableGroup",
    "ObservableScale",
    "Period",
    "Column",
    "Source",
    "SourceDefinition",
    "Class_",
    "Attribute",
    "register"
]
