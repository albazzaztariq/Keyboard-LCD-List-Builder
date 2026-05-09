"""
todo_gui.py — Tkinter GUI to author Corsair Vanguard Pro 96 LCD todo PNGs.

Method:  Listbox of existing *.png files (left) + 8 single-line text entries
         (max 26 chars each) + text/bg color selectors + filename entry (right).
         "Generate PNG" renders a 248x170 image to the same folder as this script
         and embeds the items + colors into a PNG tEXt metadata chunk so the file
         round-trips: selecting it later refills the form.
Inputs:  user types in the GUI fields; selects existing files in the listbox.
Outputs: <filename>.png in same dir as this script (the Keyboard folder).
Packages:
  - tkinter: stdlib GUI.
  - Pillow (PIL): image creation, font loading, text rendering, PNG metadata.
"""

import ctypes
import datetime
import json
import os
import random
import re
import sys
import time
import tkinter as tk
import tkinter.font as tkfont
from tkinter import colorchooser, messagebox, ttk
from pathlib import Path

print("[DEBUG] todo_gui start")

try:
    from PIL import Image, ImageDraw, ImageFont, ImageTk
    from PIL.PngImagePlugin import PngInfo
    print("[DEBUG] Pillow imported OK")
except ImportError:
    print("[DEBUG] Pillow missing, installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow", "--break-system-packages"])
    from PIL import Image, ImageDraw, ImageFont, ImageTk
    from PIL.PngImagePlugin import PngInfo

if getattr(sys, "frozen", False):
    # PyInstaller-bundled exe: user-writable files live next to the exe;
    # bundled read-only assets live under sys._MEIPASS.
    SCRIPT_DIR = Path(sys.executable).resolve().parent
    BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", SCRIPT_DIR))
else:
    SCRIPT_DIR = Path(__file__).resolve().parent
    BUNDLE_DIR = SCRIPT_DIR
IMAGES_DIR = SCRIPT_DIR / "Images"
IMAGES_DIR.mkdir(exist_ok=True)
TODO_NAME_RE = re.compile(r"^todo(\d+)$", re.IGNORECASE)

W, H = 248, 170                       # Corsair Vanguard Pro 96 native LCD resolution
MAX_CHARS = 26                        # per-line cap (matches render auto-fit)
MAX_ITEMS = 8
MIN_FONT  = 11
MAX_FONT  = 22
PAD       = 6

DEFAULT_FG = "#FFF005"                # bright yellow (matches Vanguard Pro 96 theme)
DEFAULT_BG = "#000000"

META_KEY = "todo_meta"                # PNG tEXt chunk key holding our JSON payload

PREVIEW_W, PREVIEW_H = W, H           # preview pane shows image at native LCD size

SHORTCUT_ROTATE_MS = 10_000           # interval between random-shortcut rotations

APPDATA_DIR = Path(os.getenv("APPDATA", Path.home())) / "KeyboardLCDTodoBuilder"
SETTINGS_FILE = APPDATA_DIR / "settings.json"

SHORTCUTS_FILE = BUNDLE_DIR / "windows11-shortcuts.json"


def load_shortcuts() -> dict:
    """Load Windows 11 shortcut catalog. Returns {} on any failure."""
    try:
        with SHORTCUTS_FILE.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict):
            return data
    except Exception as exc:
        print(f"[DEBUG] shortcuts load failed: {exc}")
    return {"categories": {}}


def load_user_settings() -> dict:
    """Read JSON settings from %APPDATA%\\KeyboardLCDTodoBuilder\\settings.json."""
    try:
        with SETTINGS_FILE.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict):
            return data
    except FileNotFoundError:
        pass
    except Exception as exc:
        print(f"[DEBUG] settings load failed: {exc}")
    return {}


def save_user_settings(data: dict) -> None:
    """Persist settings dict to %APPDATA% (creating the folder if needed)."""
    try:
        APPDATA_DIR.mkdir(parents=True, exist_ok=True)
        with SETTINGS_FILE.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
    except Exception as exc:
        print(f"[DEBUG] settings save failed: {exc}")

THEMES = {
    "light": {
        "bg":              "#F0F0F0",
        "fg":              "#000000",
        "muted_fg":        "#666666",
        "label_fg":        "#444444",
        "listbox_bg":      "#FFFFFF",
        "listbox_fg":      "#000000",
        "listbox_sel_bg":  "#0078D7",
        "listbox_sel_fg":  "#FFFFFF",
        "heading_bg":      "#FFFFFF",
        "heading_fg":      "#000000",
        "heading_border":  "#D0D0D0",
        "btn_bg":          "#E1E1E1",
        "btn_fg":          "#000000",
        "btn_active_bg":   "#CCE4F7",
        "entry_bg":        "#FFFFFF",
        "entry_fg":        "#000000",
        "preview_bg":      "#E0E0E0",
        "preview_border":  "#888888",
        "btn_palette": {
            "bg":         "#FFFFFF",
            "fg":         "#202020",
            "border":     "#B0B0B0",
            "hover_bg":   "#F0F6FC",
            "press_bg":   "#DCE9F7",
            "active_bg":  "#CDE0F4",
            "parent_bg":  "#F0F0F0",
        },
    },
    "dark": {
        "bg":              "#3D2185",
        "fg":              "#FFFFFF",
        "muted_fg":        "#C9BFE5",
        "label_fg":        "#E0D8F5",
        "listbox_bg":      "#2A1660",
        "listbox_fg":      "#FFFFFF",
        "listbox_sel_bg":  "#7E5BC9",
        "listbox_sel_fg":  "#FFFFFF",
        "heading_bg":      "#1F104A",
        "heading_fg":      "#FFFFFF",
        "heading_border":  "#5A3DA6",
        "btn_bg":          "#5A3DA6",
        "btn_fg":          "#FFFFFF",
        "btn_active_bg":   "#7E5BC9",
        "entry_bg":        "#2A1660",
        "entry_fg":        "#FFFFFF",
        "preview_bg":      "#2A1660",
        "preview_border":  "#9F84D9",
        "btn_palette": {
            "bg":         "#5A3DA6",
            "fg":         "#FFFFFF",
            "border":     "#8A6DD6",
            "hover_bg":   "#6F4DBE",
            "press_bg":   "#8662D0",
            "active_bg":  "#9F84D9",
            "parent_bg":  "#3D2185",
        },
    },
}

FONT_CANDIDATES = [
    "arialbd.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


def load_font(size: int):
    """Return a TrueType bold-sans font at size, or Pillow default if none found."""
    for path in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def hex_to_rgb(h: str):
    """'#RRGGBB' → (r, g, b)."""
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def measure_lines(draw, lines, font):
    """Return (total_height, line_heights, line_gap) for a vertical block of lines."""
    heights = []
    for ln in lines:
        bbox = draw.textbbox((0, 0), ln, font=font)
        heights.append(bbox[3] - bbox[1])
    line_gap = max(2, int(heights[0] * 0.22)) if heights else 0
    total = sum(heights) + line_gap * max(0, len(heights) - 1)
    return total, heights, line_gap


def render_image(items, fg_hex, bg_hex):
    """Render items into an in-memory 248x170 PIL Image. No file I/O."""
    fg_rgb = hex_to_rgb(fg_hex)
    bg_rgb = hex_to_rgb(bg_hex)
    img  = Image.new("RGB", (W, H), bg_rgb)
    if not items:
        return img
    draw = ImageDraw.Draw(img)

    bullet_lines = [f"• {it}" for it in items]
    body_top   = PAD
    body_avail = H - 2 * PAD

    body_size = MAX_FONT
    while body_size >= MIN_FONT:
        bfont = load_font(body_size)
        total, heights, gap = measure_lines(draw, bullet_lines, bfont)
        widest = max((draw.textbbox((0, 0), ln, font=bfont)[2] for ln in bullet_lines), default=0)
        if total <= body_avail and widest <= W - 2 * PAD:
            break
        body_size -= 1
    bfont = load_font(body_size)
    total, heights, gap = measure_lines(draw, bullet_lines, bfont)

    y = body_top
    for ln, h in zip(bullet_lines, heights):
        draw.text((PAD, y), ln, font=bfont, fill=fg_rgb)
        y += h + gap
    return img


def render_png(items, fg_hex, bg_hex, out_path: Path):
    """Render items as a 248x170 PNG with embedded todo_meta tEXt chunk."""
    img = render_image(items, fg_hex, bg_hex)
    meta = PngInfo()
    payload = json.dumps({"items": items, "fg": fg_hex, "bg": bg_hex}, ensure_ascii=False)
    meta.add_text(META_KEY, payload)
    img.save(out_path, "PNG", pnginfo=meta)
    print(f"[DEBUG] wrote {out_path} (items={len(items)}, fg={fg_hex}, bg={bg_hex})")


def read_png_meta(path: Path):
    """Return dict {items, fg, bg} from PNG metadata, or None if absent/unreadable."""
    try:
        with Image.open(path) as img:
            payload = img.info.get(META_KEY)
        if not payload:
            return None
        data = json.loads(payload)
        if not isinstance(data, dict) or "items" not in data:
            return None
        return data
    except Exception as exc:
        print(f"[DEBUG] read meta failed for {path.name}: {exc}")
        return None


BUTTON_FONT = ("Segoe UI", 10)


class RoundedButton(tk.Canvas):
    """Canvas-based button with rounded corners + slight border, hover and
    press states, and per-instance theming."""

    def __init__(self, parent, text="", command=None, *,
                 width=None, height=30, radius=8,
                 font=BUTTON_FONT, padx=18, pady=0, **canvas_kwargs):
        super().__init__(
            parent, height=height,
            highlightthickness=0, bd=0, **canvas_kwargs,
        )
        self._text = text
        self._font = font
        self._command = command
        self._height = height
        self._radius = radius
        self._padx = padx
        self._enabled = True
        self._state = "normal"
        self._sticky_pressed = False  # for sun/moon "active" indication

        if width is None:
            f = tkfont.Font(family=font[0], size=font[1])
            width = f.measure(text) + 2 * padx
        self._width = max(width, 2 * radius + 4)
        self.configure(width=self._width)

        # Default light-theme palette; overridden by apply_palette().
        self._palette = {
            "bg":         "#FFFFFF",
            "fg":         "#202020",
            "border":     "#C0C0C0",
            "hover_bg":   "#F0F6FC",
            "press_bg":   "#DCE9F7",
            "active_bg":  "#CDE0F4",
            "parent_bg":  "#F0F0F0",
        }
        self.configure(bg=self._palette["parent_bg"])

        self._render()
        self.bind("<Configure>", self._on_resize)
        self.bind("<Button-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    def _round_rect(self, x1, y1, x2, y2, r, fill, outline):
        # Approximate rounded rect via a smoothed polygon. Each corner
        # uses three points so smooth=True bends them into an arc.
        pts = [
            x1 + r, y1,
            x2 - r, y1, x2, y1, x2, y1 + r,
            x2, y2 - r, x2, y2, x2 - r, y2,
            x1 + r, y2, x1, y2, x1, y2 - r,
            x1, y1 + r, x1, y1, x1 + r, y1,
        ]
        return self.create_polygon(
            pts, smooth=True, splinesteps=24,
            fill=fill, outline=outline, width=1,
        )

    def _render(self):
        self.delete("all")
        p = self._palette
        if self._sticky_pressed:
            fill = p["active_bg"]
        else:
            fill = {"normal": p["bg"], "hover": p["hover_bg"],
                    "press": p["press_bg"]}.get(self._state, p["bg"])
        self._round_rect(1, 1, self._width - 1, self._height - 1,
                         self._radius, fill, p["border"])
        self.create_text(self._width / 2, self._height / 2,
                         text=self._text, fill=p["fg"], font=self._font)

    def _on_resize(self, ev):
        if ev.width and ev.width != self._width:
            self._width = ev.width
            self._render()

    def _on_press(self, _ev):
        if not self._enabled:
            return
        self._state = "press"
        self._render()

    def _on_release(self, ev):
        if not self._enabled:
            return
        was_press = self._state == "press"
        over = 0 <= ev.x < self._width and 0 <= ev.y < self._height
        self._state = "hover" if over else "normal"
        self._render()
        if was_press and over and self._command:
            self._command()

    def _on_enter(self, _ev):
        if not self._enabled or self._state == "press":
            return
        self._state = "hover"
        self._render()

    def _on_leave(self, _ev):
        if not self._enabled:
            return
        self._state = "normal"
        self._render()

    def apply_palette(self, palette: dict):
        self._palette = dict(palette)
        self.configure(bg=self._palette["parent_bg"])
        self._render()

    def set_text(self, text: str):
        self._text = text
        f = tkfont.Font(family=self._font[0], size=self._font[1])
        self._width = f.measure(text) + 2 * self._padx
        self.configure(width=self._width)
        self._render()

    def set_active(self, active: bool):
        """Show this button as the 'active' pick (used by the sun/moon toggle)."""
        self._sticky_pressed = active
        self._render()


class TodoApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Keyboard LCD - To-Do List Builder")
        self.resizable(False, False)
        self.configure(padx=14, pady=12)

        icon_path = BUNDLE_DIR / "icon.ico"
        if icon_path.exists():
            try:
                self.iconbitmap(default=str(icon_path))
            except tk.TclError as exc:
                print(f"[DEBUG] iconbitmap failed: {exc}")

        saved = load_user_settings()
        self.fg_color = saved.get("fg", DEFAULT_FG)
        self.bg_color = saved.get("bg", DEFAULT_BG)
        self._user_fg = self.fg_color
        self._user_bg = self.bg_color

        self._open_popups = []  # tk.Toplevel windows that need to follow theme changes

        # ── Left pane: file list + preview ─────────────────────────────────
        self.left_frame = ttk.Frame(self)
        self.left_frame.grid(row=0, column=0, sticky="ns", padx=(0, 14))
        left = self.left_frame

        self.existing_files_label = ttk.Label(left, text="Existing files")
        self.existing_files_label.grid(row=0, column=0, sticky="w")
        self.refresh_btn = RoundedButton(left, text="Refresh", command=self._refresh_files)
        self.refresh_btn.grid(row=1, column=0, sticky="we", pady=(4, 4))

        self.file_list = ttk.Treeview(
            left,
            columns=("name", "modified"),
            show="headings",
            height=14,
            selectmode="browse",
        )
        self.file_list.heading("name", text="Name", anchor="center")
        self.file_list.heading("modified", text="Created/Modified", anchor="center")
        self.file_list.column("name", width=170, anchor="center", stretch=True)
        self.file_list.column("modified", width=130, anchor="center", stretch=False)
        self.file_list.grid(row=2, column=0, sticky="we", pady=(0, 4))
        self.file_list.bind("<<TreeviewSelect>>", self._on_file_selected)
        self.delete_btn = RoundedButton(left, text="Delete", command=self._delete_selected)
        self.delete_btn.grid(row=3, column=0, sticky="we")
        self.new_btn = RoundedButton(left, text="New", command=self._new_entry)
        self.new_btn.grid(row=4, column=0, sticky="we", pady=(4, 10))

        self.preview_label_caption = ttk.Label(left, text="Preview")
        self.preview_label_caption.grid(row=5, column=0, sticky="w")
        self.preview_holder = tk.Frame(
            left,
            width=PREVIEW_W + 4,
            height=PREVIEW_H + 4,
            highlightthickness=1,
        )
        self.preview_holder.grid(row=6, column=0, sticky="we", pady=(4, 0))
        self.preview_holder.grid_propagate(False)
        self.preview_label = tk.Label(self.preview_holder, borderwidth=0)
        self.preview_label.place(relx=0.5, rely=0.5, anchor="center")
        self._preview_imgref = None  # keep ImageTk.PhotoImage from being GC'd

        # ── Right pane: form ────────────────────────────────────────────────
        self.right_frame = ttk.Frame(self)
        self.right_frame.grid(row=0, column=1, sticky="nw")
        right = self.right_frame

        top_row = ttk.Frame(right)
        top_row.grid(row=0, column=0, columnspan=3, sticky="we", pady=(0, 8))
        top_row.columnconfigure(0, weight=1)

        self.entries_caption = ttk.Label(
            top_row,
            text=f"Up to {MAX_ITEMS} entries, {MAX_CHARS} characters each.",
        )
        self.entries_caption.grid(row=0, column=0, sticky="w")

        theme_frame = ttk.Frame(top_row)
        theme_frame.grid(row=0, column=1, sticky="e")
        self.sun_btn = RoundedButton(
            theme_frame, text="☀",
            command=lambda: self._apply_theme("light"),
            width=34, height=28, radius=7, padx=8,
            font=("Segoe UI Symbol", 11, "bold"),
        )
        self.sun_btn.grid(row=0, column=0, padx=(0, 4))
        self.moon_btn = RoundedButton(
            theme_frame, text="☾",
            command=lambda: self._apply_theme("dark"),
            width=34, height=28, radius=7, padx=8,
            font=("Segoe UI Symbol", 11, "bold"),
        )
        self.moon_btn.grid(row=0, column=1)

        # Centered sub-frame holding the 8 entry rows so the whole label+entry
        # group sits in the visual middle of the right pane, not flush left.
        right.columnconfigure(0, weight=1)
        right.columnconfigure(2, weight=1)
        entries_block = ttk.Frame(right)
        entries_block.grid(row=1, column=0, columnspan=3, pady=(0, 0))

        self.entries = []
        self._entry_num_labels = []
        for i in range(MAX_ITEMS):
            num_lbl = ttk.Label(entries_block, text=f"{i + 1}.")
            num_lbl.grid(row=i, column=0, sticky="e", padx=(0, 6), pady=2)
            self._entry_num_labels.append(num_lbl)
            vcmd = (self.register(self._validate_len), "%P")
            e = ttk.Entry(entries_block, width=30, validate="key", validatecommand=vcmd, justify="center")
            e.grid(row=i, column=1, pady=2)
            e.bind("<KeyRelease>", lambda _ev: self._live_preview())
            self.entries.append(e)

        row = 2  # next available row after top_row (0) and entries_block (1)
        ttk.Separator(right, orient="horizontal").grid(row=row, column=0, columnspan=3, sticky="we", pady=10)

        row += 1
        self.text_color_label = ttk.Label(right, text="Text color:")
        self.text_color_label.grid(row=row, column=0, sticky="e", padx=(0, 6))
        self.fg_swatch = tk.Label(right, text="    ", bg=self.fg_color, relief="sunken", width=4)
        self.fg_swatch.grid(row=row, column=1, sticky="w")
        self.fg_select_btn = RoundedButton(right, text="Select…", command=self._pick_fg)
        self.fg_select_btn.grid(row=row, column=1, columnspan=2, sticky="we", padx=(50, 0))

        row += 1
        self.bg_color_label = ttk.Label(right, text="Background:")
        self.bg_color_label.grid(row=row, column=0, sticky="e", padx=(0, 6), pady=(4, 0))
        self.bg_swatch = tk.Label(right, text="    ", bg=self.bg_color, relief="sunken", width=4)
        self.bg_swatch.grid(row=row, column=1, sticky="w", pady=(4, 0))
        self.bg_select_btn = RoundedButton(right, text="Select…", command=self._pick_bg)
        self.bg_select_btn.grid(row=row, column=1, columnspan=2, sticky="we", padx=(50, 0), pady=(4, 0))

        row += 1
        ttk.Separator(right, orient="horizontal").grid(row=row, column=0, columnspan=3, sticky="we", pady=10)

        row += 1
        self.filename_label = ttk.Label(right, text="Filename:")
        self.filename_label.grid(row=row, column=0, sticky="e", padx=(0, 6))
        self.filename_var = tk.StringVar(value="todo1")
        ttk.Entry(right, textvariable=self.filename_var, width=22).grid(row=row, column=1, sticky="we")
        self.png_suffix_label = ttk.Label(right, text=".png")
        self.png_suffix_label.grid(row=row, column=2, sticky="w", padx=(2, 0))

        row += 1
        self.generate_btn = RoundedButton(right, text="Generate PNG", command=self._generate)
        self.generate_btn.grid(row=row, column=0, columnspan=3, sticky="we", pady=(14, 4))

        row += 1
        default_font = tkfont.nametofont("TkDefaultFont")
        self.status = tk.Text(
            right, height=4, width=44, wrap="char",
            relief="flat", bd=0, highlightthickness=0,
            padx=0, pady=0, cursor="arrow", takefocus=0,
        )
        self.status.tag_configure(
            "bold",
            font=(default_font.actual("family"), default_font.actual("size"), "bold"),
        )
        self.status.grid(row=row, column=0, columnspan=3, sticky="we", pady=(6, 0))
        self.status.configure(state="disabled")
        self._set_status(f"Output folder: {IMAGES_DIR}", bold_prefix="Output folder:")

        # ── Keyboard Shortcuts section ─────────────────────────────────────
        self._shortcuts = load_shortcuts()

        row += 1
        ttk.Separator(right, orient="horizontal").grid(
            row=row, column=0, columnspan=3, sticky="we", pady=(8, 0)
        )

        row += 1
        shortcut_frame = ttk.Frame(right, height=114)
        shortcut_frame.grid(row=row, column=0, columnspan=3, sticky="we", pady=(2, 0))
        shortcut_frame.grid_propagate(False)  # frame size never tracks content -> window cannot resize
        shortcut_frame.columnconfigure(0, weight=1)
        self.shortcut_keys_label = ttk.Label(
            shortcut_frame, text="", font=("Consolas", 10, "bold"), wraplength=320
        )
        self.shortcut_keys_label.grid(row=0, column=0, sticky="nw")
        self.shortcut_action_text = tk.Text(
            shortcut_frame, height=3, width=38, wrap="word",
            relief="flat", bd=0, highlightthickness=0,
            padx=0, pady=0, cursor="arrow", takefocus=0,
        )
        self.shortcut_action_text.grid(row=1, column=0, sticky="nw", pady=(2, 0))
        self.shortcut_action_text.configure(state="disabled")
        self.shortcut_category_label = ttk.Label(
            shortcut_frame, text="", font=("Consolas", 10, "bold")
        )
        self.shortcut_category_label.grid(row=2, column=0, sticky="nw", pady=(4, 0))

        row += 1
        self.shortcuts_ref_btn = RoundedButton(
            right, text="Keyboard Shortcuts Reference",
            command=self._open_shortcuts_reference,
        )
        self.shortcuts_ref_btn.grid(row=row, column=0, columnspan=3, sticky="we", pady=(2, 0))

        self._shortcut_after_id = None
        self._schedule_shortcut_rotation()

        # Track widget groups that need recoloring on theme change.
        self._muted_labels = [self.status, self.entries_caption, self.png_suffix_label]
        self._caption_labels = [
            self.existing_files_label, self.preview_label_caption,
        ]
        self._normal_labels = (
            self._entry_num_labels
            + [self.text_color_label, self.bg_color_label, self.filename_label,
               self.shortcut_keys_label, self.shortcut_category_label]
        )
        self._text_widgets = [self.shortcut_action_text, self.status]
        self._rounded_buttons = [
            self.refresh_btn, self.delete_btn, self.new_btn,
            self.fg_select_btn, self.bg_select_btn,
            self.generate_btn, self.shortcuts_ref_btn,
            self.sun_btn, self.moon_btn,
        ]

        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass

        saved = load_user_settings()
        initial_theme = saved.get("theme", "light")
        if initial_theme not in THEMES:
            initial_theme = "light"
        self._current_theme = initial_theme
        self._apply_theme(initial_theme)

        self._refresh_files()

    # ── helpers ────────────────────────────────────────────────────────────
    def _validate_len(self, proposed: str) -> bool:
        return len(proposed) <= MAX_CHARS

    def _pick_fg(self):
        rgb, hexv = colorchooser.askcolor(color=self.fg_color, title="Select text color")
        if hexv:
            self.fg_color = hexv
            self._user_fg = hexv
            self.fg_swatch.configure(bg=hexv)
            self._save_user_colors()
            self._live_preview()

    def _pick_bg(self):
        rgb, hexv = colorchooser.askcolor(color=self.bg_color, title="Select background color")
        if hexv:
            self.bg_color = hexv
            self._user_bg = hexv
            self.bg_swatch.configure(bg=hexv)
            self._save_user_colors()
            self._live_preview()

    def _save_user_colors(self):
        settings = load_user_settings()
        settings["fg"] = self._user_fg
        settings["bg"] = self._user_bg
        save_user_settings(settings)

    def _list_files(self):
        return sorted(IMAGES_DIR.glob("*.png"), key=lambda p: p.name.lower())

    @staticmethod
    def _format_mtime(path: Path) -> str:
        ts = path.stat().st_mtime
        dt = datetime.datetime.fromtimestamp(ts)
        return f"{dt.month}/{dt.day}/{dt.year}"

    def _refresh_files(self):
        # Treeview iid = full filename ("todo1.png"); displayed name strips ".png".
        self.file_list.delete(*self.file_list.get_children())
        for p in self._list_files():
            self.file_list.insert(
                "", tk.END, iid=p.name,
                values=(p.stem, self._format_mtime(p)),
            )

    def _selected_filename(self):
        sel = self.file_list.selection()
        return sel[0] if sel else None

    def _next_todo_name(self) -> str:
        nums = []
        for p in IMAGES_DIR.glob("*.png"):
            m = TODO_NAME_RE.match(p.stem)
            if m:
                nums.append(int(m.group(1)))
        return f"todo{max(nums, default=0) + 1}"

    def _set_entries(self, items):
        for i, e in enumerate(self.entries):
            e.delete(0, tk.END)
            if i < len(items):
                e.insert(0, items[i][:MAX_CHARS])

    def _set_colors(self, fg, bg):
        self.fg_color = fg
        self.bg_color = bg
        self.fg_swatch.configure(bg=fg)
        self.bg_swatch.configure(bg=bg)

    def _new_entry(self):
        sel = self.file_list.selection()
        if sel:
            self.file_list.selection_remove(sel)
        next_name = self._next_todo_name()
        self.filename_var.set(next_name)
        self._set_entries([])
        self._set_colors(self._user_fg, self._user_bg)
        self._live_preview()
        self._set_status(f"Fresh slate — filename set to {next_name}.png.")

    def _delete_selected(self):
        name = self._selected_filename()
        if not name:
            messagebox.showinfo("Nothing selected", "Pick a file in the list to delete.")
            return
        path = IMAGES_DIR / name
        ok = messagebox.askyesno(
            "Delete file?",
            f"Permanently delete {name}?\n\nThis cannot be undone.",
        )
        if not ok:
            return
        try:
            path.unlink()
            print(f"[DEBUG] deleted {path}")
            self._set_status(f"Deleted {name}.")
            self._refresh_files()
            self._live_preview()
        except Exception as exc:
            print(f"[DEBUG] delete failed: {exc}")
            messagebox.showerror("Delete failed", str(exc))

    def _on_file_selected(self, _event):
        name = self._selected_filename()
        if not name:
            return
        path = IMAGES_DIR / name
        self.filename_var.set(path.stem)

        self._update_preview(path)

        meta = read_png_meta(path)
        if meta is None:
            self._set_entries([])
            self.status.configure(
                text=f"{name}: no embedded metadata. Filename loaded; entries left blank."
            )
            return

        self._set_entries(meta.get("items", []))
        fg = meta.get("fg", DEFAULT_FG)
        bg = meta.get("bg", DEFAULT_BG)
        self._set_colors(fg, bg)
        self._set_status(f"Loaded {name} — generating will overwrite it.")

    def _generate(self):
        items = [e.get().strip() for e in self.entries]
        items = [it for it in items if it]
        if not items:
            messagebox.showwarning("No entries", "Type at least one todo item before generating.")
            return

        name = self.filename_var.get().strip()
        if not name:
            messagebox.showwarning("Missing filename", "Filename can't be empty.")
            return
        if name.lower().endswith(".png"):
            name = name[:-4]
        out_path = IMAGES_DIR / f"{name}.png"

        if out_path.exists():
            ok = messagebox.askyesno(
                "Overwrite?",
                f"{out_path.name} already exists in this folder.\n\nOverwrite it?",
            )
            if not ok:
                return

        try:
            t0 = time.perf_counter()
            render_png(items, self.fg_color, self.bg_color, out_path)
            ms = (time.perf_counter() - t0) * 1000
            self._set_status(f"Wrote {out_path.name} ({ms:.0f} ms) — ready to upload.")
            print(f"[DEBUG] generated {out_path} in {ms:.1f} ms")
            self._refresh_files()
            if self.file_list.exists(out_path.name):
                self.file_list.selection_set(out_path.name)
                self.file_list.see(out_path.name)
            self._update_preview(out_path)
        except Exception as exc:
            print(f"[DEBUG] render failed: {exc}")
            messagebox.showerror("Render failed", str(exc))

    def _update_preview(self, path):
        """Show the PNG at `path` in the preview pane, or clear it if path is None."""
        if path is None or not Path(path).exists():
            self._preview_imgref = None
            self.preview_label.configure(image="")
            return
        try:
            img = Image.open(path).convert("RGB")
            self._preview_imgref = ImageTk.PhotoImage(img)
            self.preview_label.configure(image=self._preview_imgref)
        except Exception as exc:
            print(f"[DEBUG] preview failed for {path}: {exc}")
            self._preview_imgref = None
            self.preview_label.configure(image="")

    def _live_preview(self):
        """Render the current form state in-memory and show it in the preview pane."""
        items = [e.get().strip() for e in self.entries]
        items = [it for it in items if it]
        try:
            img = render_image(items, self.fg_color, self.bg_color)
            self._preview_imgref = ImageTk.PhotoImage(img)
            self.preview_label.configure(image=self._preview_imgref)
        except Exception as exc:
            print(f"[DEBUG] live preview failed: {exc}")

    def _pick_random_shortcut(self):
        """Choose one shortcut at random from the catalog and display it."""
        pool = []  # list of (category_display_name, shortcut_dict)
        for cat in self._shortcuts.get("categories", {}).values():
            cname = cat.get("display_name", "")
            for s in cat.get("shortcuts", []):
                pool.append((cname, s))
        if not pool:
            self.shortcut_keys_label.configure(text="—")
            self._set_action_text("(no shortcuts loaded)")
            self.shortcut_category_label.configure(text="")
            return
        # Avoid repeating the currently shown shortcut on consecutive rotations.
        current = self.shortcut_keys_label.cget("text") if hasattr(self, "shortcut_keys_label") else ""
        if len(pool) > 1:
            choices = [p for p in pool if p[1].get("keys", "") != current]
        else:
            choices = pool
        cname, s = random.choice(choices)
        self.shortcut_keys_label.configure(text=s.get("keys", ""))
        self._set_action_text(s.get("action", ""))
        self.shortcut_category_label.configure(text=f"Shortcut Category: {cname}")

    def _set_status(self, text: str, bold_prefix: str = None):
        """Replace the contents of the (disabled) status Text widget.
        If bold_prefix is given and matches the start of `text`, that prefix
        is rendered with the 'bold' tag and the rest stays normal weight."""
        s = self.status
        s.configure(state="normal")
        s.delete("1.0", "end")
        if bold_prefix and text.startswith(bold_prefix):
            s.insert("1.0", bold_prefix, "bold")
            s.insert("end", text[len(bold_prefix):])
        else:
            s.insert("1.0", text)
        s.configure(state="disabled")

    def _set_action_text(self, text: str):
        """Replace the contents of the (disabled) action Text widget.
        If the rendered text overflows the visible area, truncate it
        word-by-word and append '...' so it always fits without ever
        clipping characters off-screen.

        Detection: dlineinfo('end-1c') returns None when the last
        character is on a line that's clipped by the widget's height."""
        w = self.shortcut_action_text
        w.configure(state="normal")
        w.delete("1.0", "end")
        w.insert("1.0", text)
        w.update_idletasks()

        for _ in range(200):  # safety cap
            if w.dlineinfo("end-1c") is not None:
                break  # last char is on a visible line -> all fits
            current = w.get("1.0", "end-1c").rstrip()
            if current.endswith("..."):
                current = current[:-3].rstrip()
            if " " in current:
                current = current.rsplit(" ", 1)[0].rstrip()
            else:
                current = current[:max(0, len(current) - 1)]
            if not current:
                w.delete("1.0", "end")
                w.insert("1.0", "...")
                break
            w.delete("1.0", "end")
            w.insert("1.0", current + "...")
            w.update_idletasks()

        w.configure(state="disabled")

    def _schedule_shortcut_rotation(self):
        """Tick the random-shortcut display every SHORTCUT_ROTATE_MS milliseconds."""
        self._pick_random_shortcut()
        self._shortcut_after_id = self.after(
            SHORTCUT_ROTATE_MS, self._schedule_shortcut_rotation
        )

    def _open_shortcuts_reference(self):
        """Open the combined keyboard-shortcuts dialog. Table on the left
        (keys column + word-wrapped action column, vertical scrollbar),
        category sidebar on the right. Action text physically cannot
        overflow because every label has its wraplength tied to the
        live canvas width."""
        cats = list(self._shortcuts.get("categories", {}).items())
        if not cats:
            return

        # Measure how wide the keys column needs to be to hold the longest
        # keystroke string in the entire catalog without wrapping (or with
        # at most a 2-line wrap if it really is unusually long).
        f = tkfont.nametofont("TkDefaultFont")
        all_shortcuts = [s for _, c in cats for s in c.get("shortcuts", [])]
        keys_col_w = min(
            340,  # cap so the keys column never dominates
            max((f.measure(s.get("keys", "")) for s in all_shortcuts), default=200) + 24,
        )

        t = THEMES[self._current_theme]
        win = tk.Toplevel(self)
        win.title("Keyboard Shortcuts Reference")
        win.configure(bg=t["bg"], padx=12, pady=12)
        win.transient(self)
        win.minsize(820, 520)
        win.geometry("980x600")

        win.columnconfigure(0, weight=1)
        win.rowconfigure(0, weight=1)

        # Left side: title, description, header strip, scrollable table body.
        main = ttk.Frame(win)
        main.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        main.columnconfigure(0, weight=1)
        main.rowconfigure(3, weight=1)

        title_label = ttk.Label(main, text="", font=("Segoe UI", 12, "bold"))
        title_label.grid(row=0, column=0, sticky="w")
        desc_label = ttk.Label(main, text="", wraplength=600)
        desc_label.grid(row=1, column=0, sticky="we", pady=(2, 8))

        header = ttk.Frame(main)
        header.grid(row=2, column=0, sticky="we")
        header.columnconfigure(0, minsize=keys_col_w)
        header.columnconfigure(1, weight=1)
        keys_hdr = ttk.Label(header, text="Keys", anchor="center",
                             borderwidth=1, relief="solid", padding=(4, 3))
        keys_hdr.grid(row=0, column=0, sticky="we")
        action_hdr = ttk.Label(header, text="Action", anchor="center",
                               borderwidth=1, relief="solid", padding=(4, 3))
        action_hdr.grid(row=0, column=1, sticky="we")

        body_outer = ttk.Frame(main)
        body_outer.grid(row=3, column=0, sticky="nsew")
        body_outer.columnconfigure(0, weight=1)
        body_outer.rowconfigure(0, weight=1)

        canvas = tk.Canvas(body_outer, highlightthickness=0, borderwidth=0,
                           bg=t["listbox_bg"])
        canvas.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(body_outer, orient="vertical", command=canvas.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        canvas.configure(yscrollcommand=scroll.set)

        body = tk.Frame(canvas, bg=t["listbox_bg"])
        body_window_id = canvas.create_window((0, 0), window=body, anchor="nw")
        body.columnconfigure(0, minsize=keys_col_w)
        body.columnconfigure(1, weight=1)

        # All tk.* widgets in the table — repainted on theme change.
        table_tk_widgets = [canvas, body, header, keys_hdr, action_hdr]

        def apply_table_palette():
            tt = THEMES[self._current_theme]
            canvas.configure(bg=tt["listbox_bg"])
            body.configure(bg=tt["listbox_bg"])
            for child in body.winfo_children():
                if isinstance(child, tk.Label):
                    child.configure(bg=tt["listbox_bg"], fg=tt["listbox_fg"])
                elif isinstance(child, tk.Frame):
                    child.configure(bg=tt["heading_border"])

        win._apply_table_palette = apply_table_palette

        def show_cat(cat_key):
            cat = self._shortcuts.get("categories", {}).get(cat_key)
            if not cat:
                return
            title_label.configure(text=cat.get("display_name", cat_key))
            desc_label.configure(text=cat.get("description", ""))
            for child in body.winfo_children():
                child.destroy()
            canvas.update_idletasks()
            cw = canvas.winfo_width() or 700
            wrap_action = max(200, cw - keys_col_w - 16)
            wrap_keys = max(120, keys_col_w - 16)
            tt = THEMES[self._current_theme]
            shortcuts = cat.get("shortcuts", [])
            # Each shortcut occupies two grid rows: a 1px separator at row r,
            # then the keys/action labels at row r+1. A final separator after
            # the last row guarantees every entry has a line above and below.
            for i, s in enumerate(shortcuts):
                base = i * 2
                sep = tk.Frame(body, height=1, bg=tt["heading_border"])
                sep.grid(row=base, column=0, columnspan=2, sticky="we")
                k = tk.Label(
                    body, text=s.get("keys", ""), font=("Consolas", 10),
                    anchor="nw", justify="left", wraplength=wrap_keys,
                    bg=tt["listbox_bg"], fg=tt["listbox_fg"],
                )
                k.grid(row=base + 1, column=0, sticky="nw", padx=8, pady=4)
                a = tk.Label(
                    body, text=s.get("action", ""),
                    anchor="nw", justify="left", wraplength=wrap_action,
                    bg=tt["listbox_bg"], fg=tt["listbox_fg"],
                )
                a.grid(row=base + 1, column=1, sticky="nw", padx=8, pady=4)
            if shortcuts:
                final_sep = tk.Frame(body, height=1, bg=tt["heading_border"])
                final_sep.grid(row=len(shortcuts) * 2, column=0, columnspan=2, sticky="we")
            body.update_idletasks()
            canvas.configure(scrollregion=canvas.bbox("all"))

        def on_canvas_resize(ev):
            canvas.itemconfigure(body_window_id, width=ev.width)
            wrap_action = max(200, ev.width - keys_col_w - 16)
            for child in body.winfo_children():
                info = child.grid_info()
                if int(info.get("column", 0)) == 1:
                    child.configure(wraplength=wrap_action)
            canvas.after_idle(
                lambda: canvas.configure(scrollregion=canvas.bbox("all"))
            )
        canvas.bind("<Configure>", on_canvas_resize)

        # Mousewheel scrolling — only while the cursor is inside the canvas.
        def _on_wheel(ev):
            canvas.yview_scroll(int(-1 * (ev.delta / 120)), "units")
        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _on_wheel))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

        # Right side: vertical sidebar of category buttons.
        sidebar = ttk.Frame(win)
        sidebar.grid(row=0, column=1, sticky="ns")
        sidebar_buttons = []
        for i, (cat_key, cat) in enumerate(cats):
            btn = RoundedButton(
                sidebar,
                text=cat.get("display_name", cat_key),
                command=lambda k=cat_key: show_cat(k),
                width=170, height=32, padx=10,
            )
            btn.grid(row=i, column=0, sticky="we", pady=(0, 4))
            sidebar_buttons.append(btn)
        win._sidebar_buttons = sidebar_buttons

        # Defer the first populate until after the dialog is mapped so the
        # canvas has its real width; otherwise action labels would all be
        # created at the fallback wraplength.
        win.after_idle(lambda: show_cat(cats[0][0]))

        self._open_popups.append(win)

        def _on_destroy(ev, w=win):
            if ev.widget is not w:
                return
            try:
                canvas.unbind_all("<MouseWheel>")
            except tk.TclError:
                pass
            if w in self._open_popups:
                self._open_popups.remove(w)
        win.bind("<Destroy>", _on_destroy)

        self._theme_popup(win, self._current_theme)

    def _apply_theme(self, name):
        """Apply the named theme palette across all themed widgets."""
        if name not in THEMES:
            return
        t = THEMES[name]
        prev_theme = getattr(self, "_current_theme", None)
        self._current_theme = name

        self.configure(bg=t["bg"])

        s = self.style
        s.configure("TFrame",     background=t["bg"])
        s.configure("TLabel",     background=t["bg"], foreground=t["fg"])
        s.configure("TSeparator", background=t["bg"])
        s.configure("TButton",
                    background=t["btn_bg"], foreground=t["btn_fg"],
                    bordercolor=t["btn_bg"], focuscolor=t["btn_active_bg"],
                    lightcolor=t["btn_bg"], darkcolor=t["btn_bg"])
        s.map("TButton",
              background=[("active", t["btn_active_bg"])],
              foreground=[("active", t["btn_fg"])])
        s.configure("TEntry",
                    fieldbackground=t["entry_bg"], foreground=t["entry_fg"],
                    insertcolor=t["entry_fg"])

        for lbl in self._muted_labels:
            lbl.configure(foreground=t["muted_fg"])
        for lbl in self._caption_labels:
            lbl.configure(foreground=t["label_fg"])
        for lbl in self._normal_labels:
            lbl.configure(foreground=t["fg"])

        s.configure("Treeview",
                    background=t["listbox_bg"], foreground=t["listbox_fg"],
                    fieldbackground=t["listbox_bg"], bordercolor=t["bg"])
        s.map("Treeview",
              background=[("selected", t["listbox_sel_bg"])],
              foreground=[("selected", t["listbox_sel_fg"])])
        s.configure("Treeview.Heading",
                    background=t["heading_bg"], foreground=t["heading_fg"],
                    relief="solid", borderwidth=1,
                    bordercolor=t["heading_border"])
        s.map("Treeview.Heading",
              background=[("active", t["heading_bg"])],
              relief=[("active", "solid")])

        self.preview_holder.configure(
            bg=t["preview_bg"],
            highlightbackground=t["preview_border"],
            highlightcolor=t["preview_border"],
        )
        self.preview_label.configure(bg=t["preview_bg"])

        for txt in getattr(self, "_text_widgets", []):
            txt.configure(
                bg=t["bg"], fg=t["fg"],
                insertbackground=t["fg"],
                selectbackground=t["listbox_sel_bg"],
                selectforeground=t["listbox_sel_fg"],
            )

        # All canvas-based RoundedButtons follow the theme's btn_palette.
        btn_pal = t["btn_palette"]
        for rb in getattr(self, "_rounded_buttons", []):
            rb.apply_palette(btn_pal)
        # Indicate active theme by 'sticky-pressing' the selected button.
        self.sun_btn.set_active(name == "light")
        self.moon_btn.set_active(name == "dark")

        self._apply_titlebar_theme(name)

        for win in list(getattr(self, "_open_popups", [])):
            try:
                if win.winfo_exists():
                    self._theme_popup(win, name)
            except tk.TclError:
                pass

        if prev_theme != name:
            settings = load_user_settings()
            settings["theme"] = name
            save_user_settings(settings)

    def _theme_popup(self, win, name):
        """Apply the named theme palette to a Toplevel window."""
        t = THEMES[name]
        try:
            win.configure(bg=t["bg"])
        except tk.TclError:
            return
        self._set_dark_titlebar(win, name == "dark")
        # If this popup registered a table-palette callback, run it so any
        # tk.* widgets inside (Canvas, tk.Frame, tk.Label) repaint too.
        fn = getattr(win, "_apply_table_palette", None)
        if callable(fn):
            try:
                fn()
            except tk.TclError:
                pass
        # Re-paint any RoundedButtons attached to this popup (e.g. sidebar).
        for rb in getattr(win, "_sidebar_buttons", []):
            try:
                rb.apply_palette(t["btn_palette"])
            except tk.TclError:
                pass

    def _apply_titlebar_theme(self, name):
        """Toggle Windows immersive dark mode on the main window's title bar."""
        self._set_dark_titlebar(self, name == "dark")

    @staticmethod
    def _set_dark_titlebar(window, dark: bool):
        """Toggle immersive dark mode on any Tk window's title bar."""
        if sys.platform != "win32":
            return
        try:
            window.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
            value = ctypes.c_int(1 if dark else 0)
            for attr in (20, 19):  # 20 = modern; 19 = pre-19041 fallback
                res = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, attr, ctypes.byref(value), ctypes.sizeof(value),
                )
                if res == 0:
                    break
        except Exception as exc:
            print(f"[DEBUG] dark titlebar toggle failed: {exc}")


if __name__ == "__main__":
    print("[DEBUG] launching Tk")
    TodoApp().mainloop()
    print("[DEBUG] Tk exited")
