#!/usr/bin/python3
import subprocess
import re
import time
import serialbegin

def is_running(process):
	s = subprocess.Popen(["ps", "-eo", "comm"],stdout=subprocess.PIPE)
	for x in s.stdout:
		if re.search(bytes('^'+process+'$', 'utf-8'), x):
			return True
	return False

serialbegin.serial_init("rf_bridge")
Serial = serialbegin.Serial

while True:
	data = Serial.readline()
	data = str(data, 'ASCII')
	data = data[2:].rstrip() #get "data" from "c;data"
	data = data.rstrip()
	print("\n\033[1m" + data + "\033[0;0m\n")

	if data == "U":
		subprocess.run(["amixer", "set", "Master", "3%+", "unmute"])
	elif data == "D":
		subprocess.run(["amixer", "set", "Master", "3%-", "unmute"])

	else:
		if is_running('chrome'):
			if data == "Z":
				subprocess.call(["xdotool", "search", "--onlyvisible", "--class", "Chrome", "windowfocus", "key", "Return"])
				time.sleep(0.5)

			elif data == "L":
				subprocess.call(["xdotool","key","shift+Tab"])
				time.sleep(0.1)

			elif data == "R":
				subprocess.call(["xdotool","key","Tab"])
				time.sleep(0.1)

			elif data == "N":
				print("a")
				foo = subprocess.Popen("urxvt -e /home/will/.local/share/scripts/pc/display-default.sh", stdout=subprocess.PIPE, shell=True)
				time.sleep(1.5)
				#subprocess.call(["xdotool","key","shift+Escape"])

		else:
			if not is_running('foobar2000.exe') and (data == "Z" or data == "L" or data == "R"): 
				subprocess.Popen(["wine", "/home/will/.foobar2000/foobar2000.exe", "/play"])

			elif data == "Z":
				subprocess.call(["wine", "/home/will/.foobar2000/foobar2000.exe", "/pause"])
				time.sleep(0.5)

			elif data == "L":
				subprocess.call(["wine", "/home/will/.foobar2000/foobar2000.exe", "/prev"])
				time.sleep(0.5)

			elif data == "R":
				subprocess.call(["wine", "/home/will/.foobar2000/foobar2000.exe", "/rand"])
				time.sleep(0.5)
			
			elif data == "N":
				print("b")
				foo = subprocess.Popen(["/home/will/.local/share/scripts/pc/netflix.sh"])
				time.sleep(1.5)
			
	Serial.flushInput()
Serial.close()