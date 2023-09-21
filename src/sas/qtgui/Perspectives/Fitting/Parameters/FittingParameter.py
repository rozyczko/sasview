from typing import Union, Optional

ValueType = Optional[Union[str, float, int]]


class FittingParameter:
    """The base class that all fitting parameters must be based on.

    Assumptions:
        - A parameter is something that will be used in the model.
        - A parameter visibility might depend on
    """

    # Does this parameter define the functionality of other parameters?
    is_conditional = False
    # Is this parameter defined by the functionality of other parameters?
    is_dependent = False
    # Should this parameter be visible to the gui?
    is_visible = True
    # Is this parameter fittable
    is_fittable = True

    def __init__(self):
        # TODO: what params should be passed?
        # Values associated with the parameter
        self.name: str = None
        # _base_name would be for dependent parameters for layered models, e.g.
        self._base_name: str = self.name
        self._value_trace: list[ValueType] = []
        self._value: ValueType = None
        self._uncertainty_trace: list[ValueType] = []
        self._uncertainty: ValueType = None
        self.d_type: type = float
        self.upper_limit: ValueType = None
        self.lower_limit: ValueType = None
        self.units = None

        # Value associated with fitting
        self.include_in_fit = False

        # Conditional parameters (formerly multiplicity)
        self.requirements = []

    @property
    def trace(self) -> list:
        """Expose the value history, but do not allow external modifications."""
        return self._value_trace

    @property
    def value(self) -> (ValueType, ValueType):
        return self._value, self._uncertainty

    @value.setter
    def value(self, value: ValueType, uncertainty: ValueType = None):
        """Set a new value of the parameter. Optionally, the uncertainty of the value can be passed.
        The value and uncertainty will be set and the history will be updated.

        :param value [ValueType]: The latest value of the parameter.
        :param uncertainty [ValueType]: The uncertainty associated with the value."""
        self._value = value
        self._value_trace.append(value)
        # Keep all uncertainties (even None) mapped to specific values
        self._uncertainty = uncertainty
        self._uncertainty_trace.append(uncertainty)
