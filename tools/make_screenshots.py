"""
Take README screenshots of the app with the synthetic demo journal.
Runs on Windows (used by .github/workflows/screenshots.yml).

    python tools/make_screenshots.py [demo/demo.Journal.tsv] [docs/screenshots]

Needs Pillow (pip install pillow).
"""

import os
import sys
import tkinter as tk

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import journal_checker as jc  # noqa: E402

DEMO = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "demo", "demo.Journal.tsv")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "docs", "screenshots")


def window_rect(win):
    """Screen rectangle of a window including its title bar (Windows), else client area."""
    win.update_idletasks()
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes
        hwnd = int(win.wm_frame(), 16)
        rect = wintypes.RECT()
        dwm = ctypes.windll.dwmapi  # exact visible frame, without the invisible resize border
        if dwm.DwmGetWindowAttribute(hwnd, 9, ctypes.byref(rect), ctypes.sizeof(rect)) != 0:
            ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
        return rect.left, rect.top, rect.right, rect.bottom
    x, y = win.winfo_rootx(), win.winfo_rooty()
    return x, y, x + win.winfo_width(), y + win.winfo_height()


def grab(win, name):
    from PIL import ImageGrab
    win.lift()
    win.update()
    path = os.path.join(OUT, name)
    ImageGrab.grab(bbox=window_rect(win), all_screens=True).save(path)
    print("saved", path)


def fit(win, width, height, x=20, y=20):
    """Place a window so it fits on screen above the taskbar."""
    sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
    width, height = min(width, sw - x - 10), min(height, sh - y - 90)
    win.geometry(f"{width}x{height}+{x}+{y}")


def set_values(app, values):
    for p, (value, tol) in values.items():
        app.rows[p]["value"].set(value)
        app.rows[p]["tol"].set(tol)
    app.update_counts()


def scenes(app):
    """Each step: (action, delay_ms)."""
    def s_covered():
        set_values(app, {"Moisture": ("4200", "100"), "P": ("5.1", "0.5"), "FFA": ("0.55", "0.01")})
        app.select("P")

    def s_gap():
        set_values(app, {"Moisture": ("4400", "100"), "P": ("12", "1"), "FFA": ("0.6", "0.01")})
        app.select("P")

    def s_help():
        app.show_help()
        fit(app.help_win, 820, 760, 40, 20)

    def s_noref():
        app.help_win.destroy()
        app.show_without_reference()
        fit(app.pending_win, 1000, 300, 30, 40)

    return [
        (lambda: app.load(DEMO), 600),
        (s_covered, 900), (lambda: grab(app, "analysis-covered.png"), 300),
        (s_gap, 900), (lambda: grab(app, "analysis-gap.png"), 300),
        (s_help, 900), (lambda: grab(app.help_win, "help.png"), 300),
        (s_noref, 900), (lambda: grab(app.pending_win, "records-without-reference.png"), 300),
        (app.destroy, 0),
    ]


def main():
    os.makedirs(OUT, exist_ok=True)
    os.environ["APPDATA"] = os.path.join(OUT, "_settings")   # do not touch real settings
    original_mainloop = tk.Misc.mainloop

    def mainloop(self, *args):
        fit(self, 1180, 820)
        steps = scenes(self)

        def run(i=0):
            if i < len(steps):
                action, delay = steps[i]
                action()
                self.after(delay, lambda: run(i + 1))
        self.after(800, run)
        original_mainloop(self, *args)

    tk.Misc.mainloop = mainloop
    jc.run_gui(None)


if __name__ == "__main__":
    main()
