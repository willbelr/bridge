#!/usr/bin/python3
import sys
import re
import subprocess
import urllib.request

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
		#print "a"
	else:
		if is_running('vlc'):
			try:
				if data == "Z":
					urllib.request.urlopen('http://127.0.0.1:8080/requests/status.xml?command=pl_pause')

				elif data == "L":
					urllib.request.urlopen('http://127.0.0.1:8080/requests/status.xml?command=seek&val=-5')

				elif data == "R":
					urllib.request.urlopen('http://127.0.0.1:8080/requests/status.xml?command=seek&val=+5')
			except urllib.error.URLError:
				print("Error: VLC web interface is disabled")
if __name__ == "__main__":
	cmd = str(sys.argv[1])
	parse(cmd)