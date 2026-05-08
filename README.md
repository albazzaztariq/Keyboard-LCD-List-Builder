# List Builder for Keyboard LCD Screens

Generates 248×170 PNG images for built-in LCD screens on keyboards. Obviously, you can use this to generate any lists, but this was made for my Corsair Vanguard 96 Pro keyboard's screen. The images are uploaded to the keyboard through the **Screen** widget in the Corsair Web Hub app — this tool does not talk to the keyboard directly.

Each image is a list of up to 8 bullet entries (≤ 26 chars each) drawn at native LCD resolution with no upscaling. Text and background colors are user-selectable, and every saved PNG carries its own metadata so that re-opening it in the GUI restores the original entries and colors.

## Features

- 8-line bullet list with auto-shrinking font (11–22 px range) so all lines fit at 248×170. 8 lines was selected because that's the most that fit neatly on my screen.
- Live preview pane that re-renders on every keystroke and color change.
- File table with **Name** and **Created/Modified** columns, sorted by name. This way you can see all the lists you've made or are in the folder for these images.
- Light / dark theme toggle. The dark theme uses purple and dark-mode-themes the Windows title bar via the DWM API.
- Theme and last-used colors persist across sessions in `%APPDATA%\KeyboardLCDTodoBuilder\settings.json`.
- Self-describing PNG output: each saved file embeds its own `{items, fg, bg}` JSON in a `tEXt` chunk, so selecting a file in the GUI refills the form.
- Bundled Windows 11 keyboard-shortcut reference panel: a random shortcut rotates every 10 seconds in the bottom-right of the window, and a 3 × 3 button grid opens scrollable reference sheets for each of the 9 categories (226 shortcuts total).

## Repository layout

```
Source Code (Python)/    todo_gui.py, icon.ico, windows11-shortcuts.json,
                         and Codebase Reference.md
Windows Binary/          KeyboardLCDListBuilder.exe (one-file build)
```

## How it was built

The application is written in Python 3.12 using the standard `tkinter` GUI library and Pillow for image rendering and PNG metadata. The single source file is `Source Code (Python)/todo_gui.py`.

The Windows binary in `Windows Binary/` is generated from the Python source with [PyInstaller](https://pyinstaller.org). The build command is:

```
pyinstaller --onefile --windowed --noconfirm \
  --icon "icon.ico" --name "KeyboardLCDListBuilder" \
  --add-data "windows11-shortcuts.json;." \
  --add-data "icon.ico;." \
  todo_gui.py
```

The result is a single self-contained `.exe`. The shortcut catalog and icon are embedded in the bundle and extracted to a temporary directory at runtime via `sys._MEIPASS`. User-writable files (the `Images/` folder, where generated PNGs are stored) sit next to the `.exe`.

## Running from source

```
python -m pip install Pillow
python todo_gui.py
```

`Pillow` is the only third-party dependency. On first run, if it is missing, the script will attempt `pip install Pillow --break-system-packages` automatically.

## Running the binary

Download `KeyboardLCDListBuilder.exe` from the [Releases](../../releases/latest) page and run it. Everything is self-contained obviously with a binary. An `Images/` folder is created next to the `.exe` on first launch and holds the generated PNGs.

## Generating an image

1. Click **New**. The filename auto-populates as the next free `todoN`.
2. Type up to 8 entries (≤ 26 chars each).
3. Pick text and background colors with the **Select…** buttons.
4. Click **Generate PNG**. The file is written to `Images/`.
5. In the Corsair Web Hub app: Vanguard Pro 96 → **Screen** tab → **+** → pick the file. iCUE works basically the same.

## Internal documentation

`Source Code (Python)/Codebase Reference.md` is the maintainer-oriented reference that describes the module layout, key functions, data shapes, theming system, and every other internal detail.

## License

Do what you wish. Modify it, break it, make it 1000x better - I just ask you let me know! I'd love to see any work contributed or hear about any issues encountered.
