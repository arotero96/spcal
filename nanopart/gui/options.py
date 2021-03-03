from PySide2 import QtCore, QtGui, QtWidgets

from nanopart.gui.units import UnitsWidget
from nanopart.gui.widgets import ValidColorLineEdit


class OptionsWidget(QtWidgets.QWidget):
    optionsChanged = QtCore.Signal()
    elementSelected = QtCore.Signal(str, float)
    limitOptionsChanged = QtCore.Signal()

    def __init__(self, parent: QtWidgets.QWidget = None):
        super().__init__(parent)

        # density_units = {"g/cm³": 1e-3 * 1e6, "kg/m³": 1.0}
        response_units = {
            "counts/(pg/L)": 1e15,
            "counts/(ng/L)": 1e12,
            "counts/(μg/L)": 1e9,
            "counts/(mg/L)": 1e6,
        }
        uptake_units = {
            "ml/min": 1e-3 / 60.0,
            "ml/s": 1e-3,
            "L/min": 1.0 / 60.0,
            "L/s": 1.0,
        }

        # Instrument wide options
        self.dwelltime = UnitsWidget(
            {"ms": 1e-3, "s": 1.0},
            default_unit="ms",
        )
        self.uptake = UnitsWidget(
            uptake_units,
            default_unit="ml/min",
        )
        self.response = UnitsWidget(
            response_units,
            default_unit="counts/(μg/L)",
        )
        self.efficiency = ValidColorLineEdit()
        self.efficiency.setValidator(QtGui.QDoubleValidator(0.0, 1.0, 10))

        self.dwelltime.setToolTip(
            "ICP-MS dwell-time, updated from imported files if time column exists."
        )
        self.uptake.setToolTip("ICP-MS sample flowrate.")
        self.response.setToolTip("ICP-MS response for ionic standard.")
        self.efficiency.setToolTip(
            "Nebulisation efficiency. Can be calculated using a reference particle."
        )

        self.efficiency_method = QtWidgets.QComboBox()
        self.efficiency_method.addItems(["Manual", "Reference", "Mass Response (None)"])
        self.efficiency_method.currentTextChanged.connect(self.efficiencyMethodChanged)

        # Complete Changed
        self.dwelltime.valueChanged.connect(self.optionsChanged)
        self.uptake.valueChanged.connect(self.optionsChanged)
        self.response.valueChanged.connect(self.optionsChanged)
        self.efficiency.textChanged.connect(self.optionsChanged)

        self.inputs = QtWidgets.QGroupBox("Instrument Options")
        self.inputs.setLayout(QtWidgets.QFormLayout())
        self.inputs.layout().addRow("Uptake:", self.uptake)
        self.inputs.layout().addRow("Dwell time:", self.dwelltime)
        self.inputs.layout().addRow("Response:", self.response)
        self.inputs.layout().addRow("Neb. Efficiency:", self.efficiency)
        self.inputs.layout().addRow("", self.efficiency_method)

        self.epsilon = QtWidgets.QLineEdit("0.5")
        self.epsilon.setValidator(QtGui.QDoubleValidator(0.0, 1e2, 2))

        self.sigma = QtWidgets.QLineEdit("3.0")
        self.sigma.setValidator(QtGui.QDoubleValidator(0.0, 1e2, 2))

        self.method = QtWidgets.QComboBox()
        self.method.addItems(["Automatic", "Highest", "Poisson", "Gaussian"])
        self.method.currentTextChanged.connect(self.limitOptionsChanged)

        self.epsilon.setToolTip(
            "Correction factor for low background counts. "
            "Default of 0.5 maintains 0.05 alpha / beta."
        )
        self.sigma.setToolTip("LOD in number of standard deviations from mean.")

        self.epsilon.textChanged.connect(self.limitOptionsChanged)
        self.sigma.textChanged.connect(self.limitOptionsChanged)

        self.limit_inputs = QtWidgets.QGroupBox("Limits inputs")
        self.limit_inputs.setLayout(QtWidgets.QFormLayout())
        self.limit_inputs.layout().addRow("Epsilon:", self.epsilon)
        self.limit_inputs.layout().addRow("Sigma:", self.sigma)
        self.limit_inputs.layout().addRow("LOD method:", self.method)

        self.diameter = UnitsWidget(
            units={"nm": 1e-9, "μm": 1e-6, "m": 1.0},
            default_unit="μm",
            invalid_color=QtGui.QColor(255, 255, 172),
        )

        self.cell_inputs = QtWidgets.QGroupBox("Single Cell Options")
        self.cell_inputs.setLayout(QtWidgets.QFormLayout())
        self.cell_inputs.layout().addRow("Hypothesised diamter:", self.diameter)

        layout_left = QtWidgets.QVBoxLayout()
        layout_left.addWidget(self.limit_inputs)
        layout_left.addWidget(self.cell_inputs)

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self.inputs)
        layout.addLayout(layout_left)

        self.setLayout(layout)

    def efficiencyMethodChanged(self, method: str) -> None:
        if method == "Manual":
            self.response.setEnabled(True)
            self.uptake.setEnabled(True)
            self.efficiency.setEnabled(True)
        elif method == "Reference":
            self.response.setEnabled(True)
            self.uptake.setEnabled(True)
            self.efficiency.setEnabled(False)
        elif method == "Mass Response (None)":
            self.response.setEnabled(False)
            self.uptake.setEnabled(False)
            self.efficiency.setEnabled(False)

        self.optionsChanged.emit()

    def isComplete(self) -> bool:
        method = self.efficiency_method.currentText()
        if method == "Manual":
            return all(
                [
                    self.dwelltime.hasAcceptableInput(),
                    self.response.hasAcceptableInput(),
                    self.uptake.hasAcceptableInput(),
                    self.efficiency.hasAcceptableInput(),
                ]
            )
        elif method == "Reference":
            return all(
                [
                    self.dwelltime.hasAcceptableInput(),
                    self.response.hasAcceptableInput(),
                    self.uptake.hasAcceptableInput(),
                ]
            )
        elif method == "Mass Response (None)":
            return all(
                [
                    self.dwelltime.hasAcceptableInput(),
                ]
            )
