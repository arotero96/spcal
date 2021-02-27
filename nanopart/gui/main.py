from PySide2 import QtCore, QtGui, QtWidgets

from nanopart.gui.options import OptionsWidget
from nanopart.gui.inputs import SampleWidget, ReferenceWidget
from nanopart.gui.results import ResultsWidget


class NanoPartWindow(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.tabs = QtWidgets.QTabWidget()
        self.tabs.currentChanged.connect(self.onTabChanged)

        self.options = OptionsWidget()
        self.sample = SampleWidget(self.options)
        self.reference = ReferenceWidget(self.options)
        self.results = ResultsWidget(self.options, self.sample, self.reference)

        self.reference.efficiency.textChanged.connect(self.options.setEfficiency)

        self.options.optionsChanged.connect(self.onInputsChanged)
        self.sample.optionsChanged.connect(self.onInputsChanged)
        self.sample.detectionsChanged.connect(self.onInputsChanged)

        self.tabs.addTab(self.options, "Options")
        self.tabs.addTab(self.sample, "Sample")
        self.tabs.addTab(self.reference, "Reference")
        self.tabs.addTab(self.results, "Results")
        self.tabs.setTabEnabled(self.tabs.indexOf(self.results), False)

        widget = QtWidgets.QWidget()

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.tabs, 1)
        widget.setLayout(layout)
        self.setCentralWidget(widget)

        self.createMenuBar()

        self.sample.loadFile("/home/tom/MEGA/Scripts/np/Sample 15 nm.csv")
        self.options.uptake.setBaseValue(0.000001566666666)
        self.options.response.setBaseValue(20e9)
        self.options.efficiency.setText("0.062")
        self.sample.density.setBaseValue(19.32e3)

    def createMenuBar(self) -> None:
        action_open_sample = QtWidgets.QAction("Open Sample", self)
        action_open_sample.triggered.connect(self.sample.dialogLoadFile)

        action_open_reference = QtWidgets.QAction("Open Reference", self)
        action_open_reference.triggered.connect(self.reference.dialogLoadFile)

        action_close = QtWidgets.QAction("Quit", self)
        action_close.triggered.connect(self.close)

        menufile = self.menuBar().addMenu("&File")
        menufile.addAction(action_open_sample)
        menufile.addAction(action_open_reference)
        menufile.addSeparator()
        menufile.addAction(action_close)

    def onInputsChanged(self) -> None:
        self.tabs.setTabEnabled(
            self.tabs.indexOf(self.results),
            self.readyForResultsMassResponse() or self.readyForResultsNebEff(),
        )

    # def onSampleComplete(self) -> None:
    #     complete = self.sample.isComplete()
    #     self.tabs.setTabEnabled(self.tabs.indexOf(self.results), complete)

    def onTabChanged(self, index: int) -> None:
        if index == self.tabs.indexOf(self.results):
            if self.readyForResultsNebEff():
                self.results.updateResultsNebEff()
            elif self.readyForResultsMassResponse():
                self.results.updateResultsMassResponse()
            else:
                raise ValueError("Results not ready!")

    def readyForResultsNebEff(self) -> bool:
        return self.options.isComplete() and self.sample.isComplete()

    def readyForResultsMassResponse(self) -> bool:
        return (
            self.reference.massresponse.hasAcceptableInput()
            and self.sample.isComplete()
        )
