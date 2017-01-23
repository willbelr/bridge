# Bridge
	Bridge is a python application allowing to communicate and interact with various radio devices. Parsing scripts are easily added to suit differents needs. A parsing script exemple for controlling sound, playback and netflix is provided.

# Dependencies
	Require python 3 and modules pyqt5, pyserial, yaml
	Media parser require python-daemon
	Linux (may also work on other platforms)

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
	Nano (atmega 328P) microusb, cable
	Raspberry Pi transparent enclosure
	Bicolor LED (R1=150 Ohm?)
	Breadboard 400 contacts

# Installation (Arch Linux)
	1. Plug your device
	2. Find the serial id (Ex. for device /dev/ttyUSB0);
	udevadm info -a -n /dev/ttyUSB0 | grep '{serial}' | head -n1

	3. Create the file /etc/udev/rules.d/66-tty.rules;
	#Set the serial id (Ex. 0000:00:14.0) according to your device
	KERNEL=="ttyUSB*",MODE="0666"
	SUBSYSTEM=="tty", ATTRS{serial}=="0000:00:14.0", SYMLINK+="rf_bridge"
	
	4. Reboot
