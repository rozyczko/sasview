import time
import logging
import re
import copy

from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtWidgets
import numpy as np

from sas.qtgui.Plotting.PlotterData import Data1D
from sas.qtgui.Plotting.Plotter import PlotterWidget
from sas.qtgui.Plotting.PlotterData import Data2D
from sas.qtgui.Plotting.Plotter2D import Plotter2DWidget
import sas.qtgui.Utilities.GuiUtils as GuiUtils

from .UI.DataOperationUtilityUI import Ui_DataOperationUtility

BG_WHITE = "background-color: rgb(255, 255, 255); color: rgb(0, 0, 0);"
BG_RED = "background-color: rgb(244, 170, 164);"

# colors for data operation plots
OUTPUT_COLOR = "#000000"  # black
DATA1_COLOR = '#B22222'  # firebrick
DATA2_COLOR = '#0000FF'  # blue
TRIMMED_COLOR = '#FFFFFF'  # white
TRIMMED_ALPHA = 0.3  # semi-transparent points trimmed for operation


class DataOperationUtilityPanel(QtWidgets.QDialog, Ui_DataOperationUtility):
    def __init__(self, parent=None):
        super(DataOperationUtilityPanel, self).__init__()
        self.setupUi(self)
        self.manager = parent
        self.communicator = self.manager.communicator()

        # To store input datafiles
        self.filenames = None
        self.list_data_items = []
        self.data1 = None
        self.data2 = None
        # To store the result
        self.output = None

        # To update content of comboboxes with files loaded in DataExplorer
        self.communicator.sendDataToPanelSignal.connect(self.updateCombobox)

        # change index of comboboxes
        self.cbData1.currentIndexChanged.connect(self.onSelectData1)
        self.cbData2.currentIndexChanged.connect(self.onSelectData2)
        self.cbOperator.currentIndexChanged.connect(self.onSelectOperator)

        # edit Coefficient text edit
        self.txtNumber.textChanged.connect(self.onInputCoefficient)
        self.txtOutputData.textChanged.connect(self.onCheckOutputName)

        # push buttons
        self.cmdClose.clicked.connect(self.onClose)
        self.cmdHelp.clicked.connect(self.onHelp)
        self.cmdSave.clicked.connect(self.onSave)
        self.cmdCompute.clicked.connect(self.onCompute)
        self.cmdReset.clicked.connect(self.onReset)

        self.cmdCompute.setEnabled(False)

        # validator for coefficient
        self.txtNumber.setValidator(GuiUtils.DoubleValidator())

        self.layoutOutput = QtWidgets.QHBoxLayout()
        self.layoutData1 = QtWidgets.QHBoxLayout()
        self.layoutData2 = QtWidgets.QHBoxLayout()

        # Create default layout for initial graphs (when they are still empty)
        self.newPlot(self.graphOutput, self.layoutOutput)
        self.newPlot(self.graphData1, self.layoutData1)
        self.newPlot(self.graphData2, self.layoutData2)

        # Flag to enable Compute pushbutton
        self.data2OK = False
        self.data1OK = False

    def updateCombobox(self, filenames):
        """ Function to fill comboboxes with names of datafiles loaded in
         DataExplorer. For Data2, there is the additional option of choosing
         a number to apply to data1 """
        self.filenames = filenames

        if list(filenames.keys()):
            # clear contents of comboboxes
            self.cbData1.clear()
            self.cbData1.addItems(['Select Data'])
            self.cbData2.clear()
            self.cbData2.addItems(['Select Data', 'Number'])

            list_datafiles = []

            for key_id in list(filenames.keys()):
                if filenames[key_id].name:
                    # filenames with titles
                    new_title = filenames[key_id].name
                    list_datafiles.append(new_title)
                    self.list_data_items.append(new_title)

                else:
                    # filenames without titles by removing time.time()
                    new_title = re.sub(r'\d{10}\.\d{2}', '', str(key_id))
                    self.list_data_items.append(new_title)
                    list_datafiles.append(new_title)

            # update contents of comboboxes
            self.cbData1.addItems(list_datafiles)
            self.cbData2.addItems(list_datafiles)

    def onHelp(self):
        """
        Bring up the Data Operation Utility Documentation whenever
        the HELP button is clicked.
        Calls Documentation Window with the path of the location within the
        documentation tree (after /doc/ ....".
        """
        location = "/user/qtgui/Calculators/data_operator_help.html"
        self.manager.showHelp(location)

    def onClose(self):
        """ Close dialog """
        self.onReset()
        self.cbData1.clear()
        self.cbData1.addItems(['No Data Available'])
        self.cbData2.clear()
        self.cbData2.addItems(['No Data Available'])
        self.close()

    def onCompute(self):
        """ perform calculation - don't send to data explorer"""
        # set operator to be applied
        operator = self.cbOperator.currentText()
        # calculate and send data to DataExplorer
        if self.data1 is None or self.data2 is None:
            logging.warning("Please set both Data1 and Data2 to complete operation.")
        try:
            data1 = self.data1
            data2 = self.data2
            output = eval("data1 %s data2" % operator)
        except Exception as ex:
            logging.error(ex)
            return

        self.output = output

        self.updatePlot(self.graphOutput, self.layoutOutput, self.output, operation_data=True)
        self.updatePlot(self.graphData1, self.layoutData1, self.data1, operation_data=True)
        self.updatePlot(self.graphData2, self.layoutData2, self.data2, operation_data=True)
        logging.info("Data operation complete.")

    def onSave(self):
        """ send to data explorer """
        # if output name was unused, write output result to it
        # and display plot
        if self.onCheckOutputName() and self.output is not None:
            # add outputname to self.filenames
            self.list_data_items.append(str(self.txtOutputData.text()))
            # send result to DataExplorer
            self.onPrepareOutputData()

            # Add the new plot to the comboboxes
            self.cbData1.addItem(self.output.name)
            self.cbData2.addItem(self.output.name)
            if self.filenames is None:
                self.filenames = {}
            self.filenames[self.output.name] = self.output
        elif self.output is None:
            logging.warning("No output data to save.")

    def onPrepareOutputData(self):
        """ Prepare datasets to be added to DataExplorer and DataManager """
        name = self.txtOutputData.text()
        self.output.name = name
        self.output.id = name + str(time.time())
        new_item = GuiUtils.createModelItemWithPlot(
            self.output,
            name=name)

        new_datalist_item = {name + str(time.time()): self.output}
        self.communicator. \
            updateModelFromDataOperationPanelSignal.emit(new_item, new_datalist_item)

    def onSelectOperator(self):
        """ Change GUI when operator changed """
        self.lblOperatorApplied.setText(self.cbOperator.currentText())
        self.resetOutput()

    def onReset(self):
        """
        Reset Panel to its initial state (default values) keeping
        the names of loaded data
        """
        self.txtNumber.setText('1.0')

        # sets new default name for output data that doesn't already exist
        self.txtOutputData.setText(self.uniqueOutputName())

        self.txtNumber.setEnabled(False)
        self.cmdCompute.setEnabled(False)

        self.cbData1.setCurrentIndex(0)
        self.cbData2.setCurrentIndex(0)
        self.cbOperator.setCurrentIndex(0)

        self.data1OK = False
        self.data2OK = False

        self.resetOutput()
        # Empty graphs and
        self.newPlot(self.graphData1, self.layoutData1)
        self.newPlot(self.graphData2, self.layoutData2)

    def onSelectData1(self):
        """ Plot for selection of Data1 """
        choice_data1 = str(self.cbData1.currentText())

        wrong_choices = ['No Data Available', 'Select Data', '']

        if choice_data1 in wrong_choices:
            # check validity of choice: input = filename
            self.newPlot(self.graphData1, self.layoutData1)
            self.data1 = None
            self.data1OK = False
            self.cmdCompute.setEnabled(False)  # self.onCheckChosenData())
            return

        else:
            self.data1OK = True
            # get Data1
            key_id1 = self._findId(choice_data1)
            self.data1 = self._extractData(key_id1)
            # plot Data1
            self.updatePlot(self.graphData1, self.layoutData1, self.data1)
            # Enable Compute button only if Data2 is defined and data compatible
            self.cmdCompute.setEnabled(self.onCheckChosenData())

    def onSelectData2(self):
        """ Plot for selection of Data2 """
        choice_data2 = str(self.cbData2.currentText())
        wrong_choices = ['No Data Available', 'Select Data', '']

        if choice_data2 in wrong_choices:
            self.newPlot(self.graphData2, self.layoutData2)
            self.data2 = None
            self.txtNumber.setEnabled(False)
            self.data2OK = False
            self.onCheckChosenData()
            self.cmdCompute.setEnabled(False)

        elif choice_data2 == 'Number':
            self.data2OK = True
            self.txtNumber.setEnabled(True)
            self.data2 = float(self.txtNumber.text())

            # Enable Compute button only if Data1 defined and compatible data
            self.cmdCompute.setEnabled(self.onCheckChosenData())
            # Display value of coefficient in graphData2
            self.updatePlot(self.graphData2, self.layoutData2, self.data2)
            self.resetOutput()
            self.onCheckChosenData()

        else:
            self.txtNumber.setEnabled(False)
            self.data2OK = True
            key_id2 = self._findId(choice_data2)
            self.data2 = self._extractData(key_id2)
            self.cmdCompute.setEnabled(self.onCheckChosenData())

            # plot Data2
            self.updatePlot(self.graphData2, self.layoutData2, self.data2)
            self.resetOutput()

        # show interpolation warning when a 1D dataset is chosen for Data2
        if isinstance(self.data2, Data1D):
            self.cautionStatement.setText(
                "CAUTION: interpolation of Data2 will occur for 1D-datasets if x-axis points\n"
                "are not close. This could introduce artifacts. Please see documentation."
            )
        else:
            self.cautionStatement.setText("")

    def onInputCoefficient(self):
        """ Check input of number when a coefficient is required
        for operation """
        if self.txtNumber.isModified():
            input_to_check = str(self.txtNumber.text())

            if input_to_check is None or input_to_check == '':
                msg = 'DataOperation: Number requires a float number'
                logging.warning(msg)
                self.txtNumber.setStyleSheet(BG_RED)

            elif float(self.txtNumber.text()) == 0.:
                # should be check that 0 is not chosen
                msg = 'DataOperation: Number requires a non zero number'
                logging.warning(msg)
                self.txtNumber.setStyleSheet(BG_RED)

            else:
                self.txtNumber.setStyleSheet(BG_WHITE)
                self.data2 = float(self.txtNumber.text())
                self.updatePlot(self.graphData2, self.layoutData2, self.data2)
                # self.updatePlot(self.graphData2, self.layoutData2, self.data2, color='tab:red')

    def onCheckChosenData(self):
        """ check that data1 and data2 are compatible """

        if not all([self.data1OK, self.data2OK]):
            return False
        else:
            if self.cbData2.currentText() == 'Number':
                self.cbData1.setStyleSheet(BG_WHITE)
                self.cbData2.setStyleSheet(BG_WHITE)
                return True

            elif self.data1.__class__.__name__ != self.data2.__class__.__name__:
                self.cbData1.setStyleSheet(BG_RED)
                self.cbData2.setStyleSheet(BG_RED)
                print(self.data1.__class__.__name__ != self.data2.__class__.__name__)
                logging.error('Cannot compute data of different dimensions')
                return False

            elif self.data1.__class__.__name__ == 'Data2D' \
                    and (len(self.data2.qx_data) != len(self.data1.qx_data) \
                         or len(self.data2.qy_data) != len(self.data1.qy_data)
                         or not all(i == j for i, j in
                                    zip(self.data1.qx_data, self.data2.qx_data))
                         or not all(i == j for i, j in
                                    zip(self.data1.qy_data, self.data2.qy_data))
            ):
                self.cbData1.setStyleSheet(BG_RED)
                self.cbData2.setStyleSheet(BG_RED)
                logging.error('Cannot compute 2D data of different lengths')
                return False

            else:
                self.cbData1.setStyleSheet(BG_WHITE)
                self.cbData2.setStyleSheet(BG_WHITE)
                return True

    def onCheckOutputName(self):
        """ Check that name of output does not already exist """
        name_to_check = str(self.txtOutputData.text())
        self.txtOutputData.setStyleSheet(BG_WHITE)

        if name_to_check is None or name_to_check == '':
            self.txtOutputData.setStyleSheet(BG_RED)
            logging.warning('No output name')
            return False

        elif name_to_check in self.list_data_items:
            self.txtOutputData.setStyleSheet(BG_RED)
            logging.warning('The Output data name already exists')
            return False

        else:
            self.txtOutputData.setStyleSheet(BG_WHITE)
            return True

    def uniqueOutputName(self):
        """Gets the next unique output name if previous outputs have been saved with default name."""
        output_name = "MyNewDataName1"
        i = 1
        while output_name in self.list_data_items:
            i += 1
            output_name = f"MyNewDataName{str(i)}"
        self.txtOutputData.setText(output_name)
        return output_name

    def resetOutput(self):
        """Resets the output data and output graph upon any change to Data1, Data2, or operator."""
        # plot default for output graph
        self.newPlot(self.graphOutput, self.layoutOutput)
        # reset the output until onCompute is called
        self.output = None
        # sets new default name for output data that doesn't already exist
        self.txtOutputData.setText(self.uniqueOutputName())

    # ########
    # Modification of inputs
    # ########
    def _findId(self, name):
        """ find id of name in list of filenames """
        isinstance(name, str)

        for key_id in list(self.filenames.keys()):
            # data with title
            if self.filenames[key_id].name:
                input = self.filenames[key_id].name
            # data without title
            else:
                input = str(key_id)
            if name in input:
                return key_id

    def _extractData(self, key_id):
        """ Extract data from file with id contained in list of filenames """
        data_complete = self.filenames[key_id]
        return copy.deepcopy(data_complete)

    # ########
    # PLOTS
    # ########
    def newPlot(self, graph, layout):
        """ Create template for graphs with default '?' layout"""
        assert isinstance(graph, QtWidgets.QGraphicsView)
        assert isinstance(layout, QtWidgets.QHBoxLayout)

        # clear layout
        if layout.count() > 0:
            item = layout.takeAt(0)
            layout.removeItem(item)

        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.prepareSubgraphWithData("?"))

        graph.setLayout(layout)

    def operationData1D(self, operation_data, reference_data=None):

        """
        Create instance of PlotterData.Data1D from the operation data for plotting purposes.
        """

        if isinstance(operation_data, float):
            new_operation_data = Data1D(2)
            if isinstance(reference_data, Data1D):
                new_operation_data.copy_from_datainfo(data1d=reference_data)
                new_operation_data.x = np.array([reference_data.x.min(), reference_data.x.max()])
            else:
                new_operation_data.x = np.array([1e-5, 1])
            new_operation_data.y = np.array([operation_data, operation_data])
            new_operation_data.dy = np.zeros(2)
            new_operation_data.dx = np.zeros(2)
        else:
            new_operation_data = Data1D(x=operation_data.x, y=operation_data.y, dy=operation_data.dy, dx=None)
            new_operation_data.copy_from_datainfo(data1d=operation_data)
        return new_operation_data

    def updatePlot(self, graph, layout, data, color=None, operation_data=False):
        """ plot data in graph after clearing its layout """

        assert isinstance(graph, QtWidgets.QGraphicsView)
        assert isinstance(layout, QtWidgets.QHBoxLayout)

        # clear layout
        if layout.count() > 0:
            item = layout.takeAt(0)
            layout.removeItem(item)

        layout.setContentsMargins(0, 0, 0, 0)
        if isinstance(data, Data2D):
            # plot 2D data
            plotter2D = Plotter2DWidget(self, quickplot=True)
            plotter2D.scale = 'linear'
            plotter2D.ax.tick_params(axis='x', labelsize=8)
            plotter2D.ax.tick_params(axis='y', labelsize=8)

            # Draw zero axis lines.
            plotter2D.ax.axhline(linewidth=1)
            plotter2D.ax.axvline(linewidth=1)

            graph.setLayout(layout)
            layout.addWidget(plotter2D)
            # remove x- and ylabels
            plotter2D.y_label = ''
            plotter2D.x_label = ''
            plotter2D.plot(data=data, show_colorbar=False)
            plotter2D.show()

        elif isinstance(data, Data1D):
            # plot 1D data
            plotter = PlotterWidget(self, quickplot=True)
            data.scale = 'linear'
            plotter.showLegend = False
            graph.setLayout(layout)
            layout.addWidget(plotter)

            plotter.ax.tick_params(axis='x', labelsize=8)
            plotter.ax.tick_params(axis='y', labelsize=8)

            # determine color based on the graph for consistency across all graphs
            if color is None:
                if graph.objectName() == 'graphData1':
                    color = DATA1_COLOR
                elif graph.objectName() == 'graphData2':
                    color = DATA2_COLOR
                elif graph.objectName() == 'graphOutput':
                    color = OUTPUT_COLOR

            # if operation data is available, outline the trim points of data1 and data2
            if operation_data and graph.objectName() != 'graphOutput':
                markerfacecolor = TRIMMED_COLOR
                markeredgecolor = color
                alpha = TRIMMED_ALPHA
            else:
                markerfacecolor = None
                markeredgecolor = None
                alpha = None

            if graph.objectName() == 'graphOutput':
                if operation_data:
                    plotter.plot(data=self.operationData1D(self.data1._operation, reference_data=self.data1),
                                 hide_error=True, marker='o', color=DATA1_COLOR,
                                 markerfacecolor=None, markeredgecolor=None)
                    if isinstance(self.data2, float):
                        operation_data = self.operationData1D(self.data2,
                                                              reference_data=self.data1 if isinstance(self.data1,
                                                                                                      Data1D) else None)
                        plotter.plot(data=operation_data, hide_error=True, marker='-', color=DATA2_COLOR)
                    else:
                        operation_data = self.operationData1D(self.data2._operation, reference_data=self.data2)
                        plotter.plot(data=operation_data,
                                     hide_error=True, marker='o', color=DATA2_COLOR,
                                     markerfacecolor=None, markeredgecolor=None)
                plotter.plot(data=data, hide_error=True, marker='o', color=color, markerfacecolor=markerfacecolor,
                             markeredgecolor=markeredgecolor)
            else:
                plotter.plot(data=data, hide_error=True, marker='o', color=color, markerfacecolor=markerfacecolor,
                             markeredgecolor=markeredgecolor, alpha=alpha)
                if graph.objectName() == 'graphData1':
                    plotter.plot(data=self.operationData1D(data._operation, reference_data=data),
                                 hide_error=True, marker='o', color=DATA1_COLOR,
                                 markerfacecolor=None, markeredgecolor=None)
                elif graph.objectName() == 'graphData2':
                    plotter.plot(data=self.operationData1D(data._operation, reference_data=data),
                                 hide_error=True, marker='o', color=DATA2_COLOR,
                                 markerfacecolor=None, markeredgecolor=None)

            plotter.show()

        elif float(data) and self.cbData2.currentText() == 'Number':
            # display value of coefficient (to be applied to Data1)
            # in graphData2 as a line
            plotter = PlotterWidget(self, quickplot=True)
            plotter.showLegend = False
            graph.setLayout(layout)
            layout.addWidget(plotter)

            plotter.ax.tick_params(axis='x', labelsize=8)
            plotter.ax.tick_params(axis='y', labelsize=8)

            operation_data = self.operationData1D(data,
                                                  reference_data=self.data1 if isinstance(self.data1, Data1D) else None)
            plotter.plot(data=operation_data, hide_error=True, marker='-', color=DATA2_COLOR)

            plotter.show()

    def prepareSubgraphWithData(self, data):
        """ Create graphics view containing scene with string """
        scene = QtWidgets.QGraphicsScene()
        scene.addText(str(data))

        subgraph = QtWidgets.QGraphicsView()
        subgraph.setScene(scene)

        return subgraph
