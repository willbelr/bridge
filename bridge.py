#!/usr/bin/python3
import subprocess
import serial
import glob
import yaml
import sys
import os
import time
from time import strftime
import pickle

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QThread, QObject, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QSystemTrayIcon, QDesktopWidget
from gui import gui

global serialState, histList, histPos, clientId
serialState = False
clientId = ""

try:
    with open('data/histList.pkl', 'rb') as f:
        histList = pickle.load(f)
except:
    histList = []
    pass
histPos = len(histList)


def loadSettings():
    f = open('data/settings.yml')
    dataMap = yaml.safe_load(f)
    f.close()
    return dataMap

def saveSettings(settings, device, value):
    dataMap = loadSettings()
    f = open('data/settings.yml', "w")
    dataMap[settings][device] = value
    yaml.dump(dataMap, f, default_flow_style=False)
    f.close()

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

    #fixme: regex? @!
    data = str(result).replace("[", '')
    data = data.replace("]", '')
    data = data.replace("'", '')
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
        global serialState, ser
        fault = 0
        reconnect = False

        while True:
            if serialState:
                try:
                    data = ser.readline()
                    data = data.decode("ASCII")
                    data = data.rstrip()
                    #ser.flushInput()
                    self.consoleWrite.emit(data)
                    fault = 0
                    reconnect = False

                    if str(data[:7]) == "client=":
                        global clientId
                        clientId = data[7:]
                        self.setStatusLabel.emit()

                    if Dialog.ui.parserCheckbox.isChecked():
                        parser = Dialog.ui.parserText.text()
                        if os.path.isfile(parser):
                            data = data[3:].rstrip()
                            run = subprocess.run(["python", parser, data], timeout=3, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                            if Dialog.ui.parseroutCheckbox.isChecked():
                                output = run.stdout.decode("ASCII")
                                if output:
                                    self.consoleWrite.emit("\n" + output)

                            if Dialog.ui.parsererrCheckbox.isChecked():
                                output = run.stderr.decode("ASCII")
                                if output:
                                    self.consoleWrite.emit("\n" + output)
                        else:
                            self.consoleWrite.emit("Error: could not open parser file")
                except:
                    fault = fault + 1
                    if fault == 5: #allow a delay after new connection
                        self.connectState.emit("Connection lost")
                        reconnect = True

            elif reconnect and Dialog.ui.reconnectCheckbox.isChecked():
                time.sleep(5)
                if not serialState:
                    self.connectButton.emit()

            time.sleep(0.1)
        self.finished.emit()

class formUpdate(QObject):
    sendButton = pyqtSignal()
    connectButton = pyqtSignal()

    @pyqtSlot()
    def send(self): # A slot takes no params
        self.sendButton.emit()

    @pyqtSlot()
    def connect(self):
        self.connectButton.emit()

class initGui(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.form = formUpdate()
        self.form.connectButton.connect(self.onConnectButton)
        self.form.sendButton.connect(self.onSendButton)

        self.ui = gui.Ui_Dialog()
        self.ui.setupUi(self)
        self.ui.connectButton.clicked.connect(self.form.connect)
        self.ui.sendButton.clicked.connect(self.form.send)
        self.ui.resetButton.clicked.connect(self.onResetButton)
        self.ui.menuList.selectionModel().selectionChanged.connect(self.menuListEvent)

        self.ui.sendText.keyPressEvent = self.sendTextEvent
        self.ui.clientText.keyPressEvent = self.clientTextKeyEvent
        #self.ui.clientText.focusOutEvent = self.clientTextFocusEvent
        self.ui.clientText.setMaxLength(4)
        self.ui.sendText.setMaxLength(27) #RH_NRF24_MAX_MESSAGE_LEN = 28

        self.ui.startupCheckbox.clicked.connect(self.autoconnectCheckboxEvent)
        self.ui.reconnectCheckbox.clicked.connect(self.autoreconnectCheckboxEvent)
        self.ui.minimizeCheckbox.clicked.connect(self.minimizeCheckboxEvent)
        self.ui.trayiconCheckbox.clicked.connect(self.trayiconCheckboxEvent)
        self.ui.lograwCheckbox.clicked.connect(self.rawCheckboxEvent)
        self.ui.logcsvCheckbox.clicked.connect(self.csvCheckboxEvent)
        self.ui.parserCheckbox.clicked.connect(self.parserCheckboxEvent)
        self.ui.savelastCheckbox.clicked.connect(self.savelastCheckboxEvent)
        self.ui.parseroutCheckbox.clicked.connect(self.parseroutCheckboxEvent)
        self.ui.parsererrCheckbox.clicked.connect(self.parsererrCheckboxEvent)
        self.ui.timestampCheckbox.clicked.connect(self.timestampCheckboxEvent)

        self.serialread = serialRead()
        self.serialread.consoleWrite.connect(self.onConsoleWrite)
        self.serialread.setStatusLabel.connect(self.onSetStatusLabel)
        self.serialread.connectState.connect(self.setConnectState)
        self.serialread.connectButton.connect(self.onConnectButton)

        self.thread = QThread() #move the Worker object to the Thread object
        self.thread.started.connect(self.serialread.loop) #init serial read at startup
        self.serialread.moveToThread(self.thread)
        self.serialread.finished.connect(self.thread.quit)
        #self.thread.finished.connect(app.exit)
        self.thread.start()

        self.center()
        self.ui.menuList.setFocus()

        if not os.path.isfile("data/settings.yml") or os.stat("data/settings.yml").st_size == 0:
            dataMap = \
            {'settings':
                {
                    'autoconnect': True,
                    'autoreconnect': False,
                    'baudrate': '9600',
                    'csvlog': False,
                    'device': '/dev/rf_bridge',
                    'logcsvfile': './data/log.csv',
                    'lograwfile': './data/log.txt',
                    'parser': True,
                    'parserfile': './parser/media.py',
                    'parserstdout': True,
                    'parserstderr': True,
                    'rawlog': False,
                    'savelastconnection': True,
                    'startminimized': False,
                    'trayicon': True,
                    'timestamp': True
                }
            }

            f = open('data/settings.yml', "w")
            yaml.dump(dataMap, f, default_flow_style=False)
            f.close()

        settings = loadSettings()
        if settings["settings"]["autoconnect"]:
            self.ui.startupCheckbox.setChecked(True)

        if settings["settings"]["autoreconnect"]:
            self.ui.reconnectCheckbox.setChecked(True)

        if settings["settings"]["savelastconnection"]:
            self.ui.savelastCheckbox.setChecked(True)

        if settings["settings"]["startminimized"]:
            self.ui.minimizeCheckbox.setChecked(True)

        if settings["settings"]["trayicon"]:
            self.ui.trayiconCheckbox.setChecked(True)

        if settings["settings"]["csvlog"]:
            self.ui.logcsvCheckbox.setChecked(True)
            self.ui.logcsvText.setEnabled(False)

        if settings["settings"]["rawlog"]:
            self.ui.lograwCheckbox.setChecked(True)
            self.ui.lograwText.setEnabled(False)

        if settings["settings"]["parser"]:
            self.ui.parserCheckbox.setChecked(True)
            self.ui.parserText.setEnabled(False)

        if settings["settings"]["parserstdout"]:
            self.ui.parseroutCheckbox.setChecked(True)

        if settings["settings"]["parserstderr"]:
            self.ui.parsererrCheckbox.setChecked(True)

        if settings["settings"]["timestamp"]:
            self.ui.timestampCheckbox.setChecked(True)

        self.ui.deviceText.setText(settings["settings"]["device"])
        self.ui.baudrateText.setText(settings["settings"]["baudrate"])
        self.ui.baudrateText.setText(settings["settings"]["baudrate"])
        self.ui.lograwText.setText(settings["settings"]["lograwfile"])
        self.ui.logcsvText.setText(settings["settings"]["logcsvfile"])
        self.ui.parserText.setText(settings["settings"]["parserfile"])

        icon = QtGui.QIcon('./gui/trayicon.svg')
        self.trayIcon = QSystemTrayIcon(self)
        self.trayIcon.setIcon(icon)
        self.trayIcon.activated.connect(self.trayClickEvent)
        self.ui.hideButton.setEnabled(self.ui.trayiconCheckbox.isChecked())
        if self.ui.trayiconCheckbox.isChecked():
            self.trayIcon.show()

        if self.ui.startupCheckbox.isChecked():
            self.onConnectButton()

    def clientTextKeyEvent(self, event):
        if event.key() == QtCore.Qt.Key_Return and self.ui.clientText.text():
            try:
                client = self.ui.clientText.text()
                foo = int(client, 0) #if int or hex #@! replace by regex
                if foo > 255:
                    foo = 255
                self.ui.clientText.setText(str(foo))

                if self.ui.clientText.text():
                    cmd = "setclient "+self.ui.clientText.text()
                    self.ui.sendText.setText(cmd)
                    self.ui.clientText.clear()
                    self.onSendButton()
                elif not self.ui.clientText.text():
                    self.ui.sendText.setText("pairing")
                    self.onSendButton()
            except:
                self.onConsoleWrite("Error: invalid client address, expected int or hex value")

        QtWidgets.QLineEdit.keyPressEvent(self.ui.clientText, event)

    def sendTextEvent(self, event):
        global histList, histPos

        key = event.key()
        histLen = len(histList)
        if histLen > 0 and (key == QtCore.Qt.Key_Down or key == QtCore.Qt.Key_Up):
            if key == QtCore.Qt.Key_Down:
                histPos += 1
            elif key == QtCore.Qt.Key_Up:
                histPos -= 1

            if histPos < 0:
                histPos = 0
            elif histPos >= histLen:
                histPos = histLen

            if histPos == histLen:
                self.ui.sendText.setText("")
            else:
                self.ui.sendText.setText(histList[histPos])

        QtWidgets.QLineEdit.keyPressEvent(self.ui.sendText, event)

    def trayClickEvent(self, click):
        if click == 3: #left
            if self.isVisible():
                self.hide()
            else:
                self.show()

        elif click == 1: #right
            app.exit()

    def center(self):
        frame = self.frameGeometry()
        screen = QDesktopWidget().availableGeometry().center()
        frame.moveCenter(screen)
        self.move(frame.topLeft())

    def onConsoleWrite(self, i):
        if self.ui.timestampCheckbox.isChecked():
            txt = strftime("[%H:%M:%S")+"] "+str(i)
        else:
            txt = str(i)
        self.ui.consoleText.append(txt)
        print(i)

        if self.ui.lograwCheckbox.isChecked():
            try:
                filename = self.ui.lograwText.text()
                with open(filename, 'a') as f:
                    f.write(txt+"\n")
                f.close
            except:
                self.ui.consoleText.append("Error: could not open raw logfile ("+filename+")")

    def onSendButton(self):
        global serialState, ser, histList, histPos
        command = self.ui.sendText.text()
        if serialState and command:

            histLen = len(histList)
            if histLen > 0:
                if not command == histList[histLen-1]:
                    histList.append(command)
                    if histLen > 20:
                        del histList[0]
                    histPos = len(histList)
                    try:
                        with open('data/histList.pkl', 'wb') as f:
                            pickle.dump(histList, f)
                    except:
                        print("Could not save pickle")
            else:
                histList.append(command)

            cmd = command + "\n"
            ser.write(cmd.encode())
            self.ui.sendText.clear()

    def onResetButton(self):
        global serialState, ser
        if serialState:
            ser.setDTR(False)
            time.sleep(0.022)
            ser.setDTR(True)

    def onConnectButton(self):
        device = self.ui.deviceText.text()
        baudrate = self.ui.baudrateText.text()
        global serialState, ser

        if serialState:
            ser.close()
            self.setConnectState("Disconnected")
        else:
            try:
                ser = serial.Serial(device, baudrate)
                self.onConsoleWrite("Connecting to " + device + " (" + baudrate + ")...")
                serialState = True

                #Send reset signal to AVR
                ser.setDTR(False)
                time.sleep(0.022)
                ser.setDTR(True)

                self.setConnectState("Connected")

                if self.ui.savelastCheckbox.isChecked():
                    saveSettings("settings", "device", device)
                    saveSettings("settings", "baudrate", baudrate)

            except serial.serialutil.SerialException:
                portsList = "Error: connection failed, available devices: " + str(portsEnumerate())
                self.onConsoleWrite(portsList)
                serialState = False

    def setConnectState(self, i):
        global serialState, ser

        if i == "Connected":
            serialState = True
            self.ui.sendButton.setEnabled(True)
            self.ui.connectButton.setText("Disconnect")
        else:
            serialState = False
            self.ui.sendButton.setEnabled(False)
            self.ui.connectButton.setText("Connect")
            self.onConsoleWrite(i)
            ser.close()
        self.onSetStatusLabel()

    def onSetStatusLabel(self):
        global serialState, clientId
        if serialState:
            self.ui.statusLabel.setText("Connected (0x"+clientId+")")
            saveSettings("settings", "clientId", clientId)
        else:
            self.ui.statusLabel.setText("Disconnected (0x"+clientId+")")

    def menuListEvent(self):
        self.ui.stackedWidget.setCurrentIndex(self.ui.menuList.currentRow())

    def csvCheckboxEvent(self):
        saveSettings("settings", "csvlog", self.ui.logcsvCheckbox.isChecked())
        self.ui.logcsvText.setEnabled(not self.ui.logcsvCheckbox.isChecked())

    def rawCheckboxEvent(self):
        saveSettings("settings", "rawlog", self.ui.lograwCheckbox.isChecked())
        self.ui.lograwText.setEnabled(not self.ui.lograwCheckbox.isChecked())

    def timestampCheckboxEvent(self):
        saveSettings("settings", "timestamp", self.ui.timestampCheckbox.isChecked())

    def parseroutCheckboxEvent(self):
        saveSettings("settings", "parserstdout", self.ui.parseroutCheckbox.isChecked())

    def parsererrCheckboxEvent(self):
        saveSettings("settings", "parserstderr", self.ui.parsererrCheckbox.isChecked())

    def parserCheckboxEvent(self):
        saveSettings("settings", "parser", self.ui.parserCheckbox.isChecked())
        self.ui.parserText.setEnabled(not self.ui.parserCheckbox.isChecked())

    def autoconnectCheckboxEvent(self):
        saveSettings("settings", "autoconnect", self.ui.startupCheckbox.isChecked())

    def autoreconnectCheckboxEvent(self):
        saveSettings("settings", "autoreconnect", self.ui.reconnectCheckbox.isChecked())

    def savelastCheckboxEvent(self):
        saveSettings("settings", "savelastconnection", self.ui.savelastCheckbox.isChecked())

    def minimizeCheckboxEvent(self):
        saveSettings("settings", "startminimized", self.ui.minimizeCheckbox.isChecked())

    def trayiconCheckboxEvent(self):
        saveSettings("settings", "trayicon", self.ui.trayiconCheckbox.isChecked())
        self.trayIcon.setVisible(not self.trayIcon.isVisible())
        self.ui.hideButton.setEnabled(self.ui.trayiconCheckbox.isChecked())

if __name__== '__main__':
    app = QtWidgets.QApplication(sys.argv)
    Dialog = initGui()

    sshFile = "./gui/gui.css"
    with open(sshFile, "r") as fh:
        Dialog.setStyleSheet(fh.read())

    if not Dialog.ui.minimizeCheckbox.isChecked():
        Dialog.show()
    sys.exit(app.exec_())
