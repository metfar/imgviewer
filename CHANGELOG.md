# Changelog

## 0.4.1.post3

- Keep the dependency on standard `pygame` (`pygame>=2.6`).
- Stop requesting a named system font with `pygame.font.SysFont`.
- Use Pygame's bundled default font instead.
- Add a compatibility fallback to Pygame's own `_freetype` backend when
  `pygame.font` is unavailable because of the pygame 2.6.1 / Python 3.14
  circular-import bug.
- No viewer/navigation behavior changed.


## 0.4.1.post1

- Package the imgviewer PNG application icon.
- Use the packaged PNG as the pygame window icon.
- `--install-desktop` now installs the icon into the user's hicolor icon theme.
- Desktop entry now uses `Icon=imgviewer`.
- No image-viewing behavior changed.


## 0.4.1 - Desktop integration fix

- Added `imgviewer --install-desktop` and `--uninstall-desktop`.
- Desktop installer writes an absolute `Exec=` path, avoiding GUI-session PATH differences.
- Removed `TryExec=imgviewer`, which could hide the application when the desktop environment did not inherit `~/.local/bin`.
- Documented cleanup when `pip` and `pipx` installations conflict.

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
