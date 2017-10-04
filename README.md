# Bridge
04/10/2017: Major update, readme file will be updated soon

Bridge is a python application allowing to communicate and interact with various radio devices. Parsing modules are easily added to suit differents needs. As a starter, two parser exemples are provided. They are used to control media applications from a nrf24 remote (see https://github.com/willbelr/rf-remote).

![alt tag](https://raw.githubusercontent.com/willbelr/rf-bridge/master/pictures/gui.png)

# Dependencies
	Require python 3 and pyqt5, qt5-svg, pyserial
	Media parser exemple require python-daemon
	Made for Linux, might work on other platforms

# Pinout
	A6: LED+ (RED)
	A7: LED+ (GREEN)
	D8: nRF24 (CE)
	D10: nRF24 (CSN)
	D11: nRF24 (MO)
	D12: nRF24 (MI)
	D13: nRF24 (SCK)

	3.3V: nRF24+
	GND: nRF24-, 150 Ohm to LED-

# Hardware
	nRF24L01P+PA+LNA wireless module, antenna
	AMS1117 5v to 3.3v Step-Down Power module
	Atmega 328P (nano package) microusb, cable
	Raspberry Pi transparent enclosure
	Bicolor LED (R1=150 Ohm?)
	Breadboard...

# Picutres
![alt tag](https://raw.githubusercontent.com/willbelr/rf-bridge/master/pictures/bridge1.jpg)
![alt tag](https://raw.githubusercontent.com/willbelr/rf-bridge/master/pictures/bridge2.jpg)
