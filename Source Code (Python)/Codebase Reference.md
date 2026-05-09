# Keyboard / Corsair Keyboard / LCD Image Generator — Codebase Reference

## Project

**Name:** Keyboard LCD — To-Do List Builder
**Type:** Single-file Python Tkinter GUI for authoring 248×170 PNGs that upload to the Corsair Vanguard Pro 96 keyboard's built-in LCD via the Corsair Web Hub app's *Screen* widget. Bundles a Windows 11 keyboard-shortcut reference panel for ambient discovery.
**Path:** `%LCD_GENERATOR_ROOT%` — registered in `HKCU\Environment`; AutoPathRef daemon keeps it current across folder renames/moves. Resolves today to `C:\Users\azt12\OneDrive\Documents\Computing\Dev Tools\Keyboard\Corsair Keyboard\LCD Image Generator for To-Do Lists & Others`.

| Attribute | Value |
|---|---|
| Language | Python 3.12 |
| Runtime | `pythonw.exe` (windowless) at `C:\Users\azt12\AppData\Local\Programs\Python\Python312\pythonw.exe` |
| GUI toolkit | tkinter (stdlib) + Pillow (with `ImageTk`) |
| Entry point | `todo_gui.py` |
| Launch shim | `C:\Users\azt12\bin\todo` (Bash) and `C:\Users\azt12\bin\todo.cmd` (cmd.exe / PowerShell) — both in PATH |
| Output canvas | 248×170 px (Vanguard Pro 96 native LCD resolution) |
| Output format | PNG with embedded `tEXt` metadata chunk |
| User settings | `%APPDATA%\KeyboardLCDTodoBuilder\settings.json` (theme + last-used colors) |
| Shortcut catalog | `windows11-shortcuts.json` (sibling to `todo_gui.py`; bundled into `_MEIPASS` when frozen) |
| Distribution | Source tree on GitHub at `Keyboard-LCD-List-Builder`; one-file Windows binary built with PyInstaller 6.x |

---

## Architectural Principles

1. **One file, no abstractions.** The whole app — render logic, GUI, file I/O, theming, settings persistence, shortcut panel — is `todo_gui.py`. No separate modules, no MVC split.
2. **PNG carries its own source of truth.** Every saved image embeds `{items, fg, bg}` JSON in a `tEXt` chunk under key `todo_meta`. There is **no sidecar `.json`, `.txt`, or database** *for image content*. Selecting a file in the table reads the chunk and refills the form. The PNG round-trips losslessly. The Corsair uploader ignores unknown chunks.
3. **One render function, two consumers.** `render_image()` returns an in-memory `PIL.Image`. `render_png()` is a thin wrapper that calls it, attaches metadata, and writes to disk. The live preview pane and the on-disk file therefore use the same drawing code — preview is pixel-identical to the eventual PNG.
4. **Native LCD resolution, no upscaling.** Output is exactly 248×170. Auto-shrink picks the largest font from `MAX_FONT` down to `MIN_FONT` that fits all bullet lines. No resampling, no scaling — pixel-aligned text.
5. **Frozen-aware paths.** When running under PyInstaller, user-writable files (the `Images/` folder) sit next to the `.exe`, while bundled read-only assets (`windows11-shortcuts.json`, `icon.ico`) are loaded from `sys._MEIPASS`. When running from source, both resolve to the script's directory.
6. **No "TODO" title in the rendered image.** The full 158 px of vertical space is bullet area.
7. **User preferences persist across sessions.** Theme choice and last-used text/background colors are saved to `%APPDATA%` — no hidden files in the project folder, no Windows Registry writes.

---

## Project Structure

```
LCD Image Generator for To-Do Lists & Others/
  todo_gui.py                     — GUI + render + metadata I/O + theming + settings + shortcut panel
  icon.ico                        — multi-size Windows icon (16/24/32/48/64/128/256)
  windows11-shortcuts.json        — bundled shortcut catalog (9 categories, 226 entries)
  Codebase Reference.md           — this file
  Images/                         — generated PNGs; auto-created at runtime, .gitignored
    todo1.png, …
  Keyboard-LCD-List-Builder/      — local staging mirror of the published GitHub repo
    Source Code (Python)/
    Windows Binary/
```

---

## Key Paths & Constants

| Path | Purpose |
|---|---|
| `SCRIPT_DIR` | When unfrozen: folder containing `todo_gui.py`. When frozen: folder containing the `.exe`. Used for *user-writable* state (`Images/`). |
| `BUNDLE_DIR` | When unfrozen: same as `SCRIPT_DIR`. When frozen: `sys._MEIPASS` (PyInstaller's runtime extraction dir). Used for *bundled read-only* assets. |
| `IMAGES_DIR` | `SCRIPT_DIR / "Images"`. Auto-created. All image reads/writes/deletes happen here. |
| `SHORTCUTS_FILE` | `BUNDLE_DIR / "windows11-shortcuts.json"`. Read-only. |
| `APPDATA_DIR` | `%APPDATA%\KeyboardLCDTodoBuilder\`. Auto-created on first settings write. |
| `SETTINGS_FILE` | `APPDATA_DIR / "settings.json"`. Holds `{"theme": ..., "fg": ..., "bg": ...}`. |
| `C:\Users\azt12\bin\todo` | Bash launch wrapper. `! todo` from inside Claude Code TUI. |
| `C:\Users\azt12\bin\todo.cmd` | cmd.exe / PowerShell launch wrapper. |

| Constant | Value | Purpose |
|---|---|---|
| `W, H` | `248, 170` | Vanguard Pro 96 LCD pixel dimensions. |
| `PREVIEW_W, PREVIEW_H` | `W, H` | Preview pane shows at native LCD size. |
| `MAX_CHARS` | `26` | Per-line character cap (validated on key entry). |
| `MAX_ITEMS` | `8` | Max bullet lines per image. |
| `MIN_FONT` / `MAX_FONT` | `11` / `22` | Auto-shrink range for the body font. |
| `PAD` | `6` | Inner padding around the body block. |
| `DEFAULT_FG` / `DEFAULT_BG` | `#FFF005` / `#000000` | Initial colors *only on very first launch* (before any settings file exists). After that, the user's last-used pair is restored. |
| `META_KEY` | `"todo_meta"` | PNG `tEXt` chunk key holding the JSON payload. |
| `TODO_NAME_RE` | `^todo(\d+)$` (case-insensitive) | Regex used by **New** to find the highest existing `todoN` and pick `N+1`. |
| `SHORTCUT_ROTATE_MS` | `10_000` | Interval between random-shortcut rotations in the bottom panel. |
| `THEMES` | dict of `light`, `dark` | Palette dictionaries used by `_apply_theme`. |

---

## Module Layout

| Section | Role |
|---|---|
| Module-level imports | stdlib + Pillow (`Image`, `ImageDraw`, `ImageFont`, `ImageTk`, `PngInfo`) + `tkinter.font` for measuring text + `ctypes` for the Windows dark-titlebar API + `random` for shortcut rotation. |
| Module-level constants | Frozen-aware path resolution, geometry, defaults, font fallback list, `THEMES` palettes (each carries a nested `btn_palette`), `APPDATA_DIR` / `SETTINGS_FILE`, `SHORTCUTS_FILE`, `SHORTCUT_ROTATE_MS`, `BUTTON_FONT`. |
| `load_user_settings()` / `save_user_settings()` | Read/write `%APPDATA%\KeyboardLCDTodoBuilder\settings.json`. Tolerant of missing file and malformed JSON. |
| `load_shortcuts()` | Read `windows11-shortcuts.json` from `BUNDLE_DIR`. Returns `{"categories": {}}` on failure. |
| `load_font(size)` | Try `arialbd.ttf`, then DejaVu, fall back to Pillow default. |
| `hex_to_rgb(h)` | `#RRGGBB` → tuple. |
| `measure_lines(draw, lines, font)` | Vertical block height + per-line heights + line gap (22% of line height). |
| `render_image(items, fg_hex, bg_hex)` | Auto-shrinks font, draws bullets, returns a `PIL.Image`. **No file I/O.** Returns a solid-bg image when `items` is empty. |
| `render_png(items, fg_hex, bg_hex, out_path)` | Calls `render_image()`, attaches `todo_meta` `tEXt` chunk, saves PNG. |
| `read_png_meta(path)` | Returns `{items, fg, bg}` dict or `None`. Tolerant of missing/garbled metadata. |
| `class RoundedButton(tk.Canvas)` | Canvas-based button with rounded corners + slight border, hover and press states, and per-instance theming via `apply_palette(...)`. Auto-sizes to text + horizontal padding; supports `sticky="we"` stretching via a `<Configure>` re-render. `set_active(bool)` renders a sticky-pressed look (used by the sun/moon toggle). |
| `class TodoApp` | The Tkinter window. Two-pane layout. |

---

## Key Functions

| Function | Purpose |
|---|---|
| `render_image` | The only place text is drawn. Used by both the saved PNG and the in-memory live preview. |
| `render_png` | Thin wrapper that writes `render_image`'s output with metadata. |
| `read_png_meta` | The only place metadata is read out. Returns `None` for any failure mode. |
| `load_user_settings` / `save_user_settings` | Persist `theme`, `fg`, `bg` across sessions in `%APPDATA%`. |
| `load_shortcuts` | Load the Windows 11 shortcut catalog at startup. |
| `TodoApp._next_todo_name` | Scans `IMAGES_DIR` for `todoN.png`, returns `f"todo{max(N)+1}"`. Drives the **New** button. |
| `TodoApp._on_file_selected` | Reads metadata from the selected file, refills entries + colors, displays the saved PNG in the preview. |
| `TodoApp._live_preview` | Re-renders in memory from the current form state and pushes it to the preview pane. Bound to every entry's `<KeyRelease>`, both color pickers, and **New** / **Delete**. |
| `TodoApp._update_preview(path)` | Loads an on-disk PNG into the preview pane. Used only by `_on_file_selected` and post-`_generate`. |
| `TodoApp._generate` | Validates inputs, prompts on overwrite, calls `render_png`, refreshes the table, re-selects the new file, updates the preview. |
| `TodoApp._pick_random_shortcut` | Choose one shortcut at random from the catalog and display it in the bottom panel. Filters out the currently shown entry to avoid back-to-back repeats. Sets `keys`, action `Text` widget, and `Shortcut Category: <name>` line. |
| `TodoApp._set_action_text(text)` | Replaces the (disabled) action `Text` widget contents. If the rendered text would overflow the visible area (detected via `dlineinfo("end-1c") is None`), peels off words from the end and appends `...` until everything fits — so it never clips off-screen. |
| `TodoApp._set_status(text, bold_prefix=None)` | Replaces the (disabled) status `Text` widget contents. If `bold_prefix` matches the start of `text`, that prefix is rendered with the `bold` tag; the rest is normal weight on the same wrapped row. Used for both the static `Output folder: <path>` line (with bold prefix) and dynamic status messages (no prefix). |
| `TodoApp._schedule_shortcut_rotation` | Calls `_pick_random_shortcut` and re-arms itself via `self.after(SHORTCUT_ROTATE_MS, ...)`. Tk auto-cancels pending callbacks on window destroy. |
| `TodoApp._open_shortcuts_reference` | Opens a single combined Toplevel — left side shows a scrollable wrap-aware table of keys + actions for the currently selected category, right side is a vertical sidebar of `RoundedButton`s (one per category). Action labels' `wraplength` is bound to the live canvas width so text never overflows. Each row has 1-px theme-colored separator frames above and below. Registers itself in `_open_popups` and binds `<Destroy>` to deregister. |
| `TodoApp._theme_popup(win, name)` | Per-popup theme applier — sets `bg`, toggles dark title bar, runs `_apply_table_palette` (if attached), and re-paints any sidebar `RoundedButton`s the popup registered. |
| `TodoApp._apply_theme(name)` | Applies a `THEMES[name]` palette across all widgets (root, ttk Style, Treeview headings, listbox, preview, status text colors, all `RoundedButton`s), themes any open popups via `_theme_popup`, persists the choice if changed. Calls `_apply_titlebar_theme`. |
| `TodoApp._apply_titlebar_theme(name)` | Toggles Windows immersive dark mode on the main window's title bar via `DwmSetWindowAttribute`. Delegates to the static `_set_dark_titlebar` helper. |
| `TodoApp._set_dark_titlebar(window, dark)` | Static helper — toggles dark mode on any Tk window's title bar (attribute id 20, fallback 19 for older Win10 builds). |
| `TodoApp._save_user_colors` | Writes `fg` + `bg` into `settings.json` after each color pick. |

---

## GUI Layout

```
┌──────────────────────────────────────────────────────────────────────┐
│ Title bar — toggles dark via DwmSetWindowAttribute                  │
├──────────────────────────────┬───────────────────────────────────────┤
│ Existing files                │ Up to 8 entries, 26 characters each. ☀ ☾ │
│ ╭─────────────────────────╮   │                                       │
│ │       Refresh           │   │       1.  [_____________]             │
│ ╰─────────────────────────╯   │       2.  [_____________]             │
│ ┌────────┬────────────────┐   │       …  (centered block)             │
│ │  Name  │Created/Modified│   │       8.  [_____________]             │
│ │  todo1 │   5/8/2026     │   │                                       │
│ │        │                │   │  Text color:    [██]  Select…        │
│ └────────┴────────────────┘   │  Background:    [██]  Select…        │
│ ╭─────────────────────────╮   │                                       │
│ │       Delete            │   │  Filename: [todo1]      .png          │
│ ╰─────────────────────────╯   │  ╭────────────────────────────────╮   │
│ ╭─────────────────────────╮   │  │       Generate PNG             │   │
│ │         New             │   │  ╰────────────────────────────────╯   │
│ ╰─────────────────────────╯   │  Output folder: C:\Users\…\Images     │
│                               │  ─────────────────────────────────    │
│ Preview                       │  ─────────────────────────────────    │
│ ┌─────────────────────────┐   │  Ctrl + C                             │
│ │  (248×170 LCD preview)  │   │  Copy the selected text.              │
│ │                         │   │  Shortcut Category: Text Editing      │
│ │                         │   │  ╭────────────────────────────────╮   │
│ │                         │   │  │ Keyboard Shortcuts Reference   │   │
│ └─────────────────────────┘   │  ╰────────────────────────────────╯   │
└──────────────────────────────┴───────────────────────────────────────┘
```

---

## Data Shapes

**Embedded PNG metadata** — JSON string under `tEXt` key `todo_meta`:

```json
{
  "items": ["Reorg azt/bin", "Fix right-click menu", "..."],
  "fg": "#FFF005",
  "bg": "#000000"
}
```

`items` is a list of 1–8 strings, each ≤ 26 chars. `fg` and `bg` are `#RRGGBB` hex strings.

**User settings** — JSON file at `%APPDATA%\KeyboardLCDTodoBuilder\settings.json`:

```json
{
  "theme": "dark",
  "fg":    "#FF00AA",
  "bg":    "#1A1A2E"
}
```

All keys are optional. Missing keys fall back to: `theme = "light"`, `fg = DEFAULT_FG`, `bg = DEFAULT_BG`.

**Shortcut catalog** — `windows11-shortcuts.json`, scraped from Microsoft's Windows 11 shortcut docs:

```json
{
  "metadata": { "source": "...", "os": "Windows 11", "total_shortcuts": 226, "total_categories": 9 },
  "categories": {
    "text_editing": {
      "display_name": "Text Editing",
      "description": "...",
      "shortcuts": [ {"keys": "Ctrl + A", "action": "Select all text."}, ... ]
    },
    ...
  }
}
```

---

## Theming

Two palettes are defined in the `THEMES` dict: `"light"` and `"dark"`. Each palette covers ~18 color slots (root bg, fg, muted/caption text, listbox row + selection, table heading + divider, entry, preview pane, etc.) plus a nested `btn_palette` sub-dict that drives every `RoundedButton` (`bg`, `fg`, `border`, `hover_bg`, `press_bg`, `active_bg`, `parent_bg`).

`_apply_theme(name)` does the work:

1. Sets root window `bg`.
2. Configures `ttk.Style` (under `clam` base theme so the colors actually take effect) for `TFrame`, `TLabel`, `TSeparator`, `TEntry`, `Treeview`, and `Treeview.Heading`. Treeview headings use `relief="solid"` + `borderwidth=1` to give the File-Explorer-style divider.
3. Walks tracked label groups (`_muted_labels`, `_caption_labels`, `_normal_labels`) and applies foreground colors per group.
4. Walks `_text_widgets` (the status `Text` and the action `Text`) and recolors `bg`/`fg`/select colors.
5. Sets the preview holder `Frame`'s `highlightbackground` for the border, and the preview Label's `bg`.
6. Calls `apply_palette(...)` on every `RoundedButton` in `_rounded_buttons` (and on the sidebar buttons of every open popup, via `_theme_popup`).
7. Calls `set_active(...)` on the sun/moon toggle so the button matching the current theme renders as sticky-pressed.
8. Calls `_apply_titlebar_theme` to switch the Windows title bar to dark or light via DWM.
9. Iterates `_open_popups` and calls `_theme_popup` on each so any open reference-sheet windows track theme changes cleanly (re-paints sidebar buttons + scrollable table cells + row separators).
10. If the theme actually changed, persists the choice to `settings.json`.

The dark palette uses `#3D2185` as the root background. `btn_palette` for dark uses `#5A3DA6` button bg with `#8A6DD6` border; light uses `#FFFFFF` button bg with `#B0B0B0` border.

---

## Live Preview

Every keystroke into one of the 8 entry fields triggers `<KeyRelease>` → `_live_preview()`, which:

1. Reads the current state of all 8 entries (stripped, blanks dropped).
2. Calls `render_image(items, self.fg_color, self.bg_color)` — same code path as the eventual saved PNG, but with no file I/O.
3. Wraps the result in `ImageTk.PhotoImage` and assigns it to the preview Label.

The same path is invoked from `_pick_fg`, `_pick_bg`, `_new_entry`, and `_delete_selected`. Selecting an existing file in the table calls `_update_preview(path)` instead, which loads the actual on-disk PNG (so what you see is the file as written, byte-for-byte). The first keystroke after that swaps to live preview.

When all entries are empty, `render_image` short-circuits and returns a solid-bg image — so the preview pane shows whatever bg color is currently selected.

---

## Keyboard Shortcut Panel

Two pieces of UI driven by `windows11-shortcuts.json`:

**Random-shortcut ticker (rotates every `SHORTCUT_ROTATE_MS`):**
- Lives in a fixed-height (114 px) frame with `grid_propagate(False)` so varying action-text length never resizes the parent window.
- Stacked vertically: row 0 = `keys` (Consolas bold, full panel width with wraplength so long key combos wrap inside the panel), row 1 = `action` rendered into a fixed 38×3 `tk.Text` widget, row 2 = `Shortcut Category: <name>` (Consolas bold).
- `_set_action_text(text)` truncates the action with `...` (peeling off whole words from the end) when its rendered height would otherwise overflow the visible 3-line area, detected via `dlineinfo("end-1c") is None`. Window size is therefore stable across all 226 shortcuts.
- `_pick_random_shortcut` builds a flat pool of `(category_display_name, shortcut)` tuples so the category travels with the chosen shortcut and lands in the third label.
- `_schedule_shortcut_rotation` re-arms itself via `self.after`. Tk cancels pending `after` callbacks automatically on window destroy.

**Single Keyboard Shortcuts Reference button → combined dialog:**
- One `RoundedButton` labeled "Keyboard Shortcuts Reference" sits below the ticker; its bottom edge is sized to align exactly with the bottom of the Preview pane on the left.
- Click → `_open_shortcuts_reference()` opens a `Toplevel`. Layout:
  - Left side: title (Segoe UI 12 bold), description, header strip with "Keys" / "Action" labels, and a scrollable `Canvas` whose interior `Frame` holds the rows.
  - Each row is two `tk.Label`s — keys (Consolas) and action (default font, `wraplength` bound to the live canvas width via `<Configure>` so resizing the dialog re-flows wrapping in real time, and action text physically can't extend past the column).
  - 1 px theme-colored separator `Frame`s above each row plus one final separator after the last, so every entry is bounded by lines top and bottom.
  - Right side: vertical sidebar of `RoundedButton`s, one per category. Click switches the table contents.
- Each popup is registered in `self._open_popups` and bound to `<Destroy>` for clean deregistration.
- `_apply_theme` re-themes all open popups so toggling sun/moon while a reference sheet is open updates it cleanly (background, title bar, sidebar buttons, table cells and row separators all follow).

---

## Error Handling

- **Missing Pillow:** auto-installed via `pip install Pillow --break-system-packages` on first import. Subsequent runs skip this.
- **Missing `icon.ico`:** silently skipped — Tk uses its default icon. (The legacy `iconphoto` fallback to `icon_clean.png` was removed.)
- **Missing `windows11-shortcuts.json`:** the random-shortcut row shows `—` / `(no shortcuts loaded)`; the reference-sheet button grid renders empty.
- **Corrupt PNG metadata:** `read_png_meta` returns `None`. The form leaves entries blank with a status message: `"<file>: no embedded metadata. Filename loaded; entries left blank."`
- **Empty entries on Generate:** modal warning, no write.
- **Overwrite:** modal Yes/No prompt before any existing file is replaced.
- **Render exceptions:** caught in `_generate` and `_live_preview`, surfaced as `messagebox.showerror` (generate) or a `[DEBUG]` print (preview).
- **Settings load/save:** failures are caught and logged via `[DEBUG]` print; the app falls back to defaults and keeps running.
- **DWM dark-titlebar API:** any exception is caught and logged; the app still works with the default light title bar.

---

## Dispatch / Control Flow

```
launch (! todo) or KeyboardLCDListBuilder.exe
   ↓
TodoApp.__init__
   ├── iconbitmap(BUNDLE_DIR/icon.ico)
   ├── load_user_settings() → fg_color, bg_color, _user_fg, _user_bg
   ├── build left pane (Existing files label, Refresh, Treeview[Name,Modified],
   │                    Delete, New, Preview caption, preview holder)
   ├── build right pane (caption + sun/moon theme toggle, 8 entries with
   │                     <KeyRelease> bound, color swatches + Select… buttons,
   │                     filename, Generate, status)
   ├── load_shortcuts() → self._shortcuts
   ├── build shortcut panel (separator, random-shortcut row in fixed-height
   │                          frame, Reference Sheets caption, 3×3 buttons)
   ├── ttk.Style theme = "clam"
   ├── _apply_theme(saved theme or "light")
   ├── _refresh_files()
   └── _schedule_shortcut_rotation()           ← starts the every-10s tick

user picks file in Treeview
   → _on_file_selected
   → read_png_meta
   → _set_entries / _set_colors / filename_var.set
   → _update_preview(path)        ← shows the on-disk PNG

user types into any entry
   → <KeyRelease> → _live_preview()  ← re-renders from current form state

user picks a color
   → _pick_fg / _pick_bg
   → _save_user_colors             ← persists to %APPDATA%
   → _live_preview

user clicks Refresh / New / Delete / Generate
   → _refresh_files / _new_entry (resets to user's last colors) /
     _delete_selected / _generate (renders + saves with metadata)

user clicks ☀ or ☾
   → _apply_theme("light"|"dark")
   → ttk.Style + tk widgets recolored
   → _theme_popup(each open popup)
   → _apply_titlebar_theme         ← DwmSetWindowAttribute
   → save_user_settings (only if theme changed)

user clicks Keyboard Shortcuts Reference
   → _open_shortcuts_reference()
   → Toplevel with scrollable wrap-aware table (left) + category sidebar (right)
   → first category's shortcuts loaded by default
   → click a sidebar button → table re-populates for that category
   → registered in _open_popups; deregistered on Destroy

every SHORTCUT_ROTATE_MS
   → _schedule_shortcut_rotation tick
   → _pick_random_shortcut (filters out currently shown to avoid repeats)
   → re-arm via self.after
```

---

## Distribution

The project is mirrored to GitHub at **`Keyboard-LCD-List-Builder`**. The repo layout:

```
Keyboard-LCD-List-Builder/
  README.md
  Source Code (Python)/
    todo_gui.py
    icon.ico
    windows11-shortcuts.json
    Codebase Reference.md
  Windows Binary/
    KeyboardLCDListBuilder.exe   — built with PyInstaller 6.x
```

The `Images/` folder is **not** mirrored — it's user-generated content.

The Windows binary is built with PyInstaller in single-file (`--onefile`) windowed (`--windowed`) mode. The build pulls in `windows11-shortcuts.json` and `icon.ico` via `--add-data`, so the `.exe` is fully self-contained. At runtime, frozen-aware path resolution puts the user-writable `Images/` folder next to the `.exe` while reading bundled assets out of `sys._MEIPASS`.

Releases attach the `.exe` directly so users can download a single file without cloning.

---

## Setup

### Prerequisites
- Python 3.12 at `C:\Users\azt12\AppData\Local\Programs\Python\Python312\` (the wrappers reference this exact path).
- Pillow installs automatically on first run.
- Corsair Web Hub app (for actually uploading the generated PNG to the keyboard's LCD).

### First run
```
todo
```
or, from inside the Claude Code TUI:
```
! todo
```

### State files

| Path | Created by | Notes |
|---|---|---|
| `Images/` | `todo_gui.py` on launch | Auto-created if missing. |
| `Images/*.png` | `_generate` | Each PNG carries its own state. No central index. |
| `%APPDATA%\KeyboardLCDTodoBuilder\settings.json` | `save_user_settings` | Holds theme + last-used fg/bg. Auto-created on first preference change. |

### Troubleshooting
- **Window doesn't appear:** another `pythonw.exe` (or `KeyboardLCDListBuilder.exe`) instance may already be running. Close it (don't `taskkill` without checking) and relaunch.
- **Icon shows as blurry / generic Tk feather:** Windows is caching the old icon for the previous process. Close the running window before relaunching.
- **`todo: command not found` in Bash:** ensure `C:\Users\azt12\bin` is in `$PATH` and `todo` (no extension) is executable.
- **Title bar didn't darken:** very old Windows 10 builds (< 1809) don't support the immersive-dark-mode DWM attribute. The body still themes correctly.
- **Reference sheet shows nothing:** verify `windows11-shortcuts.json` is next to the script (or, in frozen builds, present in the `--add-data` bundle).
- **Image won't upload to keyboard:** verify file is exactly 248×170 and < 2 MB. Check via Pillow: `Image.open(path).size`.
- **Reset to defaults:** delete `%APPDATA%\KeyboardLCDTodoBuilder\settings.json` to reset the theme and color preferences.

---

## Recipes

### Add a new LCD image
GUI workflow — no code changes:
1. `! todo`
2. Click **New**. Filename auto-populates as the next free `todoN`. Colors come from your last-used pair.
3. Type up to 8 entries (≤ 26 chars each). The preview pane updates live as you type.
4. Optionally **Select…** new text/background colors — preview updates immediately.
5. Optionally rename the file (e.g. `Biometrics`, `Schedule`).
6. **Generate PNG**. File appears in `Images/` and is selected in the table.
7. Open Corsair Web Hub app → Vanguard Pro 96 → **Screen** tab → **+** → pick the file.

### Rebuild the Windows binary
From `Source Code (Python)/`:
```
pyinstaller --onefile --windowed --noconfirm \
  --icon "icon.ico" --name "KeyboardLCDListBuilder" \
  --add-data "windows11-shortcuts.json;." \
  --add-data "icon.ico;." \
  todo_gui.py
```
Output lands in `dist/KeyboardLCDListBuilder.exe`.

### Adapt the renderer for a different keyboard's LCD
1. Open `todo_gui.py`.
2. Change `W, H` to the new resolution. (`PREVIEW_W, PREVIEW_H` will follow.)
3. Re-tune `MAX_CHARS`, `MAX_ITEMS`, `MAX_FONT`, `MIN_FONT` — wider/taller canvas → more chars/items/larger fonts.
4. Update the `MAX_CHARS` validation message in the GUI caption if needed.
5. Existing PNGs in `Images/` will keep their old dimensions until regenerated.

### Add a new persisted user setting
1. Add a key to the dict written by `save_user_settings`.
2. Read it on launch via `load_user_settings().get("your_key", default)`.
3. That's it — `settings.json` is just a free-form JSON dict, missing keys fall back to defaults.

### Add a new persisted PNG field (e.g. layout style)
1. In `render_png`, add the new field to the JSON `payload` written into the `tEXt` chunk.
2. In `read_png_meta`, no change needed — the dict survives untouched.
3. In `_on_file_selected`, read the new field from `meta` and apply to the form.
4. Add a corresponding form widget in `TodoApp.__init__` to author the field.
5. Old PNGs without the field get the default — handle the `meta.get("new_field", default)` lookup.

---

## What This Project Is NOT

- **Not a Corsair driver.** It does not talk to the keyboard. It produces PNGs that the Corsair Web Hub app uploads via its existing **Screen** widget.
- **Not a slideshow / image rotator.** Multi-image cycling is the keyboard's responsibility (`Fn + ←/→`). This app authors individual images.
- **Not a pixel editor.** Output is text-only bullet lists. Images go through a single `render_image` path.
- **Not a shortcut customizer.** The reference panel only displays the Microsoft-published Windows 11 shortcut catalog; it cannot rebind keys.
- **No tests, no CI, no packaging beyond PyInstaller.** Single-file utility for one user on one machine.
