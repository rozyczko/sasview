from abc import ABC, abstractmethod
from typing import Optional, TypeVar, Generic, Any

from PySide6.QtCore import QEvent
from matplotlib.lines import Line2D
from matplotlib.axes import Axes

from sas.qtgui.Plotting.PlotterBase import PlotterBase

# Colours
interface_color = 'black'
disable_color = 'gray'
active_color = 'red'
rho_color = 'black'
mu_color = 'green'
P_color = 'blue'
theta_color = 'orange'
profile_colors = [rho_color, mu_color, P_color, theta_color]

PlotterBaseT = TypeVar('PlotterBaseT', bound=PlotterBase)

class BaseInteractor(ABC, Generic[PlotterBaseT]):
    """
    Share some functions between the interface interactor and various layer
    interactors.

    Abstract methods:
        save(ev)  - save the current state for later restore
        restore() - restore the old state
        move(x,y,ev) - move the interactor to position x,y
        moveend(ev) - end the drag event
        setParameter(parameter_name, parameter_value) - set a parameter for this interactor
        getParameters() - get a dictionary containing the parameters for this interactor


    The following are provided by the base class:

        connect_markers(markers) - register callbacks for all markers
        clear_markers() - remove all items in self.markers
        onHighlight(ev) - enter/leave event processing
        onLeave(ev) - enter/leave event processing
        onClick(ev) - mouse click: calls save()
        onRelease(ev) - mouse click ends: calls moveend()
        onDrag(ev) - mouse move: calls move() or restore()
        onKey(ev) - keyboard move: calls move() or restore()

    Interactor attributes:

        base  - model we are operating on
        axes  - axes holding the interactor
        color - color of the interactor in non-active state
        markers - list of handles for the interactor

    """
    def __init__(self, base: PlotterBaseT, axes: Axes, color: str='black'):

        self.base: PlotterBaseT = base
        self.axes: Axes = axes
        self.color: str = color

        self.clickx: Optional[int] = None
        self.clicky: Optional[int] = None
        self.markers: list[Line2D] = []

        # TODO: Why?
        if isinstance(base.data, list):
            self.data = self.base.data[0]
        else:
            self.data = self.base.data

    def clear_markers(self):
        """
        Clear old markers and interfaces.
        """
        for h in self.markers:
            h.remove()

        if self.markers:
            self.base.connect.clear(*self.markers)

        self.markers = []

    @abstractmethod
    def save(self, ev: QEvent):
        """ save the current state for later restore """

    @abstractmethod
    def restore(self, ev: QEvent):
        """ restore the old state """

    @abstractmethod
    def move(self, x, y, ev: QEvent):
        """ move the interactor to position x,y """

    @abstractmethod
    def moveend(self, ev: QEvent):
        """ end the drag event """

    def connect_markers(self, markers: list[Line2D]):
        """
        Connect markers to callbacks
        """

        for h in markers:
            connect = self.base.connect
            connect('enter', h, self.onHighlight)
            connect('leave', h, self.onLeave)
            connect('click', h, self.onClick)
            connect('release', h, self.onRelease)
            connect('drag', h, self.onDrag)
            connect('key', h, self.onKey)

    def onHighlight(self, ev: QEvent):
        """
        Highlight the artist reporting the event, indicating that it is
        ready to receive a click.
        """
        ev.artist.set_color(active_color)
        self.base.draw()
        return True

    def onLeave(self, ev: QEvent):
        """
        Restore the artist to the original colour when the cursor leaves.
        """
        ev.artist.set_color(self.color)
        self.base.draw()
        return True

    def onClick(self, ev: QEvent):
        """
        Prepare to move the artist.  Calls save() to preserve the state for
        later restore().
        """
        self.clickx, self.clicky = ev.xdata, ev.ydata
        self.save(ev)

        return True

    def onRelease(self, ev: QEvent):
        """
        Mouse release
        """
        self.moveend(ev)
        return True

    def onDrag(self, ev: QEvent):
        """
        Move the artist.  Calls move() to update the state, or restore() if
        the mouse leaves the window.
        """
        inside, _ = self.axes.contains(ev)

        if inside:
            self.clickx, self.clicky = ev.xdata, ev.ydata
            self.move(ev.xdata, ev.ydata, ev)

        else:
            self.restore(ev)

        return True

    def onKey(self, ev: QEvent):
        """
        Respond to keyboard events.  Arrow keys move the widget.  Escape
        restores it to the position before the last click.

        Calls move() to update the state.  Calls restore() on escape.
        """
        if ev.key == 'escape':
            self.restore(ev)

        elif ev.key in ['up', 'down', 'right', 'left']:
            dx, dy = self.dpixel(self.clickx, self.clicky, nudge=ev.control)
            if ev.key == 'up':
                self.clicky += dy
            elif ev.key == 'down':
                self.clicky -= dy
            elif ev.key == 'right':
                self.clickx += dx
            else: self.clickx -= dx
            self.move(self.clickx, self.clicky, ev)

        else:
            return False

        self.base.update()

        return True

    def dpixel(self, x: float, y: float, nudge=False) -> tuple[float, float]:
        """
        Return the step size in data coordinates for a small
        step in screen coordinates.  If nudge is False (default)
        the step size is one pixel.  If nudge is True, the step
        size is 0.2 pixels.
        """
        ax = self.axes

        px, py = ax.transData.inverse_xy_tup((x, y))

        if nudge:
            nx, ny = ax.transData.xy_tup((px + 0.2, py + 0.2))
        else:
            nx, ny = ax.transData.xy_tup((px + 1.0, py + 1.0))
        dx, dy = nx - x, ny - y

        return dx, dy


