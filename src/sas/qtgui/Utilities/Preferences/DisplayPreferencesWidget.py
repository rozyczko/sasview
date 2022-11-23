from sas.system import config

from .PreferencesWidget import PreferencesWidget


class DisplayPreferencesWidget(PreferencesWidget):
    def __init__(self):
        super(DisplayPreferencesWidget, self).__init__("Display Settings")
        self.config_params = ['QT_SCALE_FACTOR', 'QT_AUTO_SCREEN_SCALE_FACTOR']

    def _addAllWidgets(self):
        self.qtScaleFactor = self.addFloatInput(
            title="QT Screen Scale Factor",
            default_number=config.QT_SCALE_FACTOR)
        self.qtScaleFactor.textChanged.connect(
            lambda: self._stageChange('QT_SCALE_FACTOR', float(self.qtScaleFactor.text())))
        self.autoScaling = self.addCheckBox(
            title="Automatic Screen Scale Factor",
            checked=config.QT_AUTO_SCREEN_SCALE_FACTOR)
        self.autoScaling.clicked.connect(
            lambda: self._stageChange('QT_AUTO_SCREEN_SCALE_FACTOR', self.autoScaling.isChecked()))

    def _toggleBlockAllSignaling(self, toggle):
        self.qtScaleFactor.blockSignals(toggle)
        self.autoScaling.blockSignals(toggle)

    def _restoreFromConfig(self):
        self.qtScaleFactor.setText(str(config.QT_SCALE_FACTOR))
        self.autoScaling.setChecked(config.QT_AUTO_SCREEN_SCALE_FACTOR)
