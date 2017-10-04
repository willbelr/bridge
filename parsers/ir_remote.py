#!/usr/bin/python3
import subprocess
import urllib.request
import sys
import re

def is_running(process):
	s = subprocess.Popen(["ps", "-eo", "comm"],stdout=subprocess.PIPE)
	for x in s.stdout:
		if re.search(bytes('^'+process+'$', 'utf-8'), x):
			return True
	return False

def parse(data):
	if data == "NEC 20df02fd": #UP
		subprocess.run(["xdotool", "mousemove_relative", "--", "0", "-50"])
	elif data == "NEC 20df827d": #DOWN
		subprocess.run(["xdotool", "mousemove_relative", "0", "50"])
	elif data == "NEC 20dfe01f": #LEFT
		subprocess.run(["xdotool", "mousemove_relative", "--", "-50", "0"])
	elif data == "NEC 20df609f": #RIGHT
		subprocess.run(["xdotool", "mousemove_relative", "50", "0"])
	elif data == "NEC 20df22dd": #Click
		subprocess.run(["xdotool", "click", "1"])

if __name__ == "__main__":
	cmd = str(sys.argv[1])
	parse(cmd)