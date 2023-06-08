# MUGEN toolchain for linux
This is mugen toolchain for linux    
There is already a bunch of mugen toolchains but   
I want to make my own (linux version because I am linux user.)   
   
# License
(C) 2023 Kumohakase - CC BY-SA 4.0 https://creativecommons.org/licenses/by-sa/4.0/   
   
Please consider supporting me through ko-fi.com    
https://ko-fi.com/kumohakase   
   
# sff.py
the biggest program in this toolchain sff.py   
yeah it is sffv1 manipulator program   
that has command line switch syntax like linux tar util   
    
simple sff making step using this:   

Please place those files under same directory.   
I recommend creating new one.   
1. Prepare your characters images and save it as 256 indexed color pcx images   
2. Make image filelist that contains filename and mandatory information for mugen
Image filelist format is like    
```
imagefilename
group# image# x y[ shared]
```
repeat those lines for all images   
meanings are   
- imagefilename: image file name
- group#: group number
- image#: image number
- x: x axis
- y: y axis
- \[ shared\]: treat image sa shared palette, treated individual palette if omitted
3. Please run `python sff.py c youroc.sff indir -f -p`. or ./sff.py    
youroc.sff is output file name, you can pick one that you want   
indir is input directory, for example characterimgs if you store all files into characterimgs  
