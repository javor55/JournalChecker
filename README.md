# JournalChecker

Small Windows desktop tool for deciding whether a new NIR sample is worth adding to the calibration. It loads the instrument's journal export (`*.Journal.tsv`) and shows, for each reference parameter, how many records with a similar Reference value the calibration already has. Adding many samples with nearly the same reference value (e.g. 100 × P = 5.1) does not improve the model.

## Download

Get `JournalChecker.exe` from the **Releases** page (or the latest **Actions** build artifact). It is a single portable file:
- no install,
- no Python needed,
- runs on 64-bit Windows 10 and 11.

On first start, Windows SmartScreen may warn about an unknown publisher (the exe is not code-signed). Click *More info → Run anyway*.

## Run from source

1. Install Python 3.9+ from python.org.
2. Double-click `run.bat`. The first run installs `tkinterdnd2` for drag & drop. You can also run `python journal_checker.py [journal.tsv]`.

To build the exe yourself, double-click `build_exe.bat`; the result is `dist\JournalChecker.exe`. Every push to `main` also builds it automatically via GitHub Actions. Pushing a tag such as `v1.3` attaches it to a release.

## Manual

The full user manual is in [MANUAL.md](MANUAL.md). The same text is built into the app: click **Help (F1)**. Every button, field and column also explains itself when you hover the mouse over it.

## How it works

1. **Load a journal** in one of three ways: **Open TSV...**, drag & drop the file onto the window, or drop it onto the .exe icon.
2. **Parameters are detected automatically.** These are the numeric columns between `Reference` and `Begin` (e.g. *Moisture, P, FFA*); any names and any number of parameters work. Empty columns and *Mahalanobis* columns are ignored.
3. **`Result` values are matched to parameters automatically** by comparing them with the Reference values. The mapping is shown in the status bar.
4. **The top table** shows these columns for each parameter (hover a column header for help):

   | Column | Meaning |
   |---|---|
   | Reference range (checked) | min – max of Reference where Check = True |
   | In file | all records |
   | Checked | Reference filled in, Check = True |
   | Unchecked | Reference filled in, Check = False |
   | No Reference | Reference empty |
   | Similar checked / unchecked | records with Reference within *New value ± Tolerance* |

5. **The Analysis panel.** Select a parameter, or click into its fields, and the panel below shows two things:
   - a histogram of its checked Reference values, with the tolerance window highlighted;
   - the list of similar records: ROW, Date, Check, Use, Reference, Result, Result − Reference, Mahalanobis, Distance (Reference − New value), and the other parameters' Reference values.

   Details of the list:
   - Unchecked records are grey.
   - **Red rows**: |Result − Reference| is larger than 2.5 × RMSE of all checked records. These are worth checking for lab or typing errors.
   - **Mahalanobis** is shown when the export contains it. Sources, in this order: columns `Mahalanobis_<param>`, the `Mahalanobis` list, then extra values in `Result`.
6. **Copy and export.** In any table, use Ctrl+C or the right-click menu to copy rows. They paste straight into Excel with the decimal separator from your Windows regional settings. **Export list to CSV...** saves the list.
7. **Records without Reference** lists records with no Reference value yet. Double-click one to copy its Result values into *New value*.

Tolerances, the selected parameter and the last opened file are remembered in `%APPDATA%\JournalChecker\settings.json`. Decimal comma is accepted in inputs and files.
