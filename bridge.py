#!/usr/bin/python3
#https://github.com/arduino/Arduino/blob/master/build/shared/manpage.adoc
import serial
import glob
import sys
import os
import json
import time
import argparse
import subprocess
from PyQt5 import QtCore, QtGui, QtWidgets, uic
from PyQt5.QtCore import QThread, QObject, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QDesktopWidget, QMainWindow, QSystemTrayIcon
import QtHistory

LOCAL = os.path.dirname(os.path.realpath(__file__))
if not os.path.exists(LOCAL + "/db"):
    os.makedirs(LOCAL + "/db")
PREFERENCES_DB = LOCAL + "/db/preferences.json"
PROFILES_DB = LOCAL + "/db/profiles.json"

class preferences(object):
    def __init__(self):
        if os.path.isfile(PREFERENCES_DB) and os.stat(PREFERENCES_DB).st_size > 0:
            with open(PREFERENCES_DB) as f:
                self.db = json.load(f)
        else:
            self.db = \
            {
                'general': { 'autoconnect': True, 'reconnect': True, 'timestamp': False, 'shell': False },
                'standalone': { 'tray_icon': True, 'minimize': True, 'icon_online': '%local/online.svg',
                'icon_offline': '%local/offline.svg', 'input_file': '%local/db/input', 'parse': True },
                'parsers': { '%local/parsers/rf_remote.py': True, '%local/parsers/if_remote.py': False }
            }
            with open(PREFERENCES_DB, "w+") as f:
                f.write(json.dumps(self.db, indent=2, sort_keys=False))
        self.load()

    def load(self):
        self.autoconnect = self.db["general"]["autoconnect"]
        self.reconnect = self.db["general"]["reconnect"]
        self.timestamp = self.db["general"]["timestamp"]
        self.shell = self.db["general"]["shell"]
        self.tray_icon = self.db["standalone"]["tray_icon"]
        self.minimize = self.db["standalone"]["minimize"]
        self.parse = self.db["standalone"]["parse"]
        self.icon_online = self.db["standalone"]["icon_online"].replace("%local", LOCAL)
        self.icon_offline = self.db["standalone"]["icon_offline"].replace("%local", LOCAL)
        self.input_file = self.db["standalone"]["input_file"].replace("%local", LOCAL)
        with open(self.input_file, "w+") as f:
            f.close()

    def save(self, name, entry, value):
        self.db[name][entry] = value
        with open(PREFERENCES_DB, "w+") as f:
            f.write(json.dumps(self.db, indent=2, sort_keys=False))
        self.load()

class profile(object):
    def __init__(self, entry):
        self.path = entry
        self.name = entry.rsplit('/', 1)[-1]

        if os.path.isfile(PROFILES_DB) and os.stat(PROFILES_DB).st_size > 0:
            with open(PROFILES_DB) as f:
                self.db = json.load(f)
        else:
            self.db = {}

        if not self.name in self.db:
            self.db[self.name] = \
            {
                'verify_cmd': 'arduino --verify %file',
                'upload_cmd': 'arduino --upload -v --board arduino:avr:nano --port %port %file',
                'baudrate': '9600'
            }

            #if self.name == "standalone":
            #    self.db[self.name]['port'] = '/dev/ttyUSB0'
            #else:
            #    self.db[self.name]['port'] = '/dev/ttyUSB1'
            self.db[self.name]['port'] = '/dev/ttyUSB0'

            with open(PROFILES_DB, 'w') as f:
                f.write(json.dumps(self.db, indent=2, sort_keys=False))
            print("# New profile created for '" + self.name + "'")
        self.load()

    def load(self):
        with open(PROFILES_DB) as f:
            self.db = json.load(f)
        self.port = self.db[self.name]["port"]
        self.baudrate = self.db[self.name]["baudrate"]
        self.verify_cmd = self.db[self.name]["verify_cmd"]
        self.upload_cmd = self.db[self.name]["upload_cmd"]

    def save(self, entry, value):
        self.load()
        self.db[self.name][entry] = value
        with open(PROFILES_DB, "w+") as f:
            f.write(json.dumps(self.db, indent=2, sort_keys=False))

def execute(output, cmd, path=None):
    if not path:
        path = profile.path
    cmd = cmd.replace("%port", profile.port)
    cmd = cmd.replace("%file", path)
    output("# " + cmd)

    if cmd.rsplit('.', 1)[-1] == "py":
        cmd = "python " + cmd

    if not preferences.shell:
        cmd = cmd.split()

    run = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=preferences.shell)
    for line in iter(run.stdout.readline, b''):
        data = line.decode().rstrip()
        output("> " + data)
    output("# Done")

def portsEnumerate():
    if sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('win'):
        ports = ['COM%s' % (i + 1) for i in range(256)]
    else:
        raise EnvironmentError('Unsupported platform')

    result = []
    for port in ports:
        try:
            session = serial.Serial(port)
            session.close()
            result.append(port)
        except (OSError, serial.SerialException):
            pass

    data = str(result)
    data = data.replace("[", '').replace("]", '').replace("'", '')
    if data == "":
        data = "none"
    return data

class serialObject(QObject):
    connectButton = pyqtSignal()
    buttonsEnable = pyqtSignal(bool)
    connectState = pyqtSignal(str)
    shout = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.cmd = ""

    @pyqtSlot()
    def loop(self):
        current, remaining = "", ""
        connected = False
        self.reset = False
        while True:
            if self.serialState:
                try:
                    #Read input from serial
                    if (self.session.inWaiting()>0):
                        data = self.session.readline()
                        data = data.decode("ASCII")
                        data = data.rstrip()
                        self.shout.emit(data)
                        connected = True

                        #Parse data from serial
                        if profile.name == "standalone" and preferences.parse:
                            for parser in preferences.db["parsers"]:
                                if preferences.db["parsers"][parser]:
                                    parser = parser.replace("%local", LOCAL)
                                    if os.path.isfile(parser):
                                        self.cmd = parser + " " + data
                                    else:
                                        self.shout.emit('Error: parser not found "' + parser + '"')

                    #Fetch commands from input_file
                    if preferences.input_file:
                        with open(preferences.input_file, 'r') as queue:
                            current = queue.readline().rstrip()
                            remaining = queue.read().splitlines(True)

                        if current or remaining:
                            self.shout.emit("# Sent '" + current + "'")
                            current = current + "\n"
                            self.session.write(current.encode())
                            with open(preferences.input_file, 'w') as queue:
                                queue.writelines(remaining)
                except:
                    self.shout.emit("# Connection lost: " + str(sys.exc_info()[0]))
                    self.connectState.emit("Disconnected")
                    connected = False

            elif not connected and preferences.reconnect:
                time.sleep(5)
                if not self.serialState:
                    self.connectButton.emit()

            #Execute command buffer
            if self.cmd != "":
                if self.reset and self.serialState:
                    self.connectButton.emit()

                self.buttonsEnable.emit(False)
                execute(self.shout.emit, self.cmd)
                self.buttonsEnable.emit(True)
                self.cmd = ""

                if self.reset and preferences.reconnect:
                    self.connectButton.emit()
                self.reset = False
            time.sleep(0.1)

class connectTimer(QObject):
    updateTimer = pyqtSignal()

    @pyqtSlot()
    def loop(self):
        while True:
            time.sleep(1)
            self.updateTimer.emit()

class initGui(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = uic.loadUi(LOCAL + '/gui.ui', self)

        self.serial = serialObject()
        self.serial.serialState = False
        self.ports = ""
        self.serial.shout.connect(self.shout)
        self.serial.connectState.connect(self.setConnectState)
        self.serial.connectButton.connect(self.connectButton_)
        self.serial.buttonsEnable.connect(self.buttonsEnable)
        self.serialThread = QThread() #move the Worker object to the Thread object
        self.serialThread.started.connect(self.serial.loop) #init serial read at startup
        self.serial.moveToThread(self.serialThread)
        self.serialThread.start()

        self.connectTimer = connectTimer()
        self.connectTimer.updateTimer.connect(self.updateTimer)
        self.timerThread = QThread()
        self.timerThread.started.connect(self.connectTimer.loop)
        self.connectTimer.moveToThread(self.timerThread)
        self.timerThread.start()

        if profile.name == "standalone":
            self.ui.cmdLabel.hide()
            self.ui.uploadText.hide()
            self.ui.resetButton.hide()
            self.ui.verifyButton.hide()
            self.ui.uploadButton.hide()

        self.setWindowTitle("Serial monitor (" + profile.name + ")")
        self.ui.reconnectCheckbox.setChecked(preferences.reconnect)
        self.ui.portText.setText(profile.port)
        self.ui.baudrateText.setText(profile.baudrate)
        self.ui.uploadText.setText(profile.upload_cmd)

        self.ui.reconnectCheckbox.clicked.connect(self.reconnectCheckboxEvent)
        self.ui.connectButton.clicked.connect(self.connectButton_)
        self.ui.sendButton.clicked.connect(self.sendButton_)
        self.ui.resetButton.clicked.connect(self.resetButton_)
        self.ui.verifyButton.clicked.connect(self.verifyButton_)
        self.ui.uploadButton.clicked.connect(self.uploadButton_)

        self.ui.sendText.keyPressEvent = self.sendTextEvent
        self.ui.portText.keyPressEvent = self.portTextEvent
        self.ui.baudrateText.keyPressEvent = self.baudrateTextEvent
        self.ui.uploadText.keyPressEvent = self.uploadTextEvent

        #History events
        self.sendTextHist = QtHistory.history(self.ui.sendText, "sendText", strict=False)
        self.sendTextHist.setFieldText.connect(self.setFieldText)
        self.portTextHist = QtHistory.history(self.ui.portText, "portText", strict=True)
        self.portTextHist.setFieldText.connect(self.setFieldText)
        self.baudrateTextHist = QtHistory.history(self.ui.baudrateText, "baudrateText", strict=True)
        self.baudrateTextHist.setFieldText.connect(self.setFieldText)
        self.uploadTextHist = QtHistory.history(self.ui.uploadText, "uploadText", strict=True)
        self.uploadTextHist.setFieldText.connect(self.setFieldText)

        if profile.name == "standalone" and preferences.tray_icon:
            self.trayIcon = QSystemTrayIcon()
            self.trayIcon.activated.connect(self.clickEvent)
            icon = QtGui.QIcon(preferences.icon_offline)
            self.trayIcon.setIcon(icon)
            self.trayIcon.show()

        if preferences.autoconnect:
            self.connectButton_()

    #Form actions
    def shout(self, output):
        if preferences.timestamp:
            output = time.strftime("[%H:%M:%S")+"] " + str(output)
        else:
            output = str(output)
        self.ui.consoleText.append(output)
        print(output)

    def sendButton_(self):
        command = self.ui.sendText.text()
        if self.serial.serialState and command:
            self.sendTextHist.save(command)
            self.shout("# Sent '" + command + "'")
            cmd = command + "\n"
            self.serial.session.write(cmd.encode())
            self.ui.sendText.clear()

    def resetButton_(self):
        if self.serial.serialState:
            self.shout("# Sent data terminal ready signal (reset)")
            self.serial.session.setDTR(False)
            time.sleep(0.022)
            self.serial.session.setDTR(True)

    def verifyButton_(self):
        profile.load()
        self.uploadTextHist.save(self.ui.uploadText.text())
        self.serial.cmd = profile.verify_cmd
        self.serial.reset = False

    def uploadButton_(self):
        profile.load()
        self.uploadTextHist.save(self.ui.uploadText.text())
        self.serial.cmd = profile.upload_cmd
        self.serial.reset = True

    def connectButton_(self):
        device = self.ui.portText.text()
        baudrate = self.ui.baudrateText.text()

        if self.serial.serialState:
            self.setConnectState("Disconnected")
        else:
            try:
                self.serial.session = serial.Serial(device, baudrate)
                self.shout("# Connecting to " + device + " (" + baudrate + ")...")
                self.serial.serialState = True

                #Send reset signal to AVR
                self.serial.session.setDTR(False)
                time.sleep(0.022)
                self.serial.session.setDTR(True)
                self.setConnectState("Connected")
                self.portTextHist.save(device)
                self.baudrateTextHist.save(baudrate)

            except serial.serialutil.SerialException:
                ports = str(portsEnumerate())
                if not self.ports == ports:
                    self.ports = ports
                    self.shout("# Error: connection failed, available ports: " + ports)
                self.serial.serialState = False

    def buttonsEnable(self, state):
        self.ui.connectButton.setEnabled(state)
        self.ui.resetButton.setEnabled(state)
        self.ui.verifyButton.setEnabled(state)
        self.ui.uploadButton.setEnabled(state)

    def updateTimer(self):
        if self.serial.serialState:
            elapsed = time.time() - self.startTime
            m, s = divmod(elapsed, 60)
            h, m = divmod(m, 60)
            elapsed = "%02d:%02d:%02d" % (h, m, s)
            status = "Connected, " + elapsed
        else:
            status = "Disconnected"

        self.statusBar().showMessage(status)
        if profile.name == "standalone" and preferences.tray_icon:
            self.trayIcon.setToolTip(status)

    def setConnectState(self, i):
        if i == "Connected":
            self.serial.serialState = True
            self.ui.sendButton.setEnabled(True)
            self.ui.resetButton.setEnabled(True)
            self.ui.connectButton.setText("Disconnect")
            self.startTime = time.time()
            self.shout("# New connection established")
            icon = QtGui.QIcon(preferences.icon_online)
        else:
            self.serial.serialState = False
            self.ui.sendButton.setEnabled(False)
            self.ui.resetButton.setEnabled(False)
            self.ui.connectButton.setText("Connect")
            self.serial.session.close()
            self.shout("# Disconnected")
            icon = QtGui.QIcon(preferences.icon_offline)

        if profile.name == "standalone" and preferences.tray_icon:
            self.trayIcon.setIcon(icon)

    #System tray icon
    def clickEvent(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()

    def minimize(self, event):
        if profile.name == "standalone" and preferences.tray_icon and event.type() == QtCore.QEvent.WindowStateChange:
            if self.windowState() and QtCore.Qt.WindowMinimized:
                self.setWindowState(QtCore.Qt.WindowNoState)
                self.clickEvent()

    #History
    def setFieldText(self, field, text):
        field.setText(text)

    def sendTextEvent(self, event):
        self.sendTextHist.move(event.key())
        QtWidgets.QLineEdit.keyPressEvent(self.ui.sendText, event)

    def portTextEvent(self, event):
        self.portTextHist.move(event.key())
        QtWidgets.QLineEdit.keyPressEvent(self.ui.portText, event)
        profile.save("port", self.ui.portText.text())

    def uploadTextEvent(self, event):
        self.uploadTextHist.move(event.key())
        QtWidgets.QLineEdit.keyPressEvent(self.ui.uploadText, event)
        profile.save("upload_cmd", self.ui.uploadText.text())

    def baudrateTextEvent(self, event):
        q = QtCore.Qt
        allowed = \
        {
            q.Key_0, q.Key_1, q.Key_2, q.Key_3, q.Key_4, q.Key_5, q.Key_6, q.Key_7, q.Key_8, q.Key_9,
            q.Key_Backspace, q.Key_Up, q.Key_Down, q.Key_Left, q.Key_Right
        }
        if event.key() in allowed or event.modifiers() == q.ControlModifier:
            self.baudrateTextHist.move(event.key())
            QtWidgets.QLineEdit.keyPressEvent(self.ui.baudrateText, event)
            profile.save("baudrate", self.ui.baudrateText.text())

    def reconnectCheckboxEvent(self):
        preferences.save("general", "reconnect", self.sender().isChecked())

if __name__== '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--open", default="standalone", help="open a file with the monitor", metavar='')
    parser.add_argument("-u", "--upload", help="upload firmware from a file", metavar='')

    preferences = preferences()
    args = parser.parse_args()
    if args.upload:
        profile = profile(args.upload)
        execute(print, profile.upload_cmd, profile.path)
        sys.exit(0)

    elif args.open:
        profile = profile(args.open)

    else:
        profile = profile("standalone")

    app = QtWidgets.QApplication(sys.argv)
    Dialog = initGui()
    if not profile.name == "standalone" or not preferences.minimize:
        Dialog.show()
    sys.exit(app.exec_())
