import os
import json
from PyQt5 import QtCore
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
HISTORY_DB = os.path.dirname(os.path.realpath(__file__)) + "/db/history.json"

class history(QObject):
    setFieldText = pyqtSignal(object, str)

    def __init__(self, field, entry, strict):
        super().__init__()
        self.strict = strict
        self.field = field
        self.entry = entry
        try:
            with open(HISTORY_DB) as f:
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
            with open(HISTORY_DB, 'r') as f:
                self.tree = json.load(f)
        except:
            self.tree = {}

        with open(HISTORY_DB, 'w+') as f:
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
