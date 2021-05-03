# SPDX-License-Identifier: CC0-1.0

import argparse
import array
import ctypes
import errno
import fcntl
import os
from pathlib import Path
import random
import sys
import time

import usb.core
import usb.util


DEFAULT_TESTS = (
    # "TEST 0:  NOP\n"

    # Simple non-queued bulk I/O tests
    1, # "TEST 1:  write %d bytes %u times\n", param->length, param->iterations
    2, # "TEST 2:  read %d bytes %u times\n", param->length, param->iterations
    3, # "TEST 3:  write/%d 0..%d bytes %u times\n", param->vary, param->length, param->iterations
    4, # "TEST 4:  read/%d 0..%d bytes %u times\n", param->vary, param->length, param->iterations

    # Queued bulk I/O tests
    5, # "TEST 5:  write %d sglists %d entries of %d bytes\n", param->iterations, param->sglen, param->length
    6, # "TEST 6:  read %d sglists %d entries of %d bytes\n", param->iterations, param->sglen, param->length
    7, # "TEST 7:  write/%d %d sglists %d entries 0..%d bytes\n", param->vary, param->iterations, param->sglen, param->length
    8, # "TEST 8:  read/%d %d sglists %d entries 0..%d bytes\n", param->vary, param->iterations, param->sglen, param->length

    # non-queued sanity tests for control (chapter 9 subset)
    9, # "TEST 9:  ch9 (subset) control tests, %d times\n", param->iterations

    # queued control messaging
    10, # "TEST 10:  queue %d control calls, %d times\n", param->sglen, param->iterations

    # simple non-queued unlinks (ring with one urb)
    11, # "TEST 11:  unlink %d reads of %d\n", param->iterations, param->length
    12, # "TEST 12:  unlink %d writes of %d\n", param->iterations, param->length

    # ep halt tests
    # FAILS "TEST 13:  set/clear %d halts\n", param->iterations

    # control write tests
    # Intel's USB 2.0 compliance test device
    # "TEST 14:  %d ep0out, %d..%d vary %d\n", param->iterations, realworld ? 1 : 0, param->length, param->vary
    # not implemented yet, tinyusb doesn't forward the request to the driver

    # iso write tests
    # "TEST 15:  write %d iso, %d entries of %d bytes\n", param->iterations, param->sglen, param->length

    # iso read tests
    # "TEST 16:  read %d iso, %d entries of %d bytes\n", param->iterations, param->sglen, param->length

    # Tests for bulk I/O using DMA mapping by core and odd address
    17, # "TEST 17:  write odd addr %d bytes %u times core map\n", param->length, param->iterations
    18, # "TEST 18:  read odd addr %d bytes %u times core map\n", param->length, param->iterations

    # Tests for bulk I/O using premapped coherent buffer and odd address
    # "TEST 19:  write odd addr %d bytes %u times premapped\n", param->length, param->iterations
    20, # "TEST 20:  read odd addr %d bytes %u times premapped\n", param->length, param->iterations

    # control write tests with unaligned buffer
    21, # "TEST 21:  %d ep0out odd addr, %d..%d vary %d\n", param->iterations, realworld ? 1 : 0, param->length, param->vary

    # unaligned iso tests
    # "TEST 22:  write %d iso odd, %d entries of %d bytes\n", param->iterations, param->sglen, param->length
    # "TEST 23:  read %d iso odd, %d entries of %d bytes\n", param->iterations, param->sglen, param->length

    # unlink URBs from a bulk-OUT queue
    # "TEST 24:  unlink from %d queues of %d %d-byte writes\n", param->iterations, param->sglen, param->length

    # Simple non-queued interrupt I/O tests
    # "TEST 25: write %d bytes %u times\n", param->length, param->iterations
    # "TEST 26: read %d bytes %u times\n", param->length, param->iterations

    # "TEST 27: bulk write %dMbytes\n", (param->iterations * param->sglen * param->length) / (1024 * 1024)
    # [Errno 5] Input/output error

    28, # "TEST 28: bulk read %dMbytes\n", (param->iterations * param->sglen * param->length) / (1024 * 1024)

    # Test data Toggle/seq_nr clear between bulk out transfers
    # "TEST 29: Clear toggle between bulk writes %d times\n", param->iterations
    )


################################################################################
#
# libusb doesn't exposed the underlying file descriptor
#

class UsbDeviceDescriptor(ctypes.Structure):
    _fields_ = [('bLength', ctypes.c_uint8),
                ('bDescriptorType', ctypes.c_uint8),
                ('bcdUSB', ctypes.c_uint16),
                ('bDeviceClass', ctypes.c_uint8),
                ('bDeviceSubClass', ctypes.c_uint8),
                ('bDeviceProtocol', ctypes.c_uint8),
                ('bMaxPacketSize0', ctypes.c_uint8),
                ('idVendor', ctypes.c_uint16),
                ('idProduct', ctypes.c_uint16),
                ('bcdDevice', ctypes.c_uint16),
                ('iManufacturer', ctypes.c_uint8),
                ('iProduct', ctypes.c_uint8),
                ('iSerialNumber', ctypes.c_uint8),
                ('bNumConfigurations', ctypes.c_uint8)]

def dev_open_fd(dev):
    for path in Path('/dev/bus/usb').rglob('*'):
        if path.is_char_device():
            with path.open(mode='rb') as f:
                data = f.read(ctypes.sizeof(UsbDeviceDescriptor))
            desc = UsbDeviceDescriptor.from_buffer_copy(data)
            if (desc.idVendor == dev.idVendor and desc.idProduct == dev.idProduct):
                return open(path, 'r+b', buffering=0)


################################################################################
#
# Run tests using the usbtest kernel module
#

_IOC_NRBITS     = 8
_IOCtype_BITS   = 8
_IOC_SIZEBITS   = 14

_IOC_NRSHIFT    = 0
_IOCtype_SHIFT  = (_IOC_NRSHIFT+_IOC_NRBITS)
_IOC_SIZESHIFT  = (_IOCtype_SHIFT+_IOCtype_BITS)
_IOC_DIRSHIFT   = (_IOC_SIZESHIFT+_IOC_SIZEBITS)

_IOC_WRITE      = 1
_IOC_READ       = 2

def _IOC(_dir,type_,nr,size):
    return ((_dir)  << _IOC_DIRSHIFT) | \
           ((ord(type_)) << _IOCtype_SHIFT) | \
           ((nr)   << _IOC_NRSHIFT) | \
           ((size) << _IOC_SIZESHIFT)

def _IOWR(type_,nr,size):
    return _IOC(_IOC_READ|_IOC_WRITE,(type_),(nr),(ctypes.sizeof(size)))


class timeval(ctypes.Structure):
    _fields_ = [
                ("tv_sec", ctypes.c_long),
                ("tv_usec", ctypes.c_long),
                ]

class usbtest_param(ctypes.Structure):
    _fields_ = [
                ("test_num", ctypes.c_uint),
                ("iterations", ctypes.c_uint),
                ("length", ctypes.c_uint),
                ("vary", ctypes.c_uint),
                ("sglen", ctypes.c_uint),

                ("duration", timeval)
                ]

USBTEST_REQUEST = _IOWR('U', 100, usbtest_param)


class usbdevfs_ioctl(ctypes.Structure):
    _fields_ = [('ifno', ctypes.c_int),         # interface 0..N ; negative numbers reserved
                ('ioctl_code', ctypes.c_int),   # MUST encode size + direction of data so the
                                                # macros in <asm/ioctl.h> give correct values
                ('data', ctypes.POINTER(usbtest_param))]     # param buffer (in, or out)

USBDEVFS_IOCTL = _IOWR('U', 18, usbdevfs_ioctl)


# REVISIT: write: length=512, 8x64, looses one 64 packet on the receiving end.
# Multiple iterations of test1 is fine but running 1 then 3 (and also more tests) will end up one packet short 448 bytes.

def usbtest_test(fd, interface, test_num, iterations=1, length=512, vary=512, sglen=1, verbose=False):
    print(f'#{test_num} iterations={iterations} length={length} vary={vary} sglen={sglen} :: ', end='', flush=True)

    param = usbtest_param()
    param.test_num = test_num
    param.iterations = iterations
    param.length = length
    param.vary = vary
    param.sglen = sglen

    arg = usbdevfs_ioctl()
    arg.ifno = interface.bInterfaceNumber
    arg.ioctl_code = USBTEST_REQUEST
    arg.data = ctypes.pointer(param)

    try:
        fcntl.ioctl(fd, USBDEVFS_IOCTL, arg)
        ms = param.duration.tv_sec * 1000 + param.duration.tv_usec / 1000
        if ms < 1000:
            status = f'{ms:.3f} ms'
        else:
            status = f'{(ms / 1000):.6f} secs'
        if test_num in (27, 28):
            total = iterations * length * sglen
            throughput = total / (ms / 1000)
            if throughput < 1024:
                status += f' - {throughput:.0f} bytes/s'
            elif throughput < 1024 * 1024:
                status += f' - {(throughput / 1024):.1f} kB/s'
            else:
                status += f' - {(throughput / 1024 / 1024):.1f} MB/s'
    except OSError as e:
        if e.errno == errno.EOPNOTSUPP:
            status = 'SKIP'
        else:
            status = str(e)

    print(status)

    if verbose:
        print_kmsg()


def run_usbtests(dev, config, args):
    interface = config.interfaces()[0]

    # Fixme check current config first
    if dev.is_kernel_driver_active(interface.bInterfaceNumber):
        if args.debug:
            print('Detach kernel driver')
        dev.detach_kernel_driver(interface.bInterfaceNumber)
        print_kmsg()

    if args.debug:
        print('Set sourcesink config')
    config.set()
    print_kmsg()

    if not dev.is_kernel_driver_active(interface.bInterfaceNumber):
        if args.debug:
            print('Attach kernel driver')
        dev.attach_kernel_driver(interface.bInterfaceNumber)
        print_kmsg()

    fd = dev_open_fd(dev)

    while True:
        for test in args.test:
            usbtest_test(fd, interface, test, iterations=args.iterations, length=args.length, vary=args.vary, sglen=args.sglen, verbose=True)
        if not args.loop:
            break


################################################################################
#
# Run loopback test
#

TRANSFER_TIMEOUT_MS = 5000

def loopback_test(interface, length):
    print(f'loopback_test: length={length} :: ', end='')

    dev = interface.device

    send = array.array('B', os.urandom(length))
    receive = array.array('B', b'\x00' * length)

    start = time.process_time()

    #print('send', send)
    try:
        ret = dev.write(0x01, send, TRANSFER_TIMEOUT_MS)
        if not len(send) % interface.endpoints()[0].wMaxPacketSize:
            dev.write(0x01, None, TRANSFER_TIMEOUT_MS) # zlp
    except usb.core.USBError as e:
        print(f'write: {e}')
        return

    #print('ret', ret)
    if ret != len(send):
        print(f'write: ret={ret} differs from expected {len(send)}')
        return

    try:
        ret = dev.read(0x81, receive, TRANSFER_TIMEOUT_MS)
    except usb.core.USBError as e:
        print(f'read: {e}')
        return

    end = time.process_time()

    if ret != len(send):
        print(f'read: ret={ret} differs from expected {len(send)}')
        return

    #print('receive', receive)
    if send != receive:
        print(f'read: sent and received differs')
        print('SENT')
        print(send)
        print('RECEIVED')
        return

    print(f'{((end - start) * 1000):.1f} ms')


def run_loopback(dev, config, args):
    interface = config.interfaces()[0]

    if dev.is_kernel_driver_active(interface.bInterfaceNumber):
        if args.debug:
            print('Detach kernel driver')
        dev.detach_kernel_driver(interface.bInterfaceNumber)
        print_kmsg()

    if args.debug:
        print('Set loopback config')
    config.set()
    time.sleep(1)
    print_kmsg()

    # Prevent kernel driver from binding to loopback config
    if dev.is_kernel_driver_active(interface.bInterfaceNumber):
        if args.debug:
            print('Unbind kernel driver')

        name = None
        for path in Path('/sys/bus/usb/drivers/usbtest').glob('*'):
            if path.is_symlink() and '-' in path.name:
                name = path.name

        #print('NAME', name)
        if name:
            with open('/sys/bus/usb/drivers/usbtest/unbind', 'w') as f:
                f.write(name)

        print_kmsg()

    if 0 and dev.is_kernel_driver_active(interface.bInterfaceNumber):
        if args.debug:
            print('Detach kernel driver')
        dev.detach_kernel_driver(interface.bInterfaceNumber)
        print_kmsg()

    length = args.vary
    while length <= args.length:
        loopback_test(interface, length)
        length += args.vary


################################################################################
#
# Read kernel messages
#

kmsg_fd = None

def init_kmsg(verbose):
    if not verbose:
        return
    global kmsg_fd
    kmsg_fd = os.open('/dev/kmsg', os.O_RDONLY | os.O_NONBLOCK)
    os.lseek(kmsg_fd, 0, os.SEEK_END)

def read_kmsg():
    if not kmsg_fd:
        return
    while True:
        try:
            buf = os.read(kmsg_fd, 512)
        except BlockingIOError:
            break
        if not buf:
            break
        try:
            lines = buf.splitlines()
            prefix, msg = lines[0].split(b';')
        except ValueError:
            yield lines[0].decode("utf-8")
        yield msg.decode("utf-8")

def print_kmsg():
    for msg in read_kmsg():
        print(f'    dmesg: {msg}')


################################################################################
#
# Find test device
#

def _find_test_device(dev):
    if dev.bDeviceClass != 0xff:
        return False

    for config in dev:
        for intf in config:
            if intf.bNumEndpoints not in [2,4]:
                return False

    return True


def find_test_device():
    return usb.core.find(find_all=False, custom_match=_find_test_device)


def main(args):
    if args.test and args.exclude:
        args.test = tuple(set(args.test) - set(args.exclude))
    if args.perf:
        args.test = (27, 28)
        # 100 * 32768 * 32 = 100MB
        args.iterations = 100
        args.length = 32768
        args.sglen = 32
    if args.test and args.debug > 1:
        print('Tests:', ', '.join([str(t) for t in args.test]))

    dev = find_test_device()
    if not dev:
        print('No device found')
        return

    sourcesink = dev[0]
    try:
        loopback = dev[1]
    except usb.core.USBError:
        loopback = None

    init_kmsg(args.debug)

    if args.reset:
        if args.debug:
            print('USB reset')
        dev.reset()
        time.sleep(1)
        print_kmsg()

    if args.test:
        run_usbtests(dev, sourcesink, args)

    if args.loopback:
        if not loopback:
            print("No loopback configuration found")
        else:
            run_loopback(dev, loopback, args)


if __name__ == '__main__':

    def device_arg_split(arg):
        vid, pid = str(arg).split(':')
        return int(vid, 16), int(pid, 16)

    def device_arg_check(arg):
        try:
            device_arg_split(arg)
        except Exception:
            raise argparse.ArgumentTypeError('Value has to be on the form: vid:pid')
        return arg

    def test_arg_parse(arg):
        try:
            tests = [int(t) for t in arg.split(',')]
        except Exception:
            raise argparse.ArgumentTypeError('Value has to be a comma separated list of tests')
        return tuple(set(tests))

    # Default: tools/usb/testusb.c
    #    param.iterations = 1000;
    #    param.length = 1024;
    #    param.vary = 1024;
    #    param.sglen = 32;

    parser = argparse.ArgumentParser(description='Tool for running the usbtest module tests')

#    parser.add_argument('--device', '-D', type=device_arg_check, help='only test specific device')
    #    -A usb-dir
    parser.add_argument('--loop', '-l', action='store_true', help='loop forever(for stress test)')
    parser.add_argument('--test', '-t', nargs='?', type=test_arg_parse, const=DEFAULT_TESTS, help='run comma separated list of test cases')
    parser.add_argument('--exclude', '-x', nargs='?', type=test_arg_parse, help='exclude specified test cases')
    #    -n              no test running, show devices to be tested
    parser.add_argument('--perf', action='store_true', help='run performance tests 27 and 28')
    parser.add_argument('--loopback', action='store_true', help='run loopback tests')
    parser.add_argument('--reset', action='store_true', help='reset USB device')
    parser.add_argument('--debug', '-d', action='count', default=0, help='increase debug output')

    group = parser.add_argument_group('case arguments')
    group.add_argument('--iterations', '-c', type=int, default=1, help='iterations')
    group.add_argument('--length', '-s', type=int, default=512, help='transfer length')
    group.add_argument('--sglen', '-g', type=int, default=1, help='sglen')
    group.add_argument('--vary', '-v', type=int, default=256, help='vary')

    args = parser.parse_args()

    main(args)
