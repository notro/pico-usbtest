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

The secondary loopback configuration is enabled in tusb_config.h:
```c
#define CFG_USBTEST_ENABLE_LOOPBACK     1
```
tinyusb doesn't support multiple configurations so my hack around it sometimes end up choosing the wrong configuration index and thus choosing the wrong loopback_complete().

This tinyusb patch is necessary for multiple configurations:
```diff
diff --git a/src/device/usbd.c b/src/device/usbd.c
index 90edc3dd..20b76148 100644
--- a/src/device/usbd.c
+++ b/src/device/usbd.c
@@ -640,7 +638,7 @@ static bool process_control_request(uint8_t rhport, tusb_control_request_t const
         {
           uint8_t const cfg_num = (uint8_t) p_request->wValue;

-          if ( !_usbd_dev.cfg_num && cfg_num ) TU_ASSERT( process_set_config(rhport, cfg_num) );
+          if ( _usbd_dev.cfg_num != cfg_num ) TU_ASSERT( process_set_config(rhport, cfg_num) );
           _usbd_dev.cfg_num = cfg_num;

           tud_control_status(rhport, p_request);
@@ -821,9 +819,6 @@ static bool process_set_config(uint8_t rhport, uint8_t cfg_num)
         // Open successfully, check if length is correct
         TU_ASSERT( sizeof(tusb_desc_interface_t) <= drv_len && drv_len <= remaining_len);

-        // Interface number must not be used already
-        TU_ASSERT(DRVID_INVALID == _usbd_dev.itf2drv[desc_itf->bInterfaceNumber]);
-
         TU_LOG2("  %s opened\r\n", driver->name);
         _usbd_dev.itf2drv[desc_itf->bInterfaceNumber] = drv_id;

@@ -1239,10 +1234,14 @@ bool usbd_edpt_stalled(uint8_t rhport, uint8_t ep_addr)
  */
 void usbd_edpt_close(uint8_t rhport, uint8_t ep_addr)
 {
+  uint8_t const epnum = tu_edpt_number(ep_addr);
+  uint8_t const dir   = tu_edpt_dir(ep_addr);
+
   TU_ASSERT(dcd_edpt_close, /**/);
   TU_LOG2("  CLOSING Endpoint: 0x%02X\r\n", ep_addr);

   dcd_edpt_close(rhport, ep_addr);
+  _usbd_dev.ep_status[epnum][dir].busy = false;

   return;
 }

```
