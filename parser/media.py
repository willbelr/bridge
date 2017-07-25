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
	if data == "U":
		subprocess.run(["amixer", "set", "Master", "3%+", "unmute"])
	elif data == "D":
		subprocess.run(["amixer", "set", "Master", "3%-", "unmute"])

	else:
		if is_running('vlc'): #VLC mode
			try:
				if data == "B2":
					urllib.request.urlopen('http://127.0.0.1:8080/requests/status.xml?command=pl_pause')

				elif data == "L":
					urllib.request.urlopen('http://127.0.0.1:8080/requests/status.xml?command=seek&val=-5')

				elif data == "R":
					urllib.request.urlopen('http://127.0.0.1:8080/requests/status.xml?command=seek&val=+5')
			except urllib.error.URLError:
				print("Error: VLC web interface is disabled")

		elif is_running('chrome'): #Netflix mode (assuming Chromium is used for browsing, and Google-Chrome ('chrome') is only used for Netflix)
			if data == "B2":
				subprocess.run(["xdotool", "search", "--onlyvisible", "--class", "Chrome", "windowfocus", "key", "Return"])

			elif data == "L":
				subprocess.run(["xdotool","key","shift+Tab"])

			elif data == "R":
				subprocess.run(["xdotool","key","Tab"])

			elif data == "H":
				subprocess.run(["bash", "-c", "/home/will/scripts/pc/display-default.sh"]) #Restore default display settings

		else: #Music mode
			if not is_running('foobar2000.exe') and (data == "B2" or data == "L" or data == "R"):
				subprocess.run(["wine", "/home/will/.foobar2000/foobar2000.exe", "/play"], stdout=False, stderr=False)

			elif data == "B2":
				subprocess.run(["wine", "/home/will/.foobar2000/foobar2000.exe", "/pause"])

			elif data == "L":
				subprocess.run(["wine", "/home/will/.foobar2000/foobar2000.exe", "/prev"])

			elif data == "R":
				subprocess.run(["wine", "/home/will/.foobar2000/foobar2000.exe", "/next"]) #/rand

			elif data == "H":
				subprocess.run(["bash", "-c", "/home/will/scripts/pc/netflix.sh"]) #Switch display to TV, open new chrome session...

if __name__ == "__main__":
	cmd = str(sys.argv[1])
	parse(cmd)