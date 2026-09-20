# Distributing I-140 Filler

## What the build does

`build.bat` uses a practical hybrid of option #1:

1. **Nuitka** compiles your core logic (`models`, `pdf_filler`, `word_extractor`) to binary `.pyd` modules — this is what protects the important source.
2. **PyInstaller** packs the Gradio UI + dependencies into `dist\I140Filler\` — full Nuitka of Gradio is too slow/large for this stack.

## Build

```bat
build.bat
```

Distribute the **entire** folder:

```text
dist\I140Filler\
```

Zip it for users. They need Windows + Microsoft Word; no Python.

## Notes

- First build downloads compilers/caches; later builds are faster.
- Keep `windows` console on until you verify the exe; then you can switch PyInstaller to `--windowed` if you want no console.
- This blocks casual `.py` theft of your fill/extract logic. It is not perfect DRM.
