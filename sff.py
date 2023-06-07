#!/usr/bin/env python3

CREDIT = """SFF v1 manipulation program
(C) 2023 Kumohakase - CC BY-SA 4.0 https://creativecommons.org/licenses/by-sa/4.0/

Please consider supporting me through ko-fi.com 
https://ko-fi.com/kumohakase
"""

HELPMSG = """python sff.py {c|d|t|x|s|o|?} sfffile [options]

c: create/append mode
d: delete mode
t: list mode
x: extract mode
s: swap mode
o: optomization mode
?: show this message

return code 0 - OK
return code 1 - command error
return code 2 - open failed
return code 3 - broken file
return code 4 - sff or pcx insanity

To get help for each modes, please execute without sfffile and [options]."""

HELPMSG_SELOPT = """-i index: Apply operation for image that has \
specified index in order of file registration order.
-g group: Apply operation for images that have specified group numbers.
-n number: Should be used with -g, apply operation for images that have specified group number \
 and image number.
index, group, number can be range like 10:20 (form 10 to 20)
"""

HELPMSG_CREATE = """Create mode, create new sfffile/append images in infiledir to new sfffile
python sff.py c sfffile infiledir [options]

Options:
-c: auto remove empty area of images.
-f: link duplicate images (files that shares same filename).
-p: remove palette data from image when shared palette mode.

infiledir is directory that contains pcx files to append to sfffile
pcx filename format should be id_grp_img_x_y_shared.pcx
id: processing order, unique grp: desired group number
img: desired image number x, y: desired coordinate
shared: shared palette mode, if individual palette mode, just don't write it.

Example:
0_9000_0_30_30_shared.pcx (id=0, group=9000, image=0, x=30, y = 30, shared palette)
1_9000_0_0_0.pcx (id=1, group=9000, image=0, x=0, y=0, nonshared palette)

If there is file named "filelist" in infiledir, information is gathered
from the file. And you don't have to include information in pcx filenames.
You have to write pcx file name in first line, and write like
"grp img x y shared" in next line, and repeat it for all images.

Example:
portrait0_kumo.pcx
9000 0 0 0
portrait1_kumo.pcx
9000 1 0 0
stand0_kumo.pcx
0 0 50 60 shared

This will output sff includes:
portrait0_kumo.pcx Id=0 Group=9000, Image=0, x=0, y=0, nonshared palette
portrait1_kumo.pcx Id=1 Group=9000, Image=1, x=0, y=0, nonshared palette
stand0_kumo.pcx Id=2 Group=0, Image=0, x=50, y=60, shared palette
"""

import sys, os, struct

#find command line option s then return next param, returns None if s not found, returns "" 
#if no next param
def getoption(s):
	for i in range(len(sys.argv)):
		e = sys.argv[i]
		if e == s:
			if i + 1 < len(sys.argv):
				return sys.argv[i + 1]
			else:
				return ""
	return None

#Return True if p is in range of mi and ma
def in_range(p, mi, ma):
	if p < mi or p > ma:
		return False
	return True

#decode "4500:6300" to (4500, 6300) and decode "450" to 450, returns None if conversion failed
#or out of range of minval and maxval
def decode_nrange_str(s, minval, maxval):
	if ":" in s:
		#split values into 2 and try to convert those to int
		t = s.split(":")
		try:
			n1 = int(t[0])
			n2 = int(t[1])
		except(ValueError):
			return None
		#first value can't be larger than second one
		if n1 > n2:
			return None
		#check range
		if in_range(n1, minval, maxval) and in_range(n2, minval, maxval):
			return (n1, n2)
	else:
		#single number, try convert and check range
		try:
			t = int(s)
		except(ValueError):
			return None
		if in_range(t, minval, maxval):
			return t
		else:
			return None

#decode selection filter command line switch, returns None if error
def getselectionfilter():
	r = []
	t = None
	i_cond = getoption("-i")
	if i_cond != None:
		t = decode_nrange_str(i_cond, 0, 65535)
		#decode error or out of range
		if t == None:
			print("-i: Must be number, range 0 - 65535")
			return None
	r.append(t)
	t = None
	g_cond = getoption("-g")
	if g_cond != None:
		#exclusive with -i
		if i_cond != None:
			print("-g: Can not be used with -i")
			return None
		t = decode_nrange_str(g_cond, 0, 65535)
		if t == None:
			print("-g: Must be number, range 0 - 65535")
			return None
	r.append(t)
	t = None
	n_cond = getoption("-n")
	if n_cond != None:
		#exclusive with -i
		if i_cond != None:
			print("-n: Can not be used with -i")
			return None
		#Accept only with -g
		if g_cond == None:
			print("-n: Please use with -g")
			return None
		t = decode_nrange_str(n_cond, 0, 65535)
		if t == None:
			print("-n: Must be number, range 0 - 65535")
			return None
	r.append(t)
	return r

#Returns true if i == sel, If sel is tuple, returns true if i is in range of
#sel[0] and sel[1], otherwise false
def eval_selector_elem(sel, i):
	if type(sel) == int:
		if sel == i:
			return True
	else:
		if in_range(i, sel[0], sel[1]):
			return True
	return False

#compare selection filter given by command parameter -i, -g and -n, and current file
def decodeselectionfilter(selector, c_i, c_g, c_n):
	dst = (c_i, c_g, c_n)
	t = 0
	for i in range(len(selector)):
		e = selector[i]
		#None means specified condition not set (always TRUE)
		if e != None:
			if eval_selector_elem(e, dst[i]):
				t += 1
		else:
			t += 1
	#if all selectors = True, return true
	if t == len(dst):
		return True
	return False

#check if pcxdata has palette, returns True if it has, otherwise false
def pcx_haspalette(pcxdata):
	#check for palette indicator located in last 769 octets
	if len(pcxdata) < 769 or pcxdata[-769] != 12:
		return False
	else:
		return True

#write ctx in binary file fname
def writebin(fname, ctx):
	f = open(fname, "wb")
	f.write(ctx)
	f.close()

#Read sff and get information, return None if fail
def sff_getinfo(sff):
	sff.seek(0)
	hdr = sff.read(0x1c) #read header
	#check read size
	if len(hdr) < 0x1c:
		print("Fatal: Broken sff.")
		return None
	#Check for header
	if hdr[0:0x10] != b"ElecbyteSpr\0\0\x01\0\x01":
		print("Fatal: Wrong file identifier.")
		None
	hp =  struct.unpack("<LL", hdr[0x14:0x1c]) #image_count, subheader_offset
	#+0x1c uint32_t (subheader len) seems to be ignored in mugen and assumed 0x20
	ptr = hp[1] #pointer for subfiles in sff
	img_info = []
	for i in range(hp[0]):
		sff.seek(ptr) #seek to next subheader offset
		hdr = sff.read(0x13) #read subheader
		#check read size
		if len(hdr) < 0x13:
			print("Fatal: Broken subheader.")
			return None
		# next offset, length, X, Y, Group#, Image#, link index, Palette mode
		p = struct.unpack("<LLhhHHH?", hdr)
		imgoff = ptr + 0x20 #Image offset = subheader addr + subheader size (0x20)
		if p[1] == 0:
			li = p[6]
		else:
			li = None
		#image offset, size, x, y, group#, image#, link index, palette mode
		img_info.append([imgoff, p[1], p[2], p[3], p[4], p[5], li, p[7]])
		ptr = p[0] #update pointer for reading next subfile
	return img_info

def list_mode():
	if len(sys.argv) < 3:
		print("List mode, Lists contained images of sfffile")
		print("python sff.py t sfffile [options]\n")
		print("Options:")
		print(HELPMSG_SELOPT)
		print("If there was no option, it means list all.")
		return 1
	selector = getselectionfilter() #get selement elector options
	#error check
	if selector == None:
		return 1
	#Try opening sff file.
	try:
		sff = open(sys.argv[2], "rb")
	except(IOError):
		print("SFF open failed")
		return 2
	img_info = sff_getinfo(sff)
	if img_info == None:
		return 3
	#show information + insanity check
	i = len(img_info)
	print(f"Total {i} images.")
	insanity = False
	for i in range(len(img_info)):
		e = img_info[i]
		#extract params
		imgoff = e[0]
		imglen = e[1]
		px = e[2]
		py = e[3]
		grp = e[4]
		img = e[5]
		li = e[6]
		#if it was linked image...
		if li != None:
		#read linked destination image offset if linked index is not wrong
			if li >= len(img_info):
				print(f"Insanity: {i}: link id exceeds image count - 1")
				insanity = True
				imgoff = 0
			else:
				imgoff = img_info[li][0]
				imglen = img_info[li][1]
			if i == 0:
				print(f"Insanity: Index0 image is not actual!")
				insanity = True
		ix = -1
		iy = -1
		if imgoff != 0:
			#read image
			sff.seek(imgoff)
			d = sff.read(imglen)
			#check size
			if len(d) < imglen:
				t = len(d)
				print(f"Insanity: {i}: Wrong pcx file size: Size={imglen} Read={t}")
				insanity = True
			if len(d) > 0x42:
				#check for image type and identifier
				if d[0] != 0xa or d[3] != 8 or d[0x41] != 1:
					print(f"Insanity: {i}: PCX file identifier mismatch or not a 256 indexed color.")
					insanity = True
				else:
					ix, iy = struct.unpack("<HH", d[8:0xc]) #read image size width, height
			else:
				#if filesize is shorter than header size
				print(f"Insanity: {i}: PCX too short!")
				insanity = True
			#Next, check for palette availability for index=0 image or non shared palette
			if (i == 0 or e[7] == 0) and not pcx_haspalette(d):
				print(f"Insanity: {i}: Non shared palette image, but there is no palette in PCX.")
				insanity = True
		#Show information
		itemselected = decodeselectionfilter(selector, i, grp, img)
		if itemselected:
			print(f"{i}: Group{grp} Image{img} Pos={px}x{py} Size={ix}x{iy}", end = "")
			if e[7] == 1:
				print(" Shared", end = "")
			if li != None:
				print(f" Linked to {li}", end = "")
			print()
	sff.close()
	if insanity:
		return 4
	print("Have a nice day")
	return 0

def extract_mode():
	if len(sys.argv) < 4:
		print("Extract mode, extract sfffile and store into outdir")
		print("python sff.py x sfffile outdir [options]\n")
		print("Options:")
		print(HELPMSG_SELOPT)
		print("-f: add basic infomation to filename (like id_group#_image#_x_y.pcx)")
		print("-p: export palette of image stored on top of sff (shared palette)")
		print("If there was no option, it means extract all.")
		return 1
	selector = getselectionfilter() #get selector option
	detailed_filename = getoption("-f")
	palette_extract = getoption("-p")
	#Try opening sff file
	try:
		sff = open(sys.argv[2], "rb")
	except(IOError):
		print("SFF open failed")
		return 2
	#Create output dir, if already exists, abort
	outdir = os.path.expanduser(sys.argv[3])
	if os.path.exists(outdir):
		print(f"Fatal: Output destination {outdir} already exists!")
		sff.close()
		return 1
	os.mkdir(outdir)
	image_list = sff_getinfo(sff)
	shared_palette = b""
	for i in range(len(image_list)):
		e = image_list[i]
		px = e[2]
		py = e[3]
		grp = e[4]
		imgno = e[5]
		#if image is not selected, skip (always process image[0])
		itemselected = decodeselectionfilter(selector, i, grp, imgno)
		if not itemselected and i != 0:
			continue
		#do not extract linked image
		if e[6] != None:
			li = e[6]
			print(f"{i}: Not extracting: linked to {li}")
			continue
		#get file content
		sff.seek(e[0]) #jump to image offset
		data = sff.read(e[1])
		#Get palette from image located on top of sff
		if pcx_haspalette(data) and i == 0:
			shared_palette = data[-769:]
			#If palette extract option is on
			if palette_extract != None:
				print("Extracting palette")
				#write except first palette indicator.
				writebin(f"{outdir}/shared.act", shared_palette[1:])
		#extract into single file
		#change palette if image is stored in shared palette mode
		if e[7] == 1:
			#if it has palette already, clear it
			if pcx_haspalette(data):
				data = data[:-769]
			data = data + shared_palette
		filename = f"{i}"
		#if detailed filename flag is on
		if detailed_filename != None:
			filename = f"{i}_{grp}_{imgno}_{px}_{py}"
			if e[7] == 1:
				filename += "_shared"
		if itemselected:
			writebin(f"{outdir}/{filename}.pcx", data)
	sff.close()
	print("SFF extract finished. Have a nice day.")
	return 0

def create_mode():
	#if there is no sfffile option and infiledir show help and exit
	if len(sys.argv) < 4:

		return 1
	#check for parameters
	m_autocrop = getoption("-c")
	m_linkmode = getoption("-f")
	m_removepal = getoption("-p")
	indir = os.path.expanduser(sys.argv[3]) #input directory
	sfffile = os.path.expanduser(sys.argv[2]) #target sff file
	#directory existence check
	if not os.path.exists(indir):
		print(f"Fatal: input directory {indir} not found!")
		return 1
	#append mode not supported yet
	if os.path.exists(sfffile):
		print("Sorry: Append mode is not supported yet.")
		return 1
	#Gather files
	filelist = []
	for i in os.listdir(indir):
		#process only for ".pcx" file
		if not os.path.isfile(f"{indir}/{i}") or i[-4:] != ".pcx":
			continue
		#decode filename
		t = i[:-4] #get basename
		t = t.split("_") #id, grp, img, x, y
		try:
			t[0] = int(t[0])
			t[1] = int(t[1])
			t[2] = int(t[2])
			t[3] = int(t[3])
			t[4] = int(t[4])
		except:
			print(f"Fatal: {indir}/{i} does not have well formatted filename!")
			return 1
		if not(0 <= t[0] <= 65535) or not(0 <= t[1] <= 65535) or not(0 <= t[2] <= 65535) \
		or not(-32768 <= t[3] <= 32767) or not(-32768 <= t[4] <= 32767):
			print(f"Fatal: {indir}/{i}: parameter over flow!")
			return 1
		#if filename has string "shared", set shared palette mode flag
		shared = False
		if len(t) > 5 and t[5] == "shared":
			shared = True
		#id, filename, group, image, px, py, shared
		filelist.append((t[0], i, t[1], t[2], t[3], t[4], shared))
	filelist = sorted(filelist, key=lambda e: e[0]) #sort by id
	#write to actual sff
	sff = open(sfffile, "wb")
	ptr = 0x200 #next subfile header offset pointer
	#write image files
	for i in filelist:
		filename = i[1]
		filename = f"{indir}/{filename}"
		filelen = os.path.getsize(filename) #get filelength
		#calculate next subfile offset
		nextptr = ptr + 0x20 + filelen
		#align at 16 octet boundary
		leftover = nextptr % 16
		if leftover != 0:
			nextptr += 16 - leftover
		#prepare header (nextptr, filelen, x, y, group#, image#, linkid, palette)
		hdr = struct.pack("<LLhhHHHB", nextptr, filelen, i[4], i[5], i[2], i[3], 0, i[6])
		hdr += b"\0\0\0\0\0\0\0\0\0\0\0\0\0"
		#read image file
		try:
			f = open(filename, "rb")
		except(IOError):
			print(f"Fatal: {filename} read failed!")
			return 3
		data = f.read()
		f.close()
		#write data to sff
		sff.seek(ptr)
		sff.write(hdr + data)
		g = i[2]
		im = i[3]
		px = i[4]
		py = i[5]
		print(f"{filename}: Group{g} Image{im} {px}x{py}", end = "")
		if i[6]:
			print(" Shared")
		print()
		ptr = nextptr #update sff file pointer for next file
	#finally, write header and close sff
	sff.seek(0)
	sff.write(b"ElecbyteSpr\0\0\x01\0\x01")
	img_ctr = len(filelist)
	print(f"{img_ctr} images written.")
	sff.write(struct.pack("<LLLLB", 0, img_ctr, 0x200, 0x20, 1))
	sff.write(b"\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0")
	sff.write(b"Made by kumotech sprmaker clone for spr v1 (C) 2023 kumohakase")
	sff.close()
	print("SFF file written successfully. Good bye.")
	return 0
		
def main(args):
	print(CREDIT)
	#if no mode specified then show help and quit
	if len(sys.argv) < 2:
		print(HELPMSG)
		return 1
	#run function specified by mode
	m = sys.argv[1]
	if m == "c":
		return create_mode()
	elif m == "d":
		return delete_mode()
	elif m == "t":
		return list_mode()
	elif m == "x":
		return extract_mode()
	elif m == "s":
		return swap_mode()
	elif m == "o":
		return optimization_mode()
	else:
		print(HELPMSG)
		return 1

if __name__ == '__main__':
	sys.exit(main(sys.argv))
