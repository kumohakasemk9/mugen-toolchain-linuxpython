#!/usr/bin/env python3

CREDIT = """SFF v1 manipulation program
(C) 2023 Kumohakase - CC BY-SA 4.0 https://creativecommons.org/licenses/by-sa/4.0/

Please consider supporting me through ko-fi.com 
https://ko-fi.com/kumohakase
"""

import sys, os, struct, tempfile

PROGNAME = sys.argv[0]

HELPMSG = f"""{PROGNAME} {{c|d|t|x|r|o|?}} [sfffile] [options]

c: create/append mode
d: delete mode
t: list mode
x: extract mode
r: reorder mode
o: optomization mode
?: show this message

return code 0 - OK
return code 1 or greater - Error

To get help for each modes, please execute without sfffile and [options]."""

HELPMSG_SELOPT = """-i index: Apply operation for image that has \
specified index in order of file registration order.
-g group: Apply operation for images that have specified group numbers.
-n number: Should be used with -g, apply operation for images that have specified group number \
 and image number.
index, group, number can be range like 10:20 (form 10 to 20)
"""

HELPMSG_LIST = f"""List mode, Lists contained images of sfffile
{PROGNAME} t sfffile [options]

Options:
{HELPMSG_SELOPT}
If there was no option, it means list all."""

HELPMSG_EXTRACT = f"""Extract mode, extract sfffile and store into outdir
{PROGNAME} x sfffile outdir [options]

Options:
-f: add basic infomation to filename (like id_group#_image#_x_y.pcx)
-p: export palette of image stored on top of sff (shared palette)
{HELPMSG_SELOPT}
If there was no option, it means extract all."""

HELPMSG_CREATE = """Create mode, create new sfffile/append images in infiledir to new sfffile
{PROGNAME} c sfffile infiledir [options]

Options:
-c: auto remove empty area of images. (Not yet implemented)
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
stand0_kumo.pcx Id=2 Group=0, Image=0, x=50, y=60, shared palette"""

HELPMSG_DELETE = f"""Delete mode: delete image files in sff
{PROGNAME} d sfffile options

Options:
-y: Do not confirm when deleting. Use with caution.
{HELPMSG_SELOPT}
You need to specify at least -i, -g or -n."""

HELPMSG_REORDER = """Reorder mode, change sff image file order of specified image.
{PROGNAME} r sfffile options index1 index2

Not yet implemented.
Changes location of image in index1 to index2"""

HELPMSG_OPTIMIZE = f"""Optimize mode, tries to reconstruct sff with specified shrinking options
{PROGNAME} o sfffile [options]

Not yet implemented.
-c: auto remove empty area of images.
-f: compare images and detect same file, then link them.
-p: delete palette information from shared palette images"""

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

#Remove palette from pcx data if it has palette data
def pcx_tryremovepal(pcxdata):
	if pcx_haspalette(pcxdata):
		return pcxdata[:-769]
	return pcxdata

#returns true if group no, image no, x and y are in acceptable range.
def sff_checkparam(grp, img, x, y):
	if 0 <= grp <= 65535 and 0 <= img <= 65535 and -32768 <= x <= 32767 and -32767 <= y <= 32767:
		return True
	return False

#get optimal offset of next subheader when current subheader offset
#is ptr and image size is filelen
def sff_getoptimaloffset(ptr, filelen):
	r = ptr + 0x20 + filelen #current subheader pointer + subheader size + image length
	#Align for 16 octets boundary
	leftover = r % 16
	if leftover != 0:
		return r + (16 - leftover)
	return r

#write sff header, imglen: image count
def sff_writeheader(sff, imglen):
	sff.seek(0)
	sff.write(b"ElecbyteSpr\0\0\x01\0\x01")
	sff.write(struct.pack("<LLLLB", 0, imglen, 0x200, 0x20, 1))
	sff.write(b"\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0")
	sff.write(b"Made by kumotech sprmaker clone for spr v1 (C) 2023 kumohakase")

#generates subheader for sff
def sff_generatesubheader(nextptr, filelen, x, y, grp, img, linkid, pal):
	p = 0
	if pal == True:
		p = 1
	li = linkid
	if linkid == None:
		li = 0
	#sub header size 0x20 (fixed?)
	#uint32_t uint32_t int16_t int16_t uint16_t uint16_t uint16_t uint8_t 000000...
	#nextptr length x y group# image# linkid isshared
	hdr = struct.pack("<LLhhHHHB", nextptr, filelen, x, y, grp, img, li, pal)
	hdr += b"\0\0\0\0\0\0\0\0\0\0\0\0\0"
	return hdr

#write ctx in binary file fname
def writebin(fname, ctx):
	f = open(fname, "wb")
	f.write(ctx)
	f.close()

#Read sff and get information, return None if fail
#list element content = [image offset, size, x, y, group#, image#, link index, palette mode]
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
		return None
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

#reconstruct sff by originalsff file object and new image information list fixedinfo
def sff_reconstruct(sffname, originalsff, fixedinfo):
	tmpsff = tempfile.TemporaryFile()
	ptr = 0x200
	c = 0
	#write subheader and files
	for i in fixedinfo:
		#skip if deleted
		if i == None:
			continue
		filelen = i[1]
		data = b""
		#if not linked, read original content
		if filelen != 0:
			originalsff.seek(i[0]) #seek to image file offset
			data = originalsff.read(filelen) #read pcx
		nextptr = sff_getoptimaloffset(ptr, filelen) #get optimal next subheader offset
		#prepare subheader
		hdr = sff_generatesubheader(nextptr, filelen, i[2], i[3], i[4], i[5], i[6], i[7])
		#write subheader + file
		tmpsff.seek(ptr)
		tmpsff.write(hdr + data)
		ptr = nextptr
		c = c + 1
	sff_writeheader(tmpsff, c) #write header
	originalsff.close() #close original sff
	#overwrite original sff with tmpsff
	tmpsff.seek(0)
	writebin(sffname, tmpsff.read())
	tmpsff.close() #close new sff

def list_mode():
	if len(sys.argv) < 3:
		print(HELPMSG_LIST)
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
		print(HELPMSG_EXTRACT)
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
			print(f"Extracted: {i}: Group{grp} Image{imgno} -> {outdir}/{filename}.pcx")
			writebin(f"{outdir}/{filename}.pcx", data)
	sff.close()
	print("SFF extract finished. Have a nice day.")
	return 0

def create_mode():
	#if there is no sfffile option and infiledir show help and exit
	if len(sys.argv) < 4:
		print(HELPMSG_CREATE)
		return 1
	#check for parameters
	m_autocrop = getoption("-c")
	if m_autocrop != None:
		print("Sorry: Autocrop is not implemented yet!")
		return 1
	m_linkmode = getoption("-f")
	m_removepal = getoption("-p")
	indir = os.path.expanduser(sys.argv[3]) #input directory
	sfffile = os.path.expanduser(sys.argv[2]) #target sff file
	#directory existence check
	if not os.path.exists(indir):
		print(f"Fatal: input directory {indir} not found!")
		return 1
	#Gather files
	filelist = []
	if os.path.exists(f"{indir}/filelist"):
		print("Filelist mode")
		#if filelist exists
		j = 0
		t = [0]
		for i in open(f"{indir}/filelist"):
			if len(t) == 1:
				t.append(i.strip()) #get filename from first line
			elif len(t) == 2:
				# group# image# x y shared?
				e = i.strip().split() #get additional information from second line
				try:
					t.append(int(e[0]))
					t.append(int(e[1]))
					t.append(int(e[2]))
					t.append(int(e[3]))
				except:
					print(f"Fatal: {e} is not well formatted information.");
					return 1
				if not sff_checkparam(t[2], t[3], t[4], t[5]):
					print("Fatal: parameter not in range.")
					return 1
				if len(e) > 4 and e[4] == "shared":
					t.append(True)
				else:
					t.append(False)
				#Find duplicated filename and link if -f option is present
				if m_linkmode != None:
					for j in range(len(filelist)):
						if t[1] == filelist[j][1]:
							t.append(j)
							break
				if len(t) < 8:
					t.append(None)
				filelist.append(t)
				t = [0]
		if len(t) == 2:
			print("Fatal: Incomplete file list")
			return 1
	else:
		print("Filename guess mode")
		#iff there's no filelist, guess information from filename
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
			if not sff_checkparam(t[1], t[2], t[3], t[4]):
				print(f"Fatal: {indir}/{i}: parameter over flow!")
				return 1
			#if filename has string "shared", set shared palette mode flag
			shared = False
			if len(t) > 5 and t[5] == "shared":
				shared = True
			#id, filename, group, image, px, py, shared
			filelist.append((t[0], i, t[1], t[2], t[3], t[4], shared, None))
		filelist = sorted(filelist, key=lambda e: e[0]) #sort by id
	ptr = 0x200 # next subfile header offset pointer
	indexoffset = 0
	#Duplication check, multiple existance of images that shares same grp# and img# is forbidden.
	for i in range(len(filelist)):
		grp = filelist[i][2]
		img = filelist[i][3]
		for j in range(len(filelist)):
			#exit if not comparing same object + grp id are same + img id are same
			if i != j and grp == filelist[j][2] and img == filelist[j][3]:
				print(f"Fatal: FileList: Already exists: Group{grp} Image{img}")
				return 1
	#if sff already exists, open in append mode
	if os.path.exists(sfffile):
		#in append mode, change image count on header with existing image count + appending image
		#count and change last next_ptr to appropriate one
		sff = open(sfffile, "r+b") #open file for read/write mode (non-turncate)
		#get last image pointer and image size
		l = sff_getinfo(sff)
		if l == None:
			return 3
		if len(l) != 0:
			lastfileptr = l[-1][0] #get final image pointer
			# find optimal offset of next image
			ptr = sff_getoptimaloffset(lastfileptr, l[-1][1])
			#rewrite next subheader pointer of final image
			sff.seek(lastfileptr - 0x20) #seek to final subfile header
			sff.write(struct.pack("<L", ptr)) #overwrite next_ptr
			#Duplication check with existing images
			for i in range(len(filelist)):
				grp = filelist[i][2]
				img = filelist[i][3]
				for k in l:
					if grp == k[4] and img == k[5]:
						print(f"Fatal: AppendSFF: Already exists: Group{grp} Image{img}")
						sff.close()
						return 1
		indexoffset = len(l) #index offset for getting appropriate link num
		#rewrite header - rewrite image count 
		sff.seek(0x14)
		sff.write(struct.pack("<L", len(l) + len(filelist)))
		#rewrite header
		sff.seek(0x30)
		sff.write(b"Made by kumotech sprmaker clone for spr v1 (C) 2023 kumohakase")
	else:
		#if sff doesn't exist, open file for writing and write header
		sff = open(sfffile, "wb")
		sff_writeheader(sff, len(filelist))
	#write image files
	for i in range(len(filelist)):
		e = filelist[i]
		filename = e[1]
		g = e[2]
		im = e[3]
		px = e[4]
		py = e[5]
		filename = f"{indir}/{filename}"
		data = b""
		linkid = e[7]
		#read image file if not linked
		if e[7] == None:
			try:
				f = open(filename, "rb")
			except(IOError):
				print(f"Fatal: {filename} read failed!")
				sff.close()
				return 3
			data = f.read()
			f.close()
			#if shared palette mode and -p (Remove palette) option is present, remove palette
			#first image of sff can't be palette-omitted data
			if m_removepal != None and e[6] and i != 0:
				data = pcx_tryremovepal(data) #if data has palette, remove
		filelen = len(data) #get filelength
		nextptr = sff_getoptimaloffset(ptr, filelen) #calculate next subfile offset
		#prepare header (nextptr, filelen, x, y, group#, image#, linkid, palette)
		hdr = sff_generatesubheader(nextptr, filelen, px, py, g, im, linkid, e[6])
		#write data to sff
		sff.seek(ptr)
		sff.write(hdr + data)
		_i = i + indexoffset
		print(f"{_i}: {filename}: Group{g} Image{im} {px}x{py}", end = "")
		if e[6]:
			print(" Shared", end = "")
		if filelen == 0:
			li = e[7] + indexoffset
			print(f" Linked to {li}", end = "")
		print()
		ptr = nextptr #update sff file pointer for next file
	sff.close()
	img_ctr = len(filelist)
	print(f"Written {img_ctr} images. Have a nice day.")
	return 0

def delete_mode():
	if len(sys.argv) < 3:
		print(HELPMSG_DELETE)
		return 1
	selector = getselectionfilter() #get selector options
	m_noconfirm = getoption("-y")
	#stop dangerous operation
	if selector[0] == None and selector[1] == None and selector[2] == None:
		print("Stopped: Please specify selector (-i or -g or -n).")
		return 1
	infile = sys.argv[2]
	removedcount = 0
	try:
		sff = open(infile, "rb")
	except(IOError):
		print("Open failed")
		return 2
	#savedpal = None
	#[image offset, size, x, y, group#, image#, link index, palette mode]
	l = sff_getinfo(sff) #get all image information in sff
	#fix image infomation according to selected deletion list
	for i in range(len(l)):
		e = l[i]
		grp = e[4]
		img = e[5]
		#abort operation if not selected
		if not decodeselectionfilter(selector, i, grp, img):
			continue
		#avoid deleting index0
		if i == 0:
			print("Index0 image can not be removed!")
			return 1
		#Show deleteing file information
		print(f"Deleting: {i}: Group{grp} Image{img}")
		#if no confirm option not present, ask
		if m_noconfirm == None:
			print("Are you sure? [y/n]", end = "")
			t = input().strip()
			if t != "y":
				print(f"Undeleting: {i}: Group{grp} Image{img}")
				continue
		#fix link index number
		for j in range(len(l)):
			if l[j] == None:
				continue
			linkno = l[j][6]
			#if linked index is bigger (and equal) than deleted image index, it will be decremented
			if linkno != None and linkno >= i:
				l[j][6] = linkno - 1#Store index=0 palette if deleting index 0 image.
		#if program is going to delete index=0 image, program have to save palette
		#data or sff will be broken
		#if i == 0:
		#	ioff = e[0] #image offset
		#	isiz = e[1] #image size
			#read image
		#	sff.seek(ioff)
		#	iimg = sff.read(isiz)
		#	if not pcx_haspalette(iimg):
		#		print("Insanity: SFF image 0 does not have palette. Aborting operation.")
		#		return 1
		#	savedpal = iimg[:-769] #save palette
		l[i] = None #finally, set file information to None to notify the file is delete
		removedcount = removedcount + 1
	if removedcount == 0:
		print("SFF file is untouched.")
		sff.close()
		return 0
	sff_reconstruct(infile, sff, l, savedpal) #reconstruct sff file by fixed information
	print(f"Removed {removedcount} images.")
	return 0

def reorder_mode():
	if len(sys.argv) < 3:
		print(HELPMSG_REORDER)
		return 1
	return 1

def optimization_mode():
	if len(sys.argv) < 3:
		print(HELPMSG_OPTIMIZE)
		return 1
	return 1
		
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
	elif m == "r":
		return reorder_mode()
	elif m == "o":
		return optimization_mode()
	else:
		print(HELPMSG)
		return 1

if __name__ == '__main__':
	sys.exit(main(sys.argv))
