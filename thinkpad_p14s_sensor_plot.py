#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pyqtgraph",
#   "qtconsole",
#   "pyside6==6.9.0", # https://github.com/pyqtgraph/pyqtgraph/issues/3328
#   "gitpython",
#   "psutil",
# ]
# ///

# suuuper messy live plot for my thinkpad p14s' sensors

import pyqtgraph as pg
import numpy
import pathlib, typing,sys
import psutil
from pyqtgraph.Qt import QtCore, QtGui
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout
#pyqtgraph.examples.run()

def discover_sensors():
    hwmon = pathlib.Path('/sys/class/hwmon')
    devices = {}
    for device in hwmon.iterdir():
        name_file = device / 'name'
        name = name_file.read_text().strip()
        print(f'looking for {device} {name} sensors')
        for sensor in device.iterdir():
            #print(f'sensor: {sensor.name}')
            sn = sensor.name.strip()
            if sn.endswith('_input'):
                devices[f'{name}.{sn}'] = sensor
    return devices

import typing

sensor_files: typing.Dict[str, pathlib.Path] = discover_sensors()

print(f'sensors: {sensor_files.keys()}')

allowed = [
        'coretemp.temp1_input',
        'nvme.temp1_input',
        'acpitz.temp1_input',
        'spd5118.temp1_input',
        'thinkpad.temp1_input',
        'thinkpad.temp2_input',
        'thinkpad.temp2_input',
        'thinkpad.fan1_input',
        'thinkpad.fan2_input',
        ]

data: typing.Dict[str, list[int]] = {}
for name in sensor_files:
    if name in allowed:
        data[name] = []

xAxis = []
xi = 0
fan_info_path = pathlib.Path("/proc/acpi/ibm/fan")

def fan_info():
    d = {}
    for l in fan_info_path.read_text().splitlines():
        k = l[0:l.find(':')]
        v = l[l.find('\t'):].strip()
        if k == 'commands':
            continue
        d[k] = v
    return d
last_fan_info = fan_info()
last_fan_changes = {}

def read_data():
    global xi
    xAxis.append(xi)
    xi += 1

    for name in data:
        prev = data[name]
        path = sensor_files[name]
        try:
            y = int(path.read_text().strip())
            prev.append(y)
        except:
            print(f'failed to read {path}')
            prev.append(-1)


read_data()
print(data)

class Latch:
    def __init__(self, value):
        self.last_value = value
        self.change_x = 0
        self.current_x = 0
    def push(self, value):
        try:
            if self.last_value != value:
                ret = (self.last_value, self.change_x, self.current_x + 1)
                self.last_value = value
                self.change_x = self.current_x + 1
                return ret
            return None
        finally:
            self.current_x += 1

class FuncSeries:
    def __init__(self, plot):
        self.plot = plot
        self.values = []
        self.xAxis = [0]
        self.x = 1
        self.values.append(self.sample())
    def update(self):
        self.xAxis.append(self.x)
        val = self.sample()
        self.values.append(val)
        self.plot.setData(self.xAxis, self.values)
        self.x += 1

    def sample(self):
        raise Exception("no")

class CpuFuncSeries(FuncSeries):
    def __init__(self, plot):
        super().__init__(plot)

    def sample(self):
        return psutil.cpu_percent(interval=None)

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        fi = fan_info()
        self.fan_mode_latch = Latch(fi['level'])
        self.layout = QVBoxLayout()
        self.graphWidget = pg.PlotWidget()
        self.graphWidget.addLegend()
        self.graphWidget.setYRange(0, 110000)
#        self.graphWidget.setXRange(0, 20)
        self.configGraphWidget = pg.PlotWidget()
        self.configGraphWidget.addLegend()
        self.configGraphWidget.setXLink(self.graphWidget)

        self.cpuGraphWidget = pg.PlotWidget()
        self.cpuGraphWidget.addLegend()
        self.cpuGraphWidget.setXLink(self.graphWidget)
        self.cpuGraphWidget.setYRange(0, 100)
        self.cpuGraphWidgetFuncSeries = [CpuFuncSeries(self.cpuGraphWidget.plot(name='cpu'))]

        self.graphWidgets = [self.graphWidget, self.configGraphWidget, self.cpuGraphWidget]
        for gw in self.graphWidgets:
            self.layout.addWidget(gw)

        self.cwidget = QWidget()
        self.cwidget.setLayout(self.layout)
        self.setCentralWidget(self.cwidget)

        self.legend = pg.LegendItem((80, 60), offset=(70, 20))
        self.plots = {}
        i = 0
        i_count = len(data)
        
        for name in data:
            pen = pg.mkPen(color=(255, 0, 0))
            if 'temp' in name:
                self.plots[name] = self.graphWidget.plot(pen=(i,i_count), name=name)
            else:
                self.plots[name] = self.configGraphWidget.plot(pen=(i,i_count), name=name)
            i += 1

        # plot data: x, y values
        #self.graphWidget.plot(hour, temperature)
        self.plot_update()
        self.timer = pg.QtCore.QTimer()
        def timer_func():
            self._timer_update()
        self.timer.timeout.connect(timer_func)
        self.timer.start(500)

    def plot_update(self):
        global fan_info
        for name in data:
            splot = self.plots[name]
            splot.setData(xAxis, data[name])
        fi = fan_info()
        level_changed = self.fan_mode_latch.push(fi['level'])
        if level_changed:
            prev_level, min_x, max_x = level_changed
            for g in self.graphWidgets:
                region = pg.LinearRegionItem(movable=False, values=[min_x, max_x])
                g.addItem(region)
                label = pg.InfLineLabel(region.lines[0], f'level: {prev_level}', position=0.70, rotateAxis=(1,0), anchor=(1,1))

        for func_series in self.cpuGraphWidgetFuncSeries:
            func_series.update()


        next_fan_info = fan_info()


        #self.graphWidget.setXRange(0, xAxis[-1])

    def _timer_update(self):
        read_data()
        self.plot_update()


app = QApplication(sys.argv)
w = MainWindow()
w.show()
app.exec()
