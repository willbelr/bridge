# Bridge
Bridge is a python application allowing to communicate and interact with various radio devices. Parsing modules are easily added to suit differents needs. As a starter, two parser exemples are provided. They are used to control media applications from a nrf24 remote (see https://github.com/willbelr/rf_remote).

![alt tag](https://raw.githubusercontent.com/willbelr/rf_bridge/master/pictures/gui.png)

# Dependencies
	Require python 3 and modules pyqt5, qt5-svg, pyserial, yaml
	Media parser exemple require python-daemon
	Tested on Linux (may also work on other platforms)

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
	4. Set the serial id (Ex. 0000:00:14.0) according to your device
	KERNEL=="ttyUSB*",MODE="0666"
	SUBSYSTEM=="tty", ATTRS{serial}=="0000:00:14.0", SYMLINK+="rf_bridge"
	
	Or
	
	If you use multiple chinese clones on the same computer, they might all have the
	same serial number. Therefore, to avoid conflicts the devices must always be
	plugged in the same slot, and identified with their KERNELS id instead.
	
	Again you can find the kernels id using;
	udevadm info -a -n /dev/ttyUSBx
	
	Ex. KERNEL=="ttyUSB*", KERNELS=="1-2", SYMLINK+="rf_bridge"
	
	5. Reboot to load the new udev rules
	

# Picutres
![alt tag](https://raw.githubusercontent.com/willbelr/rf_bridge/master/pictures/bridge1.jpg)
![alt tag](https://raw.githubusercontent.com/willbelr/rf_bridge/master/pictures/bridge2.jpg)
