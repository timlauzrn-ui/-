# Separation email automation

This script runs on a Windows PC that is signed in to desktop Outlook, has desktop Word installed, and can see the company share. It files separation mail onto that share and sends one summary to the MIS distribution list.

For each unread separation message it:

1. Opens the Word attachment and reads Form No, Department, Staff No, Staff Name, AD Account, Last Working Day, and Received Date.
2. Appends one row to the Termination Form Logsheet. Disable and Delete stay blank under the merged Action Date header.
3. Exports the Word file to PDF, appends the checklist PDF from the share, and saves `YYMMNNN.pdf`.
4. Stores that PDF at `{share}\{Year}\{Month}\{YYMMNNN}.pdf`, creating the year and month folders when they are missing.

After the batch, it sends one Outlook message with the staff names, form numbers, last working days, and PDF paths. Messages that were filed are marked so a later run leaves them alone. Messages that fail stay unread.

The Word form stays on the company machines. Field names, share paths, and recipients live in `config.json`, which is gitignored.

## Requirements

- Windows, with the user logged on
- Desktop Outlook, already signed in
- Desktop Word
- The network share available as a UNC path
- Python 3.10 or newer

Mail and the Word form are handled through those desktop apps. Close the logsheet in Excel before a run so the file can be saved.

## Setup

From this folder:

```
py -m pip install -r requirements.txt
copy config.example.json config.json
```

Fill the empty values in `config.json`. Leave that file uncommitted.

`pywin32` installs on Windows only. `openpyxl` writes the logsheet and `pypdf` appends the checklist.

## Config

Paths and the field map:

| Key | What to enter |
| --- | --- |
| `share_root` | UNC folder that contains the year folders |
| `logsheet_path` | Full path of the Termination Form Logsheet `.xlsx` (or `.xlsm`) |
| `logsheet_sheet` | Sheet name, or empty to use the active sheet |
| `logsheet_header_rows` | Header depth, or empty to detect it from the header labels |
| `logsheet_columns` | Column letters such as `A`, or empty to match the header labels |
| `checklist_pdf` | Full path of the one checklist PDF |
| `outlook.mailbox` | Mailbox display name, or empty for the default profile |
| `outlook.folder_path` | Dedicated folder, using the names shown in Outlook, such as `Inbox\Separation` |
| `outlook.subject_contains` | Subject substring. Required when `folder_path` is empty or is the Inbox |
| `outlook.processed_folder` | Folder to move mail into after filing, or empty to leave it in place |
| `outlook.processed_category` | Category that a later run skips. The default is `SeparationFiled` |
| `summary_mail.to` | MIS distribution list display name or address, as a list |
| `summary_mail.cc` | Extra recipients, or `[]` |
| `summary_mail.subject` | Subject of the one summary mail |

`filing_date_field` chooses the folder month. `last_working_day` follows Last Working Day. Set it to `received_date` to follow Received Date instead.

`year_folder_format` and `month_folder_format` are `strftime` patterns. `%Y` and `%m` produce folders such as `2026\10`. `%B` uses the month name from the Windows locale.

`date_formats` lists the `strptime` patterns tried on the two date fields, in order.

Header labels the logsheet scan understands: Form No, Department, Staff No, Staff Name, AD Account, Last Working Day, Received Date, plus Disable and Delete on the Action Date header. When the sheet uses different labels, set `logsheet_columns` to the column letters and set `logsheet_header_rows` to the number of header rows. The script writes the seven values and leaves Disable and Delete empty. It keeps the Action Date merge as it found it.

### Word field map

Each `word_fields` entry is a content control or a table cell. Indexes are 1-based, as in Word.

Content control (set `tag`, or `title` when the control has no tag):

```json
"form_no": {"kind": "content_control", "tag": "", "title": ""}
```

Table cell:

```json
"department": {"kind": "table_cell", "table": 1, "row": 1, "column": 1}
```

In Word, the content control properties show Tag and Title. For a table, count tables, rows, and columns from 1.

The map in `config.example.json` is empty on purpose. Fill it from the real form and keep the result in `config.json`.

## Numbering

`2610001` is the first file for October 2026. `2611001` is the first file for November 2026. The first four digits are year and month (`YYMM`). The last three digits start at `001` each month.

Each run looks at the PDFs already in that month's folder. The next file is one higher than the highest `YYMMNNN.pdf` in that folder. Other files in the folder are ignored. The script reads the folder again every time, so the highest matching PDF plus one is the name that gets used.

## Run

Outlook should be open. From this folder:

```
py src\main.py --config config.json
```

Task Scheduler can run the same command when the user is logged on. Use a full path for `--config`.

Check the match list before filing:

```
py src\main.py --config config.json --dry-run
```

A filed message is marked read and given `processed_category`. When `processed_folder` is set, the message is moved there after that save. A message that fails validation, the logsheet, or the PDF stays unread and is left for the next run. The summary mail is sent when at least one form was filed. If every message fails, the script prints the errors and does not send mail.

The script expects one Word attachment on each message (`.doc`, `.docx`, or `.docm`) and appends one logsheet row for it. The checklist is the second part of the saved PDF.

## Tests

Naming, the logsheet merge, and the PDF append can be checked on a machine that does not have Outlook or Word:

```
py -m unittest discover -s tests -v
```
