import sys
import unittest
import numpy

import pytest

import os
os.environ["MPLBACKEND"] = "qtagg"

from PyQt5 import QtGui, QtWidgets
from unittest.mock import MagicMock
import matplotlib as mpl

# set up import paths
import sas.qtgui.path_prepare

from sas.qtgui.Plotting.PlotterData import Data2D
import sas.qtgui.Plotting.Plotter2D as Plotter2D
from sas.qtgui.UnitTesting.TestUtils import WarningTestNotImplemented
from sas.qtgui.UnitTesting.TestUtils import QtSignalSpy

# Local
from sas.qtgui.Plotting.ColorMap import ColorMap

if not QtWidgets.QApplication.instance():
    app = QtWidgets.QApplication(sys.argv)

class ColorMapTest(unittest.TestCase):
    '''Test the ColorMap'''
    def setUp(self):
        '''Create the ColorMap'''
        self.plotter = Plotter2D.Plotter2D(None, quickplot=True)

        self.data = Data2D(image=[0.1]*4,
                           qx_data=[1.0, 2.0, 3.0, 4.0],
                           qy_data=[10.0, 11.0, 12.0, 13.0],
                           dqx_data=[0.1, 0.2, 0.3, 0.4],
                           dqy_data=[0.1, 0.2, 0.3, 0.4],
                           q_data=[1,2,3,4],
                           xmin=-1.0, xmax=5.0,
                           ymin=-1.0, ymax=15.0,
                           zmin=-1.0, zmax=20.0)

        # setup failure: 2022-09
        # The data object does not have xmin/xmax etc set in it; the values
        # are initially set by Data2D's call to PlottableData2D.__init__
        # but are then *unset* by call to LoadData2D.__init__ since they
        # are not explicitly passed to that constructor, and that constructor
        # saves all values. Lack of xmin/xmax etc means that the following
        # instantiation of the ColorMap class fails.

        self.data.title="Test data"
        self.data.id = 1
        self.widget = ColorMap(parent=self.plotter, data=self.data)

    def tearDown(self):
        '''Destroy the GUI'''
        self.widget.close()
        self.widget = None

    @pytest.mark.skip(reason="2022-09 already broken - causes segfault")
    def testDefaults(self):
        '''Test the GUI in its default state'''
        assert isinstance(self.widget, QtWidgets.QDialog)

        assert self.widget._cmap_orig == "jet"
        assert len(self.widget.all_maps) == 150
        assert len(self.widget.maps) == 75
        assert len(self.widget.rmaps) == 75

        assert self.widget.lblWidth.text() == "0"
        assert self.widget.lblHeight.text() == "0"
        assert self.widget.lblQmax.text() == "18"
        assert self.widget.lblStopRadius.text() == "-1"
        assert not self.widget.chkReverse.isChecked()
        assert self.widget.cbColorMap.count() == 75
        assert self.widget.cbColorMap.currentIndex() == 60

        # validators
        assert isinstance(self.widget.txtMinAmplitude.validator(), QtGui.QDoubleValidator)
        assert isinstance(self.widget.txtMaxAmplitude.validator(), QtGui.QDoubleValidator)

        # Ranges
        assert self.widget.txtMinAmplitude.text() == "0"
        assert self.widget.txtMaxAmplitude.text() == "100"
        assert isinstance(self.widget.slider, QtWidgets.QSlider)

    @pytest.mark.skip(reason="2022-09 already broken - causes segfault")
    def testOnReset(self):
        '''Check the dialog reset function'''
        # Set some controls to non-default state
        self.widget.cbColorMap.setCurrentIndex(20)
        self.widget.chkReverse.setChecked(True)
        self.widget.txtMinAmplitude.setText("20.0")

        # Reset the widget state
        self.widget.onReset()

        # Assure things went back to default
        assert self.widget.cbColorMap.currentIndex() == 20
        assert not self.widget.chkReverse.isChecked()
        assert self.widget.txtMinAmplitude.text() == "0"

    @pytest.mark.skip(reason="2022-09 already broken - causes segfault")
    def testOnApply(self):
        '''Check the dialog apply function'''
        # Set some controls to non-default state
        self.widget.show()
        self.widget.cbColorMap.setCurrentIndex(20) # PuRd_r
        self.widget.chkReverse.setChecked(True)
        self.widget.txtMinAmplitude.setText("20.0")

        spy_apply = QtSignalSpy(self.widget, self.widget.apply_signal)
        # Reset the widget state
        self.widget.onApply()

        # Assure the widget is still up and the signal was sent.
        assert self.widget.isVisible()
        assert spy_apply.count() == 1
        assert 'PuRd_r' in spy_apply.called()[0]['args'][1]

    @pytest.mark.skip(reason="2022-09 already broken - causes segfault")
    def testInitMapCombobox(self):
        '''Test the combo box initializer'''
        # Set a color map from the direct list
        self.widget._cmap = "gnuplot"
        self.widget.initMapCombobox()

        # Check the combobox
        assert self.widget.cbColorMap.currentIndex() == 55
        assert not self.widget.chkReverse.isChecked()

        # Set a reversed value
        self.widget._cmap = "hot_r"
        self.widget.initMapCombobox()
        # Check the combobox
        assert self.widget.cbColorMap.currentIndex() == 56
        assert self.widget.chkReverse.isChecked()

    @pytest.mark.skip(reason="2022-09 already broken - causes segfault")
    def testInitRangeSlider(self):
        '''Test the range slider initializer'''
        # Set a color map from the direct list
        self.widget._cmap = "gnuplot"
        self.widget.initRangeSlider()

        # Check the values
        assert self.widget.slider.minimum() == 0
        assert self.widget.slider.maximum() == 100
        assert self.widget.slider.orientation() == 1

        # Emit new low value
        self.widget.slider.lowValueChanged.emit(5)
        # Assure the widget received changes
        assert self.widget.txtMinAmplitude.text() == "5"

        # Emit new high value
        self.widget.slider.highValueChanged.emit(45)
        # Assure the widget received changes
        assert self.widget.txtMaxAmplitude.text() == "45"

    @pytest.mark.skip(reason="2022-09 already broken - causes segfault")
    def testOnMapIndexChange(self):
        '''Test the response to the combo box index change'''

        self.widget.canvas.draw = MagicMock()
        mpl.colorbar.ColorbarBase = MagicMock()

        # simulate index change
        self.widget.cbColorMap.setCurrentIndex(1)

        # Check that draw() got called
        assert self.widget.canvas.draw.called
        assert mpl.colorbar.ColorbarBase.called

    @pytest.mark.skip(reason="2022-09 already broken - causes segfault")
    def testOnColorMapReversed(self):
        '''Test reversing the color map functionality'''
        # Check the defaults
        assert self.widget._cmap == "jet"
        self.widget.cbColorMap.addItems = MagicMock()

        # Reverse the choice
        self.widget.onColorMapReversed(True)

        # check the behaviour
        assert self.widget._cmap == "jet_r"
        assert self.widget.cbColorMap.addItems.called

    @pytest.mark.skip(reason="2022-09 already broken - causes segfault")
    def testOnAmplitudeChange(self):
        '''Check the callback method for responding to changes in textboxes'''
        self.widget.canvas.draw = MagicMock()
        mpl.colors.Normalize = MagicMock()
        mpl.colorbar.ColorbarBase = MagicMock()

        self.widget.vmin = 0.0
        self.widget.vmax = 100.0

        # good values in fields
        self.widget.txtMinAmplitude.setText("1.0")
        self.widget.txtMaxAmplitude.setText("10.0")

        self.widget.onAmplitudeChange()

        # Check the arguments to Normalize
        mpl.colors.Normalize.assert_called_with(vmin=1.0, vmax=10.0)
        assert self.widget.canvas.draw.called

        # Bad values in fields
        self.widget.txtMinAmplitude.setText("cake")
        self.widget.txtMaxAmplitude.setText("more cake")

        self.widget.onAmplitudeChange()

        # Check the arguments to Normalize - should be defaults
        mpl.colors.Normalize.assert_called_with(vmin=0.0, vmax=100.0)
        assert self.widget.canvas.draw.called


if __name__ == "__main__":
    unittest.main()
