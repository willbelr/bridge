#!/usr/bin/python3
import time
import serial
import sys
import glob

def serial_ports():
	if sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
		ports = glob.glob('/dev/tty[A-Za-z]*')

	elif sys.platform.startswith('win'):
		ports = ['COM%s' % (i + 1) for i in range(256)]

	result = []
	for port in ports:
		try:
			s = serial.Serial(port)
			s.close()
			result.append(port)
		except (OSError, serial.SerialException):
			pass
	return result

class serial_init:
	def __init__(self, device=""):
		if device == "":
			print("Available serial ports:")
			print(serial_ports())
			print("\n")

			if sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
				port = input("Enter serial port number for /dev/tty* (default is /dev/rf_bridge):\n")
				if port == "":
					port = "/dev/rf_bridge"
				else:
					port = "/dev/tty" + str(port)
				
			elif sys.platform.startswith('win'):
				port = input("Enter serial port number for COMx: ")
				if port == "":
					port = "COM0"
				else:
					port = "COM" + str(port)

			else:
				raise EnvironmentError('Unsupported platform')

		else:
			print("Port preset as: /dev/" + device)
			port = "/dev/" + device

		##Open serial connection
		global Serial
		Serial = serial.Serial(port, 9600)
		Serial.setDTR(False) # Drop DTR
		time.sleep(0.022)    # Read somewhere that 22ms is what the UI does.
		Serial.setDTR(True)  # UP the DTR back