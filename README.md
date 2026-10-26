# fury-rgb

Standalone control for **Kingston FURY DDR5 RGB** memory (Beast / Renegade) on Linux —
no OpenRGB required. Single Python file, standard library only, talks to the DIMMs'
RGB controllers over SMBus via `/dev/i2c-N`.

The protocol is taken from OpenRGB's
[KingstonFuryDRAMController](https://gitlab.com/CalcProgrammer1/OpenRGB/-/tree/master/Controllers/KingstonFuryDRAMController).

## Why

OpenRGB never detected these DDR5 sticks here, and its boot-time detector sweep
(`openrgb --mode off`) left the whole memory SMBus unresponsive — even the SPD
temperature sensors — until a full power-off. This tool only touches the FURY RGB
controller addresses (`0x60`–`0x67`).

## Usage

```sh
./fury_rgb.py detect                         # list RGB controllers found
./fury_rgb.py off                            # LEDs off (static black, brightness 0)
./fury_rgb.py static ff0000 --brightness 50  # static colour
./fury_rgb.py --bus 1 detect                 # override auto-detected SMBus
```

Needs read/write access to `/dev/i2c-N` (root, or a uaccess/udev rule) and the
`i2c_i801` + `i2c_dev` kernel modules. The Intel i801 SMBus adapter is found
automatically.

## Turn off at boot

`openrgb-off.service` runs `fury_rgb.py off` at startup:

```sh
sudo cp openrgb-off.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now openrgb-off.service
```

Adjust the script path in `ExecStart` if the repo lives elsewhere. The script is run
through `/usr/bin/python3` because SELinux (Fedora) blocks systemd from executing
files under `/home` directly.

## Troubleshooting

- `sudo i2cdetect -y -r 1` should show `UU` at the SPD hubs (`0x51`/`0x53` etc.) and
  the RGB controllers at `0x60 + slot`.
- If the bus is completely empty (even the SPD hubs are gone), something wedged it —
  e.g. an OpenRGB scan. A reboot is not enough: shut down and switch the PSU off for
  ~10 s.
- Nothing at `0x60`–`0x67` while the SPD hubs respond usually means non-RGB sticks.

## Tested on

ASRock Z790 Pro RS WiFi, i7-14700K, Fedora 44 (kernel 7.2), 2× Kingston FURY
DDR5-5200 32 GB (`KF552C36…`), slots 1 and 3 → controllers at `0x61`/`0x63`.

## License

MIT — see [LICENSE](LICENSE).
