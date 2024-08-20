from PySide6 import QtWidgets
from PySide6 import QtCore
from PySide6 import QtGui

class TabbedPlotWidget(QtWidgets.QTabWidget):
    """
    Central plot widget that holds tabs and subtabs for all existing plots
    """
    def __init__(self, parent=None):
        super(TabbedPlotWidget, self).__init__()

        self.manager = parent

        self._set_icon()
        self.setWindowTitle('TabbedPlotWidget')

        self.setMinimumSize(500, 500)
        self.hide()

    def _set_icon(self):
        icon = QtGui.QIcon()
        icon.addFile(u":/res/ball.ico", QtCore.QSize(), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.setWindowIcon(icon)

    def show_or_activate(self):
        """
        Shows the widget itself, if it is hidden. Activates is, if already shown.
        """
        if self.isVisible():
            self.activateWindow()
        else:
            self.show()
            self.activateWindow()
