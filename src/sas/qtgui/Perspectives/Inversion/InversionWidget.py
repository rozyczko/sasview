import logging
import numpy as np
import qtpy

from PyQt5 import QtGui, QtCore, QtWidgets

# sas-global
import sas.qtgui.Utilities.GuiUtils as GuiUtils

# pr inversion GUI elements
from .InversionUtils import WIDGETS
from sas.qtgui.Perspectives.Inversion.UI.TabbedInversionUI import Ui_PrInversion
from .InversionLogic import InversionLogic

# pr inversion calculation elements
from sas.sascalc.pr.invertor import Invertor
from sas.qtgui.Plotting.PlotterData import Data1D, Data2D

# Batch calculation display
from sas.qtgui.Utilities.GridPanel import BatchInversionOutputPanel
from ...Plotting.Plotter import Plotter, PlotterWidget
from ...Plotting.Plotter2D import Plotter2D
from ...Plotting.Slicers.SectorSlicer import SectorInteractor


def is_float(value):
    """Converts text input values to floats. Empty strings throw ValueError"""
    try:
        return float(value)
    except ValueError:
        return 0.0


NUMBER_OF_TERMS = 10
REGULARIZATION = 0.0001
BACKGROUND_INPUT = 0.0
MAX_DIST = 140.0

START_POINT = 60
NO_OF_SLICES = 6
NO_OF_QBIN = 20
DICT_KEYS = ["Calculator", "PrPlot", "DataPlot"]

logger = logging.getLogger(__name__)


class InversionWidget(QtWidgets.QWidget, Ui_PrInversion):
    """
    The main window for the P(r) Inversion perspective.
    """

    name = "Inversion"
    ext = "pr"  # Extension used for saving analyse
    estimateSignal = QtCore.pyqtSignal(tuple)
    estimateNTSignal = QtCore.pyqtSignal(tuple)
    estimateDynamicNTSignal = QtCore.pyqtSignal(tuple)
    estimateDynamicSignal = QtCore.pyqtSignal(tuple)
    calculateSignal = QtCore.pyqtSignal(tuple)

    def __init__(self, parent=None, data=None, tab_id=1):
        super(InversionWidget, self).__init__()

        # Necessary globals

        # 2D Data globals #####################
        self.is2D = False
        self.batchData = list()
        self.calculatedData = None
        self.isSlicing = None
        self.startPoint = None
        self.noOfSlices = None
        self.slices = list()  # List to store the slices from 2D data

        self.phi = None  # Start Point
        self.deltaPhi = None  # Number of slicer
        self.qbins = None  # Number of points on plot

        self.active_plots = {}
        self.plot_widget = None
        self.plot2D = Plotter2D(self, quickplot=True)
        self.plot1D = Plotter(quickplot=True)
        self.plotList = None

        ########################################

        # Which tab is this widget displayed in?
        self.tab_id = tab_id

        # data index for the batch set
        self.data_index = 0
        self.tab_name = None

        self.setupUi(self)

        self.setWindowTitle("P(r) Inversion Perspective")

        self._manager = parent
        # Needed for Batch fitting
        self.parent = parent
        self._parent = parent
        self.communicate = self.parent.communicate
        self.communicate.dataDeletedSignal.connect(self.removeData)
        self.batchResults = {}

        self.logic = InversionLogic()

        # Allow Tabs to close
        self._allowClose = True

        # Visible data items
        # current QStandardItem showing on the panel
        self._data = None

        if data is not None:
            self.data = data
            if isinstance(data, list):
                self._data = data[0]

        # Reference to Dmax window for self._data
        self.dmaxWindow = None
        # p(r) calculator for self._data
        self._calculator = Invertor()
        # Default to background estimate
        self._calculator.est_bck = True
        # plots of self._data
        self.prPlot = None
        self.dataPlot = None
        # suggested nTerms
        self.nTermsSuggested = NUMBER_OF_TERMS
        self.maxIndex = 1

        # Calculation threads used by all data items
        self.calcThread = None
        self.estimationThread = None
        self.estimationThreadNT = None
        self.isCalculating = False

        # Mapping for all data items
        # Dictionary mapping data to all parameters
        self._dataList = {}
        self._data = data

        self.dataDeleted = False

        self.model = QtGui.QStandardItemModel(self)
        self.mapper = QtWidgets.QDataWidgetMapper(self)

        # Batch fitting parameters
        self.batchResults = {}
        self.batchComplete = []
        self.isBatch = False
        self.batchResultsWindow = None
        self._allowPlots = True

        # Add validators
        self.setupValidators()
        # Link user interactions with methods
        self.setupLinks()
        # Set values
        self.setupModel()
        # Set up the Widget Map
        self.setupMapper()
        self.setupWindow()
    ######################################################################
    # Base Perspective Class Definitions

    def communicator(self):
        return self.communicate

    def allowBatch(self):
        """
        Allows Pr Interface to accept multiple datasets for batch processing
        """
        return True

    def allowSwap(self):
        """
        Tell the caller we don't accept swapping data
        """
        return False

    def setClosable(self, value=True):
        """
        Allow outsiders close this widget
        """
        assert isinstance(value, bool)
        self._allowClose = value

    def setPlotable(self, value=True):
        """
        Let Plots to be displayable - needed so batch mode is not clutter with plots
        """
        assert isinstance(value, bool)
        self._allowPlots = value

    def isClosable(self):
        """
        Allow outsiders close this widget
        """
        return self._allowClose

    def isSerializable(self):
        """
        Tell the caller that this perspective writes its state
        """
        return True

    def closeEvent(self, event):
        """
        Overwrite QDialog close method to allow for custom widget close
        """
        # Close report widgets before closing/minimizing main widget
        self.closeDMax()
        self.closeBatchResults()
        if self._allowClose:
            # reset the closability flag
            self.setClosable(value=False)
            # Tell the MdiArea to close the container if it is visible
            if self.parentWidget():
                self.parentWidget().close()
            event.accept()
        else:
            event.ignore()
            # Maybe we should just minimize
            self.setWindowState(QtCore.Qt.WindowMinimized)

    def closeDMax(self):
        if self.dmaxWindow is not None:
            self.dmaxWindow.close()

    def closeBatchResults(self):
        if self.batchResultsWindow is not None:
            self.batchResultsWindow.close()

    ######################################################################
    # Initialization routines

    def setupLinks(self):
        """Connect the use controls to their appropriate methods"""
        self.dataList.currentIndexChanged.connect(self.displayChange)
        self.calculateAllButton.clicked.connect(self.startThreadAll)
        self.calculateThisButton.clicked.connect(self.startThread)
        self.stopButton.clicked.connect(self.stopCalculation)
        self.removeButton.clicked.connect(self.removeData)
        self.showResultsButton.clicked.connect(self.showBatchOutput)
        self.sliceButton.clicked.connect(self.slice)
        self.helpButton.clicked.connect(self.help)
        self.estimateBgd.toggled.connect(self.toggleBgd)
        self.manualBgd.toggled.connect(self.toggleBgd)
        self.regConstantSuggestionButton.clicked.connect(self.acceptAlpha)
        self.noOfTermsSuggestionButton.clicked.connect(self.acceptNoTerms)
        self.explorerButton.clicked.connect(self.openExplorerWindow)

        self.backgroundInput.textChanged.connect(
            lambda: self.set_background(self.backgroundInput.text()))
        self.regularizationConstantInput.textChanged.connect(
            lambda: self._calculator.set_alpha(is_float(self.regularizationConstantInput.text())))
        self.maxDistanceInput.textChanged.connect(
            lambda: self._calculator.set_dmax(is_float(self.maxDistanceInput.text())))
        self.maxQInput.editingFinished.connect(self.check_q_high)
        self.minQInput.editingFinished.connect(self.check_q_low)
        self.slitHeightInput.textChanged.connect(
            lambda: self._calculator.set_slit_height(is_float(self.slitHeightInput.text())))
        self.slitWidthInput.textChanged.connect(
            lambda: self._calculator.set_slit_width(is_float(self.slitWidthInput.text())))

        self.model.itemChanged.connect(self.model_changed)
        self.estimateNTSignal.connect(self._estimateNTUpdate)
        self.estimateDynamicNTSignal.connect(self._estimateDynamicNTUpdate)
        self.estimateDynamicSignal.connect(self._estimateDynamicUpdate)
        self.estimateSignal.connect(self._estimateUpdate)
        self.calculateSignal.connect(self._calculateUpdate)

        self.maxDistanceInput.textEdited.connect(self.performEstimateDynamic)

    def setupMapper(self):
        # Set up the mapper.
        self.mapper.setOrientation(QtCore.Qt.Vertical)
        self.mapper.setModel(self.model)

        # Filename
        self.mapper.addMapping(self.dataList, WIDGETS.W_FILENAME)
        # Background
        self.mapper.addMapping(self.backgroundInput, WIDGETS.W_BACKGROUND_INPUT)
        self.mapper.addMapping(self.estimateBgd, WIDGETS.W_ESTIMATE)
        self.mapper.addMapping(self.manualBgd, WIDGETS.W_MANUAL_INPUT)

        # Qmin/Qmax
        self.mapper.addMapping(self.minQInput, WIDGETS.W_QMIN)
        self.mapper.addMapping(self.maxQInput, WIDGETS.W_QMAX)

        # Slit Parameter items
        self.mapper.addMapping(self.slitWidthInput, WIDGETS.W_SLIT_WIDTH)
        self.mapper.addMapping(self.slitHeightInput, WIDGETS.W_SLIT_HEIGHT)

        # Parameter Items
        self.mapper.addMapping(self.regularizationConstantInput, WIDGETS.W_REGULARIZATION)
        self.mapper.addMapping(self.regConstantSuggestionButton, WIDGETS.W_REGULARIZATION_SUGGEST)
        self.mapper.addMapping(self.explorerButton, WIDGETS.W_EXPLORE)
        self.mapper.addMapping(self.maxDistanceInput, WIDGETS.W_MAX_DIST)
        self.mapper.addMapping(self.noOfTermsInput, WIDGETS.W_NO_TERMS)
        self.mapper.addMapping(self.noOfTermsSuggestionButton, WIDGETS.W_NO_TERMS_SUGGEST)

        # Output
        self.mapper.addMapping(self.rgValue, WIDGETS.W_RG)
        self.mapper.addMapping(self.iQ0Value, WIDGETS.W_I_ZERO)
        self.mapper.addMapping(self.backgroundValue, WIDGETS.W_BACKGROUND_OUTPUT)
        self.mapper.addMapping(self.computationTimeValue, WIDGETS.W_COMP_TIME)
        self.mapper.addMapping(self.chiDofValue, WIDGETS.W_CHI_SQUARED)
        self.mapper.addMapping(self.oscillationValue, WIDGETS.W_OSCILLATION)
        self.mapper.addMapping(self.posFractionValue, WIDGETS.W_POS_FRACTION)
        self.mapper.addMapping(self.sigmaPosFractionValue, WIDGETS.W_SIGMA_POS_FRACTION)

        # Main Buttons
        self.mapper.addMapping(self.removeButton, WIDGETS.W_REMOVE)
        self.mapper.addMapping(self.calculateAllButton, WIDGETS.W_CALCULATE_ALL)
        self.mapper.addMapping(self.calculateThisButton, WIDGETS.W_CALCULATE_VISIBLE)
        self.mapper.addMapping(self.showResultsButton, WIDGETS.W_CALCULATE_VISIBLE)
        self.mapper.addMapping(self.helpButton, WIDGETS.W_HELP)

        self.mapper.toFirst()

    def setupModel(self):
        """
        Update boxes with initial values
        """
        bgd_item = QtGui.QStandardItem(str(BACKGROUND_INPUT))
        self.model.setItem(WIDGETS.W_BACKGROUND_INPUT, bgd_item)
        blank_item = QtGui.QStandardItem("")
        self.model.setItem(WIDGETS.W_QMIN, blank_item)
        blank_item = QtGui.QStandardItem("")
        self.model.setItem(WIDGETS.W_QMAX, blank_item)
        blank_item = QtGui.QStandardItem("")
        self.model.setItem(WIDGETS.W_SLIT_WIDTH, blank_item)
        blank_item = QtGui.QStandardItem("")
        self.model.setItem(WIDGETS.W_SLIT_HEIGHT, blank_item)
        no_terms_item = QtGui.QStandardItem(str(NUMBER_OF_TERMS))
        self.model.setItem(WIDGETS.W_NO_TERMS, no_terms_item)
        reg_item = QtGui.QStandardItem(str(REGULARIZATION))
        self.model.setItem(WIDGETS.W_REGULARIZATION, reg_item)
        max_dist_item = QtGui.QStandardItem(str(MAX_DIST))
        self.model.setItem(WIDGETS.W_MAX_DIST, max_dist_item)
        blank_item = QtGui.QStandardItem("")
        self.model.setItem(WIDGETS.W_RG, blank_item)
        blank_item = QtGui.QStandardItem("")
        self.model.setItem(WIDGETS.W_I_ZERO, blank_item)
        bgd_item = QtGui.QStandardItem(str(BACKGROUND_INPUT))
        self.model.setItem(WIDGETS.W_BACKGROUND_OUTPUT, bgd_item)
        blank_item = QtGui.QStandardItem("")
        self.model.setItem(WIDGETS.W_COMP_TIME, blank_item)
        blank_item = QtGui.QStandardItem("")
        self.model.setItem(WIDGETS.W_CHI_SQUARED, blank_item)
        blank_item = QtGui.QStandardItem("")
        self.model.setItem(WIDGETS.W_OSCILLATION, blank_item)
        blank_item = QtGui.QStandardItem("")
        self.model.setItem(WIDGETS.W_POS_FRACTION, blank_item)
        blank_item = QtGui.QStandardItem("")
        self.model.setItem(WIDGETS.W_SIGMA_POS_FRACTION, blank_item)

    def setupWindow(self):
        """Initialize base window state on init"""
        self.enableButtons()
        self.estimateBgd.setChecked(True)

    def setupValidators(self):
        """Apply validators to editable line edits"""
        self.noOfTermsInput.setValidator(QtGui.QIntValidator())
        self.regularizationConstantInput.setValidator(GuiUtils.DoubleValidator())
        self.maxDistanceInput.setValidator(GuiUtils.DoubleValidator())
        self.minQInput.setValidator(GuiUtils.DoubleValidator())
        self.maxQInput.setValidator(GuiUtils.DoubleValidator())
        self.slitHeightInput.setValidator(GuiUtils.DoubleValidator())
        self.slitWidthInput.setValidator(GuiUtils.DoubleValidator())

    ######################################################################
    # Methods for updating GUI

    def enableButtons(self):
        """
        Enable buttons when data is present, else disable them
        """
        self.calculateAllButton.setEnabled(not self.isCalculating)
        self.calculateThisButton.setEnabled(self.logic.data_is_loaded
                                            and not self.isBatch
                                            and not self.isCalculating)
        self.showResultsButton.setEnabled(self.logic.data_is_loaded
                                          and not self.isBatch
                                          and not self.isCalculating)
        self.sliceButton.setEnabled(not self.isSlicing)
        self.sliceButton.setVisible(self.logic.data_is_loaded and self.is2D)
        self.removeButton.setEnabled(self.logic.data_is_loaded and not self.isCalculating)
        self.explorerButton.setEnabled(self.logic.data_is_loaded and not self.isCalculating)
        self.stopButton.setVisible(self.isCalculating)
        self.regConstantSuggestionButton.setEnabled(self.logic.data_is_loaded and not self.isCalculating)
        self.noOfTermsSuggestionButton.setEnabled(self.logic.data_is_loaded and not self.isCalculating)

    def populateDataComboBox(self, name, data_ref):
        """
        Append a new name to the data combobox
        :param name: data name
        :param data_ref: QStandardItem reference for data set to be added
        """
        self.dataList.addItem(name, data_ref)

    def acceptNoTerms(self):
        """Send estimated no of terms to input"""
        self.model.setItem(WIDGETS.W_NO_TERMS, QtGui.QStandardItem(
            self.noOfTermsSuggestionButton.text()))

    def acceptAlpha(self):
        """Send estimated alpha to input"""
        self.model.setItem(WIDGETS.W_REGULARIZATION, QtGui.QStandardItem(
            self.regConstantSuggestionButton.text()))

    def displayChange(self, data_index):
        """Switch to another item in the data list"""
        if self.dataDeleted:
            return
        self.updateDataList(self._data)
        self.setCurrentData(self.dataList.itemData(data_index))

    ######################################################################
    # GUI Interaction Events

    def updateCalculator(self):
        """Update all p(r) params"""
        self._calculator.set_x(self.logic.data.x)
        self._calculator.set_y(self.logic.data.y)
        self._calculator.set_err(self.logic.data.dy)
        self.set_background(self.backgroundInput.text())

    def set_background(self, value):
        self._calculator.background = float(value)

    def model_changed(self):
        """Update the values when user makes changes"""
        if not self.mapper:
            msg = "Unable to update P{r}. The connection between the main GUI "
            msg += "and P(r) was severed. Attempting to restart P(r)."
            logger.warning(msg)
            self.setClosable(True)
            self.close()
            InversionWidget.__init__(self.parent(), list(self._dataList.keys()))
            exit(0)
        if self.dmaxWindow is not None:
            self.dmaxWindow.nfunc = self.getNFunc()
            self.dmaxWindow.pr_state = self._calculator
        self.mapper.toLast()

    def help(self):
        """
        Open the P(r) Inversion help browser
        """
        tree_location = "/user/qtgui/Perspectives/Inversion/pr_help.html"

        # Actual file anchor will depend on the combo box index
        # Note that we can be clusmy here, since bad current_fitter_id
        # will just make the page displayed from the top
        self._manager.showHelp(tree_location)

    def toggleBgd(self):
        """
        Toggle the background between manual and estimated
        """
        self.model.blockSignals(True)
        value = 1 if self.estimateBgd.isChecked() else 0
        itemt = QtGui.QStandardItem(str(value == 1).lower())
        self.model.setItem(WIDGETS.W_ESTIMATE, itemt)
        itemt = QtGui.QStandardItem(str(value == 0).lower())
        self.model.setItem(WIDGETS.W_MANUAL_INPUT, itemt)
        self._calculator.set_est_bck(value)
        self.backgroundInput.setEnabled(self._calculator.est_bck == 0)
        self.model.blockSignals(False)

    def openExplorerWindow(self):
        """
        Open the Explorer window to see correlations between params and results
        """
        from .DMaxExplorerWidget import DmaxWindow
        self.dmaxWindow = DmaxWindow(pr_state=self._calculator,
                                     nfunc=self.getNFunc(),
                                     parent=self)
        self.dmaxWindow.show()

    def showBatchOutput(self):
        """
        Display the batch output in tabular form
        :param output_data: Dictionary mapping name -> P(r) instance
        """
        # for i in range(self.dataList.count()):
        #     self.setCurrentData(self.dataList.itemData(i))
        #     self.batchResults[self.logic.data.name] = self._dataList[self.dataList.itemData(i)].get(DICT_KEYS[0])
        #     print(self._dataList[self.dataList.itemData(i)].get(DICT_KEYS[0]))


        self.batchResultsWindow = BatchInversionOutputPanel(parent=self, output_data=self.batchResults)
        self.batchResultsWindow.setupTable(self.batchResults)
        self.batchResultsWindow.show()

    def stopCalculation(self):
        """ Stop all threads, return to the base state and update GUI """
        self.stopCalcThread()
        self.stopEstimationThread()
        self.stopEstimateNTThread()
        # Show any batch calculations that successfully completed
        if self.isBatch and self.batchResultsWindow is not None:
            self.showBatchOutput()
        self.isBatch = False
        self.isCalculating = False
        self.updateGuiValues()

    def check_q_low(self, q_value=None):
        """ Validate the low q value """
        if not q_value:
            q_value = float(self.minQInput.text()) if self.minQInput.text() else '0.0'
        q_min = min(self._calculator.x) if any(self._calculator.x) else -1 * np.inf
        q_max = self._calculator.get_qmax() if self._calculator.get_qmax() is not None else np.inf
        if q_value > q_max:
            # Value too high - coerce to max q
            self.model.setItem(WIDGETS.W_QMIN, QtGui.QStandardItem("{:.4g}".format(q_max)))
        elif q_value < q_min:
            # Value too low - coerce to min q
            self.model.setItem(WIDGETS.W_QMIN, QtGui.QStandardItem("{:.4g}".format(q_min)))
        else:
            # Valid Q - set model item
            self.model.setItem(WIDGETS.W_QMIN, QtGui.QStandardItem("{:.4g}".format(q_value)))
            self._calculator.set_qmin(q_value)

    def check_q_high(self, q_value=None):
        """ Validate the value of high q sent by the slider """
        if not q_value:
            q_value = float(self.maxQInput.text()) if self.maxQInput.text() else '1.0'
        q_max = max(self._calculator.x) if any(self._calculator.x) else np.inf
        q_min = self._calculator.get_qmin() if self._calculator.get_qmin() is not None else -1 * np.inf
        if q_value > q_max:
            # Value too high - coerce to max q
            self.model.setItem(WIDGETS.W_QMAX, QtGui.QStandardItem("{:.4g}".format(q_max)))
        elif q_value < q_min:
            # Value too low - coerce to min q
            self.model.setItem(WIDGETS.W_QMAX, QtGui.QStandardItem("{:.4g}".format(q_min)))
        else:
            # Valid Q - set model item
            self.model.setItem(WIDGETS.W_QMAX, QtGui.QStandardItem("{:.4g}".format(q_value)))
            self._calculator.set_qmax(q_value)

    ######################################################################
    # Response Actions

    def updateDataList(self, dataRef):
        """Save the current data state of the window into self._data_list"""
        if dataRef is None:
            return
        self._dataList[dataRef] = {
            DICT_KEYS[0]: self._calculator,
            DICT_KEYS[1]: self.prPlot,
            DICT_KEYS[2]: self.dataPlot
        }

    def getState(self):
        """
        Collects all active params into a dictionary of {name: value}
        :return: {name: value}
        """
        # If no measurement performed, calculate using base params
        if self.chiDofValue.text() == '':
            self._calculator.out, self._calculator.cov = self._calculator.invert()
        return {
            'alpha': self._calculator.alpha,
            'background': self._calculator.background,
            'chi2': self._calculator.chi2,
            'cov': self._calculator.cov,
            'd_max': self._calculator.d_max,
            'elapsed': self._calculator.elapsed,
            'err': self._calculator.err,
            'est_bck': self._calculator.est_bck,
            'iq0': self._calculator.iq0(self._calculator.out),
            'nerr': self._calculator.nerr,
            'nfunc': self.getNFunc(),
            'npoints': self._calculator.npoints,
            'ny': self._calculator.ny,
            'out': self._calculator.out,
            'oscillations': self._calculator.oscillations(self._calculator.out),
            'pos_frac': self._calculator.get_positive(self._calculator.out),
            'pos_err': self._calculator.get_pos_err(self._calculator.out,
                                                    self._calculator.cov),
            'q_max': self._calculator.q_max,
            'q_min': self._calculator.q_min,
            'rg': self._calculator.rg(self._calculator.out),
            'slit_height': self._calculator.slit_height,
            'slit_width': self._calculator.slit_width,
            'suggested_alpha': self._calculator.suggested_alpha,
            'x': self._calculator.x,
            'y': self._calculator.y,
        }

    def getNFunc(self):
        """Get the n_func value from the GUI object"""
        try:
            nfunc = int(self.noOfTermsInput.text())
        except ValueError:
            logger.error("Incorrect number of terms specified: %s" % self.noOfTermsInput.text())
            self.noOfTermsInput.setText(str(NUMBER_OF_TERMS))
            nfunc = NUMBER_OF_TERMS
        return nfunc

    def setCurrentData(self, data_ref):
        """Get the data by reference and display as necessary"""
        if data_ref is None:
            return
        if not isinstance(data_ref, QtGui.QStandardItem):
            msg = "Incorrect type passed to the P(r) Perspective"
            raise AttributeError(msg)
        # Data references
        self._data = data_ref
        self.logic.data = GuiUtils.dataFromItem(data_ref)
        self._calculator = self._dataList[data_ref].get(DICT_KEYS[0])
        self.prPlot = self._dataList[data_ref].get(DICT_KEYS[1])
        self.dataPlot = self._dataList[data_ref].get(DICT_KEYS[2])
        self.performEstimate()

    def updateDynamicGuiValues(self):
        pr = self._calculator
        alpha = self._calculator.suggested_alpha
        self.model.setItem(WIDGETS.W_MAX_DIST,
                            QtGui.QStandardItem("{:.4g}".format(pr.get_dmax())))
        self.regConstantSuggestionButton.setText("{:-3.2g}".format(alpha))
        self.noOfTermsSuggestionButton.setText(
             "{:n}".format(self.nTermsSuggested))

        self.enableButtons()

    def updateGuiValues(self):
        pr = self._calculator
        out = self._calculator.out
        cov = self._calculator.cov
        elapsed = self._calculator.elapsed
        alpha = self._calculator.suggested_alpha
        self.check_q_high(pr.get_qmax())
        self.check_q_low(pr.get_qmin())
        self.model.setItem(WIDGETS.W_BACKGROUND_INPUT,
                           QtGui.QStandardItem("{:.3g}".format(pr.background)))
        self.model.setItem(WIDGETS.W_BACKGROUND_OUTPUT,
                           QtGui.QStandardItem("{:.3g}".format(pr.background)))
        self.model.setItem(WIDGETS.W_COMP_TIME,
                           QtGui.QStandardItem("{:.4g}".format(elapsed)))
        self.model.setItem(WIDGETS.W_MAX_DIST,
                           QtGui.QStandardItem("{:.4g}".format(pr.get_dmax())))
        self.regConstantSuggestionButton.setText("{:.2g}".format(alpha))

        if isinstance(pr.chi2, np.ndarray):
            self.model.setItem(WIDGETS.W_CHI_SQUARED,
                               QtGui.QStandardItem("{:.3g}".format(pr.chi2[0])))
        if out is not None:
            self.model.setItem(WIDGETS.W_RG,
                               QtGui.QStandardItem("{:.3g}".format(pr.rg(out))))
            self.model.setItem(WIDGETS.W_I_ZERO,
                               QtGui.QStandardItem(
                                   "{:.3g}".format(pr.iq0(out))))
            self.model.setItem(WIDGETS.W_OSCILLATION, QtGui.QStandardItem(
                "{:.3g}".format(pr.oscillations(out))))
            self.model.setItem(WIDGETS.W_POS_FRACTION, QtGui.QStandardItem(
                "{:.3g}".format(pr.get_positive(out))))
            if cov is not None:
                self.model.setItem(WIDGETS.W_SIGMA_POS_FRACTION,
                                   QtGui.QStandardItem(
                                       "{:.3g}".format(
                                           pr.get_pos_err(out, cov))))
        if self.prPlot is not None:
            title = self.prPlot.name
            self.prPlot.plot_role = Data1D.ROLE_RESIDUAL
            GuiUtils.updateModelItemWithPlot(self._data, self.prPlot, title)
            self.communicate.plotRequestedSignal.emit([self._data,self.prPlot], None)
        if self.dataPlot is not None:
            title = self.dataPlot.name
            self.dataPlot.plot_role = Data1D.ROLE_DEFAULT
            self.dataPlot.symbol = "Line"
            self.dataPlot.show_errors = False
            GuiUtils.updateModelItemWithPlot(self._data, self.dataPlot, title)
            self.communicate.plotRequestedSignal.emit([self._data,self.dataPlot], None)
        self.enableButtons()

    def removeData(self, data_list=None):
        """Remove the existing data reference from the P(r) Persepective"""
        self.dataDeleted = True
        self.batchResults = {}
        if not data_list:
            data_list = [self._data]
        self.closeDMax()
        for data in data_list:
            self._dataList.pop(data, None)
        if self.dataPlot:
            # Reset dataplot sliders
            self.dataPlot.slider_low_q_input = []
            self.dataPlot.slider_high_q_input = []
            self.dataPlot.slider_low_q_setter = []
            self.dataPlot.slider_high_q_setter = []
        self._data = None
        length = len(self.dataList)
        for index in reversed(range(length)):
            if self.dataList.itemData(index) in data_list:
                self.dataList.removeItem(index)
        # Last file removed
        self.dataDeleted = False
        if len(self._dataList) == 0:
            self.prPlot = None
            self.dataPlot = None
            self.logic.data = None
            self._calculator = Invertor()
            self.closeBatchResults()
            self.nTermsSuggested = NUMBER_OF_TERMS
            self.noOfTermsSuggestionButton.setText("{:n}".format(
                self.nTermsSuggested))
            self.regConstantSuggestionButton.setText("{:-3.2g}".format(
                REGULARIZATION))
            self.updateGuiValues()
            self.setupModel()
        else:
            self.dataList.setCurrentIndex(0)
            self.updateGuiValues()

    def serializeAll(self):
        """
        Serialize the inversion state so data can be saved
        Inversion is not batch-ready so this will only effect a single page
        :return: {data-id: {self.name: {inversion-state}}}
        """
        return self.serializeCurrentPage()

    def serializeCurrentPage(self):
        # Serialize and return a dictionary of {data_id: inversion-state}
        # Return original dictionary if no data
        state = {}
        if self.logic.data_is_loaded:
            tab_data = self.getPage()
            data_id = tab_data.pop('data_id', '')
            state[data_id] = {'pr_params': tab_data}
        return state

    def getPage(self):
        """
        serializes full state of this fit page
        """
        # Get all parameters from page
        param_dict = self.getState()
        param_dict['data_name'] = str(self.logic.data.name)
        param_dict['data_id'] = str(self.logic.data.id)
        return param_dict

    def currentTabDataId(self):
        """
        Returns the data ID of the current tab
        """
        tab_id = []
        if self.logic.data_is_loaded:
            tab_id.append(str(self.logic.data.id))
        return tab_id

    def updateFromParameters(self, params):
        self._calculator.q_max = params['q_max']
        self.check_q_high(self._calculator.get_qmax())
        self._calculator.q_min = params['q_min']
        self.check_q_low(self._calculator.get_qmin())
        self._calculator.alpha = params['alpha']
        self._calculator.suggested_alpha = params['suggested_alpha']
        self._calculator.d_max = params['d_max']
        self._calculator.nfunc = params['nfunc']
        self.nTermsSuggested = self._calculator.nfunc
        self.updateDynamicGuiValues()
        self.acceptAlpha()
        self.acceptNoTerms()
        self._calculator.background = params['background']
        self._calculator.chi2 = params['chi2']
        self._calculator.cov = params['cov']
        self._calculator.elapsed = params['elapsed']
        self._calculator.err = params['err']
        self._calculator.set_est_bck = bool(params['est_bck'])
        self._calculator.nerr = params['nerr']
        self._calculator.npoints = params['npoints']
        self._calculator.ny = params['ny']
        self._calculator.out = params['out']
        self._calculator.slit_height = params['slit_height']
        self._calculator.slit_width = params['slit_width']
        self._calculator.x = params['x']
        self._calculator.y = params['y']
        self.updateGuiValues()
        self.updateDynamicGuiValues()

    ######################################################################
    # Thread Creators

    def startThreadAll(self):
        self.isCalculating = True
        self.isBatch = True
        self.batchComplete = []
        self.calculateAllButton.setText("Calculating...")
        self.enableButtons()
        self.performEstimate()

    def startNextBatchItem(self):
        self.isBatch = False
        print(self.dataList.count())
        for index in range(self.dataList.count()):
            if index not in self.batchComplete:
                self.dataList.setCurrentIndex(index)
                self.isBatch = True
                # Add the index before calculating in case calculation fails
                self.batchComplete.append(index)
                break
        if self.isBatch:
            self.performEstimate()
        else:
            # If no data sets left, end batch calculation
            self.isCalculating = False
            self.batchComplete = []
            self.calculateAllButton.setText("Calculate All")
            self.enableButtons()
            if self.batchResultsWindow is not None and not self.batchResults:
                self.showBatchOutput()

    def startThread(self):
        """
            Start a calculation thread
        """
        from .Thread import CalcPr

        # Set data before running the calculations
        self.isCalculating = True
        self.enableButtons()
        self.updateCalculator()
        # Disable calculation buttons to prevent thread interference

        # If the thread is already started, stop it
        self.stopCalcThread()

        pr = self._calculator.clone()
        # Making sure that nfunc and alpha parameters are correctly initialized
        pr.suggested_alpha = self._calculator.alpha
        self.calcThread = CalcPr(pr, self.nTermsSuggested,
                                 error_func=self._threadError,
                                 completefn=self._calculateCompleted,
                                 updatefn=None)
        self.calcThread.queue()
        self.calcThread.ready(2.5)


    def stopCalcThread(self):
        """ Stops a thread if it exists and is running """
        if self.calcThread is not None and self.calcThread.isrunning():
            self.calcThread.stop()

    def performEstimateNT(self):
        """
        Perform parameter estimation
        """
        from .Thread import EstimateNT

        self.updateCalculator()

        # If a thread is already started, stop it
        self.stopEstimateNTThread()

        pr = self._calculator.clone()
        # Skip the slit settings for the estimation
        # It slows down the application and it doesn't change the estimates
        pr.slit_height = 0.0
        pr.slit_width = 0.0
        nfunc = self.getNFunc()

        self.estimationThreadNT = EstimateNT(pr, nfunc,
                                             error_func=self._threadError,
                                             completefn=self._estimateNTCompleted,
                                             updatefn=None)
        self.estimationThreadNT.queue()
        self.estimationThreadNT.ready(2.5)

    def performEstimateDynamicNT(self):
        """
        Perform parameter estimation
        """
        from .Thread import EstimateNT

        self.updateCalculator()

        # If a thread is already started, stop it
        self.stopEstimateNTThread()

        pr = self._calculator.clone()
        # Skip the slit settings for the estimation
        # It slows down the application and it doesn't change the estimates
        pr.slit_height = 0.0
        pr.slit_width = 0.0
        nfunc = 10 # change this to get the no of terms onky once using "nfunc = self.getNFunc()" gets messy with batch as it uses the vaues of the brevous calculation


        self.estimationThreadNT = EstimateNT(pr, nfunc,
                                             error_func=self._threadError,
                                             completefn=self._estimateDynamicNTCompleted,
                                             updatefn=None)
        self.estimationThreadNT.queue()
        self.estimationThreadNT.ready(2.5)

    def stopEstimateNTThread(self):
        if (self.estimationThreadNT is not None and
                self.estimationThreadNT.isrunning()):
            self.estimationThreadNT.stop()

    def performEstimate(self):
        """
            Perform parameter estimation
        """
        from .Thread import EstimatePr

        # If a thread is already started, stop it
        self.stopEstimationThread()

        self.estimationThread = EstimatePr(self._calculator.clone(),
                                           self.getNFunc(),
                                           error_func=self._threadError,
                                           completefn=self._estimateCompleted,
                                           updatefn=None)
        self.estimationThread.queue()
        self.estimationThread.ready(2.5)

    def performEstimateDynamic(self):
        """
            Perform parameter estimation
        """
        from .Thread import EstimatePr

        # If a thread is already started, stop it
        self.stopEstimationThread()

        self.estimationThread = EstimatePr(self._calculator.clone(),
                                           self.getNFunc(),
                                           error_func=self._threadError,
                                           completefn=self._estimateDynamicCompleted,
                                           updatefn=None)
        self.estimationThread.queue()
        self.estimationThread.ready(2.5)

    def stopEstimationThread(self):
        """ Stop the estimation thread if it exists and is running """
        if (self.estimationThread is not None and
                self.estimationThread.isrunning()):
            self.estimationThread.stop()

    ######################################################################
    # Thread Complete

    def _estimateCompleted(self, alpha, message, elapsed):
        ''' Send a signal to the main thread for model update'''
        self.estimateSignal.emit((alpha, message, elapsed))

    def _estimateDynamicCompleted(self, alpha, message, elapsed):
        ''' Send a signal to the main thread for model update'''
        self.estimateDynamicSignal.emit((alpha, message, elapsed))

    def _estimateUpdate(self, output_tuple):
        """
        Parameter estimation completed,
        display the results to the user

        :param alpha: estimated best alpha
        :param elapsed: computation time
        """
        alpha, message, elapsed = output_tuple
        self._calculator.alpha = alpha
        self._calculator.elapsed += self._calculator.elapsed
        if message:
            logger.info(message)
        self.performEstimateNT()
        self.performEstimateDynamicNT()

    def _estimateDynamicUpdate(self, output_tuple):
        """
        Parameter estimation completed,
        display the results to the user

        :param alpha: estimated best alpha
        :param elapsed: computation time
        """
        alpha, message, elapsed = output_tuple
        self._calculator.alpha = alpha
        self._calculator.elapsed += self._calculator.elapsed
        if message:
            logger.info(message)
        self.performEstimateDynamicNT()

    def _estimateNTCompleted(self, nterms, alpha, message, elapsed):
        ''' Send a signal to the main thread for model update'''
        self.estimateNTSignal.emit((nterms, alpha, message, elapsed))

    def _estimateDynamicNTCompleted(self, nterms, alpha, message, elapsed):
        ''' Send a signal to the main thread for model update'''
        self.estimateDynamicNTSignal.emit((nterms, alpha, message, elapsed))

    def _estimateNTUpdate(self, output_tuple):
        """
        Parameter estimation completed,
        display the results to the user

        :param alpha: estimated best alpha
        :param nterms: estimated number of terms
        :param elapsed: computation time
        """
        nterms, alpha, message, elapsed = output_tuple
        self._calculator.elapsed += elapsed
        self._calculator.suggested_alpha = alpha
        self.nTermsSuggested = nterms
        # Save useful info
        self.updateGuiValues()
        if message:
            logger.info(message)
        if self.isBatch:
            self.acceptAlpha()
            self.acceptNoTerms()
            self.startThread()

    def _estimateDynamicNTUpdate(self, output_tuple):
        """
        Parameter estimation completed,
        display the results to the user

        :param alpha: estimated best alpha
        :param nterms: estimated number of terms
        :param elapsed: computation time
        """
        nterms, alpha, message, elapsed = output_tuple
        self._calculator.elapsed += elapsed
        self._calculator.suggested_alpha = alpha
        self.nTermsSuggested = nterms
        # Save useful info
        self.updateDynamicGuiValues()
        if message:
            logger.info(message)
        if self.isBatch:
            self.acceptAlpha()
            self.acceptNoTerms()
            self.startThread()

    def _calculateCompleted(self, out, cov, pr, elapsed):
        ''' Send a signal to the main thread for model update'''
        self.calculateSignal.emit((out, cov, pr, elapsed))

    def _calculateUpdate(self, output_tuple):
        """
        Method called with the results when the inversion is done

        :param out: output coefficient for the base functions
        :param cov: covariance matrix
        :param pr: Invertor instance
        :param elapsed: time spent computing
        """
        out, cov, pr, elapsed = output_tuple
        # Save useful info
        cov = np.ascontiguousarray(cov)
        pr.cov = cov
        pr.out = out
        pr.elapsed = elapsed

        # Save Pr invertor
        self._calculator = pr

        # Update P(r) and fit plots
        # do not show/update plot if batch (Clutters and slows down interface)
        if self._allowPlots:
            self.prPlot = self.logic.newPRPlot(out, self._calculator, cov)
            self.prPlot.show_yzero = True
            self.prPlot.filename = self.logic.data.filename
            self.dataPlot = self.logic.new1DPlot(out, self._calculator)
            self.dataPlot.filename = self.logic.data.filename

            self.dataPlot.show_q_range_sliders = True
            self.dataPlot.slider_update_on_move = False
            self.dataPlot.slider_perspective_name = "Inversion"
            self.dataPlot.slider_low_q_input = ['minQInput']
            self.dataPlot.slider_low_q_setter = ['check_q_low']
            self.dataPlot.slider_high_q_input = ['maxQInput']
            self.dataPlot.slider_high_q_setter = ['check_q_high']

        # Udpate internals and GUI
        self.updateDataList(self._data)
        if self.isBatch:
            self.startNextBatchItem()
        else:
            self.isCalculating = False
        self.updateGuiValues()

    def _threadError(self, error):
        """
            Call-back method for calculation errors
        """
        logger.error(error)
        if self.isBatch:
            self.startNextBatchItem()
        else:
            self.stopCalculation()

    #####################
    # comment the following code

    def slice(self):
        self.sliceButton.setText("Slicing...")
        self.isSlicing = True
        self.enableButtons()

        slicedData = self.muiltiSlicer()
        self.updateSlicerParams()

        self.sliceList.setHorizontalHeaderLabels(["title", "phi"])
        self.sliceList.setColumnCount(2)
        self.sliceList.setRowCount(self.noOfSlices)

        for row, slice in enumerate(slicedData):
            self.plot1D.plot(slice)
            # self.removeData()
            self.plot1D.show()
            plotButton = QtWidgets.QPushButton(str(slice.phi))
            self.sliceList.setItem(row, 0, QtWidgets.QTableWidgetItem(slice.title))
            self.sliceList.setCellWidget(row, 1, plotButton)
            # self.logic.data = Data1D(x=slice.x, y=slice.y, dx=slice.dx, dy=slice.dy)
            # self.calculator = Invertor()
            # self.slices.append(slice.data)
            self.logic.data = Data1D(x=slice.x, y=slice.y, dx=slice.dx, dy=slice.dy)
            self._calculator = Invertor()
            self._calculator.out = slice.phi
            self.batchResults[slice.phi] = self._calculator
            print("Calculating Pr of Phi {}".format(slice.phi))
        self.calculateAllButton.setVisible(True)
        self.dataList.removeItem(0)

        self.plot2D.update()
        self.sliceList.resizeColumnsToContents()
        self.sliceList.resizeRowsToContents()
        self.sliceButton.setText("Slice")
        self.sliceList.show()
        self.batchResultsWindow = BatchInversionOutputPanel(parent=self, output_data=self.batchResults)
        self.batchResultsWindow.setupTable(self.batchResults)
        self.batchResultsWindow.show()
        self.enableButtons()
        self.calculateThisButton.setEnabled(True)
        self.showResultsButton.setVisible(True)

    def set_tab_name(self, name=None):
        # set name to "New Pr Tab" if no name is set to the data set
        if name is not None:
            self.tab_name = name
        else:
            self.tab_name = "Untitled Pr Tab"

        if self.isBatch:
            self.tab_name = "Pr Batch"

        # if the length of the name is over 23 shorten it and add ellipsis
        if len(self.tab_name) >= 23:
            self.tab_name = self.tab_name[:20] + "..."

    def show2DPlot(self):
        self.plot2D.plot(data=self.logic.data, marker='-')
        self.plot_widget = QtWidgets.QWidget()
        self.plot_widget.setWindowTitle("2D Plot - " + self.logic.data.name)
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.plot2D)
        self.plot_widget.setLayout(layout)
        self.plot2D._item = self.plot2D
        self.plot2D.setSlicer(SectorInteractor)
        self.plot_widget.show()
        self.updateSlicerParams()
        self.enableButtons()

    def show1DPlot(self):
        selectedSlice = self.plot2D.slicer.getSlice()
        selectedSlice.title += ' @slic={}; start={}'.format(self.phi, self.deltaPhi)
        self.plot1D.plot(selectedSlice)
        self.plot1D.show()
        self.plot2D.update()

    def updateSlicerParams(self):
        try:
            self.startPoint = float(self.startPointInput.text())
        except ValueError:
            self.startPoint = START_POINT
            self.startPointInput.setText(str(START_POINT))

        try:
            self.noOfSlices = int(self.noOfSlicesInput.text())
        except ValueError:
            self.noOfSlices = NO_OF_SLICES
            self.noOfSlicesInput.setText(str(NO_OF_SLICES))

        try:
            self.qbins = float(self.noOfQbinInput.text())
        except ValueError:
            self.qbins = NO_OF_QBIN
            self.noOfQbinInput.setText(str(NO_OF_QBIN))

        self.phi = self.startPoint
        self.deltaPhi = (180 / self.noOfSlices)
        print(self.deltaPhi)
        self.setSlicerParms()

    def setSlicerParms(self):
        params = self.plot2D.slicer.getParams()
        params["Phi [deg]"] = self.phi
        params["Delta_Phi [deg]"] = self.deltaPhi
        params["nbins"] = self.qbins

        self.deltaPhiValue.setText(str(self.deltaPhi))
        self.plot2D.slicer.setParams(params)

    def muiltiSlicer(self):
        listOfSlices = list()
        self.plot1D.clean()
        params = self.plot2D.slicer.getParams()
        self.updateSlicerParams()

        for i in range(self.noOfSlices):
            params["Phi [deg]"] = self.phi
            self.plot2D.slicer.setParams(params)
            slicePlot = self.plot2D.slicer.getSlice()
            slicePlot.title += ' @Phi={}'.format(self.phi)
            slicePlot.phi = self.phi
            listOfSlices.append(slicePlot)
            self.phi += (self.deltaPhi)

        return listOfSlices


def debug(checkpoint):
    print(" - - - - - - - - [ DEBUG :: Checkpoint {} ] - - - - - - - - ".format(checkpoint))
