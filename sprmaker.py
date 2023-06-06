#!/usr/bin/env python3

"""
sprmaker.exe clone
(C) 2023 Kumohakase
CC BY-SA 4.0 https://creativecommons.org/licenses/by-sa/4.0/
Please consider supporting me through ko-fi.com 
https://ko-fi.com/kumohakase

This is easy clone of sprmaker.exe.
It is easy clone because it has only basic feature
no command switch, no compress, no palette and duplicated file omitting,
always non shared palette mode.

"""

import sys, os, struct

#ask number, ask again if NaN passed or out of range of limmin-limmax
def asknumber(askstr, limmin, limmax):
	while True:
		t = None
		print(askstr, end = "")
		try:
			t = int(input().strip())
		except ValueError:
			print("Insufficient input!") #if input is NaN
			continue
		if t < limmin or t > limmax:
			print("Overflow!")
			continue
		else:
			return t

def main():
	#Ask output file name, if it is empty or existing, ask again.
	outfile = ""
	while outfile == "":
		print("Enter name of new SFF file: ", end = "")
		outfile = os.path.expanduser(input().strip())
		if outfile != "" and os.path.exists(outfile):
			print("Already exists.")
			outfile = ""
	image_info = []
	#ask about image files until empty path was passed.
	while True:
		#ask image file, ask again if it does not exist, exit loop if empty
		infile = ""
		while infile == "":
			print("Enter name of graphic file: ", end = "")
			infile = os.path.expanduser(input().strip())
			if infile == "":
				break
			if not os.path.exists(infile):
				print("Not found!")
				infile = ""
		if infile == "":
			break
		groupno = asknumber("Group no: ", 0, 65535) #ask for groupno
		imageno = asknumber("Image no: ",0 , 65535) #ask for imageno
		px = asknumber("X axis: ", -32768, 32767) #ask for axis x
		py = asknumber("Y axis: ", -32768, 32767) #ask for axis y
		image_info.append([infile, groupno, imageno, px, py]) #append to array
	sff = open(outfile, "wb") #prepare to write to sff
	for i in range(len(image_info)):
		e = image_info[i]
		#write to sff
		isize = os.path.getsize(e[0]) #get image size
		#calculate next subfile offset
		nextptr = ptr + 0x20 + isize
		#align at 16 octet boundary
		leftover = nextptr % 16
		if leftover != 0:
			nextptr += 16 - leftover
		#prepare header
		hdr = struct.pack("<LLhhHH", nextptr, isize, e[3], e[4], e[1], e[2])
		hdr += b"\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0"
		#read out image
		img = open(e[0], "rb")
		data = img.read()
		img.close()
		#write data to sff
		sff.seek(ptr)
		sff.write(hdr + data)
		ptr = nextptr #update sff file pointer for next file
	#finally, write header and close sff
	sff.seek(0)
	sff.write(b"ElecbyteSpr\0\0\x01\0\x01")
	img_ctr = len(image_info)
	sff.write(struct.pack("<LLLLB", 0, img_ctr, 0x200, 0x20, 0))
	sff.write(b"\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0")
	sff.write(b"Made by kumotech sprmaker clone for spr v1 (C) 2023 kumohakase")
	sff.close()

if __name__=="__main__":
	main()
