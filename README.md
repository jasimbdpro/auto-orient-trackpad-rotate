# Auto Orient

Rotates your Windows laptop's trackpad direction to match the screen orientation.

When you rotate the display (portrait, upside-down), Windows rotates the picture but not the trackpad, so your finger and the cursor move in different directions. Auto Orient detects the orientation change and remaps trackpad movement automatically.

- Supports 0°, 90°, 180° and 270°
- Runs silently in the background
- No installation and no Python needed

**Requires:** Windows 10/11.

## How to use

1. Double-click `Auto Orient.exe`. No window appears; it runs in the background.
2. Rotate the screen: **Win + I > System > Display > Display orientation**. The trackpad follows.
3. To stop it, end `Auto Orient.exe` in Task Manager.
4. To start at login: press **Win + R**, type `shell:startup`, and put a shortcut to the exe there.

Windows Defender may flag the unsigned exe (false positive). If so, add an exclusion for it.

## Run the Python script instead

Needs Python 3.8+ (no extra packages).

```
python trackpad_rotate.py
```

Use `pythonw` instead of `python` for no console window. Press Ctrl+C to stop (or end `pythonw.exe` in Task Manager if it has no window).

Optional flags:

- `--swap` swaps the 90° and 270° directions, if they feel reversed.
- `--force N` tests as if the screen were at `N` (0=0°, 1=90°, 2=180°, 3=270°).

## Notes

- A log is written to `trackpad_rotate.log` next to the exe.
- Only one copy runs at a time.
- It remaps every pointer, including external mice, and uses the primary display only.
- Cursor may feel slightly sticky at screen edges.
- To work over admin windows (e.g. Task Manager), run it as administrator.

## License

Free to use, modify and share, without warranty.
