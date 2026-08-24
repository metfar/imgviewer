# imgviewer

**imgviewer** is a fast, keyboard-first image viewer written in Python with pygame.
Its interface is inspired by **xzgv**: filenames and directories stay visible in a
list on the left while the selected image is displayed on the right.

The design deliberately avoids thumbnail generation. Only the image being viewed
is decoded, so browsing large directories starts quickly and uses substantially
less CPU, memory, and I/O than a contact-sheet style gallery.

## Features

- Filename/directory browser on the left and image preview on the right.
- No thumbnail generation.
- Sequential and shuffled-cycle random slideshow modes.
- Keyboard-first controls inspired by xzgv.
- Mouse controls and touch support.
- Fit-to-window, 1:1 view, zoom, and panning.
- Automatic initial window sizing so window decorations remain on-screen.
- Keyboard repeat defaults to 500 ms initial delay and 32 repeats/s (~31 ms).
- Opens either a directory or a specific image.
- Optional fullscreen mode.
- Local `.Trash/YYYYMMDD` safety area instead of permanent deletion.
- Optional recursive `.nomedia` and `.no-media` creation for Android/Pydroid use.
- No dependency on imgclassifier or any particular directory layout.

## Requirements

- Python 3.10 or newer.
- pygame 2.6 or newer.

Linux is the primary desktop target. The pygame-only architecture also keeps the
program suitable for environments such as Pydroid where pygame is available.

## Install

### Recommended: pipx

From a cloned repository:

```bash
pip install -r requirements.txt
pip install .
pipx install .
```

This installs the executable command:

```bash
imgviewer
```

For development:

```bash
pipx install --editable .
```

### Virtual environment

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install .
```

Then run:

```bash
imgviewer
```

### Run without installing

Install pygame and execute the module directly:

```bash
python -m pip install -r requirements.txt
python src/imgviewer.py
```

## Usage

Open the current directory:

```bash
imgviewer
```

Open another directory:

```bash
imgviewer ~/Pictures
```

Open a specific image:

```bash
imgviewer ~/Pictures/photo.jpg
```

Start fullscreen:

```bash
imgviewer --fullscreen ~/Pictures
```

Start a random slideshow with a 250 ms interval:

```bash
imgviewer --random --interval 0.25 ~/Pictures
```

Show all options:

```bash
imgviewer --help
```

## Keyboard

### File list

| Key | Action |
| --- | --- |
| `Up`, `k` | Previous entry |
| `Down`, `j` | Next entry |
| `Page Up`, `Ctrl-U` | Previous page |
| `Page Down`, `Ctrl-V` | Next page |
| `Home`, `Ctrl-A` | First entry |
| `End`, `Ctrl-E` | Last entry |
| `Enter` | Enter directory / focus viewer |
| `Backspace` | Parent directory |
| `Ctrl-R` | Rescan directory |
| `Tab`, `Esc` | Switch list/view focus |

### Image viewer

| Key | Action |
| --- | --- |
| `Space` | Next image |
| `b` | Previous image |
| `z` | Fit-to-window / 1:1 |
| `+`, `-` | Zoom |
| Arrows, `h/j/k/l` | Pan zoomed image |
| `s` | Slideshow on/off |
| `r` | Sequential/random order |
| `[`, `]` | Decrease/increase slideshow interval |
| `Ctrl-D` | Move selected image to local Trash |
| `F11`, `Alt-Enter` | Fullscreen/windowed |
| `q` | Quit |

Navigation, panning, zoom and interval keys repeat after 500 ms at approximately
32 repeats per second by default. The defaults can still be overridden with
`--repeat-delay` and `--repeat-rate`.

## Mouse and touch

The toolbar provides Previous, Next, Play/Pause, sequential/random, interval,
Fit and Trash actions. In the image area, the left and right edge zones navigate
between images. Touch input follows the same general model and supports dragging.

## Trash behavior

`Ctrl-D` and the **Trash** button do **not** permanently delete the selected entry.
The file is moved to a local directory beside its original directory:

```text
.Trash/YYYYMMDD/
```

A `trash-index.jsonl` audit log is kept in `.Trash`. If the selected entry is a
symbolic link, imgviewer moves the link itself and leaves its target untouched.

This local Trash is intentionally simple and is not the freedesktop.org desktop
Trash specification.

## Android media markers

A general-purpose image viewer should not silently hide arbitrary folders from
Android's media scanner. Marker creation is therefore explicit.

Create `.nomedia` and `.no-media` recursively and then open the viewer:

```bash
imgviewer --media-markers /path/to/images
```

Create the markers and exit:

```bash
imgviewer --markers-only /path/to/images
```

Trash directories receive media markers automatically.

## Desktop integration on Linux

After installing the `imgviewer` command, let imgviewer create its desktop
entry with the absolute path to the installed executable:

```bash
imgviewer --install-desktop
```

This writes `~/.local/share/applications/imgviewer.desktop` (or the equivalent
location below `$XDG_DATA_HOME`), installs the packaged icon as
`~/.local/share/icons/hicolor/64x64/apps/imgviewer.png`, and refreshes the
desktop MIME database when
`update-desktop-database` is available. The generated entry uses `Icon=imgviewer` and intentionally does
not use `TryExec`, so it is not hidden merely because the graphical login
session has a different `PATH` from an interactive shell.

To remove it:

```bash
imgviewer --uninstall-desktop
```

The repository still includes `contrib/imgviewer.desktop` as a generic template,
but `--install-desktop` is the recommended method.

### If pip and pipx conflict

Do not keep the same application installed simultaneously with user `pip` and
`pipx`. If `pipx install .` reports that `~/.local/bin/imgviewer` already exists
or points somewhere unexpected, remove the older pip installation first:

```bash
python -m pip uninstall imgviewer
pipx uninstall imgviewer
pipx install .
pipx ensurepath
imgviewer --install-desktop
```

After `pipx ensurepath`, a logout/login may be required for the graphical
session to inherit the updated path. The desktop entry itself uses an absolute
executable path and therefore does not depend on that for launching.

## Development checks

```bash
python -m py_compile src/imgviewer.py
python src/imgviewer.py --version
python src/imgviewer.py --help
python src/imgviewer.py --self-test
```

The repository also includes a GitHub Actions workflow performing these checks
and testing the installed console command.

## Project layout

```text
imgviewer/
├── .github/workflows/ci.yml
├── contrib/imgviewer.desktop
├── src/imgviewer.py
├── .gitignore
├── CHANGELOG.md
├── LICENSE
├── pyproject.toml
├── README.md
└── requirements.txt
```

## License

imgviewer is free software licensed under the **GNU General Public License,
version 2 or (at your option) any later version** (`GPL-2.0-or-later`).

See `LICENSE` for the complete GPL version 2 text.


## Application icon

The application icon is packaged in the Python distribution and used in two
places:

- the pygame window calls `pygame.display.set_icon()` with the packaged PNG;
- `imgviewer --install-desktop` installs the same PNG in the user's freedesktop
  `hicolor` icon theme and writes `Icon=imgviewer` in the desktop entry.

The source icon lives at:

```text
src/imgviewer_assets/imgviewer.png
```

To replace the artwork for a later release, replace that file and rebuild the
wheel/package.


## Font compatibility

imgviewer deliberately uses Pygame's bundled default font rather than a named
system font.  On normal installations it uses `pygame.font.Font(None, size)`.
For pygame 2.6.1 builds where Python 3.14 triggers the known
`pygame.font`/`pygame.sysfont` circular import, imgviewer falls back to Pygame's
own low-level FreeType backend (`pygame._freetype`) and still uses the bundled
default font.  This does not add a new dependency and does not replace pygame.

<p align=center><b>- oOo -</b></p>
