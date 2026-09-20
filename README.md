# I-140 Automation

Fill USCIS Form I-140 from an internal Word info questionnaire, with a Gradio UI for review/edit/save.

## Features

- Extract data from filled I-140 info Word docs (`.doc` / `.docx`) via Microsoft Word COM
- Map fields onto the official I-140 PDF
- Gradio UI: upload → edit → preview → save
- Optional Windows packaging via `build.bat` (Nuitka + PyInstaller)

## Requirements

- Windows 10/11
- Python 3.11+
- Microsoft Word (for Word extraction)
- Blank I-140 PDF template under `assets/i-140-uscis.pdf` or `test/i-140-uscis.pdf`

## Setup

```bat
pip install -r requirements.txt
```

## Run UI

```bat
run_ui.bat
```

Or:

```bat
python app.py
```

Open http://127.0.0.1:7860

## CLI

```bat
python fill_i140.py --word "path\to\info.docx" --pdf-template "test\i-140-uscis.pdf" --output "filled.pdf"
```

JSON input is also supported with `--json sample_data.json`.

## Package for distribution

```bat
build.bat
```

Produces `dist\I140Filler\` and `dist\I140Filler.zip`. End users need Windows + Word; no Python.

## Project layout

| Path | Purpose |
|------|---------|
| `app.py` | Gradio UI |
| `word_extractor.py` | Word form extraction |
| `pdf_filler.py` | PDF field mapping / fill |
| `models.py` | Data model |
| `fill_i140.py` | CLI entrypoint |
| `build.bat` | Packaging script |
| `assets/` | Template PDF for packaged builds |
| `test/` | Blank templates and sample inputs |
