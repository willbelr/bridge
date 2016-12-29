#!/usr/bin/env python
from time import strftime
import os.path
from serialbegin import *

def logStr(data):
	print(data.rstrip())
	with open(filename, 'a', newline="") as f:
		f.write(data)
	f.close

beginSerialConnection()

if not os.path.exists('log'):
	os.makedirs('log')

date = strftime("%Y-%b-%d")
filename = input("Enter log name: ")
if filename == "":
	filename = date.upper()
filenameLen = len('log/' + filename)
filename = 'log/' + filename + ".csv"

n = 0
while os.path.isfile(filename):
	n += 1
	filename = filename[:filenameLen]
	filename = filename + " (" + str(n) + ")" + ".csv"
	
print("\n\033[1m" + filename + "\033[0;0m\n")
logStr("Temps (s);Temperature (C);Setpoint (C);PWM\n")

while True:
	data = Serial.readline()
	data = str(data, 'ASCII')

	##Strip and log temperature
	if data[2:3] == "t":
		data = data[4:].replace(".",',')
		logStr(data)
	
Serial.close()
