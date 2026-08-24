# Changelog

All notable changes to **imgviewer** are documented here.

## 0.4.0 - 2026-08-24

- Turned imgviewer into an independent installable Python project.
- Added `pyproject.toml` and the system command `imgviewer`.
- Added GPL-2.0-or-later license metadata and repository license file.
- Added README, GitHub CI workflow, desktop integration example, and requirements file.
- Kept the xzgv-style filename list + single-image preview design.
- Kept keyboard repeat defaults at 500 ms initial delay and 32 repeats/s (~31 ms).
- Kept automatic window fitting to the available desktop size.
- Fixed a duplicated local-trash date assignment from 0.3.0.

## 0.3.0

- General-purpose viewer independent from imgclassifier.
- Local `.Trash/YYYYMMDD` behavior.
- Optional Android `.nomedia` / `.no-media` marker creation.

## 0.2.x

- Reimplemented the viewer in pygame with an xzgv-inspired split layout.
- Added slideshow, random/sequential order, keyboard navigation, mouse and touch support.
