# global
import sys
import os
import logging

from PySide6 import QtWidgets, QtGui
from pathlib import Path

from sas.sascalc.fit import models
from sas.sascalc.fit.models import find_plugins_dir

import sas.qtgui.Utilities.GuiUtils as GuiUtils
from sas.qtgui.Utilities.DocViewer.UI.DocEditor import Ui_DocEditor
from sas.qtgui.Utilities.PluginDefinition import PluginDefinition
from sas.qtgui.Utilities.ModelEditor import ModelEditor


class DocEditor(QtWidgets.QDialog, Ui_DocEditor):
    """
    Model editor "container" class describing interaction between
    plugin definition widget and model editor widget.
    Once the model is defined, it can be saved as a plugin.
    """
    # Signals for intertab communication plugin -> editor
    def __init__(self, parent=None, edit_only=False, load_file=None):
        super(DocEditor, self).__init__()

        self.parent = parent

        self.setupUi(self)

        # globals
        self.filename = ""
        self.is_python = True
        self.is_documentation = False
        self.window_title = self.windowTitle()
        self.edit_only = edit_only
        self.load_file = load_file.lstrip("//") if load_file else None
        self.is_modified = False
        self.label = None
        self.help = None
        self.file_to_regenerate = ""

        self.addWidgets()

        self.addSignals()

        if self.load_file is not None:
            self.onLoad(at_launch=True)

    def addWidgets(self):
        """
        Populate tabs with widgets
        """
        # Set up widget enablement/visibility
        self.cmdLoad.setVisible(self.edit_only)
        # Initially, nothing in the editor

        self.editor_widget = ModelEditor(self)
        self.editor_widget.setEnabled(False)
        self.tabWidget.addTab(self.editor_widget, "Documentation editor")
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).setEnabled(False)

        if self.edit_only:
            self.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).setText("Save")
            # and hide the tab/widget itself
            self.tabWidget.removeTab(0)
        
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
        self.editor_widget.modelModified.connect(self.editorDocModified)

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

    def onLoad(self, at_launch=False):
        """
        Loads a model plugin file. at_launch is value of whether to attempt a load of a file from launch of the widget or not
        """
        self.is_python = True # By default assume the file you load is python

        if self.is_modified:
            saveCancelled = self.saveClose()
            if saveCancelled:
                return
            self.is_modified = False

        # If we are loading in a file at the launch of the editor instead of letting the user pick, we need to process the HTML location from
        # the documentation viewer into the filepath for its corresponding RST
        if at_launch:
            from sas.sascalc.doc_regen.makedocumentation import MAIN_DOC_SRC
            user_models = find_plugins_dir()
            user_model_name = user_models + self.load_file + ".py"

            if os.path.isfile(user_models + self.load_file + ".py"):
                filename = user_model_name
            elif os.path.isfile(MAIN_DOC_SRC / "user" / "models" / "src" / (self.load_file + ".py")):
                filename = MAIN_DOC_SRC / "user" / "models" / "src" / (self.load_file + ".py")
            else:
                filename = MAIN_DOC_SRC / self.load_file.replace(".html", ".rst")
                self.is_python = False
                self.is_documentation = True
        else:
            plugin_location = models.find_plugins_dir()
            filename = QtWidgets.QFileDialog.getOpenFileName(
                                            self,
                                            'Open Plugin',
                                            plugin_location,
                                            'SasView Plugin Model (*.py)',
                                            None)[0]

        # Load the file
        if not filename:
            logging.info("No data file chosen.")
            return

        # remove c-plugin tab, if present.
        if self.tabWidget.count()>1:
            self.tabWidget.removeTab(1)
        self.file_to_regenerate = filename
        self.loadFile(str(filename))

    def loadFile(self, filename):
        """
        Performs the load operation and updates the view
        """
        self.editor_widget.blockSignals(True)
        plugin_text = ""
        with open(filename, 'r', encoding="utf-8") as plugin:
            plugin_text = plugin.read()
            self.editor_widget.txtEditor.setPlainText(plugin_text)
        self.editor_widget.setEnabled(True)
        self.editor_widget.blockSignals(False)
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).setEnabled(True)
        self.filename = Path(filename)
        display_name = self.filename.stem
        self.setWindowTitle("Documentation Editor" + " - " + display_name)
        # Name the tab with .py filename
        self.tabWidget.setTabText(0, display_name)

        # In case previous model was incorrect, change the frame colours back
        self.editor_widget.txtEditor.setStyleSheet("")
        self.editor_widget.txtEditor.setToolTip("")

        # See if there is filename.c present
        c_path = self.filename.parent / self.filename.name.replace(".py", ".c")
        if not c_path.exists() or ".rst" in c_path.name: return
        # add a tab with the same highlighting
        c_display_name = c_path.name
        self.c_editor_widget = ModelEditor(self, is_python=False)
        self.tabWidget.addTab(self.c_editor_widget, c_display_name)
        # Read in the file and set in on the widget
        with open(c_path, 'r', encoding="utf-8") as plugin:
            self.c_editor_widget.txtEditor.setPlainText(plugin.read())
        self.c_editor_widget.modelModified.connect(self.editorDocModified)

    def onModifiedExit(self):
        msg_box = QtWidgets.QMessageBox(self)
        msg_box.setWindowTitle("SasView Model Editor")
        msg_box.setText("The document has been modified.")
        msg_box.setInformativeText("Do you want to save your changes?")
        msg_box.setStandardButtons(QtWidgets.QMessageBox.Save | QtWidgets.QMessageBox.Discard | QtWidgets.QMessageBox.Cancel)
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

    def editorDocModified(self):
        """
        User modified the model in the Model Editor.
        Disable the plugin editor and show that the model is changed.
        """
        self.setTabEdited(True)
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).setEnabled(True)
        self.is_modified = True

    def pluginTitleSet(self):
        """
        User modified the model name.
        Display the model name in the window title
        and allow for model save.
        """
        # Ensure plugin name is non-empty
        model = self.getModel()
        if 'filename' in model and model['filename']:
            self.setWindowTitle(self.window_title + " - " + model['filename'])
            self.setTabEdited(True)
            self.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).setEnabled(True)
            self.is_modified = True
        else:
            # the model name is empty - disable Apply and clear the editor
            self.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).setEnabled(False)
            self.editor_widget.blockSignals(True)
            self.editor_widget.txtEditor.setPlainText('')
            self.editor_widget.blockSignals(False)
            self.editor_widget.setEnabled(False)

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

    def updateFromPlugin(self):
        """
        Write the plugin and update the model editor
        """
        # get current model
        model = self.getModel()
        if 'filename' not in model: return

        # get required filename
        filename = model['filename']

        # check if file exists
        plugin_location = models.find_plugins_dir()
        full_path = os.path.join(plugin_location, filename)
        if os.path.splitext(full_path)[1] != ".py":
            full_path += ".py"

        # Update the global path definition
        self.filename = full_path

        if not self.canWriteModel(model, full_path):
            return

        # generate the model representation as string
        model_str = self.generateModel(model, full_path)
        self.writeFile(full_path, model_str)

        # disable "Apply"
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).setEnabled(False)

        # Run the model test in sasmodels
        if not self.isModelCorrect(full_path):
            return

        self.editor_widget.setEnabled(True)

        # Update the editor here.
        # Simple string forced into control.
        self.editor_widget.blockSignals(True)
        self.editor_widget.txtEditor.setPlainText(model_str)
        self.editor_widget.blockSignals(False)

        # Set the widget title
        self.setTabEdited(False)

        # Notify listeners
        self.parent.communicate.customModelDirectoryChanged.emit()

        # Notify the user
        msg = "Custom model "+filename + " successfully created."
        self.parent.communicate.statusBarUpdateSignal.emit(msg)
        logging.info(msg)

    def updateFromEditor(self):
        """
        Save the current state of the Model Editor
        """
        filename = self.filename
        w = self.tabWidget.currentWidget()
        if not w.is_python:
            base, _ = os.path.splitext(filename)
            filename = base + '.c'

        # make sure we have the file handle ready
        assert(filename != "")
        # Retrieve model string
        model_str = self.getModel()['text']
        if w.is_python and self.is_python:
            error_line = self.checkModel(model_str)
            if error_line > 0:
                # select bad line
                cursor = QtGui.QTextCursor(w.txtEditor.document().findBlockByLineNumber(error_line-1))
                w.txtEditor.setTextCursor(cursor)
                return

        # change the frame colours back
        w.txtEditor.setStyleSheet("")
        w.txtEditor.setToolTip("")
        # Save the file
        self.writeFile(filename, model_str)
        # Update the tab title
        self.setTabEdited(False)

        # Notify listeners, since the plugin name might have changed
        self.parent.communicate.customModelDirectoryChanged.emit()

        # notify the user
        msg = str(filename) + " successfully saved."
        self.parent.communicate.statusBarUpdateSignal.emit(msg)
        logging.info(msg)
        if self.is_documentation:
            self.regenerateDocumentation()
    
    def regenerateDocumentation(self):
        """
        Defer to subprocess the documentation regeneration process
        """
        # TODO: Move the doc regen methods out of the documentation window - this forces the window to remain open
        #  in order for the documentation regeneration process to run.
        # The regen method is part of the documentation window. If the window is closed, the method no longer exists.
        if hasattr(self.parent, 'helpWindow'):
            self.parent.helpWindow.regenerateHtml(self.filename)

    def onHelp(self):
        """
        Bring up the Model Editor Documentation whenever
        the HELP button is clicked.
        Calls Documentation Window with the path of the location within the
        documentation tree (after /doc/ ....".
        """
        location = "/user/qtgui/Perspectives/Fitting/plugin.html"
        self.help = GuiUtils.showHelp(location)

    @classmethod
    def writeFile(cls, fname, model_str=""):
        """
        Write model content to file "fname"
        """
        with open(fname, 'w', encoding="utf-8") as out_f:
            out_f.write(model_str)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    sheet = DocEditor()
    sheet.show()
    app.exec_()
    
