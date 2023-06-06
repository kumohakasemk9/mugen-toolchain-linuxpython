#!/usr/bin/env python3

"""
SFF v1 extractor program
(C) 2023 Kumohakase
CC BY-SA 4.0 https://creativecommons.org/licenses/by-sa/4.0/
Please consider supporting me through ko-fi.com 
https://ko-fi.com/kumohakase

This program will extract pcx files
contained inside sff and output some information inside
outdir.

This is prototype and may be buggy.

Usage: python sff_extractor.py (sff_file_name) (outdir)

Sffv1 file structure:
Header (Offset = 0)
+0x0, 16 octets, FileIdentifier ("ElecbyteSpr\0\0\x01\0\x01")
+0x14, uint32_t, Contained image count
+0x18, uint32_t, First subfile header address (Common value=0x200)
+0x1c, uint32_t, Subfile header length (Common value=0x20)
+0x20, uint8_t, Palette mode (Common value=1) I am not sure what it is.
+0x21, 3 octets, Constant(\0\0\0)

Subfile header (Offset = non fixed)
+0x0, uint32_t, Next subfile header address
+0x4, uint32_t, Image length
+0x8, uint16_t, Axis X
+0xa, uint16_t, Axis Y
+0xc, uint16_t, Group#
+0xe, uint16_t, Image#
+0x10, uint16_t, If nonzero and Image length = 0, actual image is in specified subfile index
+0x12, uint8_t, If 1, the image uses previous image palette

Exact image offset = Subfile header address + Subfile header length
Image format: pcx 256 indexed color (index=0 will treated as transparent)

"""
import sys, os, struct

def main():
	#Check for params, if not enough show help and exit
	if len(sys.argv) < 3:
		print("Parameters: sfffile outdir")
		print("Extract information and contents of sfffile to outdir/")
		return
	sffpath = sys.argv[1] #sff file to open
	outdir = sys.argv[2] #output directory
	#if output dir already exists, exit
	if os.path.exists(outdir):
		print(f"{outdir} already exists!")
		return
	os.mkdir(outdir) #make output dir
	try:
		sff = open(sffpath, "rb")
	except(IOException):
		print(f"Open failed: {sffpath}")
		return
	hdr = sff.read(0x20) #read sff header
	#Check file identifier, exit if different
	if hdr[0:0x10] != b"ElecbyteSpr\0\0\x01\0\x01":
		print("Header is weird!")
		sff.close()
		return
	#read image count, first subheader offset and subheader length
	img_cnt, ptr, subh_len = struct.unpack("<LLL", hdr[0x14:0x20])
	#check for value
	if img_cnt == 0 or ptr < 0x200 or subh_len < 0x20:
		print("Header data is weird!")
		sff.close()
		return
	#Prepare report file to output sff information
	rep = open(f"{outdir}/report", "w")
	rep.write("<!DOCTYPE html><html><head><meta charset=\"utf-8\"></head><body>" +
				f"<h1>{sffpath}</h1><br>Total {img_cnt} images.<br><table border=1><tr>" +
				"<th>#</th><th>Group#</th><th>Image#</th><th>X</th><th>Y</th>" +
				"<th>Shared palette?</th><th>link to?</th></tr>")
	pal = b"" #palette data for shared palette feature
	#loop for process subfiles inside sff
	for i in range(img_cnt):
		sff.seek(ptr) #jump to next subfile offset
		hdr = sff.read(0x13) #read subfile header
		#read out next subfile offset, subfile length, X, Y, GroupNo, ImageNo, LinkIndex,
		#Palette mode
		_ptr, flen, px, py, grp, ino, linki, pl = struct.unpack("<LLhhHHHB", hdr)
		#Write subfile information to report
		pm = ""
		if pl:
			pm = "Shared"
		lm = ""
		if flen == 0:
			lm = f"{linki}"
		rep.write(f"<tr><td><b>{i}</b></td><td>{grp}</td><td>{ino}</td><td>{px}</td><td>{py}</td>" +
					f"<td>{pm}</td><td>{lm}</td></tr>")
		#Extract subfile to individual file
		if flen != 0:
			sff.seek(ptr + subh_len) #jump to actual image offset
			data = sff.read(flen) #read subfile content
			#write
			f = open(f"{outdir}/{i}.pcx", "wb")
			f.write(data)
			#add recorded palette if palette data was omitted
			if data[1] == 5 and data[-769] != 12:
				f.write(pal)
			else:
				#if shared flag = 1 but data have palette data, i think it is wrong palette
				if pl == 1:
					f.seek(769, 2)
					f.write(pal)
				pal = data[-769:] #record palette data for shared=1 img (use previous image pal)
			f.close()
		ptr = _ptr #update next subfile pointer
	#write footer and close report file
	rep.write("</table></body></html>")
	rep.close()
	sff.close() #close sff

if __name__=="__main__":
	main()
