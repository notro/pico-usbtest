Raspberry Pi Pico usbtest
=========================

Partial port of the Linux Gadget driver [g_zero](https://elixir.bootlin.com/linux/latest/source/drivers/usb/gadget/legacy/zero.c).

I gave up on getting all the tests to run, so I settled on the performance tests.

The ```PICO_SDK_PATH``` env var should point to the Pico SDK.

Build:
```
$ cd pico-usbtest
$ mkdir build
$ cd build
$ cmake ..
$ make

```

Use test.py to run tests:
```
$ sudo python3 test.py --perf
#27 iterations=100 length=32768 vary=256 sglen=32 :: 101.216362 secs - 1011.7 kB/s
#28 iterations=100 length=32768 vary=256 sglen=32 :: 96.557829 secs - 1.0 MB/s

$ sudo python3 test.py --test=1,2,3,4,5,6,7,8,9,10,11,12,17,18,20,21,27,28 -c100 -d
#1 iterations=100 length=512 vary=256 sglen=1 :: 58.222 ms
    dmesg: usbtest 1-1.4:1.0: TEST 1:  write 512 bytes 100 times
#2 iterations=100 length=512 vary=256 sglen=1 :: 59.307 ms
    dmesg: usbtest 1-1.4:1.0: TEST 2:  read 512 bytes 100 times
#3 iterations=100 length=512 vary=256 sglen=1 :: 33.696 ms
    dmesg: usbtest 1-1.4:1.0: TEST 3:  write/256 0..512 bytes 100 times
#4 iterations=100 length=512 vary=256 sglen=1 :: 33.611 ms
    dmesg: usbtest 1-1.4:1.0: TEST 4:  read/256 0..512 bytes 100 times
#5 iterations=100 length=512 vary=256 sglen=1 :: 54.383 ms
    dmesg: usbtest 1-1.4:1.0: TEST 5:  write 100 sglists 1 entries of 512 bytes
#6 iterations=100 length=512 vary=256 sglen=1 :: 53.006 ms
    dmesg: usbtest 1-1.4:1.0: TEST 6:  read 100 sglists 1 entries of 512 bytes
#7 iterations=100 length=512 vary=256 sglen=1 :: 54.670 ms
    dmesg: usbtest 1-1.4:1.0: TEST 7:  write/256 100 sglists 1 entries 0..512 bytes
#8 iterations=100 length=512 vary=256 sglen=1 :: 53.116 ms
    dmesg: usbtest 1-1.4:1.0: TEST 8:  read/256 100 sglists 1 entries 0..512 bytes
#9 iterations=100 length=512 vary=256 sglen=1 :: 310.098 ms
    dmesg: usbtest 1-1.4:1.0: TEST 9:  ch9 (subset) control tests, 100 times
#10 iterations=100 length=512 vary=256 sglen=1 :: 77.009 ms
    dmesg: usbtest 1-1.4:1.0: TEST 10:  queue 1 control calls, 100 times
#11 iterations=100 length=512 vary=256 sglen=1 :: 3.997971 secs
    dmesg: usbtest 1-1.4:1.0: TEST 11:  unlink 100 reads of 512
    dmesg: usbtest 1-1.4:1.0: unlink retry
    dmesg: usbtest 1-1.4:1.0: unlink retry
    dmesg: usbtest 1-1.4:1.0: unlink retry
    dmesg: usbtest 1-1.4:1.0: unlink retry
    dmesg: usbtest 1-1.4:1.0: unlink retry
#12 iterations=100 length=512 vary=256 sglen=1 :: 4.154918 secs
    dmesg: usbtest 1-1.4:1.0: TEST 12:  unlink 100 writes of 512
    dmesg: usbtest 1-1.4:1.0: unlink retry
    dmesg: usbtest 1-1.4:1.0: unlink retry
#17 iterations=100 length=512 vary=256 sglen=1 :: 60.786 ms
    dmesg: usbtest 1-1.4:1.0: TEST 17:  write odd addr 512 bytes 100 times core map
#18 iterations=100 length=512 vary=256 sglen=1 :: 58.830 ms
    dmesg: usbtest 1-1.4:1.0: TEST 18:  read odd addr 512 bytes 100 times core map
#20 iterations=100 length=512 vary=256 sglen=1 :: 66.625 ms
    dmesg: usbtest 1-1.4:1.0: TEST 20:  read odd addr 512 bytes 100 times premapped
#21 iterations=100 length=512 vary=256 sglen=1 :: [Errno 32] Broken pipe
    dmesg: usbtest 1-1.4:1.0: TEST 21:  100 ep0out odd addr, 1..512 vary 256
    dmesg: usbtest 1-1.4:1.0: ctrl_out write failed, code -32, count 0
#27 iterations=100 length=512 vary=256 sglen=1 :: 53.307 ms - 938.0 kB/s
    dmesg: usbtest 1-1.4:1.0: TEST 27: bulk write 0Mbytes
#28 iterations=100 length=512 vary=256 sglen=1 :: 50.933 ms - 981.7 kB/s
    dmesg: usbtest 1-1.4:1.0: TEST 28: bulk read 0Mbytes

```

Maximum theoretical USB 1.1 bulk throughput is 19 blocks of 64 bytes per frame (1ms): 19*64*1000/1024/1024 = 1.2 MB/s

Use Linux tool: [tools/usb/testusb.c](https://github.com/torvalds/linux/blob/master/tools/usb/testusb.c)
```
# Build and install tool
$ cd linux/tools/usb/
$ mkdir ~/build-testusb
$ make O=~/build-testusb/
$ sudo make O=~/build-testusb/ install

$ dmesg
[48697.838867] usb 1-1.4: new full-speed USB device number 10 using xhci_hcd
[48697.982153] usbtest 1-1.4:1.0: Linux gadget zero
[48697.982180] usbtest 1-1.4:1.0: full-speed {control in/out bulk-in bulk-out} tests (+alt)

$ sudo testusb -a -t 27 -c 100 -s 32768 -g 32
full speed  /dev/bus/usb/001/006    0
/dev/bus/usb/001/006 test 27,  101.248025 secs
$ dmesg
[72827.558565] usbtest 1-1.4:1.0: TEST 27: bulk write 100Mbytes
$ python -c "print('%.2f MB/s' % (100/101.25))"
0.99 MB/s

$ sudo testusb -a -t 28 -c 100 -s 32768 -g 32
full speed  /dev/bus/usb/001/006    0
/dev/bus/usb/001/006 test 28,   96.546343 secs
$ dmesg
[72974.084173] usbtest 1-1.4:1.0: TEST 28: bulk read 100Mbytes
$ python -c "print('%.2f MB/s' % (100/96.55))"
1.04 MB/s

```

Host kernel module: [drivers/usb/misc/usbtest.c](https://elixir.bootlin.com/linux/latest/source/drivers/usb/misc/usbtest.c)
