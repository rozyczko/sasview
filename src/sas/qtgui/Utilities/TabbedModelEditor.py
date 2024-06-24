# global
import sys
import os
import re
import ast
import datetime
import logging
import traceback

from PySide6 import QtWidgets, QtCore, QtGui
from pathlib import Path

from sas.sascalc.fit import models
from sas.sascalc.fit.models import find_plugins_dir

import sas.qtgui.Utilities.GuiUtils as GuiUtils
from sas.qtgui.Utilities.UI.TabbedModelEditor import Ui_TabbedModelEditor
from sas.qtgui.Utilities.PluginDefinition import PluginDefinition
from sas.qtgui.Utilities.ModelEditor import ModelEditor

class TabbedModelEditor(QtWidgets.QDialog, Ui_TabbedModelEditor):
    """
    Model editor "container" class describing interaction between
    plugin definition widget and model editor widget.
    Once the model is defined, it can be saved as a plugin.
    """
    # Signals for intertab communication plugin -> editor
    def __init__(self, parent=None, edit_only=False, model=False, load_file=None):
        super(TabbedModelEditor, self).__init__(parent._parent)

        self.parent = parent

        self.setupUi(self)

        # globals
        self.filename_py = ""
        self.filename_c = ""
        self.is_python = True
        self.is_documentation = False
        self.window_title = self.windowTitle()
        self.edit_only = edit_only
        self.load_file = load_file.lstrip("//") if load_file else None
        self.model = model
        self.is_modified = False
        self.label = None
        self.file_to_regenerate = ""
        self.include_polydisperse = False

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

        # Initially hide form function box
        self.plugin_widget.formFunctionBox.setVisible(False)

        if self.edit_only:
            self.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).setText("Save")
            # Hide signals from the plugin widget
            self.plugin_widget.blockSignals(True)
            # and hide the tab/widget itself
            self.tabWidget.removeTab(0)
        
        if self.model is not None:
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
        self.plugin_widget.modelModified.connect(self.editorModelModified)
        self.editor_widget.modelModified.connect(self.editorModelModified)
        self.plugin_widget.txtName.editingFinished.connect(self.pluginTitleSet)
        self.plugin_widget.includePolydisperseFuncsSignal.connect(self.includePolydisperseFuncs)
        self.plugin_widget.omitPolydisperseFuncsSignal.connect(self.omitPolydisperseFuncs)

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

            if self.model is True:
                # Find location of model .py files and load from that location
                if os.path.isfile(user_model_name):
                    filename = user_model_name
                else:
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
                                            None,
                                            QtWidgets.QFileDialog.DontUseNativeDialog)[0]

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
        self.filename_py = Path(filename)
        display_name = self.filename_py.stem
        if not self.model:
            self.setWindowTitle(self.window_title + " - " + display_name)
        else:
            self.setWindowTitle("Documentation Editor" + " - " + display_name)
        # Name the tab with .py filename
        self.tabWidget.setTabText(0, display_name)

        # Check the validity of loaded model if the model is python
        if self.is_python:
            error_line = self.checkModel(plugin_text, run_unit_test=False)
            if error_line > 0:
                # select bad line
                cursor = QtGui.QTextCursor(self.editor_widget.txtEditor.document().findBlockByLineNumber(error_line-1))
                self.editor_widget.txtEditor.setTextCursor(cursor)
                return

        # In case previous model was incorrect, change the frame colours back
        self.editor_widget.txtEditor.setStyleSheet("")
        self.editor_widget.txtEditor.setToolTip("")

        # See if there is filename.c present
        self.filename_c = self.filename_py.parent / self.filename_py.name.replace(".py", ".c")
        if not self.filename_c.exists() or ".rst" in self.filename_c.name: return
        # add a tab with the same highlighting
        c_display_name = self.filename_c.name
        self.c_editor_widget = ModelEditor(self, is_python=False)
        self.tabWidget.addTab(self.c_editor_widget, c_display_name)
        # Read in the file and set in on the widget
        with open(self.filename_c, 'r', encoding="utf-8") as plugin:
            self.c_editor_widget.txtEditor.setPlainText(plugin.read())
        self.c_editor_widget.modelModified.connect(self.editorModelModified)

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

    def editorModelModified(self):
        """
        User modified the model in the Model Editor.
        Disable the plugin editor and show that the model is changed.
        """
        self.setTabEdited(True)
        self.plugin_widget.txtFunction.setStyleSheet("")
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).setEnabled(True)
        self.is_modified = True
    
    def omitPolydisperseFuncs(self):
        """
        User has no polydisperse parameters.
        Omit polydisperse-only functions from model text.
        Note that this is necessary because Form Volume Function text box does not clear its text when it disappears.
        """
        self.include_polydisperse = False
    
    def includePolydisperseFuncs(self):
        """
        User has defined polydisperse parameters.
        Include polydisperse-only functions from model text.
        By default these are not included even if text exists in Form Volume Function text box.
        """
        self.include_polydisperse = True
            
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

        # If user has not specified an output file type, throw error message
        if model['gen_python'] == False and model['gen_c'] == False:
                msg = "No output model language specified.\n"
                msg += "Please select which types of model (Python, C) to generate."
                QtWidgets.QMessageBox.critical(self, "Plugin Error", msg)
                return

        # check if file exists
        plugin_location = models.find_plugins_dir()
        if model['gen_python'] == True:
            full_path = os.path.join(plugin_location, filename)
            if os.path.splitext(full_path)[1] != ".py":
                full_path += ".py"
            # Update the global path definition
            self.filename_py = full_path
            if not self.canWriteModel(model, full_path):
                return
            # generate the model representation as string
            model_str = self.generatePyModel(model, full_path)
            self.writeFile(full_path, model_str)

        if model['gen_c'] == True:
            c_path = os.path.join(plugin_location, filename)
            if os.path.splitext(c_path)[1] != ".c":
                c_path += ".c"
            # Update the global path definition
            self.filename_c = c_path
            if not self.canWriteModel(model, c_path):
                return
            # generate the model representation as string
            c_model_str = self.generateCModel(model, c_path)
            self.writeFile(c_path, c_model_str)

        # disable "Apply"
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).setEnabled(False)

        # Run the model test in sasmodels and check model syntax. Returns error line if checks fail.
        error_line = self.checkModel(full_path)
        if error_line > 0:
            return

        self.editor_widget.setEnabled(True)
        
        # Update the editor here.
        # Simple string forced into control.
        if model['gen_python'] == True:
            self.editor_widget.blockSignals(True)
            self.editor_widget.txtEditor.setPlainText(model_str)
            self.editor_widget.blockSignals(False)
        if model['gen_c'] == True:
            # Add a tab to TabbedModelEditor for the C model
            c_display_name = Path(self.filename_c).name
            self.c_editor_widget = ModelEditor(self, is_python=False)
            self.tabWidget.addTab(self.c_editor_widget, c_display_name)

            # Update the editor
            self.c_editor_widget.blockSignals(True)
            self.c_editor_widget.txtEditor.setPlainText(c_model_str)
            self.c_editor_widget.blockSignals(False)

            # Connect 'modified' signal
            self.c_editor_widget.modelModified.connect(self.editorModelModified)

        # Set the widget title
        self.setTabEdited(False)

        # Notify listeners
        self.parent.communicate.customModelDirectoryChanged.emit()

        # Notify the user
        msg = "Custom model "+filename + " successfully created."
        self.parent.communicate.statusBarUpdateSignal.emit(msg)
        logging.info(msg)

    def checkModel(self, full_path, run_unit_test=True):
        """
        Run the ast check
        and return True if the model is good.
        False otherwise.
        """
        # successfulCheck = True
        error_line = 0
        try:
            with open(full_path, 'r', encoding="utf-8") as plugin:
                model_str = plugin.read()
            ast.parse(model_str)
            if run_unit_test:
                model_check = GuiUtils.checkModel(full_path)

        except Exception as ex:
            msg = "Error building model: " + str(ex)
            logging.error(msg)
            # print four last lines of the stack trace
            # this will point out the exact line failing
            all_lines = traceback.format_exc().split('\n')
            last_lines = all_lines[-4:]
            traceback_to_show = '\n'.join(last_lines)
            logging.error(traceback_to_show)

            # Set the status bar message
            # GuiUtils.Communicate.statusBarUpdateSignal.emit("Model check failed")
            self.parent.communicate.statusBarUpdateSignal.emit("Model check failed")

            # Remove the file so it is not being loaded on refresh
            os.remove(full_path)

            # Put a thick, red border around the editor.
            from sas.qtgui.Utilities.CodeEditor import QCodeEditor

            # Find all QTextBrowser and QCodeEditor children
            text_browsers = self.tabWidget.currentWidget().findChildren(QtWidgets.QTextBrowser)
            code_editors = self.tabWidget.currentWidget().findChildren(QCodeEditor)

            # Combine the lists and apply the stylesheet
            for child in text_browsers + code_editors:
                child.setStyleSheet("border: 5px solid red")
                # last_lines = traceback.format_exc().split('\n')[-4:]
                traceback_to_show = '\n'.join(last_lines)
                child.setToolTip(traceback_to_show)

            # attempt to find the failing command line number, usually the last line with
            # `File ... line` syntax
            reversed_error_text = list(reversed(all_lines))
            for line in reversed_error_text:
                if ('File' in line and 'line' in line):
                    # If model check fails (not syntax) then 'line' and 'File' will be in adjacent lines
                    error_line = re.split('line ', line)[1]
                    try:
                        error_line = int(error_line)
                        break
                    except ValueError:
                        # Sometimes the line number is followed by more text
                        try:
                            error_line = error_line.split(',')[0]
                            error_line = int(error_line)
                            break
                        except ValueError:
                            error_line = 0

        return error_line

    def isModelCorrect(self, full_path):
        """
        Run the sasmodels method for model check
        and return True if the model is good.
        False otherwise.
        """
        successfulCheck = True
        try:
            model_results = GuiUtils.checkModel(full_path)
            logging.info(model_results)
        # We can't guarantee the type of the exception coming from
        # Sasmodels, so need the overreaching general Exception
        except Exception as ex:
            msg = "Error building model: "+ str(ex)
            logging.error(msg)
            #print three last lines of the stack trace
            # this will point out the exact line failing
            last_lines = traceback.format_exc().split('\n')[-4:]
            traceback_to_show = '\n'.join(last_lines)
            logging.error(traceback_to_show)

            # Set the status bar message
            self.parent.communicate.statusBarUpdateSignal.emit("Model check failed")

            # Remove the file so it is not being loaded on refresh
            os.remove(full_path)
            # Put a thick, red border around the mini-editor
            self.plugin_widget.txtFunction.setStyleSheet("border: 5px solid red")
            # Use the last line of the traceback for the tooltip
            last_lines = traceback.format_exc().split('\n')[-2:]
            traceback_to_show = '\n'.join(last_lines)
            self.plugin_widget.txtFunction.setToolTip(traceback_to_show)
            successfulCheck = False
        return successfulCheck

    def updateFromEditor(self):
        """
        Save the current state of the Model Editor
        """
        filename = self.filename_py
        w = self.tabWidget.currentWidget()
        if not w.is_python:
            base, _ = os.path.splitext(filename)
            filename = base + '.c'
        # make sure we have the file handle ready
        assert filename != ""

        # Retrieve model string
        model_str = self.getModel()['text']
        # Save the file
        self.writeFile(filename, model_str)

        # Get model filepath
        plugin_location = models.find_plugins_dir()
        full_path = os.path.join(plugin_location, filename)
        if os.path.splitext(full_path)[1] != ".py":
            full_path += ".py"
        if w.is_python and self.is_python:
            error_line = self.checkModel(full_path)
            if error_line > 0:
                # select bad line
                cursor = QtGui.QTextCursor(w.txtEditor.document().findBlockByLineNumber(error_line-1))
                w.txtEditor.setTextCursor(cursor)
                return

        # change the frame colours back
        w.txtEditor.setStyleSheet("")
        w.txtEditor.setToolTip("")

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
            self.parent.helpWindow.regenerateHtml(self.filename_py)

    def canWriteModel(self, model=None, full_path=""):
        """
        Determine if the current plugin can be written to file
        """
        assert(isinstance(model, dict))
        assert(full_path!="")

        # Make sure we can overwrite the file if it exists
        if os.path.isfile(full_path):
            # can we overwrite it?
            if not model['overwrite']:
                # notify the viewer
                msg = "Plugin with specified name already exists.\n"
                msg += "Please specify different filename or allow file overwrite."
                QtWidgets.QMessageBox.critical(self, "Plugin Error", msg)
                # Don't accept but return
                return False
        # Update model editor if plugin definition changed
        func_str = model['func_text']
        form_vol_str = model['form_volume_text']
        msg = None
        if func_str:
            if 'return' not in func_str:
                msg = "Error: The func(x) must 'return' a value at least.\n"
                msg += "For example: \n\nreturn 2*x"
        elif form_vol_str:
            if 'return' not in form_vol_str:
                msg = "Error: The form_volume() must 'return' a value at least.\n"
                msg += "For example: \n\nreturn 0.0"
        else:
            msg = 'Error: Function is not defined.'
        if msg is not None:
            QtWidgets.QMessageBox.critical(self, "Plugin Error", msg)
            return False
        return True

    def onHelp(self):
        """
        Bring up the Model Editor Documentation whenever
        the HELP button is clicked.
        Calls Documentation Window with the path of the location within the
        documentation tree (after /doc/ ....".
        """
        location = "/user/qtgui/Perspectives/Fitting/plugin.html"
        self.parent.showHelp(location)

    def getModel(self):
        """
        Retrieves plugin model from the currently open tab
        """
        return self.tabWidget.currentWidget().getModel()

    @classmethod
    def writeFile(cls, fname, model_str=""):
        """
        Write model content to file "fname"
        """
        with open(fname, 'w', encoding="utf-8") as out_f:
            out_f.write(model_str)
    
    def generateCModel(self, model, fname):
        """
        Generate C model from the current plugin state
        :param model: plugin model
        :param fname: filename
        """

        model_text = C_COMMENT_TEMPLATE

        param_names = []
        pd_param_names = []
        param_str = self.strFromParamDict(model['parameters'])
        pd_param_str = self.strFromParamDict(model['pd_parameters'])
        for pname, _, _ in self.getParamHelper(param_str):
                param_names.append('double ' + pname)
        for pd_pname, _, _ in self.getParamHelper(pd_param_str):
                pd_param_names.append('double ' + pd_pname)
        
        # Add polydisperse-dependent functions if polydisperse parameters are present
        if pd_param_names != []:
            model_text += C_PD_TEMPLATE.format(poly_args = ', '.join(pd_param_names),
                                              poly_arg1 = pd_param_names[0].split(' ')[1]) # Remove 'double' from the first argument
        # Add all other function templates
        model_text += C_TEMPLATE.format(args = ',\n\t'.join(param_names))
        
        return model_text
        

    def generatePyModel(self, model, fname):
        """
        generate model from the current plugin state
        """
        name = model['filename']
        if not name:
            model['filename'] = fname
            name = fname
        desc_str = model['description']
        param_str = self.strFromParamDict(model['parameters'])
        pd_param_str = self.strFromParamDict(model['pd_parameters'])
        func_str = model['func_text']
        form_vol_str = model['form_volume_text']
        model_text = CUSTOM_TEMPLATE.format(name = name,
                                            title = 'User model for ' + name,
                                            description = desc_str,
                                            date = datetime.datetime.now().strftime('%Y-%m-%d')
                                            )

        # Write out parameters
        param_names = []    # to store parameter names
        pd_params = []
        model_text += 'parameters = [ \n'
        model_text += '#   ["name", "units", default, [lower, upper], "type", "description"],\n'
        if param_str:
            for pname, pvalue, desc in self.getParamHelper(param_str):
                param_names.append(pname)
                model_text += "    ['%s', '', %s, [-inf, inf], '', '%s'],\n" % (pname, pvalue, desc)
        if pd_param_str:
            for pname, pvalue, desc in self.getParamHelper(pd_param_str):
                param_names.append(pname)
                pd_params.append(pname)
                model_text += "    ['%s', '', %s, [-inf, inf], 'volume', '%s'],\n" % (pname, pvalue, desc)
        model_text += '    ]\n\n'

        # If creating a C model, link it to the Python file

        if model['gen_c']:
            model_text += LINK_C_MODEL_TEMPLATE.format(c_model_name = name + '.c')
            model_text += '\n\n'

        # Write out function definition
        model_text += 'def Iq(%s):\n' % ', '.join(['q'] + param_names)
        model_text += '    """Absolute scattering"""\n'
        if "scipy." in func_str:
            model_text +="    import scipy\n"
        if "numpy." in func_str:
            model_text +="    import numpy\n"
        if "np." in func_str:
            model_text +="    import numpy as np\n"
        for func_line in func_str.split('\n'):
                model_text +='%s%s\n' % ("    ", func_line)
        model_text +='\n## uncomment the following if Iq works for vector x\n'
        model_text +='#Iq.vectorized = True\n'

        # Add parameters to ER and VR functions and include placeholder functions
        model_text += "\n"
        model_text += ER_VR_TEMPLATE.format(args = ', '.join(param_names))

        # If polydisperse, create place holders for form_volume
        if pd_params and self.include_polydisperse == True:
            model_text +="\n"
            model_text +=CUSTOM_TEMPLATE_PD.format(args = ', '.join(pd_params))
            for func_line in form_vol_str.split('\n'):
                model_text +='%s%s\n' % ("    ", func_line)

        # Create place holder for Iqxy
        model_text +="\n"
        model_text +='#def Iqxy(%s):\n' % ', '.join(["x", "y"] + param_names)
        model_text +='#    """Absolute scattering of oriented particles."""\n'
        model_text +='#    ...\n'
        model_text +='#    return oriented_form(x, y, args)\n'
        model_text +='## uncomment the following if Iqxy works for vector x, y\n'
        model_text +='#Iqxy.vectorized = True\n'

        return model_text

    @classmethod
    def getParamHelper(cls, param_str):
        """
        yield a sequence of name, value pairs for the parameters in param_str

        Parameters can be defined by one per line by name=value, or multiple
        on the same line by separating the pairs by semicolon or comma.  The
        value is optional and defaults to "1.0".
        """
        for line in param_str.replace(';', ',').split('\n'):
            for item in line.split(','):
                defn, desc = item.split('#', 1) if '#' in item else (item, '')
                name, value = defn.split('=', 1) if '=' in defn else (defn, '1.0')
                if name:
                    yield [v.strip() for v in (name, value, desc)]

    @classmethod
    def strFromParamDict(cls, param_dict):
        """
        Creates string from parameter dictionary

        Example::

            {
                0: ('variable','value'),
                1: ('variable','value'),
                ...
            }
        """
        param_str = ""
        for _, params in param_dict.items():
            if not params[0]: continue
            value = 1
            if params[1]:
                try:
                    value = float(params[1])
                except ValueError:
                    # convert to default
                    value = 1
            param_str += params[0] + " = " + str(value) + "\n"
        return param_str


CUSTOM_TEMPLATE = '''\
r"""
Definition
----------

Calculates {name}.

{description}

References
----------

Authorship and Verification
---------------------------

* **Author:** --- **Date:** {date}
* **Last Modified by:** --- **Date:** {date}
* **Last Reviewed by:** --- **Date:** {date}
"""

from sasmodels.special import *
from numpy import inf

name = "{name}"
title = "{title}"
description = """{description}"""

# Optional flags (can be removed). Read documentation by pressing 'Help' for more information.

# single = True indicates that the model can be run using single precision floating point values. Defaults to True.
single = True

# opencl = False indicates that the model should not be run using OpenCL. Defaults to False.
opencl = False

# structure_factor = False indicates that the model cannot be used as a structure factor to account for interactions between particles. Defaults to False.
structure_factor = False

# have_fq = False indicates that the model does not define F(Q) calculations in a linked C model. Note that F(Q) calculations are only necessary for accomadating beta approximation. Defaults to False.
have_fq = False
'''

ER_VR_TEMPLATE = '''\
def ER({args}):
    """
    Effective radius of particles to be used when computing structure factors.

    Input parameters are vectors ranging over the mesh of polydispersity values.
    """
    return 0.0

def VR({args}):
    """
    Volume ratio of particles to be used when computing structure factors.

    Input parameters are vectors ranging over the mesh of polydispersity values.
    """
    return 1.0
'''

CUSTOM_TEMPLATE_PD = '''\
def form_volume({args}):
    """
    Volume of the particles used to compute absolute scattering intensity
    and to weight polydisperse parameter contributions.
    """
'''

SUM_TEMPLATE = """
from sasmodels.core import load_model_info
from sasmodels.sasview_model import make_model_from_info

model_info = load_model_info('{model1}{operator}{model2}')
model_info.name = '{name}'{desc_line}
Model = make_model_from_info(model_info)
"""

LINK_C_MODEL_TEMPLATE = '''\
# Note: removing the "source = []" line will unlink the C model from the Python model, 
# which means the C model will not be checked for errors when edited.
source = ['{c_model_name}']
'''

C_COMMENT_TEMPLATE = '''\
//:::Custom C model template:::
// This is a template for a custom C model.
// C Models are used for a variety of reasons in SasView, including better performance and the ability to perform calculations not possible in Python.
// For example, all oriented and magnetic models, as well as most models using structure factor calculations, are written in C.
// HOW TO USE THIS TEMPLATE:
// 1. Determine which functions you will need to perform your calculations; delete unused functions.
//   1.1 Note that you must define either Iq, Fq, or one of Iqac, Iqabc:
//     Iq if your model does not use orientation parameters or use structure factor calculations;
//     Fq if your model uses structure factor calculations;
//     Iqac or Iqabc if your model uses orientation parameters/is magnetic;
//     Fq AND Iqac/Iqabc if your model uses orientation parameters/is magnetic and has structure factor calculations.
// 2. Write C code independently of this editor and paste it into the appropriate functions.
//   2.1 Note that the C editor does not support C syntax checking, so writing C code directly into the SasView editor is not reccomended.
// 3. Ensure a python file links to your C model (source = ['filename.c'])
// 4. Press 'Apply' or 'Save' to save your model and run a model check (note that the model check will fail if there is no python file of the same name in your plugins directory)

'''

C_PD_TEMPLATE = '''\
static double
form_volume({poly_args}) // Remove arguments as needed
{{
    return 0.0*{poly_arg1};
}}
'''

C_TEMPLATE = """\
static double
radius_effective(int mode) // Add arguments as needed
{{
    switch (mode) {{
    default:
    case 1:
    // Define effective radius calculations here...
    return 0.0;
    }}
}}

static void
Fq(double q, 
    double *F1,
    double *F2,
    {args}) // Remove arguments as needed
{{
    // Define F(Q) calculations here...
    // IMPORTANT: You do not have to define Iq if your model uses Fq for beta approximation; the *F2 value is <F(Q)^2> and equivalent to the output of Iq.
    // IMPORTANT: You may use Fq instead of Iq even if you do not need <F(Q)> (*F1) for beta approximation, but this is not recommended.
    // IMPORTANT: Additionally, you must still define Iqac or Iqabc if your model has orientation parameters.
    *F1 = 0.0;
    *F2 = 0.0;
}}

static double
Iq(double q,
    {args}) // Remove arguments as needed
{{
    // Define I(Q) calculations here for models independent of shape orientation
    // IMPORTANT: Only define ONE calculation for I(Q): either Iq, Iqac, or Iqabc; remove others.
    return 1.0;
}}

static double
Iqac(double qab,
    double qc,
    {args}) // Remove arguments as needed
{{
    // Define I(Q) calculations here for models dependent on shape orientation in which the shape is rotationally symmetric about *c* axis
    // Note: *psi* angle not needed for shapes symmetric about *c* axis
    // IMPORTANT: Only define ONE calculation for I(Q): either Iq, Iqac, Iqabc, or Iqxy; remove others.
    return 1.0;
}}

static double
Iqabc(double qa,
    double qb,
    double qc,
    {args}) // Remove arguments as needed
{{
    // Define I(Q) calculations here for models dependent on shape orientation in all three axes
    // IMPORTANT: Only define ONE calculation for I(Q): either Iq, Iqac, Iqabc, or Iqxy; remove others.
    return 1.0;
}}

static double
Iqxy(double qx,
    double qy,
    {args}) // Remove arguments as needed
{{
    // Define I(Q) calculations here for 2D magnetic models.
    // WARNING: The use of Iqxy is generally discouraged; Use Iqabc instead for its better orientational averaging and documentation for details.
    // IMPORTANT: Only define ONE calculation for I(Q): either Iq, Iqac, Iqabc, or Iqxy; remove others.
    return 1.0;
}}
"""

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    sheet = TabbedModelEditor()
    sheet.show()
    app.exec_()
    
