I-140 PDF Filler
================

Requirements
------------
- Windows 10/11
- Microsoft Word installed (used to read .doc / .docx info forms)
- No Python install needed

How to install
--------------
1. Delete any previous I140Filler folder (important when updating).
2. Unzip I140Filler.zip to a local folder (e.g. Desktop or Documents).
   Do not run the .exe from inside the .zip.
3. Keep the whole unzipped folder together (do not move only the .exe).

How to run
----------
1. Double-click I140Filler.exe
2. A browser window opens at http://127.0.0.1:7860
3. Upload an I-140 info Word document, review/edit fields, generate PDF,
   then Confirm & save

If it fails on startup
----------------------
- Fully extract the zip again into a new empty folder
- Allow the app in antivirus / Windows SmartScreen if prompted
- Confirm this file exists:
  _internal\gradio_client\types.json

Files
-----
- I140Filler.exe     Application
- assets\            Blank USCIS I-140 PDF template (required)
- output\            Working copies of generated PDFs
- README.txt         This file

Notes
-----
- First launch may take a little longer while the UI starts.
- If the browser does not open, go to http://127.0.0.1:7860 manually.
