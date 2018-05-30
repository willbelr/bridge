#!/usr/bin/python3
import json
import logging
import os
import sys
import time
from PyQt5 import QtCore, QtGui, QtWidgets, QtDBus, QtSerialPort, uic
from PyQt5.QtCore import Qt, QObject, QProcess, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QMainWindow, QSystemTrayIcon

# Init logger
LOG_LEVEL = logging.INFO
LOG_FORMAT_DATE = "%H:%M:%S"
LOG_FORMAT = "%(levelname)s\t[%(asctime)s] %(message)s"
logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT, datefmt=LOG_FORMAT_DATE)
logging.SESSION = 32
logging.addLevelName(logging.SESSION, 'SESSION')
logger = logging.getLogger()
logger.session = lambda msg, *args: logger._log(logging.SESSION, msg, args)

# Load pre-compiled Ui files if available
try:
    import bridge.gui_main
except ImportError:
    logger.warning("Could not load pre-compiled ui modules")

# Define paths
LOCAL_DIR = os.path.dirname(os.path.realpath(__file__))
ICONS = LOCAL_DIR + "/icons/"
CONFIG_DIR = os.path.expanduser("~/.config/bridge/")
PREFERENCES_FILE = CONFIG_DIR + "preferences.json"
PROFILES_FILE = CONFIG_DIR + "profiles.json"
HISTORY_FILE = CONFIG_DIR + "history.json"
if not os.path.exists(CONFIG_DIR):
    os.makedirs(CONFIG_DIR)


class Preferences(object):
    def __init__(self):
        if os.path.isfile(PREFERENCES_FILE) and os.stat(PREFERENCES_FILE).st_size > 0:
            self.load()
        else:
            self.db = PREFERENCES_DEFAULT
            with open(PREFERENCES_FILE, "w") as f:
                f.write(json.dumps(self.db, indent=2, sort_keys=False))
            logger.info("Created preferences file")
        self.parse()

    def load(self):
        with open(PREFERENCES_FILE, "r") as f:
            self.db = json.load(f)
        logger.info("Loaded preferences database")

    def save(self, name, entry, value=None):
        self.db[name][entry] = value
        with open(PREFERENCES_FILE, "w") as f:
            f.write(json.dumps(self.db, indent=2, sort_keys=False))
        self.parse()
        logger.info("Saved preferences database")

    def parse(self):
        self.q = {}
        for category in self.db:
            if type(self.db[category]) is dict:
                for key in self.db[category]:
                    self.q[key] = self.db[category][key]
            else:
                self.q[category] = self.db[category]

    def query(self, entry):
        if entry not in self.q:
            db = {}
            for category in PREFERENCES_DEFAULT:
                for key in PREFERENCES_DEFAULT[category]:
                    db[key] = PREFERENCES_DEFAULT[category][key]

            self.q[entry] = db[entry]
            logger.error("Key '" + entry + "' is missing in preferences database, using default value (" + str(db[entry]) + ")")
        return self.q[entry]


class Profile(object):
    def __init__(self, path):
        self.path = path
        self.name = path.rsplit('/', 1)[-1].rsplit('.', 1)[0]
        self.fullname = path.rsplit('/', 1)[-1]
        if os.path.isfile(PROFILES_FILE) and os.stat(PROFILES_FILE).st_size > 0:
            self.load()
        else:
            self.db = {}
        if self.name not in self.db:
            self.db[self.name] = preferences.db["profile_default"]
            with open(PROFILES_FILE, 'w') as f:
                f.write(json.dumps(self.db, indent=2, sort_keys=False))
            logger.info("Created profile for '" + self.name + "'")
        self.parse()

    def load(self):
        with open(PROFILES_FILE) as f:
            self.db = json.load(f)
        logger.info("Loaded profiles database (" + self.name + ")")

    def save(self, entry=None, value=None):
        self.db[self.name][entry] = value
        with open(PROFILES_FILE, "w") as f:
            f.write(json.dumps(self.db, indent=2, sort_keys=False))
        self.parse()
        logger.info("Saved profile database (" + self.name + ")")

    def parse(self):
        if self.name in self.db:
            self.q = {}
            for entry in self.db[self.name]:
                self.q[entry] = self.db[self.name][entry]

    def query(self, entry):
        if entry not in self.q:
            self.q[entry] = PREFERENCES_DEFAULT["styleDefault"][entry]
            logger.error("Key '" + entry + "' is missing in profiles database, using default value (" + str(self.q[entry]) + ")")
        return self.q[entry]


class Slave(QtCore.QProcess):
    setButtonState = pyqtSignal(bool)
    setReconnectTimer = pyqtSignal(bool)
    setConnectState = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__()
        self.readyReadStandardOutput.connect(self.stdoutEvent)
        self.readyReadStandardError.connect(self.stderrEvent)
        self.errorOccurred.connect(self.errorEvent)
        self.finished.connect(self.finishEvent)
        self.parent = parent

    def execute(self, cmd, upload=False):
        if upload:
            # Load a profile to upload from cli
            global profile, preferences
            preferences = Preferences()
            profile = Profile(cmd)
            cmd = profile.query("upload_cmd")
            cmd = cmd.replace("%port", profile.query("port"))
        else:
            cmd = cmd.replace("%port", self.parent.ui.portBox.currentText())
            self.setReconnectTimer.emit(False)
            self.setConnectState.emit(False)
            self.setButtonState.emit(False)
        cmd = cmd.replace("%file", profile.path)
        self.shout("# " + cmd + "\n")
        self.start(cmd)

    def stdoutEvent(self):
        stdout = self.readAllStandardOutput()
        self.shout(stdout)

    def stderrEvent(self):
        stderr = self.readAllStandardError()
        self.shout(stderr)

    def finishEvent(self):
        self.setButtonState.emit(True)
        if preferences.query("reconnect"):
            self.setReconnectTimer.emit(True)

    def errorEvent(self, error):
        logger.error("# QProcess error (" + str(error) + ")")
        self.finishEvent()

    def shout(self, data):
        try:
            # Decode to utf8 if needed (byte object)
            data = bytes(data)
            data = data.decode("utf8", errors="ignore")
        except TypeError:
            pass

        if data and self.parent:
            self.parent.shout(data)
        elif data:
            self.print(data)

    def print(self, data):
        print(data, end="")


class QDBusServer(QObject):
    send = pyqtSignal(str)

    def __init__(self):
        QObject.__init__(self)
        self.__dbusAdaptor = QDBusServerAdapter(self)


class QDBusServerAdapter(QtDBus.QDBusAbstractAdaptor):
    QtCore.Q_CLASSINFO("D-Bus Interface", "org.bridge.session")
    QtCore.Q_CLASSINFO("D-Bus Introspection",
    '  <interface name="org.bridge.session">\n'
    '    <method name="send">\n'
    '      <arg direction="in" type="s" name="cmd"/>\n'
    '    </method>\n'
    '  </interface>\n')

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

    @pyqtSlot(str, result=str)
    def send(self, cmd):
        self.parent.send.emit(cmd)


class Serial(QtSerialPort.QSerialPort):
    setConnectState = pyqtSignal(bool)
    shout = pyqtSignal(str)
    execute = pyqtSignal(str)
    stopReconnect = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.readyRead.connect(self.read)
        self.errorOccurred.connect(self.errorEvent)
        if profile.name == "standalone":
            self.bus = QtDBus.QDBusConnection.sessionBus()
            self.server = QDBusServer()
            self.server.send.connect(self.send)
            self.bus.registerObject('/org/bridge/session', self.server)
            self.bus.registerService('org.bridge.session')

    def ports(self):
        availables = []
        for port in QtSerialPort.QSerialPortInfo.availablePorts():
            availables.append(port.systemLocation())
        if availables:
            availables = str(availables)
            return(availables.translate({ord(c): None for c in "[']"}))
        return("none")

    def connect(self, port, baudrate):
        self.setPortName(port)
        self.setBaudRate(baudrate)
        if self.open(QtCore.QIODevice.ReadWrite):
            self.setConnectState.emit(True)
            self.reset()
        else:
            self.setConnectState.emit(False)
            self.stopReconnect.emit()
            self.shout.emit("# Could not connect to device on port " + port + "\n")
            self.shout.emit("# Currently available ports: " + self.ports() + "\n")

    def read(self):
        if self.canReadLine():
            data = self.readLine()
            data = bytes(data).decode("utf8", errors="ignore")
            self.shout.emit("> " + data)

        # Parse data from serial
        if profile.name == "standalone" and preferences.query("parse"):
            for parser in preferences.db["parsers"]:
                if preferences.db["parsers"][parser]:
                    parser = parser.replace("%local", LOCAL_DIR)
                    parser = parser.replace("%config", CONFIG_DIR)
                    if os.path.isfile(parser):
                        self.execute.emit(parser + " " + data)
                    else:
                        self.shout.emit('Error: parser not found "' + parser + '"\n')

    def send(self, data):
        if "\\n" in data or "\\r" in data:
            data = data.replace("\\n", "\n")
            data = data.replace("\\r", "\r")
        else:
            data = data + "\n"
        self.shout.emit("# Sent " + repr(data) + "\n")
        self.write(data.encode())

    def reset(self):
        self.setDataTerminalReady(False)
        time.sleep(0.022)
        self.setDataTerminalReady(True)
        self.clear()
        self.shout.emit("# Sent data terminal ready signal (reset)\n")

    def errorEvent(self, event):
        if self.connected:
            if event == QtSerialPort.QSerialPort.ReadError or event == QtSerialPort.QSerialPort.TimeoutError:
                self.setConnectState.emit(False)
                self.shout.emit("# Connection lost\n")

class Main(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        # Load the ui file in case the gui modules are not loaded
        if "bridge.gui_main" in sys.modules:
            self.ui = bridge.gui_main.Ui_MainWindow()
            self.ui.setupUi(self)
        else:
            self.ui = uic.loadUi(LOCAL_DIR + '/gui_main.ui', self)

        self.connectTimer = QtCore.QTimer()
        self.connectTimer.timeout.connect(self.updateTimer)
        self.connectTimer.setInterval(1000)
        self.connectTimer.start()

        self.portTimer = QtCore.QTimer()
        self.portTimer.timeout.connect(self.resetPortsList)
        self.portTimer.setInterval(1000)
        self.portTimer.start()

        self.reconnectTimer = QtCore.QTimer()
        self.reconnectTimer.timeout.connect(self.reconnect)
        self.reconnectTimer.setInterval(1000) ##5000

        self.lastAvailables = []
        for port in QtSerialPort.QSerialPortInfo.availablePorts():
            self.ui.portBox.addItem(port.systemLocation())
            self.lastAvailables.append(port.systemLocation())

        self.serial = Serial()
        self.serial.connected = False
        self.serial.shout.connect(self.shout)
        self.serial.setConnectState.connect(self.setConnectState)
        self.serial.execute.connect(self.execute)
        self.serial.stopReconnect.connect(self.reconnectTimer.stop)
        self.slave = Slave(self)
        self.slave.setButtonState.connect(self.setButtonState)
        self.slave.setReconnectTimer.connect(self.setReconnectTimer)
        self.slave.setConnectState.connect(self.setConnectState)

        if preferences.query("autoconnect"):
            self.reconnectTimer.start(0)

        if profile.name == "standalone":
            self.ui.cmdLabel.hide()
            self.ui.uploadText.hide()
            self.ui.verifyButton.hide()
            self.ui.uploadButton.hide()

        self.setWindowTitle("Serial monitor (" + profile.fullname + ")")
        self.ui.reconnectCheckbox.setChecked(preferences.query("reconnect"))
        self.ui.autoconnectCheckbox.setChecked(preferences.query("autoconnect"))
        self.ui.baudrateText.setText(profile.query("baudrate"))
        self.ui.uploadText.setText(profile.query("upload_cmd"))
        self.ui.endBox.setCurrentText(profile.query("end"))
        self.ui.reconnectCheckbox.clicked.connect(self.reconnectCheckboxEvent)
        self.ui.autoconnectCheckbox.clicked.connect(self.autoconnectCheckboxEvent)
        self.ui.connectButton.clicked.connect(self.connectEvent)
        self.ui.sendButton.clicked.connect(self.send)
        self.ui.resetButton.clicked.connect(self.reset)
        self.ui.verifyButton.clicked.connect(self.verify)
        self.ui.uploadButton.clicked.connect(self.upload)

        self.ui.sendText.keyPressEvent = self.sendTextEvent
        self.ui.baudrateText.keyPressEvent = self.baudrateTextEvent
        self.ui.portBox.keyPressEvent = self.portBoxEvent
        self.ui.uploadText.keyPressEvent = self.uploadTextEvent
        self.ui.changeEvent = self.changeEvent

        # History events
        self.sendTextHist = History(self.ui.sendText, "sendText", strict=False)
        self.sendTextHist.setFieldText.connect(self.setFieldText)
        self.baudrateTextHist = History(self.ui.baudrateText, "baudrateText", strict=True)
        self.baudrateTextHist.setFieldText.connect(self.setFieldText)
        self.uploadTextHist = History(self.ui.uploadText, "uploadText", strict=True)
        self.uploadTextHist.setFieldText.connect(self.setFieldText)

        if profile.name == "standalone" and preferences.query("tray_icon"):
            self.trayIcon = QSystemTrayIcon()
            self.trayIcon.activated.connect(self.clickEvent)
            icon = QtGui.QIcon(ICONS + "offline.svg")
            self.trayIcon.setIcon(icon)
            self.trayIcon.show()

    def execute(self, cmd):
        self.slave.execute(cmd)

    def shout(self, output):
        if preferences.query("timestamp"):
            output = time.strftime("[%H:%M:%S")+"] " + str(output)
        else:
            output = str(output)
        logger.session(output.rstrip())

        # Lock scrolling position if below maximum
        sbCurrent = self.ui.consoleText.verticalScrollBar().value()
        sbMax = self.ui.consoleText.verticalScrollBar().maximum()
        self.ui.consoleText.moveCursor(QtGui.QTextCursor.End)
        self.ui.consoleText.insertPlainText(output)
        if sbCurrent == sbMax:
            sbMax = self.ui.consoleText.verticalScrollBar().maximum()
            self.ui.consoleText.verticalScrollBar().setValue(sbMax)
        else:
            self.ui.consoleText.verticalScrollBar().setValue(sbCurrent)

    def send(self):
        command = self.ui.sendText.text()
        if self.serial.connected and command:
            self.sendTextHist.save(command)
            end = self.ui.endBox.currentText()
            profile.save("end", end)
            cmd = command + end
            self.serial.send(cmd)
            self.ui.sendText.clear()

    def reset(self):
        if self.serial.connected:
            self.serial.reset()

    def verify(self):
        ##profile.load()
        self.uploadTextHist.save(self.ui.uploadText.text())
        self.execute(profile.query("verify_cmd"))

    def upload(self):
        ##profile.load()
        if self.ui.uploadText.text():
            self.uploadTextHist.save(self.ui.uploadText.text())
            self.execute(profile.query("upload_cmd"))

    def connectEvent(self):
        if self.serial.connected:
            self.reconnectTimer.stop()
        else:
            self.reconnectTimer.start()
        self.connect()

    def connect(self):
        if self.serial.connected:
            self.setConnectState(False)
        else:
            device = self.ui.portBox.currentText()
            baudrate = self.ui.baudrateText.text()
            self.shout("# Connecting to " + device + " (" + baudrate + ")...\n")
            self.serial.connect(device, int(baudrate))

    def reconnect(self):
        if not self.serial.connected:
            self.resetPortsList()
            self.connect()

    def updateTimer(self):
        if self.serial.connected:
            s = time.time() - self.startTime
            m, s = divmod(s, 60)
            h, m = divmod(m, 60)
            d, h = divmod(h, 24)
            elapsed = "%01d days, %02d:%02d:%02d" % (d, h, m, s)
            status = "Connected, " + elapsed
        else:
            status = "Disconnected"

        self.statusBar().showMessage(status)
        if profile.name == "standalone" and preferences.query("tray_icon"):
            self.trayIcon.setToolTip(status)

    def setConnectState(self, connected):
        if connected:
            self.serial.connected = True
            self.ui.sendButton.setEnabled(True)
            self.ui.resetButton.setEnabled(True)
            self.ui.connectButton.setText("Disconnect")
            self.startTime = time.time()
            self.baudrateTextHist.save(self.ui.baudrateText.text())
            self.shout("# New connection established\n")
            icon = QtGui.QIcon(ICONS + "online.svg")
            profile.save("port", self.ui.portBox.currentText())
            profile.save("baudrate", self.ui.baudrateText.text())
        ##elif self.serial.connected:
        else:
            self.serial.connected = False
            self.ui.sendButton.setEnabled(False)
            self.ui.resetButton.setEnabled(False)
            self.ui.connectButton.setText("Connect")
            self.serial.close()
            self.shout("# Disconnected\n")
            icon = QtGui.QIcon(ICONS + "offline.svg")

        if profile.name == "standalone" and preferences.query("tray_icon"):
            self.trayIcon.setIcon(icon)

    def resetPortsList(self):
        availables = []
        for port in QtSerialPort.QSerialPortInfo.availablePorts():
            availables.append(port.systemLocation())
        if not availables == self.lastAvailables:
            self.ui.portBox.clear()
            self.ui.portBox.addItems(availables)
            prefered = profile.query("port")
            if prefered in availables:
                self.ui.portBox.setCurrentText(prefered)
            if preferences.query("reconnect") and len(availables) > len(self.lastAvailables):
                self.reconnectTimer.start(0)
            self.lastAvailables = availables

    def setReconnectTimer(self, state):
        if state:
            self.reconnectTimer.start()
        else:
            self.reconnectTimer.stop()

    def setButtonState(self, state):
        self.ui.connectButton.setEnabled(state)
        self.ui.resetButton.setEnabled(state)
        self.ui.verifyButton.setEnabled(state)
        self.ui.uploadButton.setEnabled(state)

    def clickEvent(self):
        # System tray icon
        if self.isVisible():
            self.hide()
        else:
            self.show()

    def changeEvent(self, event):
        # Override minimize event
        if event.type() == QtCore.QEvent.WindowStateChange:
            if self.ui.windowState() & Qt.WindowMinimized:
                if profile.name == "standalone" and preferences.query("tray_icon"):
                    self.setWindowState(Qt.WindowNoState)
                    self.clickEvent()

    def setFieldText(self, field, text):
        field.setText(text)

    def sendTextEvent(self, event):
        self.sendTextHist.move(event.key())
        QtWidgets.QLineEdit.keyPressEvent(self.ui.sendText, event)

    def uploadTextEvent(self, event):
        self.uploadTextHist.move(event.key())
        QtWidgets.QLineEdit.keyPressEvent(self.ui.uploadText, event)
        profile.save("upload_cmd", self.ui.uploadText.text())

    def portBoxEvent(self, event):
        QtWidgets.QComboBox.keyPressEvent(self.ui.portBox, event)
        profile.save("port", self.ui.portBox.currentText())

    def baudrateTextEvent(self, event):
        allowed = \
        {
            Qt.Key_0, Qt.Key_1, Qt.Key_2, Qt.Key_3, Qt.Key_4, Qt.Key_5, Qt.Key_6, Qt.Key_7, Qt.Key_8, Qt.Key_9,
            Qt.Key_Backspace, Qt.Key_Up, Qt.Key_Down, Qt.Key_Left, Qt.Key_Right
        }
        if event.key() in allowed or event.modifiers() == Qt.ControlModifier:
            self.baudrateTextHist.move(event.key())
            QtWidgets.QLineEdit.keyPressEvent(self.ui.baudrateText, event)
            profile.save("baudrate", self.ui.baudrateText.text())

    def reconnectCheckboxEvent(self):
        preferences.save("general", "reconnect", self.sender().isChecked())

    def autoconnectCheckboxEvent(self):
        preferences.save("general", "autoconnect", self.sender().isChecked())


class History(QObject):
    setFieldText = pyqtSignal(object, str)

    def __init__(self, field, entry, strict):
        super().__init__()
        self.strict = strict
        self.field = field
        self.entry = entry
        try:
            with open(HISTORY_FILE) as f:
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

                if length >= 20:  # Roll
                    del self.list[0]
                self.pos = len(self.list)
                self.dump()
        else:
            self.list.append(command)
            self.dump()

    def dump(self):
        try:
            with open(HISTORY_FILE, 'r') as f:
                self.tree = json.load(f)
        except:
            self.tree = {}

        with open(HISTORY_FILE, 'w+') as f:
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


PREFERENCES_DEFAULT = \
{
    'general':
    {
        'reconnect': True,
        'autoconnect': True,
        'timestamp': False
    },
    'standalone':
    {
        'tray_icon': True,
        'minimize': True,
        'parse': True
    },
    'parsers':
    {
        '%config/parsers/rf_remote.py': False,
        '%config/parsers/if_remote.py': False
    },
    'profile_default':
    {
        'verify_cmd': 'arduino --verify %file',
        'upload_cmd': 'arduino --upload -v --board arduino:avr:nano --port %port %file',
        'baudrate': '9600',
        'port': '/dev/ttyUSB0',
        'end': '\n'
    }
}


def main(args="standalone"):
    global preferences, profile
    logger.info("Init of a new instance (%s)" % args)
    preferences = Preferences()
    profile = Profile(args)
    app = QtWidgets.QApplication([])
    daemon = Main()
    if not profile.name == "standalone" or not preferences.query("minimize"):
        daemon.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
