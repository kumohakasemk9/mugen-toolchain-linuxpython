#!/usr/bin/env python3

"""
sprmaker.exe clone
(C) 2023 Kumohakase
CC BY-SA 4.0 https://creativecommons.org/licenses/by-sa/4.0/
Please consider supporting me through ko-fi.com 
https://ko-fi.com/kumohakase

This is easy clone of sprmaker.exe.
It is easy clone because it has some missing future
There's no autocrop, there's no appending,
and -p option might be buggy

"""

import sys, os, struct

#ask number, ask again if NaN passed or out of range of limmin-limmax
def asknumber(askstr, limmin, limmax):
	while True:
		t = None
		if not quiet:
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
	#Check for commandline options
	autocrop = False
	linkfiles = False
	removepal = False
	debug = False
	global quiet = False
	for i in sys.argv:
		#-c for autocrop mode, auto remove empty area of images
		if i == "-c":
			autocrop = True
		#-f for link mode, link duplicate files inside sff (same filename will be linked)
		if i == "-f":
			linkfiles = True
		#-p for palette removal mode, removes "palette-shared-image" palette
		if i == "-p":
			removepal = True
		#-q for quiete mode, supress all outputs.
		if i == "-q":
			quiet = True
		#-d for debug mode, shows link info and more
		if i == "-s":
			debug = True
	global_pal_type = 1
	#Ask output file name, if it is empty or existing, ask again.
	outfile = ""
	while outfile == "":
		if not quiet:
			print("Enter name of new SFF file: ", end = "")
		outfile = input().strip()
		# passing hash mark in this prompt will call palette mode menu
		if outfile == "#":
			#This looks nonsence since there is only valid input '1'
			#but mtools.txt said me to do so.
			asknumber("Options:\n1. Palette type\nChoose: ", 1, 1)
			#avoiding long line
			prompt = """Palette type
1. Individual palette
2. Use palette of first image
Choose: """
			global_pal_type = asknumber(prompt, 1, 2)
			outfile = ""
			continue
		outfile = os.path.expanduser(outfile)
		if outfile != "" and os.path.exists(outfile):
			print("Already exists.")
			outfile = ""
	image_info = []
	#ask about image files until empty path was passed.
	while True:
		pal_mode = global_pal_type
		#ask image file, ask again if it does not exist, exit loop if empty
		infile = ""
		while infile == "":
			if not quiet:
				print("Enter name of graphic file: ", end = "")
			infile = input().strip()
			# passing hash mark in this prompt will call palette mode menu
			if infile == "#":
				# :(
				prompt = "Options:\n1. Palette type\n2. Override duplicate file linking\nChoose: "
				asknumber(prompt, 1, 1)
				prompt = f"""Palette type
1. Individual palette
2. Use palette of first image
Choose(was {pal_mode}): """
				pal_mode = asknumber(prompt, 1, 2)
				infile = ""
				continue
			infile = os.path.expanduser(infile)
			if infile == "":
				break
			if not os.path.exists(infile):
				print("Not found!")
				infile = ""
		if infile == "":
			break
		#duplicate check and link if linkfiles = True
		linkno = -1 #-1 if do not link
		if linkfiles:
			for i in range(len(image_info)):
				if image_info[i][0] == infile:
					if debug:
						print(f"Duplication found, linked to {i}")
					linkno = i
					break
		dup = True
		while dup:
			groupno = asknumber("Group no: ",0 , 65535) #ask for groupno
			imageno = asknumber("Image no: ",0 , 65535) #ask for imageno
			dup = False
			#check for dup, ask again if dup
			for r in image_info:
				if r[1] == groupno and r[2] == imageno:
					print("Duplication found!")
					dup = True
					break
		px = asknumber("X axis: ", -32768, 32767) #ask for axis x
		py = asknumber("Y axis: ", -32768, 32767) #ask for axis y
		image_info.append([infile, groupno, imageno, px, py, linkno, pal_mode]) #append to array
	sff = open(outfile, "wb") #prepare to write to sff
	ptr = 0x200
	#write subfile headers and images
	for i in range(len(image_info)):
		e = image_info[i]
		data = b""
		linkid = e[5]
		#if linkid == -1, store actual image file
		if linkid == -1:
			img = open(e[0], "rb")
			data = img.read()
			img.close()
			linkid = 0 # linkid can not be -1
		#calculate next subfile offset
		nextptr = ptr + 0x20 + len(data)
		#align at 16 octet boundary
		leftover = nextptr % 16
		if leftover != 0:
			nextptr += 16 - leftover
		pm = 0
		#if palette mode = 2 (Shared palette), pm == 1
		if e[6] == 2:
			pm = 1
			#if shared palette mode and palette removal mode, remove palette from file
			if removepal and data[1] == 5 and data[-769] == 12:
				if debug:
					print(f"{i}: Deleting palette info from data")
				data = data[:-769]
		#prepare header
		hdr = struct.pack("<LLhhHHHB", nextptr, len(data), e[3], e[4], e[1], e[2], linkid, pm)
		hdr += b"\0\0\0\0\0\0\0\0\0\0\0\0\0"
		#write data to sff
		sff.seek(ptr)
		sff.write(hdr + data)
		g = e[1]
		im = e[2]
		px = e[3]
		py = e[4]
		if not quiet:
			print(f"{i}: Group{g} Image{im} {px}x{py} data written.")
		ptr = nextptr #update sff file pointer for next file
	#finally, write header and close sff
	sff.seek(0)
	sff.write(b"ElecbyteSpr\0\0\x01\0\x01")
	img_ctr = len(image_info)
	if not quiet:
		print(f"{img_ctr} images written.")
	sff.write(struct.pack("<LLLLB", 0, img_ctr, 0x200, 0x20, 1))
	sff.write(b"\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0")
	sff.write(b"Made by kumotech sprmaker clone for spr v1 (C) 2023 kumohakase")
	sff.close()
	if not quiet:
		print("SFF file written successfully. Good bye.")

if __name__=="__main__":
	main()
