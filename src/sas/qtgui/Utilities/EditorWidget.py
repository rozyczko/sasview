# global
import logging

from PySide6 import QtWidgets
from pathlib import Path

import sas.qtgui.Utilities.GuiUtils as GuiUtils
from sas.qtgui.Utilities.UI.FileEditor import Ui_FileEditor
from sas.qtgui.Utilities.PluginDefinition import PluginDefinition
from sas.qtgui.Utilities.ModelEditor import ModelEditor


class EditorWidget(QtWidgets.QDialog, Ui_FileEditor):
    """
    Model editor "container" class describing interaction between
    plugin definition widget and model editor widget.
    Once the model is defined, it can be saved as a plugin.
    """

    # Signals for intertab communication plugin -> editor
    def __init__(self, parent=None, load_file=None):
        super(EditorWidget, self).__init__(parent)
        self.parent = parent
        self.communicate = GuiUtils.Communicate()
        self.setupUi(self)

        # globals
        self.filename = ""
        self.window_title = self.windowTitle()
        self.load_file = load_file.lstrip("//") if load_file else None
        self.is_modified = False
        self.label = None
        self.help = None

        self.addWidgets()
        self.addSignals()

        if self.load_file is not None:
            self.onLoad()

    def addWidgets(self):
        """
        Populate tabs with widgets
        """
        # Add tabs
        # Plugin definition widget
        self.plugin_widget = PluginDefinition(self)
        self.tabWidget.addTab(self.plugin_widget, "Plugin Definition")
        self.setPluginActive(True)

        self.editor_widget = ModelEditor(self)
        # Initially, nothing in the editor
        self.editor_widget.setEnabled(False)
        self.tabWidget.addTab(self.editor_widget, "Model editor")
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).setEnabled(False)

        self.cmdLoad.setText("Load file...")

    def addSignals(self):
        """
        Define slots for common widget signals
        """
        # buttons
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).clicked.connect(self.onApply)
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).clicked.connect(self.onCancel)
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Help).clicked.connect(self.onHelp)
        self.cmdLoad.clicked.connect(self.onLoad)
        # signals from tabs
        self.plugin_widget.modelModified.connect(self.editorModified)
        self.editor_widget.modelModified.connect(self.editorModified)
        self.plugin_widget.txtName.editingFinished.connect(self.pluginTitleSet)

    def setPluginActive(self, is_active=True):
        """
        Enablement control for all the controls on the simple plugin editor
        """
        self.plugin_widget.setEnabled(is_active)

    def saveClose(self):
        """
        Check if file needs saving before closing or model reloading
        """
        saveCancelled = False
        ret = self.onModifiedExit()
        if ret == QtWidgets.QMessageBox.Cancel:
            saveCancelled = True
        elif ret == QtWidgets.QMessageBox.Save:
            self.updateFromEditor()
        return saveCancelled

    def closeEvent(self, event):
        """
        Overwrite the close even to assure intent
        """
        if self.is_modified:
            saveCancelled = self.saveClose()
            if saveCancelled:
                return
        event.accept()

    def onModifiedExit(self):
        msg_box = QtWidgets.QMessageBox(self)
        msg_box.setWindowTitle("SasView Model Editor")
        msg_box.setText("The document has been modified.")
        msg_box.setInformativeText("Do you want to save your changes?")
        msg_box.setStandardButtons(
            QtWidgets.QMessageBox.Save | QtWidgets.QMessageBox.Discard | QtWidgets.QMessageBox.Cancel)
        msg_box.setDefaultButton(QtWidgets.QMessageBox.Save)
        return msg_box.exec()

    def onCancel(self):
        """
        Accept if document not modified, confirm intent otherwise.
        """
        if self.is_modified:
            saveCancelled = self.saveClose()
            if saveCancelled:
                return
        self.reject()

    def onApply(self):
        """
        Write the plugin and update the model editor if plugin editor open
        Write/overwrite the plugin if model editor open
        """
        if isinstance(self.tabWidget.currentWidget(), PluginDefinition):
            self.updateFromPlugin()
        else:
            self.updateFromEditor()
        self.is_modified = False

    def editorModified(self):
        """
        User modified the model in the Model Editor.
        Disable the plugin editor and show that the model is changed.
        """
        self.setTabEdited(True)
        self.plugin_widget.txtFunction.setStyleSheet("")
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).setEnabled(True)
        self.is_modified = True

    def setTabEdited(self, is_edited):
        """
        Change the widget name to indicate unsaved state
        Unsaved state: add "*" to filename display
        saved state: remove "*" from filename display
        """
        current_text = self.windowTitle()

        if is_edited:
            if current_text[-1] != "*":
                current_text += "*"
        else:
            if current_text[-1] == "*":
                current_text = current_text[:-1]
        self.setWindowTitle(current_text)

    def updateFromEditor(self):
        """
        Save the current state of the Model Editor
        """
        self.validateChanges()
        # Save the file
        self.writeFile(self.filename, self.load_file)
        # Update the tab title
        self.setTabEdited(False)

        # Notify listeners, since the plugin name might have changed
        self.parent.communicate.customModelDirectoryChanged.emit()

        # notify the user
        msg = str(self.filename) + " successfully saved."
        self.parent.communicate.statusBarUpdateSignal.emit(msg)
        logging.info(msg)

    def validateChanges(self):
        """Open the help file for this window."""
        NotImplementedError(f"Please add a validateChanges method for {self.__class__.__name__}.")

    def onHelp(self):
        """Open the help file for this window."""
        NotImplementedError(f"Please add a help file for the {self.__class__.__name__} editor.")

    def onLoad(self):
        """Loads a file. at_launch is value of whether to attempt a load of a file from launch of the widget or not"""
        NotImplementedError(f"Please add an onLoad method for {self.__class__.__name__}.")

    def loadFile(self, filename: str | Path):
        """Performs the load operation and updates the view"""
        NotImplementedError(f"Please add a loadFile method for {self.__class__.__name__}.")

    @classmethod
    def readFile(cls, f_name: Path):
        """
        Write model content to file "fname"
        """
        with open(f_name, 'r', encoding="utf-8") as out_f:
            f = out_f.read()
        return f

    @classmethod
    def writeFile(cls, f_name: Path, f_str: str = ""):
        """
        Write model content to file "fname"
        """
        with open(f_name, 'w', encoding="utf-8") as out_f:
            out_f.write(f_str)
