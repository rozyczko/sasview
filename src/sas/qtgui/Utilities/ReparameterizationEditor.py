from PySide6 import QtWidgets, QtCore, QtGui

from sas.qtgui.Utilities.UI.ReparameterizationEditorUI import Ui_ReparameterizationEditor
from sas.qtgui.Utilities.ModelSelector import ModelSelector
from sas.qtgui.Utilities.ParameterEditDialog import ParameterEditDialog

class ReparameterizationEditor(QtWidgets.QDialog, Ui_ReparameterizationEditor):

    def __init__(self, parent=None):
        super(ReparameterizationEditor, self).__init__(parent._parent)

        self.parent = parent

        self.setupUi(self)

        self.addSignals()

        self.newParamTreeEditable = False
    
    def addSignals(self):
        self.selectModelButton.clicked.connect(self.onSelectModel)
        self.cmdCancel.clicked.connect(self.close)
        self.cmdAddParam.clicked.connect(self.onAddParam)
        self.cmdEditSelected.clicked.connect(self.editSelected)

    def onSelectModel(self):
        """
        Launch model selection dialog
        """
        self.model_selector = ModelSelector(self)
        self.model_selector.returnModelParamsSignal.connect(lambda params: self.loadParams(params, self.oldParamTree))
        self.model_selector.show()

    def loadParams(self, params, tree):
        """
        Load parameters from the selected model into the oldParamTree
        :param param:
        :param tree: the tree widget to load the parameters into
        """
        for param in params:
            item = QtWidgets.QTreeWidgetItem(tree)
            item.setText(0, param.name)
            tree.addTopLevelItem(item)
            self.addSubItems(param, item)

    def onAddParam(self):
        """
        Add parameter to "New parameters box" by invoking parameter editor dialog
        """
        self.param_creator = ParameterEditDialog(self)
        self.param_creator.returnNewParamsSignal.connect(lambda params: self.loadParams(params, self.newParamTree))
        self.param_creator.show()
    
    def editSelected(self):
        """
        Edit the selected parameter in a new parameter editor dialog
        """
        # get selected item
        selected_item = self.newParamTree.currentItem()
        param_to_open = None
        if selected_item.parent() is None:
            # User selected a parametery, not a property
            param_to_open = selected_item.text(0)
        else:
            # User selected a property, not a parameter
            param_to_open = selected_item.parent().text(0)
        
        highlighted_property = selected_item.text(0) # What the user wants to edit specifically
        
        # Find the parameter item by using param_to_open and format as a dictionary
        param_properties = self.getParamProperties(self.newParamTree, param_to_open)
        param_properties['highlighted_property'] = highlighted_property # Which property the cursor will start on
        self.param_editor = ParameterEditDialog(self, param_properties)
        self.param_editor.returnEditedParamSignal.connect(self.updateParam)
        self.param_editor.show()
    
    def getParamProperties(self, tree, param_name):
        """
        Return a dictionary of property name: value pairs for the given parameter name
        """
        properties = {}
        for param in range(tree.topLevelItemCount()): # Iterate over all top-level items (parameters)
            param_item = tree.topLevelItem(param)
            if param_item.text(0) == param_name: # If the parameter name is the one the user selected
                properties['name'] = param_item.text(0)
                for property in range(param_item.childCount()): # Iterate over all properties (children) of the parameter and add them to dict
                    prop_item = param_item.child(property)
                    properties[prop_item.text(0)] = prop_item.text(1)
                break
        return properties
    
    def updateParam(self, updated_param, old_name):
        """
        Update given parameter in the newParamTree with the updated properties
        :param updated_param: Sasview Parameter class with updated properties
        :param old_name: the old name of the parameter (so we can detect which parameter to update)
        """
        unpacked_param = updated_param[0] # updated_param is sent as a list but will only have one item. Unpack it.

        for i in range(self.newParamTree.topLevelItemCount()):
            param = self.newParamTree.topLevelItem(i)
            if param.text(0) == old_name:
                # First delete all sub-items of the parameter
                while param.childCount() > 0:
                    sub_item = param.child(0)
                    param.removeChild(sub_item)

                # Now add all the updated properties
                self.addSubItems(unpacked_param, param)
                # Make sure to update the name of the parameter
                param.setText(0, unpacked_param.name)

    @classmethod
    def addSubItems(cls, param, top_item):
        """
        Add sub-items to the given top-level item for the given parameter
        :param param: the Sasmodels Parameter class that contains properties to add
        :param top_item: the top-level item to add the properties to (QTreeWidgetItem)
        """
        # Create list of properties: (display name, property name)
        properties = [ ("default", "default"),
                    ("min", "limits[0]"),
                    ("max", "limits[1]"),
                    ("units", "units"),
                    ("type", "type")
                    ]
        for prop in properties:
            sub_item = QtWidgets.QTreeWidgetItem(top_item)
            sub_item.setText(0, prop[0]) # First column is display name
            if '[' in prop[1]:
                # Limit properties have an index, so we need to extract it
                prop_name, index = prop[1].split('[')
                index = int(index[:-1])  # Remove the closing ']' and convert to int
                # Use getattr to get the property, then index into it
                sub_item.setText(1, str(getattr(param, prop_name)[index]))
            else:
                sub_item.setText(1, str(getattr(param, prop[1])))

    def closeEvent(self, event):
        self.close()
        self.deleteLater()  # Schedule the window for deletion