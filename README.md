# JournalChecker

Small Windows desktop tool for deciding whether a new sample is worth adding to the NIR calibration. It shows how many records with a similar Reference value each parameter already has. Adding many samples with nearly the same reference value (e.g. 100 × P = 5.1) does not improve the model.

## Install / run

**Option A – run with Python** (Windows 10/11)
1. Install Python 3.9+ from python.org.
2. Double-click `run.bat`. The first run installs `tkinterdnd2` for drag & drop. You can also run `python journal_checker.py [journal.tsv]`.

**Option B – standalone .exe** (to share with colleagues who don't have Python)
1. On a PC with Python, double-click `build_exe.bat`.
2. Share `dist\JournalChecker.exe` – a single file, no install needed.

## How it works

1. Load the journal (`*.Journal.tsv`) in one of three ways:
   - **Open TSV...**
   - **drag & drop** it onto the window
   - drop it onto the .exe icon
2. Parameters are detected automatically from the numeric columns between `Reference` and `Begin` (e.g. *Moisture, P, FFA*). Empty columns and *Mahalanobis* columns are ignored. The per-parameter columns hold the same values as the `Reference` list.
3. `Result` values (NIR predictions) are matched to parameters automatically by comparing them with Reference values. The mapping is shown in the status bar.
4. For each parameter, the top table shows:

   | Column | Meaning |
   |---|---|
   | Reference range (checked) | min – max of Reference where Check = True |
   | In file | all records |
   | Checked | Reference filled in, Check = True |
   | Unchecked | Reference filled in, Check = False |
   | No Reference | Reference empty |
   | Similar checked / unchecked | records with Reference within *new value ± tolerance* |

5. Select a parameter (or click into its fields). The **Analysis** panel below then shows two things:
   - a histogram of its checked Reference values, with the tolerance window highlighted,
   - the list of similar records: ROW, Date, Check, Use, Reference, Result, Result − Reference, distance to the new value, and the other parameters' Reference values.

   **Mahalanobis** is shown when the file contains it. Sources, in this order:
   - columns `Mahalanobis_<param>`,
   - the `Mahalanobis` list,
   - the extra values in `Result` after the predictions.

   Unchecked records are shown in grey. Click a column header to sort. **Export list to CSV...** saves the list.
6. **Records without Reference** lists records with no Reference value yet. Double-click one to copy its Result values into *New value*.

Tolerances, the selected parameter and the last opened file are remembered in `%APPDATA%\JournalChecker\settings.json`. Decimal comma is accepted.
