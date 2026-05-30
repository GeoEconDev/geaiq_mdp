from ruamel.yaml import YAML
from ruamel.yaml.composer import Composer


class PersistentAnchorComposer(Composer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pila para almacenar diccionarios de anchors
        self.anchor_stack = []

    def compose_document(self):
        self.recover_anchors()
        node = super().compose_document()
        return node

    # Sobrescribimos el método que almacena anchors
    def compose_node(self, parent, index):
        node = super().compose_node(parent, index)
        if node.anchor:
            # Si la pila está vacía, iniciamos un nuevo diccionario
            if not self.anchor_stack:
                self.anchor_stack.append({})
            # Guardamos el anchor en el diccionario más reciente (último en la pila)
            self.anchor_stack[-1][node.anchor] = node
        return node

    # Recuperar todos los anchors disponibles recorriendo la pila
    def recover_anchors(self):
        self.anchors = {}
        for anchor_dict in self.anchor_stack:
            self.anchors.update(anchor_dict)  # Fusionar los diccionarios de anchors

    # Método para hacer rollback (pop) de los anchors más recientes
    def pop_anchors(self):
        if self.anchor_stack:
            self.anchors = self.anchor_stack.pop()

    # Método para hacer push de un nuevo diccionario de anchors en la pila
    def push_anchors(self):
        self.anchor_stack.append({})


class PersistentAnchorYAML(YAML):
    def __init__(self, *args, **kwargs):
        anchors = kwargs.pop("anchors", None)
        anchor_stack = kwargs.pop("anchor_stack", None)
        super().__init__(*args, **kwargs)
        self.Composer = PersistentAnchorComposer
        if anchors:
            self.composer.anchors = anchors
        if anchor_stack:
            self.composer.anchor_stack = anchor_stack

    def push_anchors(self):
        self.composer.push_anchors()

    def pop_anchors(self):
        self.composer.pop_anchors()
