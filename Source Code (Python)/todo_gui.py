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
        self.refresh_btn = ttk.Button(left, text="Refresh", command=self._refresh_files)
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
        self.delete_btn = ttk.Button(left, text="Delete", command=self._delete_selected)
        self.delete_btn.grid(row=3, column=0, sticky="we")
        self.new_btn = ttk.Button(left, text="New", command=self._new_entry)
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
            text=f"Up to {MAX_ITEMS} entries, {MAX_CHARS} chars each.",
        )
        self.entries_caption.grid(row=0, column=0, sticky="w")

        theme_frame = ttk.Frame(top_row)
        theme_frame.grid(row=0, column=1, sticky="e")
        self.sun_btn = tk.Button(
            theme_frame, text="☀", width=2,
            command=lambda: self._apply_theme("light"),
            relief="flat", borderwidth=1, font=("Segoe UI Symbol", 11, "bold"),
        )
        self.sun_btn.grid(row=0, column=0, padx=(0, 2))
        self.moon_btn = tk.Button(
            theme_frame, text="☾", width=2,
            command=lambda: self._apply_theme("dark"),
            relief="flat", borderwidth=1, font=("Segoe UI Symbol", 11, "bold"),
        )
        self.moon_btn.grid(row=0, column=1)

        self.entries = []
        self._entry_num_labels = []
        for i in range(MAX_ITEMS):
            num_lbl = ttk.Label(right, text=f"{i + 1}.")
            num_lbl.grid(row=1 + i, column=0, sticky="e", padx=(0, 6), pady=2)
            self._entry_num_labels.append(num_lbl)
            vcmd = (self.register(self._validate_len), "%P")
            e = ttk.Entry(right, width=30, validate="key", validatecommand=vcmd)
            e.grid(row=1 + i, column=1, columnspan=2, sticky="we", pady=2)
            e.bind("<KeyRelease>", lambda _ev: self._live_preview())
            self.entries.append(e)

        row = 1 + MAX_ITEMS
        ttk.Separator(right, orient="horizontal").grid(row=row, column=0, columnspan=3, sticky="we", pady=10)

        row += 1
        self.text_color_label = ttk.Label(right, text="Text color:")
        self.text_color_label.grid(row=row, column=0, sticky="e", padx=(0, 6))
        self.fg_swatch = tk.Label(right, text="    ", bg=self.fg_color, relief="sunken", width=4)
        self.fg_swatch.grid(row=row, column=1, sticky="w")
        ttk.Button(right, text="Select…", command=self._pick_fg).grid(row=row, column=1, columnspan=2, sticky="we", padx=(50, 0))

        row += 1
        self.bg_color_label = ttk.Label(right, text="Background:")
        self.bg_color_label.grid(row=row, column=0, sticky="e", padx=(0, 6), pady=(4, 0))
        self.bg_swatch = tk.Label(right, text="    ", bg=self.bg_color, relief="sunken", width=4)
        self.bg_swatch.grid(row=row, column=1, sticky="w", pady=(4, 0))
        ttk.Button(right, text="Select…", command=self._pick_bg).grid(row=row, column=1, columnspan=2, sticky="we", padx=(50, 0), pady=(4, 0))

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
        ttk.Button(right, text="Generate PNG", command=self._generate).grid(
            row=row, column=0, columnspan=3, sticky="we", pady=(14, 4)
        )

        row += 1
        self.status = ttk.Label(right, text=f"Output folder: {IMAGES_DIR}", wraplength=320)
        self.status.grid(row=row, column=0, columnspan=3, sticky="w", pady=(6, 0))

        # ── Keyboard Shortcuts section ─────────────────────────────────────
        self._shortcuts = load_shortcuts()

        row += 1
        ttk.Separator(right, orient="horizontal").grid(
            row=row, column=0, columnspan=3, sticky="we", pady=(12, 8)
        )

        row += 1
        self.shortcut_caption = ttk.Label(right, text="Randomly Selected Keyboard Shortcut")
        self.shortcut_caption.grid(row=row, column=0, columnspan=3, sticky="w")

        row += 1
        shortcut_frame = ttk.Frame(right, height=60)
        shortcut_frame.grid(row=row, column=0, columnspan=3, sticky="we", pady=(2, 8))
        shortcut_frame.grid_propagate(False)
        shortcut_frame.columnconfigure(1, weight=1)
        self.shortcut_keys_label = ttk.Label(
            shortcut_frame, text="", font=("Consolas", 10, "bold")
        )
        self.shortcut_keys_label.grid(row=0, column=0, sticky="nw", padx=(0, 14))
        self.shortcut_action_label = ttk.Label(shortcut_frame, text="", wraplength=240)
        self.shortcut_action_label.grid(row=0, column=1, sticky="nw")

        row += 1
        self.refsheets_caption = ttk.Label(right, text="Reference Sheets")
        self.refsheets_caption.grid(row=row, column=0, columnspan=3, sticky="w", pady=(4, 4))

        row += 1
        buttons_frame = ttk.Frame(right)
        buttons_frame.grid(row=row, column=0, columnspan=3, sticky="we")
        cats = list(self._shortcuts.get("categories", {}).items())
        cols = 3
        for i, (cat_key, cat) in enumerate(cats):
            r, c = divmod(i, cols)
            btn = ttk.Button(
                buttons_frame,
                text=cat["display_name"],
                command=lambda k=cat_key: self._open_category(k),
            )
            btn.grid(row=r, column=c, sticky="we", padx=2, pady=2)
        for c in range(cols):
            buttons_frame.columnconfigure(c, weight=1)

        self._shortcut_after_id = None
        self._schedule_shortcut_rotation()

        # Track widget groups that need recoloring on theme change.
        self._muted_labels = [self.status, self.entries_caption, self.png_suffix_label]
        self._caption_labels = [
            self.existing_files_label, self.preview_label_caption,
            self.shortcut_caption, self.refsheets_caption,
        ]
        self._normal_labels = (
            self._entry_num_labels
            + [self.text_color_label, self.bg_color_label, self.filename_label,
               self.shortcut_keys_label, self.shortcut_action_label]
        )

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
        self.status.configure(text=f"Fresh slate — filename set to {next_name}.png.")

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
            self.status.configure(text=f"Deleted {name}.")
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
        self.status.configure(text=f"Loaded {name} — generating will overwrite it.")

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
            self.status.configure(text=f"Wrote {out_path.name} ({ms:.0f} ms) — ready to upload.")
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
        all_shortcuts = []
        for cat in self._shortcuts.get("categories", {}).values():
            all_shortcuts.extend(cat.get("shortcuts", []))
        if not all_shortcuts:
            self.shortcut_keys_label.configure(text="—")
            self.shortcut_action_label.configure(text="(no shortcuts loaded)")
            return
        # Avoid repeating the currently shown shortcut on consecutive rotations.
        current = self.shortcut_keys_label.cget("text") if hasattr(self, "shortcut_keys_label") else ""
        if len(all_shortcuts) > 1:
            choices = [s for s in all_shortcuts if s.get("keys", "") != current]
        else:
            choices = all_shortcuts
        s = random.choice(choices)
        self.shortcut_keys_label.configure(text=s.get("keys", ""))
        self.shortcut_action_label.configure(text=s.get("action", ""))

    def _schedule_shortcut_rotation(self):
        """Tick the random-shortcut display every SHORTCUT_ROTATE_MS milliseconds."""
        self._pick_random_shortcut()
        self._shortcut_after_id = self.after(
            SHORTCUT_ROTATE_MS, self._schedule_shortcut_rotation
        )

    def _open_category(self, cat_key):
        """Open a popup window listing all shortcuts in a category."""
        cat = self._shortcuts.get("categories", {}).get(cat_key)
        if not cat:
            return
        t = THEMES[self._current_theme]
        win = tk.Toplevel(self)
        win.title(cat.get("display_name", cat_key))
        win.configure(bg=t["bg"], padx=12, pady=12)
        win.transient(self)
        win.minsize(560, 360)

        if cat.get("description"):
            desc = ttk.Label(win, text=cat["description"], wraplength=540)
            desc.pack(anchor="w", pady=(0, 8))

        tree_frame = ttk.Frame(win)
        tree_frame.pack(fill="both", expand=True)

        tree = ttk.Treeview(
            tree_frame, columns=("keys", "action"),
            show="headings", height=18, selectmode="browse",
        )
        tree.heading("keys", text="Keys", anchor="center")
        tree.heading("action", text="Action", anchor="center")
        tree.column("keys", width=200, anchor="w", stretch=False)
        tree.column("action", width=400, anchor="w", stretch=True)
        tree.pack(side="left", fill="both", expand=True)

        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        sb.pack(side="right", fill="y")
        tree.configure(yscrollcommand=sb.set)

        for s in cat.get("shortcuts", []):
            tree.insert("", "end", values=(s.get("keys", ""), s.get("action", "")))

        self._open_popups.append(win)
        win.bind("<Destroy>",
                 lambda ev, w=win: (ev.widget is w) and self._open_popups.remove(w)
                 if w in self._open_popups else None)
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

        for btn in (self.sun_btn, self.moon_btn):
            btn.configure(
                bg=t["btn_bg"], fg=t["btn_fg"],
                activebackground=t["btn_active_bg"], activeforeground=t["btn_fg"],
                highlightbackground=t["bg"],
            )
        # Indicate active theme by raising the selected button.
        self.sun_btn.configure(relief=("sunken" if name == "light" else "flat"))
        self.moon_btn.configure(relief=("sunken" if name == "dark" else "flat"))

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
