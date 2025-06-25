#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pyqtgraph",
#   "qtconsole",
#   "pyside6==6.9.0",
#   "gitpython",
#   "numpy",
# ]
# ///

from PySide6.QtWidgets import QMainWindow, QApplication
import pyqtgraph as pg
import sys


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.graphWidget = pg.PlotWidget()
        self.setCentralWidget(self.graphWidget)

        hour = [1,2,3,4,5,6,7,8,9,10]
        temperature = [30,32,34,32,33,31,29,32,35,45]

        #self.graphWidget.setBackground('w')
        pen = pg.mkPen(color=(255, 0, 0))
        p = self.graphWidget.plot(hour, temperature, pen=pen)
        self.graphWidget.setXRange(0,15)
        self.graphWidget.setYRange(0, 50)


app = QApplication(sys.argv)
main = MainWindow()
main.show()
app.exec()
