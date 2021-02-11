from PySide2 import QtCore, QtGui, QtWidgets
from PySide2.QtCharts import QtCharts

import numpy as np

import nanopart

from nanopart.gui.charts import ParticleChart
from nanopart.gui.tables import ParticleModel, ParticleTable
from nanopart.gui.units import UnitsWidget
from nanopart.gui.widgets import RangeSlider, ValidColorLineEdit

from nanopart.gui.npoptions import NPOptionsWidget

from typing import Tuple


class NPInputWidget(QtWidgets.QWidget):
    optionsChanged = QtCore.Signal()
    detectionsChanged = QtCore.Signal(int)

    def __init__(self, options: NPOptionsWidget, parent: QtWidgets.QWidget = None):
        super().__init__(parent)
        self.setAcceptDrops(True)

        self.options = options
        self.options.dwelltime.valueChanged.connect(self.updateLimits)
        self.options.method.currentTextChanged.connect(self.updateLimits)

        self.limits: Tuple[str, float, float, float] = None
        self.detections: np.ndarray = None
        self.true_background = 0.0

        self.button_file = QtWidgets.QPushButton("Open File")
        self.button_file.pressed.connect(self.dialogLoadfile)

        self.chart = ParticleChart()
        self.chartview = QtCharts.QChartView(self.chart)
        self.chartview.setRubberBand(QtCharts.QChartView.HorizontalRubberBand)

        self.model = ParticleModel(np.ndarray((0, 1), dtype=np.float64))
        self.model.dataChanged.connect(self.redrawChart)
        self.model.dataChanged.connect(self.updateLimits)

        self.table = ParticleTable(self.model)
        self.table.unitChanged.connect(self.updateLimits)

        self.slider = RangeSlider()
        self.slider.setRange(0, 100)
        self.slider.valueChanged.connect(self.updateTrim)
        self.slider.value2Changed.connect(self.updateTrim)
        self.slider.sliderReleased.connect(self.updateLimits)

        # Sample options

        self.inputs = QtWidgets.QGroupBox("Inputs")
        self.inputs.setLayout(QtWidgets.QFormLayout())

        self.count = QtWidgets.QLineEdit("0")
        self.count.setReadOnly(True)
        self.background = QtWidgets.QLineEdit()
        self.background.setReadOnly(True)

        self.outputs = QtWidgets.QGroupBox("Outputs")
        self.outputs.setLayout(QtWidgets.QFormLayout())
        self.outputs.layout().addRow("Particle count:", self.count)
        self.outputs.layout().addRow("Background mean:", self.background)

        layout_table = QtWidgets.QVBoxLayout()
        layout_table.addWidget(self.button_file, 0, QtCore.Qt.AlignLeft)
        layout_table.addWidget(self.table)

        layout_slider = QtWidgets.QHBoxLayout()
        layout_slider.addWidget(QtWidgets.QLabel("Trim:"))
        layout_slider.addWidget(self.slider, QtCore.Qt.AlignRight)

        layout_io = QtWidgets.QHBoxLayout()
        layout_io.addWidget(self.inputs)
        layout_io.addWidget(self.outputs)

        layout_chart = QtWidgets.QVBoxLayout()
        layout_chart.addLayout(layout_io)
        layout_chart.addWidget(self.chartview, 1)
        layout_chart.addLayout(layout_slider)

        layout = QtWidgets.QHBoxLayout()
        layout.addLayout(layout_table, 0)
        layout.addLayout(layout_chart, 1)

        self.setLayout(layout)

    def dragEnterEvent(self, event: QtGui.QDragEnterEvent) -> None:
        if (
            event.mimeData().hasHtml()
            or event.mimeData().hasText()
            or event.mimeData().hasUrls()
        ):
            event.acceptProposedAction()
        else:  # pragma: no cover
            super().dragEnterEvent(event)

    def dropEvent(self, event: QtGui.QDropEvent) -> None:
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                self.loadFile(url.toLocalFile())
            event.acceptProposedAction()
        elif event.mimeData().hasHtml():
            pass
        elif event.mimeData().hasText():
            pass
        else:
            super().dropEvent(event)

    def timeAsSeconds(self) -> np.ndarray:
        dwell = self.options.dwelltime.baseValue()
        if dwell is None:
            return None
        return (self.slider.right() - self.slider.left()) * dwell

    def dialogLoadfile(self) -> None:
        file, _filter = QtWidgets.QFileDialog.getOpenFileName(self, "Open", "")
        if file != "":
            self.loadFile(file)

    def loadFile(self, file: str) -> np.ndarray:
        try:
            parameters = self.table.loadFile(file)
        except ValueError:
            return

        # Update dwell time
        if "dwelltime" in parameters:
            self.options.dwelltime.setBaseValue(parameters["dwelltime"])

        # Update Chart and slider
        self.slider.setRange(0, self.model.rowCount())
        self.slider.setValues(0, self.model.rowCount())

        self.redrawChart()
        self.chart.xaxis.setRange(self.slider.left(), self.slider.right())

    def redrawChart(self) -> None:
        responses = self.table.asCounts(
            self.options.dwelltime.baseValue(),
            trim=(self.slider.left(), self.slider.right()),
        )
        if responses is None:
            return

        events = np.arange(responses.size)
        self.chart.setData(np.stack((events, responses), axis=1))

        values = [self.slider.left(), self.slider.right()]
        colors = [QtGui.QColor(255, 0, 0), QtGui.QColor(255, 0, 0)]
        self.chart.drawVerticalLines(
            values, colors=colors, visible_in_legend=False  # type: ignore
        )

        self.updateLimits()

    def updateDetections(self, responses: np.ndarray) -> None:
        if self.limits is not None:
            detections, labels = nanopart.accumulate_detections(
                responses, self.limits[3], self.limits[2]
            )

            self.detections = detections
            self.count.setText(str(detections.size))
            background = np.mean(responses[labels == 0])
            self.background.setText(f"{background:.4g}")
            self.detectionsChanged.emit(detections.size)
        else:
            self.count.setText("")
            self.background.setText("")
            self.detectionsChanged.emit(0)

    def updateLimits(self) -> None:
        self.chart.clearHorizontalLines()
        self.limits = None

        method = self.options.method.currentText()
        responses = self.table.asCounts(
            self.options.dwelltime.baseValue(),
            trim=(self.slider.left(), self.slider.right()),
        )
        if responses is None or responses.size == 0:
            return

        mean = np.mean(responses)
        gaussian = None
        poisson = None
        if method in ["Highest", "Gaussian"]:
            if self.options.sigma.hasAcceptableInput():
                sigma = float(self.options.sigma.text())
                gaussian = mean + sigma * np.std(responses)

        if method in ["Highest", "Poisson"]:
            if self.options.epsilon.hasAcceptableInput():
                epsilon = float(self.options.epsilon.text())
                yc, yd = nanopart.poisson_limits(mean, epsilon=epsilon)
                poisson = (mean + yc, mean + yd)

        if method == "Highest":
            if gaussian is not None and poisson is not None:
                method = "Gaussian" if gaussian > poisson[1] else "Poisson"

        if method == "Gaussian" and gaussian is not None:
            self.limits = (method, mean, gaussian, gaussian)
            self.chart.drawHorizontalLines(
                [self.limits[1], self.limits[3]],
                colors=[QtGui.QColor(255, 0, 0), QtGui.QColor(0, 0, 255)],
                names=["mean", f"{sigma}σ"],
                styles=[QtCore.Qt.DashLine] * 2,
            )
        elif method == "Poisson" and poisson is not None:
            self.limits = (method, mean, *poisson)
            self.chart.drawHorizontalLines(
                [self.limits[1], self.limits[2], self.limits[3]],
                colors=[
                    QtGui.QColor(255, 0, 0),
                    QtGui.QColor(0, 255, 0),
                    QtGui.QColor(0, 0, 255),
                ],
                names=["mean", "Lc", "Ld"],
                styles=[QtCore.Qt.DashLine] * 3,
            )

        self.updateDetections(responses)

    def updateTrim(self) -> None:
        values = [self.slider.left(), self.slider.right()]
        self.chart.setVerticalLines(values)  # type: ignore


class NPSampleWidget(NPInputWidget):
    def __init__(self, options: NPOptionsWidget, parent: QtWidgets.QWidget = None):
        super().__init__(options, parent=parent)

        self.density = UnitsWidget(
            {"g/cm³": 1e-3 * 1e6, "kg/m³": 1.0},
            default_unit="g/cm³",
        )
        self.molarratio = ValidColorLineEdit("1.0")
        self.molarratio.setValidator(QtGui.QDoubleValidator(0.0, 1.0, 4))

        self.density.setToolTip("Sample particle density.")
        self.molarratio.setToolTip("Ratio of the mass of the particle to the analyte.")

        self.density.valueChanged.connect(self.optionsChanged)
        self.molarratio.textChanged.connect(self.optionsChanged)

        self.inputs.layout().addRow("Density:", self.density)
        self.inputs.layout().addRow("Molar ratio:", self.molarratio)


class NPReferenceWidget(NPInputWidget):
    def __init__(self, options: NPOptionsWidget, parent: QtWidgets.QWidget = None):
        super().__init__(options, parent=parent)

        concentration_units = {
            "fg/L": 1e-18,
            "pg/L": 1e-15,
            "ng/L": 1e-12,
            "μg/L": 1e-9,
            "mg/L": 1e-6,
            "g/L": 1e-3,
            "kg/L": 1.0,
        }

        self.concentration = UnitsWidget(
            units=concentration_units,
            default_unit="ng/L",
            invalid_color=QtGui.QColor(255, 255, 172),
        )
        self.density = UnitsWidget(
            {"g/cm³": 1e-3 * 1e6, "kg/m³": 1.0},
            default_unit="g/cm³",
        )
        self.diameter = UnitsWidget(
            {"nm": 1e-9, "μm": 1e-6, "m": 1.0},
            default_unit="nm",
        )
        self.molarratio = ValidColorLineEdit(
            "1.0", color_bad=QtGui.QColor(255, 255, 172)
        )
        self.molarratio.setValidator(QtGui.QDoubleValidator(0.0, 1.0, 4))

        self.concentration.setToolTip("Reference particle concentration.")
        self.density.setToolTip("Reference particle density.")
        self.diameter.setToolTip("Reference particle diameter.")
        self.molarratio.setToolTip("Ratio of the mass of the particle to the analyte.")

        self.concentration.valueChanged.connect(self.optionsChanged)
        self.density.valueChanged.connect(self.optionsChanged)
        self.diameter.valueChanged.connect(self.optionsChanged)
        self.molarratio.textChanged.connect(self.optionsChanged)

        self.inputs.layout().addRow("Concentration:", self.concentration)
        self.inputs.layout().addRow("Density:", self.density)
        self.inputs.layout().addRow("Diameter:", self.diameter)
        self.inputs.layout().addRow("Molar ratio:", self.molarratio)

        self.efficiency = ValidColorLineEdit()
        self.efficiency.setValidator(QtGui.QDoubleValidator(0.0, 1.0, 10))
        self.efficiency.setReadOnly(True)

        self.outputs.layout().addRow("Neb. Efficiency:", self.efficiency)

        self.options.response.valueChanged.connect(self.calculateEfficiency)
        self.optionsChanged.connect(self.calculateEfficiency)
        self.detectionsChanged.connect(self.calculateEfficiency)

    def calculateEfficiency(self) -> None:
        self.efficiency.setText("")

        density = self.density.baseValue()
        diameter = self.diameter.baseValue()
        if self.detections is None or density is None or diameter is None:
            return

        mass = nanopart.reference_particle_mass(density, diameter)

        concentration = self.concentration.baseValue()
        uptake = self.options.uptake.baseValue()
        time = self.timeAsSeconds()
        if all(o is not None for o in [concentration, uptake, time]):
            efficiency = nanopart.nebulisation_efficiency_from_concentration(
                self.detections.size,
                concentration=concentration,
                mass=mass,
                flow=uptake,
                time=time,
            )
            self.efficiency.setText(f"{efficiency:.4g}")
            return

        dwell = self.options.dwelltime.baseValue()
        response = self.options.response.baseValue()
        ratio = (
            float(self.molarratio.text())
            if self.molarratio.hasAcceptableInput()
            else None
        )
        if all(o is not None for o in [dwell, response, ratio, uptake]):
            efficiencies = nanopart.nebulisation_efficiency_from_mass(
                self.detections,
                dwell=dwell,
                mass=mass,
                flowrate=uptake,
                response_factor=response,
                mass_fraction=ratio,
            )
            efficiency = np.mean(efficiencies)
            self.efficiency.setText(f"{efficiency:.4g}")