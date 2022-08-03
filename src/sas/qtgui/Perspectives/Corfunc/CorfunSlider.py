from typing import Optional, Tuple

import math
import numpy as np

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFontMetrics

from sas.qtgui.Perspectives.Corfunc.extrapolation_data import ExtrapolationParameters, ExtrapolationInteractionState

class CorfuncSlider(QtWidgets.QWidget):

    valueEdited = pyqtSignal(ExtrapolationParameters, name='valueEdited')
    valueEditing = pyqtSignal(ExtrapolationInteractionState, name='valueEditing')

    def __init__(self,
                 q_min: float = 1,
                 q_point_1: float = 2,
                 q_point_2: float = 4,
                 q_point_3: float = 8,
                 q_max: float = 16,
                 enabled: bool = False,
                 *args, **kwargs):


        super().__init__(*args, **kwargs)

        if q_min >= q_point_1:
            raise ValueError("min_q should be smaller than q_point_1")

        if q_point_1 > q_point_2:
            raise ValueError("q_point_1 should be smaller or equal to q_point_2")

        if q_point_2 > q_point_3:
            raise ValueError("q_point_2 should be smaller or equal to q_point_3")

        if q_point_3 > q_max:
            raise ValueError("q_point_3 should be smaller or equal to max_q")

        self.setEnabled(enabled)

        self._min = q_min
        self._point_1 = q_point_1
        self._point_2 = q_point_2
        self._point_3 = q_point_3
        self._max = q_max


        # Display Parameters
        self.vertical_size = 60
        self.guinier_color = QtGui.QColor('orange')
        self.data_color = QtGui.QColor('white')
        self.porod_color = QtGui.QColor('green')
        self.text_color = QtGui.QColor('black')
        self.line_drag_color = mix_colours(QtGui.QColor('white'), QtGui.QColor('black'), 0.4)
        self.hover_colour = QtGui.QColor('white')
        self.disabled_line_color = QtGui.QColor('light grey')
        self.disabled_line_color.setAlpha(0)
        self.disabled_text_color = QtGui.QColor('grey')
        self.disabled_non_data_color = QtGui.QColor('light grey')

        # - define hover colours by mixing with a grey
        mix_color = QtGui.QColor('grey')
        mix_fraction = 0.7
        self.guinier_hover_color = mix_colours(self.guinier_color, mix_color, mix_fraction)
        self.data_hover_color = mix_colours(self.data_color, mix_color, mix_fraction)
        self.porod_hover_color = mix_colours(self.porod_color, mix_color, mix_fraction)

        # Mouse control
        self._hovering = False
        self._hover_id: Optional[int] = None

        self._drag_id: Optional[int] = None
        self._movement_line_position: Optional[int] = None

        # Qt things
        # self.setAttribute(Qt.WA_Hover)
        self.setMouseTracking(True)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.Fixed
        )

    def enterEvent(self, a0: QtCore.QEvent) -> None:
        if self.isEnabled():
            self._hovering = True

        self.update()

    def leaveEvent(self, a0: QtCore.QEvent) -> None:
        if self.isEnabled():
            self._hovering = False

        self.update()

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        if self.isEnabled():
            mouse_x = event.x()

            self._drag_id = self._nearest_line(mouse_x)
            self._movement_line_position = mouse_x
            self._hovering = False

        self.update()

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        if self.isEnabled():
            mouse_x = event.x()

            if self._hovering:
                self._hover_id = self._nearest_line(mouse_x)

            if self._drag_id is not None:
                if self._validate_new_position(self._drag_id, mouse_x):
                    self._movement_line_position = mouse_x

                self.valueEditing.emit(self.interaction_state)


        self.update()

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        if self.isEnabled():
            if self._drag_id is not None and self._movement_line_position is not None:
                self.set_boundary(self._drag_id, self.inverse_transform(self._movement_line_position))

            self._drag_id = None
            self._movement_line_position = None

            x, y = event.x(), event.y()

            self._hovering = self._mouse_inside(x, y)
            if self._hovering:
                self._hover_id = self._nearest_line(x)
            else:
                self._hover_id = None

            self.valueEdited.emit(self.extrapolation_parameters)
        self.update()

    def _mouse_inside(self, x, y):
        """ Is the mouse inside the window"""
        return (0 < x < self.width()) and (0 < y < self.height())

    def _validate_new_position(self, line_id: int, new_position: float):
        """ Checks whether a new position for a line is valid"""
        l1, l2, l3 = self.line_paint_positions

        if line_id == 0:
            return 0 < new_position < l2
        elif line_id == 1:
            return l1 < new_position < l3
        elif line_id == 2:
            return l2 < new_position < self.width()
        else:
            raise ValueError("line_id must be 0, 1 or 2")

    def _nearest_line(self, x: float) -> int:
        """ Get id of the nearest line"""
        distances = [abs(x - line_x) for line_x in self.line_paint_positions]
        return int(np.argmin(distances))

    def set_boundaries(self, q_point_1: float, q_point_2: float, q_point_3: float):
        """ Set the boundaries between the sections"""
        self._point_1 = q_point_1
        self._point_2 = q_point_2
        self._point_3 = q_point_3

        self.update()

    def set_boundary(self, index: int, q: float):
        """ Set the value of the boundary points by (0-)index"""
        if index == 0:
            self._point_1 = q
        elif index == 1:
            self._point_2 = q
        elif index == 2:
            self._point_3 = q
        else:
            raise IndexError("Boundary index must be 0,1 or 2")

        self.update()

    @property
    def extrapolation_parameters(self):
        return ExtrapolationParameters(self._min, self._point_1, self._point_2, self._point_3, self._max)

    @extrapolation_parameters.setter
    def extrapolation_parameters(self, params: ExtrapolationParameters):
        self._min, self._point_1, self._point_2, self._point_3, self._max = params
        print(params)
        self.update()

    @property
    def interaction_state(self) -> ExtrapolationInteractionState:
        """ The current state of the slider, including temporary data about how it is being moved"""
        return ExtrapolationInteractionState(
            self.extrapolation_parameters,
            self._drag_id,
            None if self._movement_line_position is None else self.inverse_transform(self._movement_line_position)
        )

    @property
    def _dragging(self) -> bool:
        """ Are we dragging? """
        return self._drag_id is not None

    @property
    def data_width(self) -> float:
        """ Length of range spanned by the data"""
        return math.log(self._max/self._min)

    @property
    def scale(self) -> float:
        """ Scale factor from input to draw scale e.g. A^-1 -> px"""
        return self.width() / self.data_width

    def transform(self, q_value: float) -> float:
        """Convert a value from input to draw coordinates"""

        if q_value == 0:
            return 0

        if self._min == 0:
            return self.width()

        return self.scale * (math.log(q_value) - math.log(self._min))

    def inverse_transform(self, px_value: float) -> float:
        """Convert a value from draw coordinates to input value"""
        return self._min*math.exp((px_value/self.scale))

    @property
    def guinier_label_position(self) -> float:
        """ Position to put the text for the guinier region"""
        return 15

    @property
    def data_label_centre(self) -> float:
        """ Centre of the interpolation region"""
        return 0.5 * (self.transform(self._point_1) + self.transform(self._point_2))

    @property
    def transition_label_centre(self) -> float:
        """ Centre of the data-porod transition"""
        return 0.5 * (self.transform(self._point_2) + self.transform(self._point_3))

    @property
    def porod_label_centre(self) -> float:
        """ Centre of the Porod region"""

        return 0.5 * (self.transform(self._point_3) + self.transform(self._max))

    @property
    def line_paint_positions(self) -> Tuple[float, float, float]:
        """ x coordinate of the painted lines"""
        return (self.transform(self._point_1),
                self.transform(self._point_2),
                self.transform(self._point_3))

    def paintEvent(self, e):
        painter = QtGui.QPainter(self)
        brush = QtGui.QBrush()
        brush.setColor(QtGui.QColor('black'))
        brush.setStyle(Qt.SolidPattern)
        rect = QtCore.QRect(0, 0, painter.device().width(), self.vertical_size)
        painter.fillRect(rect, brush)

        positions = [0,
                     self.transform(self._point_1),
                     self.transform(self._point_2),
                     self.transform(self._point_3),
                     self.transform(self._max)]



        positions = [int(x) for x in positions]
        widths = [positions[i+1] - positions[i] for i in range(4)]

        #
        # Draw the sections
        #
        brush.setStyle(Qt.SolidPattern)
        if self.isEnabled():
            if self._hovering or self._dragging:
                guinier_color = self.guinier_hover_color
                data_color = self.data_hover_color
                porod_color = self.porod_hover_color
            else:
                guinier_color = self.guinier_color
                data_color = self.data_color
                porod_color = self.porod_color
        else:
            guinier_color = self.disabled_non_data_color
            data_color = self.data_color
            porod_color = self.disabled_non_data_color

        grad = QtGui.QLinearGradient(0, 0, widths[0], 0)
        grad.setColorAt(0.0, guinier_color)
        grad.setColorAt(1.0, data_color)
        rect = QtCore.QRect(positions[0], 0, widths[0], self.vertical_size)
        painter.fillRect(rect, grad)

        brush.setColor(data_color)
        rect = QtCore.QRect(positions[1], 0, widths[1], self.vertical_size)
        painter.fillRect(rect, brush)

        grad = QtGui.QLinearGradient(positions[2], 0, positions[3], 0)
        grad.setColorAt(0.0, data_color)
        grad.setColorAt(1.0, porod_color)
        rect = QtCore.QRect(positions[2], 0, widths[2], self.vertical_size)
        painter.fillRect(rect, grad)

        brush.setColor(porod_color)
        rect = QtCore.QRect(positions[3], 0, widths[3], self.vertical_size)
        painter.fillRect(rect, brush)

        #
        # Dividing lines
        #
        for i, x in enumerate(positions[1:-1]):
            if self.isEnabled():
                # different color if it's the one that will be moved
                if self._hovering and i == self._hover_id:
                    pen = QtGui.QPen(self.hover_colour, 5)
                else:
                    pen = QtGui.QPen(self.text_color, 5)
            else:
                pen = QtGui.QPen(self.disabled_line_color, 5)

            painter.setPen(pen)
            painter.drawLine(x, 0, x, self.vertical_size)

        if self._movement_line_position is not None:
            pen = QtGui.QPen(self.line_drag_color, 5)
            painter.setPen(pen)
            painter.drawLine(self._movement_line_position, 0, self._movement_line_position, self.vertical_size)

        #
        # Labels
        #


        self._paint_label(self.guinier_label_position, "Guinier", False)
        self._paint_label(self.data_label_centre, "Data")
        # self._paint_label(self.transition_label_centre, "Transition") # Looks better without this
        self._paint_label(self.porod_label_centre, "Porod")


    def _paint_label(self, position: float, text: str, centre_justify=True):

        painter = QtGui.QPainter(self)

        pen = painter.pen()

        if self.isEnabled():
            pen.setColor(self.text_color)
        else:
            pen.setColor(self.disabled_text_color)

        painter.setPen(pen)

        font = painter.font()
        font.setFamily('Times')
        font.setPointSize(10)
        painter.setFont(font)

        font_metrics = QFontMetrics(font)
        text_height = font_metrics.height()

        if centre_justify:
            x_offset = -0.5*font_metrics.horizontalAdvance(text)
        else:
            x_offset = 0

        painter.drawText(int(position + x_offset), int(0.5*self.vertical_size + 0.3*text_height), text)
        painter.end()

    def sizeHint(self):
        return QtCore.QSize(800, self.vertical_size)


def mix_colours(a: QtGui.QColor, b: QtGui.QColor, k: float) -> QtGui.QColor:
    return QtGui.QColor(
        int(k * a.red() + (1-k) * b.red()),
        int(k * a.green() + (1-k) * b.green()),
        int(k * a.blue() + (1-k) * b.blue()),
        int(k * a.alpha() + (1-k) * b.alpha()))


def main():
    """ Show a demo of the slider """
    app = QtWidgets.QApplication([])
    slider = CorfuncSlider(enabled=True)
    slider.show()
    app.exec_()


if __name__ == "__main__":
    main()
