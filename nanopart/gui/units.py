from PySide2 import QtCore, QtGui, QtWidgets
from nanopart.gui.widgets import ValidColorLineEdit

from typing import Dict, Tuple, Union

# mass_per_volume = {
#     "fg/L": 1e-18,
#     "pg/L": 1e-15,
#     "ng/L": 1e-12,
#     "μg/L": 1e-9,
#     "mg/L": 1e-6,
#     "g/L": 1e-3,
#     "kg/L": 1.0,
# }
# density = {"g/cm³": 1e-3 * 1e6, "kg/m³": 1.0}
# response_units = {
#     "counts/(pg/L)": 1e15,
#     "counts/(ng/L)": 1e12,
#     "counts/(μg/L)": 1e9,
#     "counts/(mg/L)": 1e6,
# }
# flowrate = {"ml/min": 1e-3 / 60.0, "ml/s": 1e-3, "L/min": 1.0 / 60.0, "L/s": 1.0}


# class SigFigValidator(QtWidgets.QDoubleValidator):
#     sigfig_re = re.compile("[^0]")

#     def __init__(
#         self,
#         bottom: float,
#         top: float,
#         decimals: int = 4,

#         parent: QtWidgets.QWidget = None,
#     ):
#         super().__init__(bottom, top, decimals, parent)

#     def count_significant(self, input: str) -> int:
#         sigfigs = input.replace(".", "").replace("E", "e").split("e")
#         match = self.sigfig_re.search(sigfigs)
#         if match:
#             return len(sigfigs) - match.start()
#         return -1

#     def validate(self, input: str, pos: int) -> Tuple[QtGui.QValidator.State, str, int]:
#         sigfigs = input.replace(".", "").replace("E", "e").split("e")[0]
#         match = self.sigfig_re.search(sigfigs)
#         if match:
#             count = len(sigfigs) - match.start()
#         else:
#             count = -1


class UnitsWidget(QtWidgets.QWidget):
    valueChanged = QtCore.Signal()

    def __init__(
        self,
        units: Dict[str, float],
        default_unit: str = None,
        value: float = None,
        validator: Tuple[float, float, int] = (0.0, 1e99, 10),
        invalid_color: QtGui.QColor = None,
        update_value_with_unit: bool = False,
        parent: QtWidgets.QWidget = None,
    ):
        super().__init__(parent)

        self.units = units
        self.update_value_with_unit = update_value_with_unit

        self.lineedit = ValidColorLineEdit(color_bad=invalid_color)
        self.lineedit.textChanged.connect(self.valueChanged)
        self.lineedit.setValidator(QtGui.QDoubleValidator(*validator))

        self.combo = QtWidgets.QComboBox()
        self.combo.addItems(units.keys())
        if default_unit is not None:
            self.combo.setCurrentText(default_unit)
        self.combo.currentTextChanged.connect(self.unitChanged)

        self._previous_unit = self.combo.currentText()

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.lineedit, 1)
        layout.addWidget(self.combo, 0)
        self.setLayout(layout)

    def setValue(self, value: Union[float, str]) -> None:
        if isinstance(value, float):
            decimals = self.lineedit.validator().decimals()
            self.lineedit.setText(f"{value:.{decimals}g}")
            if not self.lineedit.hasAcceptableInput():
                self.lineedit.setText(f"{value:.{decimals}f}")
        else:
            self.lineedit.setText(value)

    def baseValue(self) -> float:
        unit = self.combo.currentText()
        if not self.lineedit.hasAcceptableInput():
            return None
        return float(self.lineedit.text()) * self.units[unit]

    def setBaseValue(self, base: float) -> None:
        unit = self.combo.currentText()
        self.setValue(base / self.units[unit])

    def unitChanged(self, unit: str) -> None:
        if self.update_value_with_unit and self.lineedit.hasAcceptableInput():
            base = float(self.lineedit.text()) * self.units[self._previous_unit]
            self.setBaseValue(base)
        else:
            self.valueChanged.emit()
        self._previous_unit = unit

    def sync(self, other: "UnitsWidget") -> None:
        self.lineedit.textChanged.connect(other.lineedit.setText)
        other.lineedit.textChanged.connect(self.lineedit.setText)
        self.combo.currentTextChanged.connect(other.combo.setCurrentText)
        other.combo.currentTextChanged.connect(self.combo.setCurrentText)

    # Reimplementations
    def hasAcceptableInput(self) -> bool:
        return self.lineedit.hasAcceptableInput()

    def setReadOnly(self, readonly: bool) -> None:
        self.lineedit.setReadOnly(readonly)

    def setToolTip(self, text: str) -> None:
        self.lineedit.setToolTip(text)
        self.combo.setToolTip(text)
