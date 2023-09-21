from .FittingParameter import ValueType, FittingParameter


class ConditionalParameter(FittingParameter):
    is_conditional = True
    is_fittable = False
    
    def __init__(self):
        super().__init__()
        self.dependent_params: list[str] = []

    @property
    def value(self) -> ValueType:
        return super().value()

    @value.setter
    def value(self, value: ValueType, uncertainty: ValueType = None):
        """An overridden value setter that will """
        super().value(value, uncertainty)
        for param in self.dependent_params:

            # TODO: How should this be handled? Likely by emitting an action
            print(param)
            pass
