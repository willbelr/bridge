#!/usr/bin/python3
import serial
import glob
import sys
import os
import subprocess
import json
import time
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QThread, QObject, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QSystemTrayIcon, QDesktopWidget
from gui import gui

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
            s = serial.Serial(port)
            s.close()
            result.append(port)
        except (OSError, serial.SerialException):
            pass

    data = str(result)
    data = data.replace("[", '').replace("]", '').replace("'", '')
    if data == "":
        data = "none"
    return data

class serialRead(QObject):
    finished = pyqtSignal()
    connectButton = pyqtSignal()
    setStatusLabel = pyqtSignal()
    consoleWrite = pyqtSignal(str)
    connectState = pyqtSignal(str)

    @pyqtSlot()
    def loop(self):
        fault = 0
        reconnect = False
        self.clientId = "00"

        while True:
            if self.serialState:
                try:
                    data = self.ser.readline()
                    data = data.decode("ASCII")
                    data = data.rstrip()
                    self.consoleWrite.emit(data)
                    fault = 0
                    reconnect = False

                    if str(data[:7]) == "client=": #@! todo: decent parsing function
                        self.clientId = data[7:]
                        self.setStatusLabel.emit()

                    if Dialog.ui.parserCheckbox.isChecked():
                        parser = Dialog.ui.parserText.text()
                        if os.path.isfile(parser):
                            data = data[3:].rstrip()
                            parserName = parser.rsplit('/', 1)[-1]
                            run = subprocess.run(["python", parser, data], timeout=5, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                            
                            if Dialog.ui.parseroutCheckbox.isChecked():
                                output = run.stdout.decode("ASCII")

                                if output:
                                    self.consoleWrite.emit(parserName + ";\n" + output)

                            if Dialog.ui.parsererrCheckbox.isChecked():
                                output = run.stderr.decode("ASCII")
                                if output:
                                    self.consoleWrite.emit(parserName + ";\n" + output)
                        else:
                            self.consoleWrite.emit("Error: could not open parser file")
                except:
                    fault = fault + 1
                    if fault == 5: #allow a delay after new connection
                        self.connectState.emit("Connection lost")
                        reconnect = True

            elif reconnect and Dialog.ui.reconnectCheckbox.isChecked():
                time.sleep(5)
                if not self.serialState:
                    self.connectButton.emit()

            time.sleep(0.1)
        self.finished.emit()

class connectTimer(QObject):
    updateTimer = pyqtSignal()

    @pyqtSlot()
    def loop(self):
        while True:
            time.sleep(1)
            self.updateTimer.emit()

class history(QObject):
    setFieldText = pyqtSignal(object, str)

    def load(self, field, entry, strict):
        selfPath = os.path.dirname(os.path.realpath(__file__))
        self.historyFile = selfPath + '/data/history.json'
        self.strict = strict
        self.field = field
        self.entry = entry
        try:
            with open(self.historyFile) as f:
                self.tree = json.load(f)
                self.list = self.tree[entry]
        except:
            self.tree = {}
            self.list = []
        self.pos = len(self.list)

    def save(self, command):
        length = len(self.list)
        if length > 0:

            fault = False
            if self.strict:
                for x in self.list:
                    if x == command:
                        fault = True

            if not command == self.list[length-1] and not fault:
                self.list.append(command)

                if length >= 20: #roll
                    del self.list[0]
                self.pos = len(self.list)
                self.dump()
        else:
            self.list.append(command)
            self.dump()

    def dump(self):
        try:
            with open(self.historyFile, 'r') as f:
                self.tree = json.load(f)
        except:
            self.tree = {}

        with open(self.historyFile, 'w+') as f:
            self.tree[self.entry] = self.list
            f.write(json.dumps(self.tree, indent=2, sort_keys=False))

    @pyqtSlot()
    def move(self, key):
        length = len(self.list)
        if length > 0 and (key == QtCore.Qt.Key_Down or key == QtCore.Qt.Key_Up):
            if key == QtCore.Qt.Key_Down:
                self.pos += 1
            elif key == QtCore.Qt.Key_Up:
                self.pos -= 1

            if self.pos < 0:
                self.pos = 0
            elif self.pos >= length:
                self.pos = length

            if self.pos == length:
                self.setFieldText.emit(self.field, "")
            else:
                self.setFieldText.emit(self.field, self.list[self.pos])

def loadSettings():
    selfPath = os.path.dirname(os.path.realpath(__file__))
    with open(selfPath + '/data/settings.json') as f:
        dataMap = json.load(f)
    return dataMap

def saveSettings(settings, device, value):
    selfPath = os.path.dirname(os.path.realpath(__file__))
    dataMap = loadSettings()
    dataMap[settings][device] = value
    with open(selfPath + '/data/settings.json', "w+") as f:
        f.write(json.dumps(dataMap, indent=2, sort_keys=False))

    f.close()

def getInt(value):
    try:
        foo = int(value) #int
    except:
        try:
            foo = int(value, 16) #hex
            if foo > 255:
                foo = 255
        except:
            return False
    return str(foo)

class initGui(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.ui = gui.Ui_Dialog()
        self.ui.setupUi(self)

        self.serialread = serialRead()
        self.serialread.serialState = False
        self.serialread.consoleWrite.connect(self.consoleWrite)
        self.serialread.setStatusLabel.connect(self.setStatusLabel)
        self.serialread.connectState.connect(self.setConnectState)
        self.serialread.connectButton.connect(self.connectButton)

        self.serialThread = QThread() #move the Worker object to the Thread object
        self.serialThread.started.connect(self.serialread.loop) #init serial read at startup
        self.serialread.moveToThread(self.serialThread)
        self.serialread.finished.connect(self.serialThread.quit)
        self.serialThread.start()

        self.connectTimer = connectTimer()
        self.connectTimer.updateTimer.connect(self.updateTimer)
        self.timerThread = QThread()
        self.timerThread.started.connect(self.connectTimer.loop)
        self.connectTimer.moveToThread(self.timerThread)
        self.timerThread.start()

        self.ui.startupCheckbox.clicked.connect(self.genericCheckboxEvent)
        self.ui.reconnectCheckbox.clicked.connect(self.genericCheckboxEvent)
        self.ui.minimizeCheckbox.clicked.connect(self.genericCheckboxEvent)
        self.ui.savelastCheckbox.clicked.connect(self.genericCheckboxEvent)
        self.ui.parseroutCheckbox.clicked.connect(self.genericCheckboxEvent)
        self.ui.parsererrCheckbox.clicked.connect(self.genericCheckboxEvent)
        self.ui.timestampCheckbox.clicked.connect(self.genericCheckboxEvent)

        self.ui.parserCheckbox.clicked.connect(self.parserCheckboxEvent)
        self.ui.trayiconCheckbox.clicked.connect(self.trayiconCheckboxEvent)

        self.ui.connectButton.clicked.connect(self.connectButton)
        self.ui.sendButton.clicked.connect(self.sendButton)
        self.ui.resetButton.clicked.connect(self.resetButton)
        self.ui.menuList.selectionModel().selectionChanged.connect(self.menuListEvent)
        
        self.ui.clientText.keyPressEvent = self.clientTextEvent
        self.ui.serverText.keyPressEvent = self.serverTextEvent
        self.ui.sendText.keyPressEvent = self.sendTextEvent
        self.ui.parserText.keyPressEvent = self.parserTextEvent
        self.ui.deviceText.keyPressEvent = self.deviceTextEvent
        self.ui.baudrateText.keyPressEvent = self.baudrateTextEvent

        #Center
        #frame = self.frameGeometry()
        #screen = QDesktopWidget().availableGeometry().center()
        #frame.moveCenter(screen)
        #self.move(frame.topLeft())

        self.ui.menuList.setFocus()
        self.ui.clientText.setMaxLength(4)
        self.ui.serverText.setMaxLength(4)
        self.ui.sendText.setMaxLength(27) #RH_NRF24_MAX_MESSAGE_LEN = 28
        self.applySettings()
        self.loadHistory()

        icon = QtGui.QIcon(os.path.dirname(os.path.realpath(__file__)) + '/gui/trayicon.svg')
        self.trayIcon = QSystemTrayIcon(self)
        self.trayIcon.setIcon(icon)
        self.trayIcon.activated.connect(self.trayClickEvent)
        self.ui.hideButton.setEnabled(self.ui.trayiconCheckbox.isChecked())
        if self.ui.trayiconCheckbox.isChecked():
            self.trayIcon.show()

        if self.ui.startupCheckbox.isChecked():
            self.connectButton()

    #Load settings and history
    def applySettings(self):
        selfPath = os.path.dirname(os.path.realpath(__file__))
        if not os.path.isfile(selfPath + "/data/settings.json") or os.stat(selfPath + "/data/settings.json").st_size == 0:
            dataMap = \
            {'settings':
                {
                    'baudrateText': '9600',
                    'deviceText': '/dev/rf_bridge',
                    'parserCheckbox': True,
                    'parserText': selfPath + '/parser/media.py',
                    'trayiconCheckbox': True,
                    'startupCheckbox': True,
                    'reconnectCheckbox': True,
                    'savelastCheckbox': True,
                    'minimizeCheckbox': False,
                    'parseroutCheckbox': True,
                    'parsererrCheckbox': True,
                    'timestampCheckbox': True
                }
            }

            if not os.path.exists(selfPath + "/data"):
                os.makedirs(selfPath + "/data")

            with open("data/settings.json", 'w+') as f:
                f.write(json.dumps(dataMap, indent=2, sort_keys=False))

        settings = loadSettings()
        if settings["settings"]["startupCheckbox"]:
            self.ui.startupCheckbox.setChecked(True)

        if settings["settings"]["reconnectCheckbox"]:
            self.ui.reconnectCheckbox.setChecked(True)

        if settings["settings"]["savelastCheckbox"]:
            self.ui.savelastCheckbox.setChecked(True)

        if settings["settings"]["minimizeCheckbox"]:
            self.ui.minimizeCheckbox.setChecked(True)

        if settings["settings"]["parseroutCheckbox"]:
            self.ui.parseroutCheckbox.setChecked(True)

        if settings["settings"]["parsererrCheckbox"]:
            self.ui.parsererrCheckbox.setChecked(True)

        if settings["settings"]["timestampCheckbox"]:
            self.ui.timestampCheckbox.setChecked(True)

        if settings["settings"]["trayiconCheckbox"]:
            self.ui.trayiconCheckbox.setChecked(True)

        if settings["settings"]["parserCheckbox"]:
            self.ui.parserCheckbox.setChecked(True)
            self.ui.parserText.setEnabled(False)

        self.ui.deviceText.setText(settings["settings"]["deviceText"])
        self.ui.baudrateText.setText(settings["settings"]["baudrateText"])
        self.ui.baudrateText.setText(settings["settings"]["baudrateText"])
        self.ui.parserText.setText(settings["settings"]["parserText"])

    def loadHistory(self):
        self.sendTextHist = history()
        self.sendTextHist.load(self.ui.sendText, "commands", strict=False)
        self.sendTextHist.setFieldText.connect(self.setFieldText)

        self.deviceTextHist = history()
        self.deviceTextHist.load(self.ui.deviceText, "devices", strict=True)
        self.deviceTextHist.setFieldText.connect(self.setFieldText)

        self.baudrateTextHist = history()
        self.baudrateTextHist.load(self.ui.baudrateText, "baudrates", strict=True)
        self.baudrateTextHist.setFieldText.connect(self.setFieldText)

        self.parserTextHist = history()
        self.parserTextHist.load(self.ui.parserText, "parsers", strict=True)
        self.parserTextHist.setFieldText.connect(self.setFieldText)

        self.clientTextHist = history()
        self.clientTextHist.load(self.ui.clientText, "clients", strict=True)
        self.clientTextHist.setFieldText.connect(self.setFieldText)

        self.serverTextHist = history()
        self.serverTextHist.load(self.ui.serverText, "servers", strict=True)
        self.serverTextHist.setFieldText.connect(self.setFieldText)
    
    #Form actions
    def clientTextEvent(self, event):
        self.clientTextHist.move(event.key())
        if event.key() == QtCore.Qt.Key_Return and self.ui.clientText.text():

            client = getInt(self.ui.clientText.text())
            if client:
                self.ui.clientText.setText(client)

                if self.ui.clientText.text():
                    cmd = "setclient "+self.ui.clientText.text()
                    self.ui.sendText.setText(cmd)
                    self.sendButton()
                elif not self.ui.clientText.text():
                    self.ui.sendText.setText("pairing")
                    self.sendButton()
                self.clientTextHist.save(self.ui.clientText.text())
                self.ui.clientText.clear()
            else:
                self.consoleWrite("Error: invalid client address, expected int or hex value")

        QtWidgets.QLineEdit.keyPressEvent(self.ui.clientText, event)

    def serverTextEvent(self, event): #@! todo
        self.serverTextHist.move(event.key())

        if event.key() == QtCore.Qt.Key_Return and self.ui.serverText.text():
            server = getInt(self.ui.serverText.text())
            if server:
                print(server)
                self.serverTextHist.save(self.ui.serverText.text())
                self.ui.serverText.clear()
            else:
                self.consoleWrite("Error: invalid server address, expected int or hex value")

        QtWidgets.QLineEdit.keyPressEvent(self.ui.serverText, event)

    def consoleWrite(self, i):
        if self.ui.timestampCheckbox.isChecked():
            txt = time.strftime("[%H:%M:%S")+"] "+str(i)
        else:
            txt = str(i)
        self.ui.consoleText.append(txt)
        print(i)

    def sendButton(self):
        command = self.ui.sendText.text()

        if self.serialread.serialState and command:
            self.sendTextHist.save(command)
            cmd = command + "\n"
            self.serialread.ser.write(cmd.encode())
            self.ui.sendText.clear()

    def resetButton(self):
        if self.serialread.serialState:
            self.serialread.ser.setDTR(False)
            time.sleep(0.022)
            self.serialread.ser.setDTR(True)

    def connectButton(self):
        device = self.ui.deviceText.text()
        baudrate = self.ui.baudrateText.text()

        if self.serialread.serialState:
            self.setConnectState("Disconnected")
        else:
            try:
                self.serialread.ser = serial.Serial(device, baudrate)
                self.consoleWrite("Connecting to " + device + " (" + baudrate + ")...")
                self.serialread.serialState = True

                #Send reset signal to AVR
                self.serialread.ser.setDTR(False)
                time.sleep(0.022)
                self.serialread.ser.setDTR(True)

                self.setConnectState("Connected")

                if self.ui.savelastCheckbox.isChecked():
                    saveSettings("settings", "deviceText", device)
                    saveSettings("settings", "baudrateText", baudrate)
                self.deviceTextHist.save(device)
                self.baudrateTextHist.save(baudrate)

            except serial.serialutil.SerialException:
                portsList = "Error: connection failed, available devices: " + str(portsEnumerate())
                self.consoleWrite(portsList)
                self.serialread.serialState = False

    def setStatusLabel(self):
        if self.serialread.serialState:
            self.ui.clientLabel.setText("Client address (0x" + self.serialread.clientId + ")")
            self.ui.serverLabel.setText("Server address (0x00)") #@!

            saveSettings("settings", "clientId", self.serialread.clientId)
        else:
            self.ui.statusLabel.setText("Disconnected")

    def updateTimer(self):
        if self.serialread.serialState:
            elapsed = time.time() - self.startTime
            m, s = divmod(elapsed, 60)
            h, m = divmod(m, 60)
            elapsed = "%02d:%02d:%02d" % (h, m, s)
            self.ui.statusLabel.setText("Connected, " + elapsed+ "")
        else:
            self.ui.statusLabel.setText("Disconnected")

    def setConnectState(self, i):
        if i == "Connected":
            self.serialread.serialState = True
            self.ui.sendButton.setEnabled(True)
            self.ui.connectButton.setText("Disconnect")
            self.startTime = time.time()
        else:
            self.serialread.serialState = False
            self.ui.sendButton.setEnabled(False)
            self.ui.connectButton.setText("Connect")
            self.consoleWrite(i)
            self.serialread.ser.close()
        self.setStatusLabel()

    def trayClickEvent(self, click):
        if click == 3: #left
            if self.isVisible():
                self.hide()
            else:
                self.show()

        elif click == 1: #right
            app.exit()

    def changeEvent(self, event): #Minimize to tray
        if self.ui.trayiconCheckbox.isChecked() and event.type() == QtCore.QEvent.WindowStateChange:
            if self.windowState() and QtCore.Qt.WindowMinimized:
                self.setWindowState(QtCore.Qt.WindowNoState)
                self.trayClickEvent(3)

    def menuListEvent(self):
        self.ui.stackedWidget.setCurrentIndex(self.ui.menuList.currentRow())

    #History
    def setFieldText(self, field, text):
        field.setText(text)

    def sendTextEvent(self, event): #@! redundant
        self.sendTextHist.move(event.key())
        QtWidgets.QLineEdit.keyPressEvent(self.ui.sendText, event)

    def parserTextEvent(self, event):
        self.parserTextHist.move(event.key())
        QtWidgets.QLineEdit.keyPressEvent(self.ui.parserText, event)

    def deviceTextEvent(self, event):
        self.deviceTextHist.move(event.key())
        QtWidgets.QLineEdit.keyPressEvent(self.ui.deviceText, event)

    def baudrateTextEvent(self, event):
        self.baudrateTextHist.move(event.key())
        QtWidgets.QLineEdit.keyPressEvent(self.ui.baudrateText, event)

    #YAML
    def genericCheckboxEvent(self):
        saveSettings("settings", self.sender().objectName(), self.sender().isChecked())

    def trayiconCheckboxEvent(self):
        saveSettings("settings", "trayiconCheckbox", self.ui.trayiconCheckbox.isChecked())
        self.trayIcon.setVisible(not self.trayIcon.isVisible())
        self.ui.hideButton.setEnabled(self.ui.trayiconCheckbox.isChecked())

    def parserCheckboxEvent(self):
        saveSettings("settings", "parserCheckbox", self.ui.parserCheckbox.isChecked())
        self.ui.parserText.setEnabled(not self.ui.parserCheckbox.isChecked())

        parser = self.ui.parserText.text()
        if parser and self.ui.parserCheckbox.isChecked():
            self.parserTextHist.save(parser)

if __name__== '__main__':
    app = QtWidgets.QApplication(sys.argv)
    Dialog = initGui()

    with open(os.path.dirname(os.path.realpath(__file__)) + "/gui/gui.css", "r") as fh:
        Dialog.setStyleSheet(fh.read())

    if not Dialog.ui.trayiconCheckbox.isChecked() or not Dialog.ui.minimizeCheckbox.isChecked():
        Dialog.show()

    sys.exit(app.exec_())

"""
todo:
    #instaurer systeme d'identification indépendant de USBttyX, avec clientID.
    #ajouter button "Export" > dialog de sauvegarde, proposant .csv et .txt

    server prefix handling, serverId in label
    short checkbox names Chbx
    normalize names, ie: self.serialread.ser.readline

    rf_bridge:
        save last clientid to eeprom
        server handler
        if setclient = 0, client=all
"""