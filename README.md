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
#27 iterations=100 length=32768 vary=256 sglen=32 :: 103.220516 secs - 992.1 kB/s
#28 iterations=100 length=32768 vary=256 sglen=32 :: 98.059608 secs - 1.0 MB/s

```

Maximum theoretical USB 1.1 bulk throughput is 19 blocks of 64 bytes per frame (1ms): 19*64*1000/1024/1024 = 1.2 MB/s

Use Linux tool: [tools/usb/testusb.c](https://github.com/torvalds/linux/blob/master/tools/usb/testusb.c)
```
$ dmesg
[48697.838867] usb 1-1.4: new full-speed USB device number 10 using xhci_hcd
[48697.982153] usbtest 1-1.4:1.0: Linux gadget zero
[48697.982180] usbtest 1-1.4:1.0: full-speed {control in/out bulk-in bulk-out} tests (+alt)

$ sudo ~/testusb -a -t 27 -c 100 -s 32768 -g 32
unknown speed   /dev/bus/usb/001/005    0
/dev/bus/usb/001/005 test 27,  103.190143 secs
$ dmesg
[  629.819376] usbtest 1-1.4:1.0: TEST 27: bulk write 100Mbytes
$ python -c "print('%.2f MB/s' % (100/103.19))"
0.97 MB/s

$ sudo ~/testusb -a -t 28 -c 100 -s 32768 -g 32
unknown speed   /dev/bus/usb/001/005    0
/dev/bus/usb/001/005 test 28,   98.071589 secs
$ dmesg
[  908.701665] usbtest 1-1.4:1.0: TEST 28: bulk read 100Mbytes
$ python -c "print('%.2f MB/s' % (100/98.07))"
1.02 MB/s

```

Host kernel module: [drivers/usb/misc/usbtest.c](https://elixir.bootlin.com/linux/latest/source/drivers/usb/misc/usbtest.c)
