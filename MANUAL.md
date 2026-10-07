# JournalChecker - User Manual

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
