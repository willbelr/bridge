#!/usr/bin/python3
import subprocess
import daemon
import sys

if __name__ == "__main__":
	print("begin")
	"""
	stdin, stdout, stderr = sys.stdin, sys.stdout, sys.stderr
	with daemon.DaemonContext(stdin=stdin, stdout=stdout, stderr=stderr):
		subprocess.run(["wine", "/home/will/.foobar2000/foobar2000.exe", "/play"])
	"""
	subprocess.Popen(["wine", "/home/will/.foobar2000/foobar2000.exe", "/play"], stdout=False, stderr=False)
	print("done")