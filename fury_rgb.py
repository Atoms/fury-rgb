#!/usr/bin/env python3
"""Standalone control for Kingston FURY DDR5 RGB DIMMs (Beast / Renegade).

Protocol taken from OpenRGB's KingstonFuryDRAMController. No dependencies;
talks SMBus through /dev/i2c-N via ioctl. Needs root (or rw on /dev/i2c-N).

    fury_rgb.py detect
    fury_rgb.py off
    fury_rgb.py static RRGGBB [--brightness 0-100]
"""
import argparse
import ctypes
import fcntl
import glob
import os
import struct
import sys
import time

I2C_SLAVE = 0x0703
I2C_SMBUS = 0x0720
I2C_SMBUS_WRITE = 0
I2C_SMBUS_BYTE_DATA = 2

BASE_ADDR_DDR5 = 0x60
DELAY = 0.010

REG_APPLY = 0x08
REG_MODE = 0x09
REG_DIRECTION = 0x0C
REG_DELAY = 0x0D
REG_SPEED = 0x0E
REG_BRIGHTNESS = 0x20
REG_NUM_SLOTS = 0x27
REG_NUM_COLORS = 0x30
REG_MODE_BASE_RED = 0x31

BEGIN_TRANSFER = 0x53
END_TRANSFER = 0x44
MODE_STATIC = 0x00
DIR_BOTTOM_TO_TOP = 0x01


class SMBus:
    def __init__(self, bus):
        self.fd = os.open(f"/dev/i2c-{bus}", os.O_RDWR)

    def write_byte_data(self, addr, reg, val):
        fcntl.ioctl(self.fd, I2C_SLAVE, addr)
        data = ctypes.create_string_buffer(bytes([val]), 34)  # union i2c_smbus_data
        # struct i2c_smbus_ioctl_data { u8 read_write; u8 command; u32 size; union *data; }
        args = struct.pack("BBxxIP", I2C_SMBUS_WRITE, reg, I2C_SMBUS_BYTE_DATA,
                           ctypes.addressof(data))
        fcntl.ioctl(self.fd, I2C_SMBUS, args)

    def close(self):
        os.close(self.fd)


def find_i801_bus():
    for path in glob.glob("/sys/bus/i2c/devices/i2c-*/name"):
        with open(path) as f:
            if f.read().startswith("SMBus I801"):
                return int(path.split("/")[-2].split("-")[1])
    sys.exit("No Intel i801 SMBus adapter found (modprobe i2c_i801 i2c_dev?)")


def write(bus, addr, reg, val, retries=5):
    for attempt in range(retries):
        try:
            bus.write_byte_data(addr, reg, val)
            return
        except OSError:
            time.sleep(3 * (attempt + 1) * DELAY)
    raise OSError(f"write 0x{addr:02x} reg 0x{reg:02x}=0x{val:02x} failed")


def detect(bus):
    """A DIMM is present if it ACKs a begin-transfer on 0x60+slot."""
    found = []
    for slot in range(8):
        addr = BASE_ADDR_DDR5 + slot
        try:
            write(bus, addr, REG_APPLY, BEGIN_TRANSFER, retries=3)
        except OSError:
            continue
        write(bus, addr, REG_APPLY, END_TRANSFER)
        found.append(addr)
        time.sleep(DELAY)
    return found


def set_static(bus, addrs, rgb, brightness):
    def all_(reg, val):
        for a in addrs:
            write(bus, a, reg, val)

    all_(REG_APPLY, BEGIN_TRANSFER)
    time.sleep(DELAY)
    all_(REG_MODE, MODE_STATIC)
    all_(REG_DIRECTION, DIR_BOTTOM_TO_TOP)
    all_(REG_DELAY, 0)
    all_(REG_SPEED, 0)
    all_(REG_NUM_COLORS, 1)
    for i, c in enumerate(rgb):
        all_(REG_MODE_BASE_RED + i, c)
    all_(REG_BRIGHTNESS, brightness)
    all_(REG_NUM_SLOTS, min(len(addrs), 4))
    all_(REG_APPLY, END_TRANSFER)
    time.sleep(DELAY)


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--bus", type=int, help="i2c bus number (default: auto i801)")
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("detect")
    sub.add_parser("off")
    s = sub.add_parser("static")
    s.add_argument("color", help="RRGGBB hex")
    s.add_argument("--brightness", type=int, default=80)
    args = p.parse_args()
    if args.cmd is None:
        p.print_help()
        sys.exit(0)

    try:
        bus = SMBus(args.bus if args.bus is not None else find_i801_bus())
    except PermissionError as e:
        sys.exit(f"{e.filename}: permission denied (run with sudo)")
    try:
        addrs = detect(bus)
        if not addrs:
            sys.exit("No Kingston FURY DDR5 RGB controllers answered at 0x60-0x67")
        print("FURY DIMMs at: " + " ".join(f"0x{a:02x}" for a in addrs))
        if args.cmd == "off":
            set_static(bus, addrs, (0, 0, 0), 0)
        elif args.cmd == "static":
            c = args.color.lstrip("#")
            rgb = tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))
            set_static(bus, addrs, rgb, max(0, min(100, args.brightness)))
    finally:
        bus.close()


if __name__ == "__main__":
    main()
