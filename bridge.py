#!/usr/bin/python3
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QThread, QObject, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QSystemTrayIcon, QDesktopWidget

import consoleUi
import serial, glob, time
import sys, subprocess, yaml


global serialState
serialState = False

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
    data = str(result).replace("[",'')
    data = data.replace("]",'')
    data = data.replace("'",'')
    if data == "":
        data = "none"
    return data

class serialRead(QObject):
    finished = pyqtSignal()
    connectButton = pyqtSignal()
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
                    ser.flushInput()
                    self.consoleWrite.emit(data)
                    fault = 0
                    reconnect = False

                    if Dialog.ui.parserCheckbox.isChecked():
                        #if !exist: self.consDoleWrite.emit("Could not load parser script") #@!
                        parser = Dialog.ui.parserText.text()
                        data = data[2:].rstrip()
                        run = subprocess.run(["python",parser, data], timeout=1, stdout=subprocess.PIPE)

                        if Dialog.ui.parseroutCheckbox.isChecked():
                            output = run.stdout.decode("ASCII")
                            self.consoleWrite.emit(output)
                        run.stdout.flush()

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
        super().__init__();
        self.form = formUpdate()
        self.form.connectButton.connect(self.onConnectButton)
        self.form.sendButton.connect(self.onSendButton)

        self.ui = consoleUi.Ui_Dialog()
        self.ui.setupUi(self)
        self.ui.connectButton.clicked.connect(self.form.connect)
        self.ui.sendButton.clicked.connect(self.form.send)
        self.ui.resetButton.clicked.connect(self.onResetButton)
        self.ui.menuList.selectionModel().selectionChanged.connect(self.menuListEvent)

        self.ui.startupCheckbox.clicked.connect(self.autoconnectCheckboxEvent)
        self.ui.reconnectCheckbox.clicked.connect(self.autoreconnectCheckboxEvent)
        self.ui.minimizeCheckbox.clicked.connect(self.minimizeCheckboxEvent)
        self.ui.lograwCheckbox.clicked.connect(self.rawCheckboxEvent)
        self.ui.logcsvCheckbox.clicked.connect(self.csvCheckboxEvent)
        self.ui.parserCheckbox.clicked.connect(self.parserCheckboxEvent)
        self.ui.savelastCheckbox.clicked.connect(self.savelastCheckboxEvent)
        self.ui.parseroutCheckbox.clicked.connect(self.parseroutCheckboxEvent)

        self.serialread = serialRead()
        self.serialread.consoleWrite.connect(self.onConsoleWrite)
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

        try:
            settings = self.loadSettings()
            if settings["settings"]["autoconnect"]:
                self.ui.startupCheckbox.setChecked(True)

            if settings["settings"]["autoreconnect"]:
                self.ui.reconnectCheckbox.setChecked(True)

            if settings["settings"]["savelastconnection"]:
                self.ui.savelastCheckbox.setChecked(True)

            if settings["settings"]["startminimized"]:
                self.ui.minimizeCheckbox.setChecked(True)

            if settings["settings"]["csvlog"]:
                self.ui.logcsvCheckbox.setChecked(True)
                self.ui.logcsvText.setEnabled(False)

            if settings["settings"]["rawlog"]:
                self.ui.lograwCheckbox.setChecked(True)
                self.ui.lograwText.setEnabled(False)

            if settings["settings"]["parser"]:
                self.ui.parserCheckbox.setChecked(True)
                self.ui.parserText.setEnabled(False)

            if settings["settings"]["parserStdout"]:
                self.ui.parseroutCheckbox.setChecked(True)

            self.ui.deviceText.setText(settings["settings"]["device"])
            self.ui.baudrateText.setText(settings["settings"]["baudrate"])
            self.ui.baudrateText.setText(settings["settings"]["baudrate"])
            self.ui.lograwText.setText(settings["settings"]["lograwFile"])
            self.ui.logcsvText.setText(settings["settings"]["logcsvFile"])
            self.ui.parserText.setText(settings["settings"]["parserFile"])

        except:
            print("Warning: settings file not found or corrupted") #@!
        
        icon = QtGui.QIcon('icon.svg')
        self.trayIcon = QSystemTrayIcon(self)
        self.trayIcon.setIcon(icon)
        self.trayIcon.activated.connect(self.trayClickEvent)
        self.trayIcon.show()

        if self.ui.startupCheckbox.isChecked():
            self.onConnectButton()

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
        self.ui.consoleText.append(str(i))
        print(i)

    def onSendButton(self):
        global serialState, ser
        if serialState and self.ui.sendText.text():
            cmd = self.ui.sendText.text() + "\n"
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
                    self.saveSettings("settings","device",device)
                    self.saveSettings("settings","baudrate",baudrate)

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

    def loadSettings(self):
        f = open('settings.yml')
        dataMap = yaml.safe_load(f)
        f.close()
        return dataMap
        
    def saveSettings(self,settings,device,value):
        dataMap = self.loadSettings()
        f = open('settings.yml', "w")
        dataMap[settings][device] = value
        yaml.dump(dataMap, f, default_flow_style=False)
        f.close()

    def menuListEvent(self):
        self.ui.stackedWidget.setCurrentIndex(self.ui.menuList.currentRow())

    def csvCheckboxEvent(self):
        self.saveSettings("settings","csvlog",self.ui.logcsvCheckbox.isChecked())
        self.ui.logcsvText.setEnabled(not self.ui.logcsvCheckbox.isChecked())

    def rawCheckboxEvent(self):
        self.saveSettings("settings","rawlog",self.ui.lograwCheckbox.isChecked())
        self.ui.lograwText.setEnabled(not self.ui.lograwCheckbox.isChecked())

    def parseroutCheckboxEvent(self):
        self.saveSettings("settings","parserStdout",self.ui.parseroutCheckbox.isChecked())

    def parserCheckboxEvent(self):
        self.saveSettings("settings","parser",self.ui.parserCheckbox.isChecked())
        self.ui.parserText.setEnabled(not self.ui.parserCheckbox.isChecked())

    def autoconnectCheckboxEvent(self):
        self.saveSettings("settings","autoconnect",self.ui.startupCheckbox.isChecked())

    def autoreconnectCheckboxEvent(self):
        self.saveSettings("settings","autoreconnect",self.ui.reconnectCheckbox.isChecked())

    def savelastCheckboxEvent(self):
        self.saveSettings("settings","savelastconnection",self.ui.savelastCheckbox.isChecked())

    def minimizeCheckboxEvent(self):
        self.saveSettings("settings","startminimized",self.ui.minimizeCheckbox.isChecked())

if __name__=='__main__':
    app =  QtWidgets.QApplication(sys.argv)
    Dialog = initGui()

    sshFile="consoleUi.css"
    with open(sshFile,"r") as fh:
        Dialog.setStyleSheet(fh.read())
    
    if not Dialog.ui.minimizeCheckbox.isChecked():
        Dialog.show()
    sys.exit(app.exec_())