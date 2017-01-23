#!/usr/bin/python3
import sys
import subprocess
import re
import time
import daemon

def is_running(process):
	s = subprocess.Popen(["ps", "-eo", "comm"],stdout=subprocess.PIPE)
	for x in s.stdout:
		if re.search(bytes('^'+process+'$', 'utf-8'), x):
			return True
	return False

def parse(data):
	if data == "U":
		subprocess.run(["amixer", "set", "Master", "3%+", "unmute"])
	elif data == "D":
		subprocess.run(["amixer", "set", "Master", "3%-", "unmute"])

	else:
		if is_running('chrome'):
			if data == "Z":
				subprocess.run(["xdotool", "search", "--onlyvisible", "--class", "Chrome", "windowfocus", "key", "Return"])
				time.sleep(0.5)

			elif data == "L":
				subprocess.run(["xdotool","key","shift+Tab"])
				time.sleep(0.1)

			elif data == "R":
				subprocess.run(["xdotool","key","Tab"])
				time.sleep(0.1)

			elif data == "N":
				subprocess.run(["bash", "-c", "/home/will/scripts/pc/display-default.sh"])
				time.sleep(1.5)

		else:
			if not is_running('foobar2000.exe') and (data == "Z" or data == "L" or data == "R"):
				with daemon.DaemonContext():
					subprocess.run(["wine", "/home/will/.foobar2000/foobar2000.exe", "/play"])

			elif data == "Z":
				subprocess.run(["wine", "/home/will/.foobar2000/foobar2000.exe", "/pause"])
				time.sleep(0.3)

			elif data == "L":
				subprocess.run(["wine", "/home/will/.foobar2000/foobar2000.exe", "/prev"])
				time.sleep(0.3)

			elif data == "R":
				subprocess.run(["wine", "/home/will/.foobar2000/foobar2000.exe", "/rand"])
				time.sleep(0.3)
			
			elif data == "N":
				print("b")
				subprocess.run(["bash", "-c", "/home/will/scripts/pc/netflix.sh"])
				time.sleep(1.5)	

if __name__ == "__main__":
	cmd = str(sys.argv[1])
	parse(cmd)