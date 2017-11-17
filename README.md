# Bridge
**Integration with vim:**

Bridge is a python application that communicate with Arduino using pySerial. It replace the Serial Monitor from the Arduino IDE and make use of it's command line interface to upload and verify code, all in a single window. It's purpose is to provide a more flexible and lighter way to interact with arduino compatible boards using an external editor. The script has a command line interface that ease the commucation with other applications. Each ino file opened with Bridge has it's own profile that save the last used board type (ie: uno, nano), serial port and baudrate. An example (.vimrc) is provided for the integration with Vim, using F1 to upload and F2 to open Bridge GUI with the current file.

![alt tag](https://raw.githubusercontent.com/willbelr/rf-bridge/master/pictures/gui.png)

**Standalone mode** (parsing with rf_remote.py)

When also using the provided arduino script, it may serve as a standalone application that can send data to serial input, and monitor serial output through external parser software, allowing easy development of arduino/python interactive scripts.

![alt tag](https://raw.githubusercontent.com/willbelr/rf-bridge/master/pictures/gui-standalone.png)

# Command line interface
  usage: bridge.py [-h] [-o] [-u]

  optional arguments:
  
  -h, --help:      show this help message and exit
  
  -o, --open:     open a file with the monitor
  
  -u, --upload:   upload firmware from a file

# Dependencies
- Python 3+, PyQt5 with Qt5-svg, PySerial
- Media parser exemple require python-daemon
- Made for Linux, might work on other platforms

# Example project (serial bridge for radio device)
This example is used to control media applications from a nRF24 remote (see https://github.com/willbelr/rf-remote).

Pinout
- A6: LED+ (RED)
- A7: LED+ (GREEN)
- D8: nRF24 (CE)
- D10: nRF24 (CSN)
- D11: nRF24 (MO)
- D12: nRF24 (MI)
- D13: nRF24 (SCK)
- 3.3V: nRF24+
- GND: nRF24-, 150 Ohm to LED-

Hardware
- nRF24L01P+PA+LNA wireless module
- AMS1117 5v to 3.3v Step-Down Power module
- Atmega 328P (nano package)
- Raspberry Pi transparent enclosure
- Bicolor LED

Pictures

![alt tag](https://raw.githubusercontent.com/willbelr/rf-bridge/master/pictures/bridge1.png)
![alt tag](https://raw.githubusercontent.com/willbelr/rf-bridge/master/pictures/bridge2.png)
