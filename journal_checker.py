"""
JournalChecker
--------------
Load an NIR journal export (.tsv) and see how many records with a similar
Reference value each parameter (e.g. P, Moisture, FFA) already has, so you
can decide whether a new sample is worth adding to the calibration.

Needs only Python with tkinter. Optional: tkinterdnd2 for drag & drop.
"""

import csv
import json
import re
import math
import os
import statistics
import sys
from datetime import datetime
from itertools import permutations

APP_NAME = "JournalChecker"
APP_VERSION = "1.4"

# Result - Reference larger than this multiple of RMSE is highlighted
OUTLIER_FACTOR = 2.5

# User manual - shown in the app (Help / F1). MANUAL.md in the repository is
# generated from this text:  python journal_checker.py --write-manual
MANUAL = r"""# JournalChecker - User Manual

## What the app is for

When you add a sample to an NIR calibration, you enter its lab value (the **Reference**) for each parameter. The more samples with nearly the same Reference value the calibration already has, the less a new one brings - and adding the same value over and over (e.g. 100 samples with P = 5.1) can bias the model.

JournalChecker reads the journal exported from the NIR software and shows, for each parameter, how many records with a similar Reference value are already there. You then decide yourself whether the new sample is worth entering. The app does not change the journal or the calibration - it only reads the file.

## Quick start

1. Start `JournalChecker.exe`.
2. Drag & drop the journal file (`*.Journal.tsv`) onto the window, or click **Open TSV...**.
3. In **New sample**, type the new sample's value for a parameter (e.g. P = 5.1) and check the **± Tolerance** (e.g. 0.5).
4. Read **Similar checked** - how many calibration records already have a Reference within 4.6 - 5.6.
5. Click the parameter name to see the distribution chart and the list of those records below.

## The main window

### Toolbar

- **Open TSV...** (Ctrl+O) - choose a journal file. You can also drag & drop a file onto the window or onto the .exe icon.
- **Reload (F5)** - read the same file again, e.g. after a new export. Typed values are kept.
- **File name** - the loaded file. Hover over it to see the full path.
- **Records without Reference** - list of records that have no lab value yet (see below).
- **Help (F1)** - this manual.

### New sample

One row per parameter found in the file.

- **Parameter** - click the name (or into its fields) to show its analysis below.
- **New value** - the value of the sample you are deciding about. Use the lab value, or the NIR Result as an estimate if the lab value is not known yet. Decimal comma or point both work.
- **± Tolerance** - how close a Reference must be to count as similar. Each parameter keeps its own tolerance, and it is remembered for next time. The first default is about 1/40 of the calibration range.
- **Reference range (checked)** - lowest and highest Reference among records used in the calibration. A new value outside this range extends the calibration.
- **In file** - number of all records in the file.
- **Checked** - records with a Reference value and Check = True, i.e. used in the calibration.
- **Unchecked** - records with a Reference value but Check = False, i.e. not used.
- **No Reference** - records without a lab value for this parameter.
- **Similar checked** - records with Check = True and Reference within New value ± Tolerance. This is the main number for the decision.
- **Similar unchecked** - the same, but with Check = False.
- **Clear values** - empties all New value fields.

### Analysis

Shows the parameter selected in New sample.

- **Summary line** - how many similar records were found, split by Check = True / False.
- **Chart** - distribution of the Reference values used in the calibration (Check = True). Blue bars and the light-blue band are inside New value ± Tolerance, the red line is the new value. Tall bars mean values that are already well covered; gaps are where new samples help most.
- **Record list** - the similar records, newest first. Click a column header to sort.
- **Grey rows** - Check = False (not in the calibration).
- **Red rows** - the NIR Result differs from the Reference much more than usual (more than 2.5 x RMSE of all checked records). Worth checking for a lab or typing error.
- **Export list to CSV...** - saves the list, e.g. for Excel.

Columns of the record list:

- **ROW**, **Date**, **Check**, **Use**, **Barcode**, **Note** - copied from the journal.
- **Reference <param>** - the lab value.
- **Result <param>** - the NIR prediction stored in the file at the time of measurement. Your NIR software may show a different, recalculated value.
- **Result - Reference** - prediction error of that record.
- **Mahalanobis <param>** - how different the spectrum is from the calibration (higher = more different). Shown only if the export contains it.
- **Distance** - Reference of the record minus New value. Sort by it to see the closest records.
- **Reference <other parameters>** - lab values of the other parameters of the same record.

### Status bar

Shows how many records were loaded, which parameters were found, how the Result values were matched to parameters, and whether Mahalanobis values are available.

## How to read the numbers

The app does not make the decision - these are only guidelines:

- **Similar checked is high** (e.g. 10 or more) and Mahalanobis is low - the sample probably adds little for that parameter.
- **Similar checked is 0 or low**, or the value is **outside the Reference range** - the sample fills a gap or extends the range.
- **Mahalanobis is high** (above the limit used in your NIR software) - the spectrum is unusual, so the sample can be valuable even if its Reference value is common.
- A sample can be common in one parameter and rare in another. Check every parameter you have a value for.

## Records without Reference

The **Records without Reference** button opens a list of records that have no lab value for any parameter yet - typically the newest measurements waiting for the lab. It shows their Result and Mahalanobis values. Double-click a row to copy its Result values into New value, so you can check coverage before the lab results arrive.

## Copying to Excel

In any list, select rows and press **Ctrl+C**, or right-click and choose **Copy selected rows** / **Copy all rows**. Rows are copied with the header and paste straight into Excel. Numbers use the decimal separator from your Windows regional settings. **Ctrl+A** selects all rows.

## How the file is read

- The file must be the tab-separated journal export with a **Check** column.
- **Parameters** are the numeric columns between **Reference** and **Begin** (e.g. Moisture, P, FFA). Any names and any number of parameters work. Empty columns (e.g. Protein with no values) are hidden until they get a value. Product, Composition and Mahalanobis columns are ignored.
- The **Reference** column contains the same values as the parameter columns, so the parameter columns are used.
- **Result** values have no names in the file. The app matches each position to a parameter by comparing them with the Reference values. This needs at least 3 records with both values; otherwise Result stays empty and the status bar shows a warning.
- **Mahalanobis** is taken from the first source that has a value: a column `Mahalanobis_<param>`, the list in the `Mahalanobis` column, or extra values in `Result` after the predictions.
- Text encodings UTF-8 and Windows-1250 are supported.

## Settings and shortcuts

- Tolerances, the selected parameter and the last opened file are saved in `%APPDATA%\JournalChecker\settings.json` and restored on the next start.
- **Ctrl+O** open, **F5** reload, **F1** help, **Ctrl+C** copy rows, **Ctrl+A** select all rows.

## Troubleshooting

- **"Column 'Check' not found"** - the file is not a journal export, or the header row is missing.
- **A parameter is missing** - the column has no numeric value in the file, or it is not between Reference and Begin.
- **Result column is empty** - fewer than 3 records have both Result and Reference for that parameter.
- **Mahalanobis column is empty** - the export does not contain Mahalanobis values. Try exporting the journal with recalculated results from your NIR software.
- **Drag & drop does not work** - when running from source, install it with `pip install tkinterdnd2` (run.bat does this automatically). The .exe already includes it.
- **Windows SmartScreen warning** - the .exe is not code-signed. Click More info, then Run anyway.
"""

# Columns that are never reference parameters
NON_PARAM_COLUMNS = {"product", "composition", "recipe", "images", "begin", "end"}


# ----------------------------------------------------------------------------
# Data loading / analysis (no GUI code here)
# ----------------------------------------------------------------------------

def parse_float(text):
    """Parse a number, accepting decimal comma. Returns None for blanks / NaN."""
    if text is None:
        return None
    t = str(text).strip().replace(",", ".")
    if not t:
        return None
    try:
        v = float(t)
    except ValueError:
        return None
    if math.isnan(v) or math.isinf(v):
        return None
    return v


def parse_list(text):
    """Parse '1.2 ; 3.4 ; NaN' into [1.2, 3.4, None]."""
    if not text or not str(text).strip():
        return []
    return [parse_float(p) for p in str(text).split(";")]


def parse_date(text):
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d.%m.%Y %H:%M:%S",
                "%d.%m.%Y %H:%M", "%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(text.strip(), fmt)
        except (ValueError, AttributeError):
            pass
    return None


def read_rows(path):
    csv.field_size_limit(min(sys.maxsize, 2 ** 31 - 1))
    last_error = None
    for enc in ("utf-8-sig", "cp1250", "latin-1"):
        try:
            with open(path, newline="", encoding=enc) as f:
                return list(csv.reader(f, delimiter="\t"))
        except UnicodeDecodeError as e:
            last_error = e
    raise last_error


class Record:
    """One journal row. `ref` = Reference (lab) values, `result` = NIR Result values."""
    __slots__ = ("row", "check", "date_text", "date", "use", "note", "barcode",
                 "ref", "result", "result_raw", "mahal", "mahal_raw", "mahal_cols")

    @property
    def has_any_ref(self):
        return any(v is not None for v in self.ref.values())


class Journal:
    def __init__(self, path):
        self.path = path
        self.records = []
        self.params = []
        self.result_slot = {}      # param -> position in the Result list
        self.warnings = []
        self._load()

    # -- loading --------------------------------------------------------------
    def _load(self):
        rows = read_rows(self.path)
        rows = [r for r in rows if any(c.strip() for c in r)]
        if len(rows) < 2:
            raise ValueError("The file contains no data rows.")
        header = [h.strip() for h in rows[0]]
        idx = {h.lower(): i for i, h in enumerate(header)}

        def col(*names):
            for n in names:
                if n.lower() in idx:
                    return idx[n.lower()]
            return None

        c_row, c_check, c_date = col("ROW"), col("Check"), col("Date", "Begin")
        c_use, c_note, c_bar = col("Use"), col("Note"), col("Barcode")
        c_res, c_ref = col("Result", "Results"), col("Reference")
        c_mahal = col("Mahalanobis")
        # per-parameter Mahalanobis columns, e.g. "MahalanobiS_Moisture"
        mahal_named = {h.split("_", 1)[1].lower(): i for i, h in enumerate(header)
                       if h.lower().startswith("mahalanobis_")}
        if c_check is None:
            raise ValueError("Column 'Check' not found - is this an NIR journal file?")

        param_cols = self._detect_param_columns(header, rows[1:], c_ref)
        if not param_cols:
            raise ValueError("No reference parameter columns with numeric values were found.")
        self.params = [header[i] for i in param_cols]

        def cell(r, i):
            return r[i] if i is not None and i < len(r) else ""

        for r in rows[1:]:
            rec = Record()
            rec.row = cell(r, c_row).strip()
            rec.check = cell(r, c_check).strip().lower() in ("true", "1", "yes", "y")
            rec.date_text = cell(r, c_date).strip()
            rec.date = parse_date(rec.date_text)
            rec.use = cell(r, c_use).strip()
            rec.note = cell(r, c_note).strip()
            rec.barcode = cell(r, c_bar).strip()
            rec.ref = {header[i]: parse_float(cell(r, i)) for i in param_cols}
            rec.result_raw = parse_list(cell(r, c_res))
            rec.result = {}
            rec.mahal_raw = parse_list(cell(r, c_mahal))
            rec.mahal_cols = {p: parse_float(cell(r, mahal_named[p.lower()]))
                              for p in self.params if p.lower() in mahal_named}
            rec.mahal = {}
            self.records.append(rec)

        self._map_results()
        self._map_mahalanobis()

    @staticmethod
    def _detect_param_columns(header, data, c_ref):
        """Parameter columns sit between 'Reference' and 'Begin'/spectra.
        Keep only columns that actually contain numbers."""
        lower = [h.lower() for h in header]
        start = c_ref + 1 if c_ref is not None else 0
        stop = len(header)
        for i in range(start, len(header)):
            if lower[i] in ("begin", "end", "recipe") or lower[i].startswith("#"):
                stop = i
                break
        cols = []
        for i in range(start, stop):
            name = lower[i]
            if not name or name in NON_PARAM_COLUMNS or name.startswith("mahalanobis"):
                continue
            if c_ref is None and name in ("row", "check", "uid", "points", "date", "snr",
                                          "id", "use", "barcode", "note", "original", "result"):
                continue
            values = [parse_float(r[i]) for r in data if i < len(r)]
            if sum(v is not None for v in values) >= 1:
                cols.append(i)
        return cols

    def _map_results(self):
        """The 'Result' column holds unnamed values. Find which position belongs
        to which parameter by comparing them with Reference values."""
        n_slots = min(12, max((len(r.result_raw) for r in self.records), default=0))
        if n_slots == 0:
            self.warnings.append("No 'Result' values found.")
            return
        big = 1e6
        score = {}
        for p in self.params:
            refs = [r.ref[p] for r in self.records if r.ref[p] is not None]
            spread = statistics.pstdev(refs) if len(refs) > 1 else 0
            spread = spread or (abs(statistics.mean(refs)) if refs else 1) or 1
            for s in range(n_slots):
                errs = [abs(r.result_raw[s] - r.ref[p]) for r in self.records
                        if r.ref[p] is not None and s < len(r.result_raw)
                        and r.result_raw[s] is not None]
                score[(p, s)] = statistics.median(errs) / spread if len(errs) >= 3 else big

        params = self.params
        if len(params) <= n_slots and len(params) <= 6:
            best, best_total = None, None
            for perm in permutations(range(n_slots), len(params)):
                total = sum(score[(p, s)] for p, s in zip(params, perm))
                if best_total is None or total < best_total:
                    best, best_total = perm, total
            assignment = dict(zip(params, best))
        else:  # greedy fallback
            assignment, used = {}, set()
            for (p, s) in sorted(score, key=score.get):
                if p not in assignment and s not in used:
                    assignment[p] = s
                    used.add(s)

        for p, s in assignment.items():
            if score[(p, s)] < 2.0:
                self.result_slot[p] = s
        missing = [p for p in params if p not in self.result_slot]
        if missing:
            self.warnings.append("Result value not identified for: " + ", ".join(missing))
        for r in self.records:
            for p in params:
                s = self.result_slot.get(p)
                r.result[p] = r.result_raw[s] if s is not None and s < len(r.result_raw) else None

    def _map_mahalanobis(self):
        """Mahalanobis per parameter, first source that has a value:
        1) column 'Mahalanobis_<param>', 2) list in column 'Mahalanobis'
        (same order as Result), 3) extra values in 'Result' after the predictions."""
        n_base = max(self.result_slot.values(), default=-1) + 1
        found = 0
        for r in self.records:
            for p in self.params:
                s = self.result_slot.get(p)
                v = r.mahal_cols.get(p)
                if v is None and s is not None and s < len(r.mahal_raw):
                    v = r.mahal_raw[s]
                if v is None and s is not None and n_base and n_base + s < len(r.result_raw):
                    v = r.result_raw[n_base + s]
                r.mahal[p] = v
                found += v is not None
        self.has_mahal = found > 0
        n = sum(r.mahal and any(v is not None for v in r.mahal.values()) for r in self.records)
        self.mahal_count = n

    # -- queries --------------------------------------------------------------
    def stats(self, param):
        """Counts per parameter. Checked/Unchecked count only records WITH a Reference."""
        with_ref = [r for r in self.records if r.ref[param] is not None]
        checked_vals = [r.ref[param] for r in with_ref if r.check]
        return {
            "in_file": len(self.records),
            "checked": len(checked_vals),
            "unchecked": len(with_ref) - len(checked_vals),
            "no_ref": len(self.records) - len(with_ref),
            "min": min(checked_vals) if checked_vals else None,
            "max": max(checked_vals) if checked_vals else None,
        }

    def residual_rmse(self, param):
        """RMSE of Result - Reference over checked records (None if too few)."""
        d = [r.result[param] - r.ref[param] for r in self.records
             if r.check and r.ref[param] is not None and r.result.get(param) is not None]
        if len(d) < 5:
            return None
        return math.sqrt(sum(x * x for x in d) / len(d))

    def checked_values(self, param):
        return [r.ref[param] for r in self.records if r.ref[param] is not None and r.check]

    def similar(self, param, value, tol):
        """All records with Reference within value ± tol (checked and unchecked), newest first."""
        out = [r for r in self.records
               if r.ref[param] is not None and abs(r.ref[param] - value) <= tol + 1e-9]
        out.sort(key=lambda r: r.date or datetime.min, reverse=True)
        return out

    def without_reference(self):
        out = [r for r in self.records if not r.has_any_ref]
        out.sort(key=lambda r: r.date or datetime.min, reverse=True)
        return out


def system_decimal_separator():
    """Decimal separator of the user's Windows regional settings ('.' or ',')."""
    try:
        import locale
        locale.setlocale(locale.LC_NUMERIC, "")
        return locale.localeconv().get("decimal_point") or "."
    except Exception:
        return "."


def localize_cell(value, decimal_sep):
    """Use the system decimal separator for numbers so Excel reads them as numbers."""
    text = str(value)
    if decimal_sep != "." and "." in text and parse_float(text) is not None:
        return text.replace(".", decimal_sep)
    return text


def nice_step(x):
    """Round x to 1, 2 or 5 x 10^n."""
    if x <= 0:
        return 1.0
    exp = math.floor(math.log10(x))
    base = x / 10 ** exp
    nice = 1 if base < 1.5 else 2 if base < 3.5 else 5 if base < 7.5 else 10
    return nice * 10 ** exp


def default_tolerance(values):
    if len(values) < 2:
        return 1.0
    span = max(values) - min(values)
    return nice_step(span / 40) if span > 0 else 1.0


def fmt_num(v, ref=None):
    """Compact number formatting: 4400, 5.1, 0.736, 1.82."""
    if v is None:
        return ""
    if abs(v) >= 1000 or (ref is not None and abs(ref) >= 1000):
        return f"{v:.0f}"
    return f"{v:.4g}" if abs(v) >= 0.001 or v == 0 else f"{v:.2e}"


# ----------------------------------------------------------------------------
# Settings
# ----------------------------------------------------------------------------

def _settings_base():
    return os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".config")


def settings_path():
    return os.path.join(_settings_base(), "JournalChecker", "settings.json")


def load_settings():
    # fall back to settings of the earlier name (NIRCalibChecker)
    for path in (settings_path(),
                 os.path.join(_settings_base(), "NIRCalibChecker", "settings.json")):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            continue
    return {}


def save_settings(data):
    try:
        os.makedirs(os.path.dirname(settings_path()), exist_ok=True)
        with open(settings_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except OSError:
        pass


# ----------------------------------------------------------------------------
# GUI
# ----------------------------------------------------------------------------

def run_gui(initial_file=None):
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox

    try:  # optional drag & drop support
        from tkinterdnd2 import TkinterDnD, DND_FILES
        BaseTk = TkinterDnD.Tk
    except Exception:
        TkinterDnD, DND_FILES, BaseTk = None, None, tk.Tk

    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

    COLORS = {
        "muted": "#6b6f76",
        "bar": "#c9ced6",
        "bar_hit": "#2f6fb3",
        "window": "#e3eefb",
        "marker": "#c4314b",
    }

    HELP = {
        "Parameter": "Reference parameter found in the file. Select it to show its analysis below.",
        "New value": "Value of the new sample - the lab Reference, or its Result as an estimate.",
        "± Tolerance": "Records with Reference within New value ± Tolerance count as similar. "
                       "Saved per parameter.",
        "Reference range (checked)": "Lowest and highest Reference among records with Check = True.",
        "In file": "All records in the loaded file.",
        "Checked": "Records with a Reference value and Check = True (used in the calibration).",
        "Unchecked": "Records with a Reference value and Check = False (not used in the calibration).",
        "No Reference": "Records without a Reference value for this parameter.",
        "Similar checked": "Records with Check = True and Reference within New value ± Tolerance.",
        "Similar unchecked": "Records with Check = False and Reference within New value ± Tolerance.",
        "ROW": "Row number from the journal (ROW column).",
        "Date": "Measurement date and time.",
        "Check": "True = record is used in the calibration.",
        "Use": "Use column from the journal (CAL / VAL / -).",
        "Reference": "Lab value (Reference).",
        "Result": "NIR prediction stored in the file (Result column).",
        "Result - Reference": f"NIR prediction minus lab value. Rows highlighted in red differ by "
                              f"more than {OUTLIER_FACTOR} x RMSE of all checked records - "
                              f"worth checking for lab or typing errors.",
        "Mahalanobis": "Mahalanobis distance from the file: how different the spectrum is from the "
                       "calibration (higher = more different). Empty if not in the export.",
        "Distance": "Reference of this record minus New value.",
        "Barcode": "Barcode column from the journal.",
        "Note": "Note column from the journal.",
    }
    TIPS = {
        "open": "Open a journal export (*.tsv) - Ctrl+O. You can also drag & drop the file "
                "onto this window or onto the .exe icon.",
        "reload": "Read the same file again, e.g. after a new export - F5. Typed values are kept.",
        "noref": "Records that have no lab (Reference) value yet - usually the newest "
                 "measurements. Double-click one there to use its Result as New value.",
        "help": "User manual - what the app does and what every column means (F1).",
        "param": "Click to show the analysis of this parameter below.",
        "clear": "Empty all New value fields.",
        "export": "Save the record list below as a CSV file (opens in Excel).",
        "chart": "Distribution of Reference values used in the calibration (Check = True). "
                 "Blue bars / light-blue band = within New value ± Tolerance, red line = "
                 "New value. Tall bars are well covered; gaps are where new samples help most.",
        "info": "Summary of the similar records listed below. Grey rows = Check = False, "
                "red rows = Result differs from Reference much more than usual. "
                "Right-click or Ctrl+C to copy rows.",
        "status": "What was found in the file: parameters, which Result position belongs to "
                  "which parameter, and whether Mahalanobis values are available.",
    }

    def help_for(column):
        if column in HELP:
            return HELP[column]
        for key in ("Reference", "Result", "Mahalanobis"):
            if column.startswith(key + " "):
                return HELP[key]
        return None

    def render_markdown(text, md):
        """Very small Markdown renderer for the manual (headings, bullets, bold, code)."""
        text.tag_configure("h1", font=("Segoe UI", 17, "bold"), spacing3=8)
        text.tag_configure("h2", font=("Segoe UI", 13, "bold"), spacing1=14, spacing3=4,
                           foreground="#1f4e79")
        text.tag_configure("h3", font=("Segoe UI", 11, "bold"), spacing1=8, spacing3=2)
        text.tag_configure("item", lmargin1=12, lmargin2=30, spacing1=2)
        text.tag_configure("bold", font=("Segoe UI", 10, "bold"))
        text.tag_configure("code", font=("Consolas", 10), background="#f0f1f3")
        token = re.compile(r"(\*\*.+?\*\*|`.+?`)")

        def inline(line, base):
            for part in token.split(line):
                if part.startswith("**") and part.endswith("**") and len(part) > 4:
                    text.insert("end", part[2:-2], (base, "bold"))
                elif part.startswith("`") and part.endswith("`") and len(part) > 2:
                    text.insert("end", part[1:-1], (base, "code"))
                elif part:
                    text.insert("end", part, (base,))

        for line in md.splitlines():
            for prefix, tag in (("### ", "h3"), ("## ", "h2"), ("# ", "h1")):
                if line.startswith(prefix):
                    text.insert("end", line[len(prefix):] + "\n", tag)
                    break
            else:
                m = re.match(r"(\d+\.|-)\s+(.*)", line)
                if m:
                    bullet = "\u2022" if m.group(1) == "-" else m.group(1)
                    text.insert("end", bullet + "  ", "item")
                    inline(m.group(2), "item")
                    text.insert("end", "\n", "item")
                elif line.strip():
                    inline(line, "p")
                    text.insert("end", "\n")
                else:
                    text.insert("end", "\n")

    class Tooltip:
        """Small hover tooltip. Use show()/hide() directly or attach() to a widget."""
        def __init__(self, master):
            self.master, self.win, self.job, self.text = master, None, None, None

        def attach(self, widget, text):
            """text may be a string or a function returning the current text."""
            def enter(e):
                t = text() if callable(text) else text
                if t:
                    self.schedule(t, e.x_root, e.y_root)
            widget.bind("<Enter>", enter, add="+")
            widget.bind("<Leave>", lambda e: self.hide(), add="+")

        def schedule(self, text, x, y):
            if text == self.text and (self.win or self.job):
                return
            self.hide()
            self.text = text
            self.job = self.master.after(450, lambda: self.show(text, x, y))

        def show(self, text, x, y):
            self.job = None
            self.win = tk.Toplevel(self.master)
            self.win.wm_overrideredirect(True)
            self.win.wm_geometry(f"+{x + 12}+{y + 18}")
            tk.Label(self.win, text=text, justify="left", wraplength=340, background="#ffffe8",
                     relief="solid", borderwidth=1, padx=6, pady=4,
                     font=("Segoe UI", 9)).pack()

        def hide(self):
            if self.job:
                self.master.after_cancel(self.job)
                self.job = None
            if self.win:
                self.win.destroy()
                self.win = None
            self.text = None

    class App(BaseTk):
        def __init__(self):
            super().__init__()
            self.title(f"{APP_NAME} {APP_VERSION}")
            self.geometry("1180x800")
            self.minsize(900, 600)
            self.settings = load_settings()
            self.journal = None
            self.rows = {}               # param -> widgets of the input grid row
            self.selected = tk.StringVar(value=self.settings.get("selected_param", ""))
            self.current = None          # analysis of the selected parameter
            self.pending_win = None
            self.tooltip = Tooltip(self)
            self.decimal_sep = system_decimal_separator()

            style = ttk.Style(self)
            if "vista" in style.theme_names():
                style.theme_use("vista")
            elif "clam" in style.theme_names():
                style.theme_use("clam")
            style.configure("Title.TLabel", font=("Segoe UI", 11, "bold"))
            style.configure("Param.TRadiobutton", font=("Segoe UI", 11, "bold"))
            style.configure("Treeview", rowheight=22)

            self._build_toolbar()
            self._build_statusbar()
            self._build_input_panel()
            self._build_analysis_panel()

            if DND_FILES:
                self.drop_target_register(DND_FILES)
                self.dnd_bind("<<Drop>>", self.on_drop)

            self.bind("<Control-o>", lambda e: self.open_file())
            self.bind("<F5>", lambda e: self.reload())
            self.bind("<F1>", lambda e: self.show_help())
            self.help_win = None
            self.protocol("WM_DELETE_WINDOW", self.on_close)

            start = initial_file or self.settings.get("last_file")
            if start and os.path.exists(start):
                self.after(100, lambda: self.load(start))

        # -- layout -----------------------------------------------------------
        def _build_toolbar(self):
            bar = ttk.Frame(self, padding=(10, 8))
            bar.pack(fill="x")
            b_open = ttk.Button(bar, text="Open TSV...", command=self.open_file)
            b_open.pack(side="left")
            b_reload = ttk.Button(bar, text="Reload (F5)", command=self.reload)
            b_reload.pack(side="left", padx=(6, 0))
            self.tooltip.attach(b_open, TIPS["open"])
            self.tooltip.attach(b_reload, TIPS["reload"])
            hint = ("No file loaded - open or drag & drop a .tsv file here" if DND_FILES
                    else "No file loaded (drag & drop needs: pip install tkinterdnd2)")
            self.file_label = ttk.Label(bar, text=hint, foreground=COLORS["muted"])
            self.file_label.pack(side="left", padx=12)
            self.tooltip.attach(self.file_label,
                                lambda: self.journal.path if self.journal else TIPS["open"])
            b_help = ttk.Button(bar, text="Help (F1)", command=self.show_help)
            b_help.pack(side="right")
            self.tooltip.attach(b_help, TIPS["help"])
            self.noref_button = ttk.Button(bar, text="Records without Reference",
                                           command=self.show_without_reference, state="disabled")
            self.noref_button.pack(side="right", padx=(0, 6))
            self.tooltip.attach(self.noref_button, TIPS["noref"])

        def _build_input_panel(self):
            box = ttk.LabelFrame(self, text=" New sample ", padding=10)
            box.pack(fill="x", padx=10)
            self.input_grid = ttk.Frame(box)
            self.input_grid.pack(fill="x")
            bottom = ttk.Frame(box)
            bottom.pack(fill="x", pady=(8, 0))
            ttk.Label(bottom, foreground=COLORS["muted"],
                      text="Select a parameter to see its analysis below. "
                           "Checked / Unchecked = records with a Reference value and Check = "
                           "True / False.").pack(side="left")
            b_clear = ttk.Button(bottom, text="Clear values", command=self.clear_values)
            b_clear.pack(side="right")
            self.tooltip.attach(b_clear, TIPS["clear"])

        def _rebuild_input_grid(self):
            for w in self.input_grid.winfo_children():
                w.destroy()
            self.rows.clear()
            heads = ["Parameter", "New value", "± Tolerance", "Reference range (checked)",
                     "In file", "Checked", "Unchecked", "No Reference", "Similar checked",
                     "Similar unchecked"]
            for c, h in enumerate(heads):
                lbl = ttk.Label(self.input_grid, text=h, foreground=COLORS["muted"],
                                cursor="question_arrow")
                lbl.grid(row=0, column=c, sticky="w", padx=(0, 16), pady=(0, 4))
                self.tooltip.attach(lbl, help_for(h))
            tols = self.settings.get("tolerances", {})
            for i, p in enumerate(self.journal.params, start=1):
                st = self.journal.stats(p)
                value_var = tk.StringVar()
                tol_var = tk.StringVar(value=str(tols.get(
                    p, fmt_num(default_tolerance(self.journal.checked_values(p))))))
                rb = ttk.Radiobutton(self.input_grid, text=p, value=p, variable=self.selected,
                                     style="Param.TRadiobutton", command=self.refresh_analysis)
                rb.grid(row=i, column=0, sticky="w", padx=(0, 16), pady=2)
                self.tooltip.attach(rb, TIPS["param"])
                e1 = ttk.Entry(self.input_grid, textvariable=value_var, width=12)
                e1.grid(row=i, column=1, sticky="w", padx=(0, 16))
                e2 = ttk.Entry(self.input_grid, textvariable=tol_var, width=10)
                e2.grid(row=i, column=2, sticky="w", padx=(0, 16))
                self.tooltip.attach(e1, help_for("New value"))
                self.tooltip.attach(e2, help_for("± Tolerance"))
                rng = f"{fmt_num(st['min'])} - {fmt_num(st['max'])}" if st["min"] is not None else "-"
                cells = [rng, st["in_file"], st["checked"], st["unchecked"], st["no_ref"]]
                for c, text in enumerate(cells, start=3):
                    cell = ttk.Label(self.input_grid, text=str(text))
                    cell.grid(row=i, column=c, sticky="w", padx=(0, 16))
                    self.tooltip.attach(cell, help_for(heads[c]))
                sim_c = ttk.Label(self.input_grid, text="", style="Title.TLabel")
                sim_c.grid(row=i, column=8, sticky="w", padx=(0, 16))
                sim_u = ttk.Label(self.input_grid, text="")
                sim_u.grid(row=i, column=9, sticky="w")
                self.tooltip.attach(sim_c, help_for("Similar checked"))
                self.tooltip.attach(sim_u, help_for("Similar unchecked"))
                for e in (e1, e2):
                    e.bind("<KeyRelease>", lambda ev: self.update_counts())
                    e.bind("<FocusIn>", lambda ev, p=p: self.select(p))
                self.rows[p] = dict(value=value_var, tol=tol_var, sim_c=sim_c, sim_u=sim_u)
            if self.selected.get() not in self.rows:
                self.selected.set(self.journal.params[0])

        def _build_statusbar(self):
            self.status = ttk.Label(self, text="", foreground=COLORS["muted"],
                                    padding=(10, 0, 10, 6))
            self.status.pack(side="bottom", fill="x")
            self.tooltip.attach(self.status, TIPS["status"])

        def _build_analysis_panel(self):
            frame = ttk.LabelFrame(self, text=" Analysis ", padding=8)
            frame.pack(fill="both", expand=True, padx=10, pady=10)
            self.analysis_frame = frame
            top = ttk.Frame(frame)
            top.pack(fill="x")
            self.info = ttk.Label(top, text="")
            self.info.pack(side="left")
            self.tooltip.attach(self.info, TIPS["info"])
            b_export = ttk.Button(top, text="Export list to CSV...", command=self.export)
            b_export.pack(side="right")
            self.tooltip.attach(b_export, TIPS["export"])
            self.canvas = tk.Canvas(frame, height=165, background="white", highlightthickness=0)
            self.canvas.pack(fill="x", pady=(6, 6))
            self.canvas.bind("<Configure>", lambda e: self.draw_histogram())
            self.tooltip.attach(self.canvas, TIPS["chart"])
            self.tree_wrap = ttk.Frame(frame)
            self.tree_wrap.pack(fill="both", expand=True)
            self.tree = None

        def _make_tree(self, parent, columns):
            for w in parent.winfo_children():
                w.destroy()
            tree = ttk.Treeview(parent, columns=columns, show="headings", selectmode="extended")
            for c in columns:
                tree.heading(c, text=c, command=lambda c=c, t=tree: self.sort_tree(t, c))
                width = (150 if c == "Date" else 60 if c in ("ROW", "Check", "Use")
                         else max(90, 8 * len(c) + 24))
                tree.column(c, width=width, anchor="w" if c in ("Date", "Barcode", "Note") else "e",
                            stretch=c in ("Note",))
            vs = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
            hs = ttk.Scrollbar(parent, orient="horizontal", command=tree.xview)
            tree.configure(yscrollcommand=vs.set, xscrollcommand=hs.set)
            tree.grid(row=0, column=0, sticky="nsew")
            vs.grid(row=0, column=1, sticky="ns")
            hs.grid(row=1, column=0, sticky="ew")
            parent.rowconfigure(0, weight=1)
            parent.columnconfigure(0, weight=1)
            tree.tag_configure("unchecked", foreground="#9a9ea5")
            tree.tag_configure("outlier", background="#fbe3e6")
            tree.bind("<Control-c>", lambda e: self.copy_rows(tree))
            tree.bind("<Control-C>", lambda e: self.copy_rows(tree))
            tree.bind("<Control-a>", lambda e: (tree.selection_set(tree.get_children("")), "break")[1])
            menu = tk.Menu(tree, tearoff=0)
            menu.add_command(label="Copy selected rows (Ctrl+C)", command=lambda: self.copy_rows(tree))
            menu.add_command(label="Copy all rows", command=lambda: self.copy_rows(tree, all_rows=True))
            menu.add_command(label="Select all (Ctrl+A)",
                             command=lambda: tree.selection_set(tree.get_children("")))

            def popup(e):
                row = tree.identify_row(e.y)
                if row and row not in tree.selection():
                    tree.selection_set(row)
                menu.tk_popup(e.x_root, e.y_root)
            tree.bind("<Button-3>", popup)

            def motion(e):
                if tree.identify_region(e.x, e.y) == "heading":
                    col = tree.identify_column(e.x)
                    idx = int(col[1:]) - 1 if col.startswith("#") and col[1:].isdigit() else -1
                    text = help_for(columns[idx]) if 0 <= idx < len(columns) else None
                    if text:
                        self.tooltip.schedule(text, e.x_root, e.y_root)
                        return
                self.tooltip.hide()
            tree.bind("<Motion>", motion)
            tree.bind("<Leave>", lambda e: self.tooltip.hide())
            return tree

        def copy_rows(self, tree, all_rows=False):
            """Copy rows as tab-separated text with header - pastes straight into Excel."""
            items = tree.get_children("") if all_rows else tree.selection()
            if not items:
                return "break"
            lines = ["\t".join(tree["columns"])]
            lines += ["\t".join(localize_cell(v, self.decimal_sep) for v in tree.item(k, "values"))
                      for k in items]
            self.clipboard_clear()
            self.clipboard_append("\r\n".join(lines) + "\r\n")
            self.status.configure(text=f"Copied {len(items)} rows to the clipboard.")
            return "break"

        # -- file handling ----------------------------------------------------
        def open_file(self):
            initial = os.path.dirname(self.settings.get("last_file", "")) or None
            path = filedialog.askopenfilename(
                title="Open NIR journal", initialdir=initial,
                filetypes=[("Journal files", "*.tsv *.txt *.csv"), ("All files", "*.*")])
            if path:
                self.load(path)

        def on_drop(self, event):
            paths = [p for p in self.tk.splitlist(event.data) if os.path.isfile(p)]
            if paths:
                self.load(paths[0])
            return getattr(event, "action", None)

        def reload(self):
            if self.journal:
                self.load(self.journal.path)

        def load(self, path):
            try:
                journal = Journal(path)
            except Exception as e:  # show any parsing problem to the user
                messagebox.showerror(APP_NAME, f"Could not read the file:\n{path}\n\n{e}")
                return
            old_values = {p: w["value"].get() for p, w in self.rows.items()}
            if self.journal:
                self.store_tolerances()
            self.journal = journal
            self.settings["last_file"] = path
            self.file_label.configure(text=os.path.basename(path), foreground="")
            mapping = ", ".join(f"{p} = Result #{s + 1}" for p, s in journal.result_slot.items())
            msg = f"{len(journal.records)} records. Parameters: {', '.join(journal.params)}."
            if mapping:
                msg += f"  Result values: {mapping}."
            msg += (f"  Mahalanobis available for {journal.mahal_count} records."
                    if journal.has_mahal else "  No Mahalanobis values in this file.")
            if journal.warnings:
                msg += "  " + "  ".join(journal.warnings)
            self.status.configure(text=msg)
            n_noref = len(journal.without_reference())
            self.noref_button.configure(text=f"Records without Reference ({n_noref})",
                                        state="normal")
            self._rebuild_input_grid()
            for p, v in old_values.items():      # keep typed values on reload
                if p in self.rows:
                    self.rows[p]["value"].set(v)
            if self.pending_win and self.pending_win.winfo_exists():
                self.pending_win.destroy()
            self.update_counts()

        # -- evaluation -------------------------------------------------------
        def _inputs(self, p):
            w = self.rows[p]
            value, tol = parse_float(w["value"].get()), parse_float(w["tol"].get())
            if value is None or tol is None or tol < 0:
                return None, tol
            return value, tol

        def update_counts(self):
            if not self.journal:
                return
            for p, w in self.rows.items():
                value, tol = self._inputs(p)
                if value is None:
                    w["sim_c"].configure(text="")
                    w["sim_u"].configure(text="")
                    continue
                sim = self.journal.similar(p, value, tol)
                n_c = sum(r.check for r in sim)
                w["sim_c"].configure(text=str(n_c))
                w["sim_u"].configure(text=str(len(sim) - n_c))
            self.refresh_analysis()

        def select(self, p):
            if self.selected.get() != p:
                self.selected.set(p)
                self.refresh_analysis()

        def refresh_analysis(self):
            if not self.journal:
                return
            p = self.selected.get()
            if p not in self.rows:
                return
            self.analysis_frame.configure(text=f" Analysis - {p} ")
            value, tol = self._inputs(p)
            others = [q for q in self.journal.params if q != p]
            columns = (["ROW", "Date", "Check", "Use", f"Reference {p}", f"Result {p}",
                        "Result - Reference", f"Mahalanobis {p}", "Distance"]
                       + [f"Reference {q}" for q in others] + ["Barcode", "Note"])
            self.tree = self._make_tree(self.tree_wrap, columns)
            if value is None:
                self.current = None
                self.info.configure(text=f"Enter a new {p} value above to list records "
                                         f"with a similar Reference.")
            else:
                sim = self.journal.similar(p, value, tol)
                self.current = {"param": p, "value": value, "tol": tol, "records": sim}
                n_c = sum(r.check for r in sim)
                rmse = self.journal.residual_rmse(p)
                limit = OUTLIER_FACTOR * rmse if rmse else None
                text = (f"{len(sim)} records with Reference {p} within {fmt_num(value)} ± "
                        f"{fmt_num(tol)}:  {n_c} Check = True,  {len(sim) - n_c} Check = False"
                        f"  (newest first)")
                if limit:
                    text += (f"   |   red = |Result - Reference| > {fmt_num(limit)} "
                             f"({OUTLIER_FACTOR} x RMSE)")
                self.info.configure(text=text)
                for r in sim:
                    ref, res = r.ref[p], r.result.get(p)
                    diff = res - ref if res is not None else None
                    row = [r.row, r.date_text, "True" if r.check else "False", r.use,
                           fmt_num(ref), fmt_num(res, ref), fmt_num(diff, ref),
                           fmt_num(r.mahal.get(p)), fmt_num(ref - value, ref)]
                    row += [fmt_num(r.ref[q]) for q in others] + [r.barcode, r.note]
                    tags = [] if r.check else ["unchecked"]
                    if limit and diff is not None and abs(diff) > limit:
                        tags.append("outlier")
                    self.tree.insert("", "end", values=row, tags=tags)
            self.draw_histogram()

        # -- help -----------------------------------------------------------------
        def show_help(self):
            if self.help_win and self.help_win.winfo_exists():
                self.help_win.lift()
                return
            win = tk.Toplevel(self)
            win.title(f"{APP_NAME} {APP_VERSION} - Help")
            win.geometry("760x700")
            self.help_win = win
            text = tk.Text(win, wrap="word", padx=18, pady=14, borderwidth=0,
                           font=("Segoe UI", 10), background="white", cursor="arrow")
            sb = ttk.Scrollbar(win, orient="vertical", command=text.yview)
            text.configure(yscrollcommand=sb.set)
            sb.pack(side="right", fill="y")
            text.pack(side="left", fill="both", expand=True)
            render_markdown(text, MANUAL)
            text.configure(state="disabled")
            win.bind("<Escape>", lambda e: win.destroy())

        # -- records without reference -----------------------------------------
        def show_without_reference(self):
            if not self.journal:
                return
            if self.pending_win and self.pending_win.winfo_exists():
                self.pending_win.lift()
                return
            win = tk.Toplevel(self)
            win.title("Records without Reference")
            win.geometry("1100x380")
            self.pending_win = win
            ttk.Label(win, padding=8,
                      text="Records with no Reference value for any parameter. Double-click a "
                           "row to copy its Result values into 'New value'.").pack(anchor="w")
            wrap = ttk.Frame(win, padding=(8, 0, 8, 8))
            wrap.pack(fill="both", expand=True)
            cols = (["ROW", "Date", "Check", "Use", "Barcode"]
                    + [f"Result {p}" for p in self.journal.params]
                    + [f"Mahalanobis {p}" for p in self.journal.params])
            tree = self._make_tree(wrap, cols)
            recs = self.journal.without_reference()
            for i, r in enumerate(recs):
                row = [r.row, r.date_text, "True" if r.check else "False", r.use, r.barcode]
                row += [fmt_num(r.result.get(p)) for p in self.journal.params]
                row += [fmt_num(r.mahal.get(p)) for p in self.journal.params]
                tree.insert("", "end", iid=str(i), values=row,
                            tags=() if r.check else ("unchecked",))

            def use(event):
                sel = tree.selection()
                if not sel:
                    return
                rec = recs[int(sel[0])]
                for p, w in self.rows.items():
                    v = rec.result.get(p)
                    w["value"].set(fmt_num(v) if v is not None else "")
                self.update_counts()
                self.status.configure(text=f"New values taken from Result of ROW {rec.row} "
                                           f"({rec.date_text}). Replace with Reference values "
                                           f"when available.")
            tree.bind("<Double-1>", use)

        # -- histogram --------------------------------------------------------
        def draw_histogram(self):
            c = self.canvas
            c.delete("all")
            if not self.journal:
                return
            p = self.selected.get()
            if p not in self.rows:
                return
            W, H = max(c.winfo_width(), 200), max(c.winfo_height(), 100)
            vals = self.journal.checked_values(p)
            if not vals:
                c.create_text(W / 2, H / 2, text="No checked Reference values for this parameter",
                              fill=COLORS["muted"])
                return
            cur = self.current if self.current and self.current["param"] == p else None
            lo, hi = min(vals), max(vals)
            if cur:
                lo = min(lo, cur["value"] - cur["tol"])
                hi = max(hi, cur["value"] + cur["tol"])
            if hi == lo:
                lo, hi = lo - 1, hi + 1
            pad_l, pad_r, pad_t, pad_b = 40, 16, 36, 26
            pw, ph = W - pad_l - pad_r, H - pad_t - pad_b
            nbins = max(10, min(40, int(pw / 22)))
            step = (hi - lo) / nbins
            counts = [0] * nbins
            for v in vals:
                counts[min(nbins - 1, int((v - lo) / step))] += 1
            top = max(counts)

            def x_of(v):
                return pad_l + (v - lo) / (hi - lo) * pw

            if cur:  # tolerance window
                c.create_rectangle(x_of(cur["value"] - cur["tol"]), pad_t,
                                   x_of(cur["value"] + cur["tol"]), pad_t + ph,
                                   fill=COLORS["window"], outline="")
            for i, n in enumerate(counts):
                if not n:
                    continue
                b0, b1 = lo + i * step, lo + (i + 1) * step
                hit = cur and b1 > cur["value"] - cur["tol"] and b0 < cur["value"] + cur["tol"]
                x0, x1 = x_of(b0) + 1, x_of(b1) - 1
                y0 = pad_t + ph - n / top * ph
                c.create_rectangle(x0, y0, x1, pad_t + ph, outline="",
                                   fill=COLORS["bar_hit"] if hit else COLORS["bar"])
                if x1 - x0 > 12:
                    c.create_text((x0 + x1) / 2, y0 - 7, text=str(n), font=("Segoe UI", 8),
                                  fill=COLORS["muted"])
            c.create_line(pad_l, pad_t + ph, pad_l + pw, pad_t + ph, fill="#9a9ea5")
            for v, anchor in ((lo, "w"), ((lo + hi) / 2, "center"), (hi, "e")):
                c.create_text(x_of(v), pad_t + ph + 12, text=fmt_num(v), anchor=anchor,
                              font=("Segoe UI", 8), fill=COLORS["muted"])
            c.create_text(pad_l - 6, pad_t, text=str(top), anchor="e",
                          font=("Segoe UI", 8), fill=COLORS["muted"])
            title = f"Distribution of Reference {p}, Check = True ({len(vals)} records)"
            if cur:
                title += (f"   |   red line = new value {fmt_num(cur['value'])}, "
                          f"blue = within ± {fmt_num(cur['tol'])}")
            c.create_text(pad_l, 8, anchor="w", font=("Segoe UI", 9), text=title)
            if cur:
                x = x_of(cur["value"])
                c.create_line(x, pad_t, x, pad_t + ph, fill=COLORS["marker"], width=2)

        # -- misc ---------------------------------------------------------------
        def store_tolerances(self):
            tols = self.settings.setdefault("tolerances", {})
            for p, w in self.rows.items():
                t = parse_float(w["tol"].get())
                if t is not None and t > 0:
                    tols[p] = w["tol"].get().strip()

        def clear_values(self):
            for w in self.rows.values():
                w["value"].set("")
            self.update_counts()

        def sort_tree(self, tree, col):
            rev = getattr(tree, "_sort_rev", {}).get(col, False)
            items = [(tree.set(k, col), k) for k in tree.get_children("")]

            def key(item):
                v = parse_float(item[0])
                return (0, v, "") if v is not None else (1, 0, item[0])
            items.sort(key=key, reverse=rev)
            for i, (_, k) in enumerate(items):
                tree.move(k, "", i)
            tree._sort_rev = {col: not rev}

        def export(self):
            if not self.current or not self.tree:
                messagebox.showinfo(APP_NAME, "Enter a new value first.")
                return
            p, value = self.current["param"], self.current["value"]
            path = filedialog.asksaveasfilename(
                defaultextension=".csv", initialfile=f"similar_{p}_{fmt_num(value)}.csv",
                filetypes=[("CSV", "*.csv")])
            if not path:
                return
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow(self.tree["columns"])
                for k in self.tree.get_children(""):
                    w.writerow([localize_cell(v, self.decimal_sep)
                                for v in self.tree.item(k, "values")])
            self.status.configure(text=f"Exported {len(self.tree.get_children(''))} rows to {path}")

        def on_close(self):
            self.store_tolerances()
            self.settings["selected_param"] = self.selected.get()
            save_settings(self.settings)
            self.destroy()

    app = App()
    app.mainloop()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--write-manual":
        out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "MANUAL.md")
        with open(out, "w", encoding="utf-8", newline="\n") as f:
            f.write(MANUAL)
        print(f"Written {out}")
    else:
        run_gui(sys.argv[1] if len(sys.argv) > 1 else None)
