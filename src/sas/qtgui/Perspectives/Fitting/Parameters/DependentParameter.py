from .FittingParameter import ValueType, FittingParameter


class DependentParameter(FittingParameter):
    is_dependent = True
    is_visible = False

    def __init__(self):
        super().__init__()
        # The conditions that must be met for this parameter and whether those conditions have been met
        #
        self._conditions: dict[str, bool] = {}

    def check_condition(self, condition: str, value: ValueType):
        """Check """
        pass

    def are_all_conditions_met(self) -> bool:
        """Are all conditions met?"""
        return all(self._conditions.values())
