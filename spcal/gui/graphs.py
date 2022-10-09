from PySide6 import QtCore, QtGui, QtWidgets
import numpy as np
import pyqtgraph

from typing import Dict, List, Optional, Union


class ResultsView(pyqtgraph.GraphicsView):
    def __init__(
        self,
        pen: Optional[QtGui.QPen] = None,
        parent: Optional[QtWidgets.QWidget] = None,
    ):
        super().__init__(parent=parent, background="white")
        if pen is None:
            pen = QtGui.QPen(QtCore.Qt.black, 1.0)
            pen.setCosmetic(True)

        self.xaxis = pyqtgraph.AxisItem(
            "bottom",
            pen=pen,
            textPen=pen,
            tick_pen=pen,
            text="Intensity",
            units="count",
        )

        self.yaxis = pyqtgraph.AxisItem(
            "left", pen=pen, textPen=pen, tick_pen=pen, text="Count", units=""
        )
        self.yaxis.enableAutoSIPrefix(False)

        self.plot = pyqtgraph.PlotItem(
            title="Results",
            name="hist",
            axisItems={"bottom": self.xaxis, "left": self.yaxis},
            enableMenu=False,
            parent=parent,
        )
        self.setCentralWidget(self.plot)

    def drawData(
        self,
        name: str,
        x: np.ndarray,
        bins: Union[str, np.ndarray] = "auto",
        brush: Optional[QtGui.QBrush] = None,
    ) -> None:
        hist, edges = np.histogram(x, bins)
        curve = pyqtgraph.PlotCurveItem(
            x=edges,
            y=hist,
            stepMode="center",
            fillLevel=0,
            fillOutline=True,
            brush=brush,
            skipFiniteCheck=True,
            name=name,
        )
        self.plot.addItem(curve)


class ParticlePlotItem(pyqtgraph.PlotItem):
    limit_colors = {"mean": QtCore.Qt.red, "lc": QtCore.Qt.green, "ld": QtCore.Qt.blue}

    def __init__(
        self,
        name: str,
        xscale: float = 1.0,
        pen: Optional[QtGui.QPen] = None,
        parent: Optional[pyqtgraph.GraphicsWidget] = None,
    ):
        if pen is None:
            pen = QtGui.QPen(QtCore.Qt.black, 1.0)
            pen.setCosmetic(True)

        self.xaxis = pyqtgraph.AxisItem(
            "bottom", pen=pen, textPen=pen, tick_pen=pen, text="Time", units="s"
        )
        self.xaxis.setScale(xscale)
        self.xaxis.enableAutoSIPrefix(False)

        self.yaxis = pyqtgraph.AxisItem(
            "left", pen=pen, textPen=pen, tick_pen=pen, text="Intensity", units="count"
        )

        super().__init__(
            title=name,
            name=name,
            axisItems={"bottom": self.xaxis, "left": self.yaxis},
            enableMenu=False,
            parent=parent,
        )
        self.setMouseEnabled(y=False)
        self.setAutoVisible(y=True)
        self.enableAutoRange(y=True)
        self.hideButtons()
        self.addLegend(
            offset=(-5, 5), verSpacing=-5, colCount=3, labelTextColor="black"
        )

        self.signals: List[pyqtgraph.PlotCurveItem] = []
        self.scatters: List[pyqtgraph.ScatterPlotItem] = []
        self.limits: List[pyqtgraph.PlotCurveItem] = []

        region_pen = QtGui.QPen(QtCore.Qt.red, 1.0)
        region_pen.setCosmetic(True)

        self.region = pyqtgraph.LinearRegionItem(
            pen="grey",
            hoverPen="red",
            brush=QtGui.QBrush(QtCore.Qt.NoBrush),
            hoverBrush=QtGui.QBrush(QtCore.Qt.NoBrush),
            swapMode="block",
        )
        self.region.movable = False  # prevent moving of region, but not lines
        self.region.lines[0].addMarker("|>", 0.9)
        self.region.lines[1].addMarker("<|", 0.9)
        self.addItem(self.region)

    @property
    def region_start(self) -> int:
        return int(self.region.lines[0].value())  # type: ignore

    @property
    def region_end(self) -> int:
        return int(self.region.lines[1].value())  # type: ignore

    def clearSignal(self) -> None:
        for signal in self.signals:
            self.removeItem(signal)
        self.signals.clear()

    def clearScatters(self) -> None:
        for scatter in self.scatters:
            self.removeItem(scatter)
        self.scatters.clear()

    def clearLimits(self) -> None:
        for limit in self.limits:
            self.removeItem(limit)
        self.limits.clear()

    def drawSignal(
        self,
        x: np.ndarray,
        y: np.ndarray,
        pen: Optional[QtGui.QPen] = None,
        label: Optional[str] = None,
    ) -> None:
        if pen is None:
            pen = QtGui.QPen(QtCore.Qt.black, 1.0)
            pen.setCosmetic(True)

        # optimise by removing points with 0 change in gradient
        diffs = np.diff(y, n=2, append=0, prepend=0) != 0
        curve = pyqtgraph.PlotCurveItem(
            x=x[diffs], y=y[diffs], pen=pen, connect="all", skipFiniteCheck=True
        )
        if label is not None:
            curve.opts["name"] = label

        self.signals.append(curve)
        self.addItem(curve)

        self.setLimits(xMin=x[0], xMax=x[-1])
        self.enableAutoRange(y=True)  # rescale to max bounds

        self.region.setRegion((x[0], x[-1]))

    def drawMaxima(
        self,
        x: np.ndarray,
        y: np.ndarray,
        brush: Optional[QtGui.QBrush] = None,
    ) -> None:
        if brush is None:
            brush = QtGui.QBrush(QtCore.Qt.red)

        scatter = pyqtgraph.ScatterPlotItem(
            x=x, y=y, size=6, symbol="t", pen=None, brush=brush
        )
        self.scatters.append(scatter)
        self.addItem(scatter)

    def drawLimits(self, x: np.ndarray, limits: np.ndarray) -> None:
        skip_lc = np.all(limits["lc"] == limits["ld"])
        for name in ["mean", "lc", "ld"]:
            if name == "lc" and skip_lc:
                continue

            pen = QtGui.QPen(self.limit_colors[name], 1.0, QtCore.Qt.DashLine)
            pen.setCosmetic(True)

            if limits[name].size == 1:
                x, y = [x[0], x[-1]], [limits[name][0], limits[name][0]]
            else:
                diffs = np.diff(limits[name], n=2, append=0, prepend=0) != 0
                x, y = x[diffs], limits[name][diffs]

            curve = pyqtgraph.PlotCurveItem(
                x=x, y=y, name=name, pen=pen, connect="all", skipFiniteCheck=True
            )
            self.limits.append(curve)
            self.addItem(curve)


class ParticleView(pyqtgraph.GraphicsView):
    regionChanged = QtCore.Signal(str)

    def __init__(
        self,
        downsample: int = 1,
        minimum_plot_height: int = 150,
        parent: Optional[QtWidgets.QWidget] = None,
    ):
        self.downsample = downsample
        self.minimum_plot_height = minimum_plot_height
        self.layout = pyqtgraph.GraphicsLayout()

        super().__init__(parent=parent, background="white")
        self.setCentralWidget(self.layout)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.black_pen = QtGui.QPen(QtCore.Qt.black, 1.0)
        self.black_pen.setCosmetic(True)

        self.plots: Dict[str, ParticlePlotItem] = {}
        self.plot_colors = [
            QtGui.QColor(105, 41, 196),
            QtGui.QColor(17, 146, 232),
            QtGui.QColor(0, 93, 93),
            QtGui.QColor(159, 24, 83),
            QtGui.QColor(250, 77, 86),
            QtGui.QColor(87, 4, 8),
            QtGui.QColor(25, 128, 56),
            QtGui.QColor(0, 45, 156),
            QtGui.QColor(238, 83, 139),
            QtGui.QColor(178, 134, 0),
            QtGui.QColor(0, 157, 154),
            QtGui.QColor(1, 39, 73),
            QtGui.QColor(138, 56, 0),
            QtGui.QColor(165, 110, 255),
        ]

    # Taken from pyqtgraph.widgets.MultiPlotWidget
    def setRange(self, *args, **kwds):
        pyqtgraph.GraphicsView.setRange(self, *args, **kwds)
        if self.centralWidget is not None:
            r = self.range
            minHeight = len(self.layout.rows) * self.minimum_plot_height
            if r.height() < minHeight:
                r.setHeight(minHeight)
                r.setWidth(r.width() - self.verticalScrollBar().width())
            self.centralWidget.setGeometry(r)

    # Taken from pyqtgraph.widgets.MultiPlotWidget
    def resizeEvent(self, event: QtGui.QResizeEvent):
        if self.closed:
            return
        if self.autoPixelRange:
            self.range = QtCore.QRectF(0, 0, self.size().width(), self.size().height())
        ParticleView.setRange(
            self, self.range, padding=0, disableAutoPixel=False
        )  ## we do this because some subclasses like to redefine setRange in an incompatible way.
        self.updateMatrix()

    def addParticlePlot(self, name: str, xscale: float = 1.0) -> ParticlePlotItem:
        self.plots[name] = ParticlePlotItem(name=name, xscale=xscale)
        self.plots[name].setDownsampling(ds=self.downsample, mode="peak", auto=True)
        self.plots[name].setXLink(self.layout.getItem(0, 0))

        self.plots[name].region.sigRegionChangeFinished.connect(
            lambda: self.regionChanged.emit(name)
        )

        self.layout.addItem(self.plots[name])

        self.layout.nextRow()
        self.resizeEvent(QtGui.QResizeEvent(QtCore.QSize(0, 0), QtCore.QSize(0, 0)))

        return self.plots[name]

    # def setLinkedYAxis(self, linked: bool = True) -> None:
    #     plots = list(self.plots.values())
    #     ymax = np.argmax([plot.vb.state["limits"]["yLimits"][1] for plot in plots])
    #     print(ymax)

    #     for plot in self.plots.values():
    #         if linked:
    #             plot.setYLink(plots[ymax])
    #             # plot.setLimits(yMin=0, yMax=ymax)
    #         else:
    #             plot.setYLink(None)
    #     for plot in self.plots.values():
    #         plot.vb.updateViewRange()  # rescale to max bounds

    def clear(self) -> None:
        self.layout.clear()
        self.plots = {}