#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#pylint:disable=W0301
#  
#  Copyright 2018- William Martinez Bas <metfar@gmail.com>
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#  
#
#import warnings;
#warnings.filterwarnings("ignore", category=UserWarning);

from __future__ import annotations;

import argparse;
import contextlib;
import json;
import math;
import os;
import random;
import shutil;
import sys;
from datetime import datetime;
from pathlib import Path;
from typing import List, Optional, Tuple;

pygame = None;


def load_pygame() -> None:
    global pygame;
    if pygame is not None:
        return;
    os.environ.setdefault("SDL_VIDEO_CENTERED", "1");
    with open(os.devnull, "w", encoding="utf-8") as _devnull:
        with contextlib.redirect_stdout(_devnull), contextlib.redirect_stderr(_devnull):
            import pygame as _pygame;
    pygame = _pygame;

VERSION = "0.4.0";
APP_NAME = "imgviewer";
WINDOW_TITLE = "imgviewer";
WINDOW_SIZE = (1280, 800);
WINDOW_DECORATION_RESERVE = (32, 80);
WINDOW_MIN_SIZE = (640, 360);
FPS = 60;

KEY_REPEAT_DELAY_MS = 500;
KEY_REPEAT_RATE_CPS = 32.0;
KEY_REPEAT_INTERVAL_MS = max(1, round(1000.0 / KEY_REPEAT_RATE_CPS));

IMAGE_EXTS = (
    ".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp",
);

PANE_RATIO = 0.31;
PANE_MIN = 260;
PANE_MAX = 520;
STATUS_H = 44;
TOOLBAR_H = 52;
ROW_PAD_Y = 5;

DEFAULT_INTERVAL_MS = 2000;
MIN_INTERVAL_MS = 100;
MAX_INTERVAL_MS = 60000;
INTERVAL_STEP_FAST_MS = 500;
INTERVAL_STEP_FINE_MS = 100;

ZOOM_MIN = 0.10;
ZOOM_MAX = 8.0;
ZOOM_STEP = 0.10;
PAN_STEP = 48;

DOUBLE_CLICK_MS = 420;
TOUCH_LONGPRESS_MS = 800;
TOUCH_TAP_TOLERANCE_PX = 24.0;

COL_BG = (8, 9, 12);
COL_PANEL = (18, 20, 26);
COL_PANEL_ALT = (27, 30, 38);
COL_TEXT = (225, 228, 235);
COL_MUTED = (145, 150, 160);
COL_SELECT = (65, 80, 110);
COL_CURRENT = (46, 64, 85);
COL_BORDER = (80, 85, 96);
COL_ACCENT = (230, 215, 80);
COL_DANGER = (150, 55, 55);
COL_BUTTON = (44, 48, 58);
COL_BUTTON_HOVER = (58, 64, 78);

FOCUS_LIST = "list";
FOCUS_VIEW = "view";

ORDER_SEQUENTIAL = "sequential";
ORDER_RANDOM = "random";


def normalize_path(path: str) -> Path:
    return Path(path).expanduser().resolve();


def get_desktop_size() -> Tuple[int, int]:
    try:
        sizes = pygame.display.get_desktop_sizes();
        if sizes:
            width, height = sizes[0];
            if width > 0 and height > 0:
                return int(width), int(height);
    except (AttributeError, pygame.error):
        pass;

    try:
        info = pygame.display.Info();
        if info.current_w > 0 and info.current_h > 0:
            return int(info.current_w), int(info.current_h);
    except pygame.error:
        pass;

    return WINDOW_SIZE;


def fit_window_to_desktop(
    requested: Tuple[int, int],
    desktop: Tuple[int, int],
) -> Tuple[int, int]:
    req_w, req_h = requested;
    desk_w, desk_h = desktop;
    reserve_x, reserve_y = WINDOW_DECORATION_RESERVE;

    if req_w + reserve_x <= desk_w and req_h + reserve_y <= desk_h:
        return requested;

    safe_w = max(320, desk_w - reserve_x);
    safe_h = max(240, desk_h - reserve_y);
    width = min(req_w, safe_w);
    height = min(req_h, safe_h);

    if desk_w >= WINDOW_MIN_SIZE[0] + reserve_x:
        width = max(WINDOW_MIN_SIZE[0], width);
    if desk_h >= WINDOW_MIN_SIZE[1] + reserve_y:
        height = max(WINDOW_MIN_SIZE[1], height);

    width = min(width, safe_w);
    height = min(height, safe_h);
    return int(width), int(height);


def is_image(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in IMAGE_EXTS;


def absolute_path(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)));


def ensure_media_markers(root: Path) -> int:
    """Crea .nomedia y .no-media bajo root de forma recursiva.

    Es una operación explícita: un visualizador de propósito general no debe
    ocultar directorios a la galería del sistema sin que el usuario lo pida.
    """;
    if not root.exists():
        return 0;
    root = root if root.is_dir() else root.parent;
    created = 0;
    dirs = [root];
    try:
        dirs.extend(p for p in root.rglob("*") if p.is_dir());
    except OSError:
        pass;
    for directory in dirs:
        for name in (".nomedia", ".no-media"):
            marker = directory / name;
            if not marker.exists():
                try:
                    marker.touch();
                    created += 1;
                except OSError:
                    pass;
    return created;


def available_target(path: Path) -> Path:
    if not path.exists() and not path.is_symlink():
        return path;
    stem = path.stem;
    suffix = path.suffix;
    n = 2;
    while True:
        candidate = path.with_name(f"{stem}-{n}{suffix}");
        if not candidate.exists() and not candidate.is_symlink():
            return candidate;
        n += 1;


def move_to_local_trash(selected_path: Path) -> Path:
    """Mueve la entrada seleccionada a .Trash/YYYYMMDD junto a su carpeta.

    Si selected_path es un symlink, se mueve el symlink; no se toca su destino.
    Esto hace que el visor sea seguro y predecible fuera de imgclassifier.
    """;
    source = absolute_path(selected_path);
    if not source.exists() and not source.is_symlink():
        raise FileNotFoundError(source);

    day = datetime.now().strftime("%Y%m%d");
    trash_root = source.parent / ".Trash";
    trash_dir = trash_root / day;
    trash_dir.mkdir(parents=True, exist_ok=True);
    ensure_media_markers(trash_root);

    target = available_target(trash_dir / source.name);
    shutil.move(str(source), str(target));

    log_path = trash_root / "trash-index.jsonl";
    record = {
        "time": datetime.now().astimezone().isoformat(),
        "source": str(source),
        "target": str(target),
        "was_symlink": selected_path.is_symlink(),
    };
    try:
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n");
    except OSError:
        pass;

    return target;


class Entry:
    def __init__(self, kind: str, path: Path, label: str) -> None:
        self.kind = kind;
        self.path = path;
        self.label = label;


class Viewer:
    def __init__(
        self,
        start: Path,
        fullscreen: bool,
        interval_ms: int,
        random_order: bool,
        repeat_delay_ms: int,
        repeat_rate_cps: float,
    ) -> None:
        self.start = start;
        self.current_dir = start if start.is_dir() else start.parent;
        self.fullscreen = fullscreen;
        self.interval_ms = max(MIN_INTERVAL_MS, min(MAX_INTERVAL_MS, interval_ms));
        self.order_mode = ORDER_RANDOM if random_order else ORDER_SEQUENTIAL;
        self.slideshow = False;
        self.last_switch_ms = 0;

        self.focus = FOCUS_LIST;
        self.entries: List[Entry] = [];
        self.selected = 0;
        self.scroll_top = 0;
        self.current_image_path: Optional[Path] = None;
        self.original: Optional[pygame.Surface] = None;
        self.scaled: Optional[pygame.Surface] = None;
        self.scaled_rect = pygame.Rect(0, 0, 1, 1);
        self.zoom_mode_fit = True;
        self.zoom_factor = 1.0;
        self.pan_x = 0;
        self.pan_y = 0;

        self.image_paths: List[Path] = [];
        self.random_queue: List[Path] = [];

        self.status = "";
        self.status_until = 0;

        self.last_click_ms = 0;
        self.last_click_index = -1;

        self.touch_id: Optional[int] = None;
        self.touch_down_ms = 0;
        self.touch_down_pos = (0.0, 0.0);
        self.touch_last_pos = (0.0, 0.0);
        self.touch_dragging = False;
        self.touch_longpress_handled = False;

        self.buttons: List[Tuple[pygame.Rect, str, str]] = [];
        self.confirm_trash = False;

        self.repeat_key: Optional[int] = None;
        self.repeat_mods = 0;
        self.repeat_next_ms = 0;
        self.repeat_delay_ms = max(0, repeat_delay_ms);
        self.repeat_rate_cps = max(1.0, repeat_rate_cps);
        self.repeat_interval_ms = max(1, round(1000.0 / self.repeat_rate_cps));

        pygame.init();
        self.desktop_size = get_desktop_size();
        self.windowed_size = fit_window_to_desktop(WINDOW_SIZE, self.desktop_size);
        if fullscreen:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN);
        else:
            self.screen = pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE);
        pygame.display.set_caption(WINDOW_TITLE);
        self.clock = pygame.time.Clock();

        self.reload_directory(preserve=None);
        if start.is_file() and is_image(start):
            self.select_path(start);
        else:
            self.preview_selected();

        if not fullscreen and self.windowed_size != WINDOW_SIZE:
            self.set_status(
                f"Ventana ajustada a {self.windowed_size[0]}x{self.windowed_size[1]} "
                f"para escritorio {self.desktop_size[0]}x{self.desktop_size[1]}",
                5000,
            );


    def font(self, size: int, bold: bool = False) -> pygame.font.Font:
        h = self.screen.get_height();
        scale = max(0.85, min(1.5, h / 800.0));
        return pygame.font.SysFont("dejavu sans", max(13, int(size * scale)), bold=bold);


    def list_width(self) -> int:
        return max(PANE_MIN, min(PANE_MAX, int(self.screen.get_width() * PANE_RATIO)));


    def content_rect(self) -> pygame.Rect:
        lw = self.list_width();
        return pygame.Rect(
            lw + 1,
            0,
            max(1, self.screen.get_width() - lw - 1),
            max(1, self.screen.get_height() - STATUS_H - TOOLBAR_H),
        );


    def list_rect(self) -> pygame.Rect:
        return pygame.Rect(
            0,
            0,
            self.list_width(),
            max(1, self.screen.get_height() - STATUS_H),
        );


    def row_height(self) -> int:
        return self.font(18).get_linesize() + ROW_PAD_Y * 2;


    def visible_rows(self) -> int:
        return max(1, (self.list_rect().height - 42) // self.row_height());


    def set_status(self, text: str, ms: int = 2600) -> None:
        self.status = text;
        self.status_until = pygame.time.get_ticks() + ms;


    def scan_dir(self, directory: Path) -> Tuple[List[Entry], List[Path]]:
        entries: List[Entry] = [];
        parent = directory.parent;
        if parent != directory:
            entries.append(Entry("up", parent, "../"));

        try:
            children = list(directory.iterdir());
        except OSError as exc:
            self.set_status(f"No se puede leer: {exc}", 4000);
            return entries, [];

        dirs = sorted(
            (p for p in children if p.is_dir() and p.name not in (".Trash",)),
            key=lambda p: p.name.casefold(),
        );
        images = sorted(
            (p for p in children if is_image(p)),
            key=lambda p: p.name.casefold(),
        );

        for p in dirs:
            entries.append(Entry("dir", p, p.name + "/"));
        for p in images:
            entries.append(Entry("image", p, p.name));

        return entries, images;


    def reload_directory(self, preserve: Optional[Path]) -> None:
        self.entries, self.image_paths = self.scan_dir(self.current_dir);
        self.random_queue = [];

        if preserve is not None:
            preserve_resolved = absolute_path(preserve);
            for idx, entry in enumerate(self.entries):
                try:
                    if absolute_path(entry.path) == preserve_resolved:
                        self.selected = idx;
                        break;
                except OSError:
                    pass;
            else:
                self.selected = min(self.selected, max(0, len(self.entries) - 1));
        else:
            self.selected = min(self.selected, max(0, len(self.entries) - 1));

        self.ensure_selected_visible();


    def select_path(self, path: Path) -> None:
        target = absolute_path(path);
        for idx, entry in enumerate(self.entries):
            if entry.kind == "image" and absolute_path(entry.path) == target:
                self.selected = idx;
                self.ensure_selected_visible();
                self.load_image(entry.path);
                return;


    def selected_entry(self) -> Optional[Entry]:
        if not self.entries:
            return None;
        if self.selected < 0 or self.selected >= len(self.entries):
            return None;
        return self.entries[self.selected];


    def preview_selected(self) -> None:
        entry = self.selected_entry();
        if entry is not None and entry.kind == "image":
            self.load_image(entry.path);


    def load_image(self, path: Path) -> None:
        try:
            surface = pygame.image.load(str(path)).convert();
        except Exception as exc:
            self.set_status(f"No se pudo cargar {path.name}: {exc}", 5000);
            return;

        self.current_image_path = path;
        self.original = surface;
        self.zoom_mode_fit = True;
        self.zoom_factor = 1.0;
        self.pan_x = 0;
        self.pan_y = 0;
        self.rebuild_scaled();
        self.last_switch_ms = pygame.time.get_ticks();


    def rebuild_scaled(self) -> None:
        if self.original is None:
            self.scaled = None;
            return;

        area = self.content_rect();
        iw, ih = self.original.get_size();

        if self.zoom_mode_fit:
            scale = min(area.width / max(iw, 1), area.height / max(ih, 1));
        else:
            scale = self.zoom_factor;

        scale = max(ZOOM_MIN, min(ZOOM_MAX, scale));
        nw = max(1, int(iw * scale));
        nh = max(1, int(ih * scale));

        if nw == iw and nh == ih:
            self.scaled = self.original;
        else:
            self.scaled = pygame.transform.scale(self.original, (nw, nh));

        self.scaled_rect = self.scaled.get_rect();
        self.scaled_rect.center = area.center;
        self.scaled_rect.x += self.pan_x;
        self.scaled_rect.y += self.pan_y;
        self.clamp_scaled_rect();


    def clamp_scaled_rect(self) -> None:
        area = self.content_rect();

        if self.scaled_rect.width <= area.width:
            self.scaled_rect.centerx = area.centerx;
            self.pan_x = 0;
        else:
            if self.scaled_rect.left > area.left:
                self.scaled_rect.left = area.left;
            if self.scaled_rect.right < area.right:
                self.scaled_rect.right = area.right;

        if self.scaled_rect.height <= area.height:
            self.scaled_rect.centery = area.centery;
            self.pan_y = 0;
        else:
            if self.scaled_rect.top > area.top:
                self.scaled_rect.top = area.top;
            if self.scaled_rect.bottom < area.bottom:
                self.scaled_rect.bottom = area.bottom;


    def ensure_selected_visible(self) -> None:
        rows = self.visible_rows();
        if self.selected < self.scroll_top:
            self.scroll_top = self.selected;
        if self.selected >= self.scroll_top + rows:
            self.scroll_top = self.selected - rows + 1;
        self.scroll_top = max(0, min(self.scroll_top, max(0, len(self.entries) - rows)));


    def move_selection(self, delta: int, preview: bool = True) -> None:
        if not self.entries:
            return;
        self.selected = max(0, min(len(self.entries) - 1, self.selected + delta));
        self.ensure_selected_visible();
        if preview:
            self.preview_selected();


    def select_first(self) -> None:
        if not self.entries:
            return;
        self.selected = 0;
        self.ensure_selected_visible();
        self.preview_selected();


    def select_last(self) -> None:
        if not self.entries:
            return;
        self.selected = len(self.entries) - 1;
        self.ensure_selected_visible();
        self.preview_selected();


    def activate_selected(self) -> None:
        entry = self.selected_entry();
        if entry is None:
            return;

        if entry.kind in ("dir", "up"):
            self.current_dir = entry.path;
            self.selected = 0;
            self.scroll_top = 0;
            self.reload_directory(preserve=None);
            self.original = None;
            self.scaled = None;
            self.current_image_path = None;
            self.preview_selected();
            self.set_status(str(self.current_dir));
            return;

        if entry.kind == "image":
            self.load_image(entry.path);
            self.focus = FOCUS_VIEW;


    def go_up(self) -> None:
        parent = self.current_dir.parent;
        if parent == self.current_dir:
            return;
        old = self.current_dir;
        self.current_dir = parent;
        self.selected = 0;
        self.scroll_top = 0;
        self.reload_directory(preserve=old);
        self.preview_selected();


    def refresh(self) -> None:
        preserve = self.current_image_path or (
            self.selected_entry().path if self.selected_entry() is not None else None
        );
        self.reload_directory(preserve=preserve);
        self.preview_selected();
        self.set_status("Directorio actualizado");


    def current_image_index(self) -> int:
        if self.current_image_path is None:
            return -1;
        target = absolute_path(self.current_image_path);
        for idx, p in enumerate(self.image_paths):
            if absolute_path(p) == target:
                return idx;
        return -1;


    def next_image(self, step: int = 1) -> None:
        if not self.image_paths:
            return;

        idx = self.current_image_index();
        if idx < 0:
            idx = 0 if step >= 0 else len(self.image_paths) - 1;
        else:
            idx = (idx + step) % len(self.image_paths);

        path = self.image_paths[idx];
        self.select_path(path);


    def next_random_image(self) -> None:
        if not self.image_paths:
            return;

        current = absolute_path(self.current_image_path) if self.current_image_path else None;

        if not self.random_queue:
            self.random_queue = list(self.image_paths);
            random.shuffle(self.random_queue);
            if (
                current is not None and
                len(self.random_queue) > 1 and
                absolute_path(self.random_queue[0]) == current
            ):
                self.random_queue.append(self.random_queue.pop(0));

        path = self.random_queue.pop(0);
        self.select_path(path);


    def slideshow_advance(self) -> None:
        if self.order_mode == ORDER_RANDOM:
            self.next_random_image();
        else:
            self.next_image(1);


    def toggle_slideshow(self) -> None:
        self.slideshow = not self.slideshow;
        self.last_switch_ms = pygame.time.get_ticks();
        self.set_status(
            f"Slideshow {'ON' if self.slideshow else 'OFF'} - "
            f"{self.order_mode} - {self.interval_ms / 1000:.2f}s"
        );


    def toggle_order(self) -> None:
        self.order_mode = (
            ORDER_RANDOM if self.order_mode == ORDER_SEQUENTIAL else ORDER_SEQUENTIAL
        );
        self.random_queue = [];
        self.set_status(f"Orden: {self.order_mode}");


    def change_interval(self, direction: int) -> None:
        if self.interval_ms <= 1000:
            step = INTERVAL_STEP_FINE_MS;
        else:
            step = INTERVAL_STEP_FAST_MS;

        self.interval_ms += direction * step;
        self.interval_ms = max(MIN_INTERVAL_MS, min(MAX_INTERVAL_MS, self.interval_ms));
        self.set_status(f"Intervalo: {self.interval_ms / 1000:.2f}s");


    def toggle_fit(self) -> None:
        if self.original is None:
            return;
        if self.zoom_mode_fit:
            self.zoom_mode_fit = False;
            self.zoom_factor = 1.0;
        else:
            self.zoom_mode_fit = True;
        self.pan_x = 0;
        self.pan_y = 0;
        self.rebuild_scaled();
        self.set_status("Fit" if self.zoom_mode_fit else "1:1");


    def zoom(self, delta: float) -> None:
        if self.original is None:
            return;
        if self.zoom_mode_fit:
            area = self.content_rect();
            iw, ih = self.original.get_size();
            self.zoom_factor = min(area.width / max(iw, 1), area.height / max(ih, 1));
            self.zoom_mode_fit = False;
        self.zoom_factor = max(ZOOM_MIN, min(ZOOM_MAX, self.zoom_factor + delta));
        self.rebuild_scaled();
        self.set_status(f"Zoom: {self.zoom_factor:.2f}x");


    def pan(self, dx: int, dy: int) -> None:
        if self.scaled is None:
            return;
        self.pan_x += dx;
        self.pan_y += dy;
        self.scaled_rect.x += dx;
        self.scaled_rect.y += dy;
        self.clamp_scaled_rect();


    def request_trash(self) -> None:
        if self.current_image_path is None:
            self.set_status("No hay imagen seleccionada");
            return;
        self.confirm_trash = True;


    def do_trash(self) -> None:
        if self.current_image_path is None:
            self.confirm_trash = False;
            return;

        victim = self.current_image_path;
        try:
            target = move_to_local_trash(victim);
        except Exception as exc:
            self.set_status(f"Trash falló: {exc}", 5000);
            self.confirm_trash = False;
            return;

        self.confirm_trash = False;
        self.current_image_path = None;
        self.original = None;
        self.scaled = None;
        self.reload_directory(preserve=None);
        self.preview_selected();
        self.set_status(
            f"Movida a {target}",
            4500,
        );


    def row_index_at(self, pos: Tuple[int, int]) -> Optional[int]:
        x, y = pos;
        rect = self.list_rect();
        if not rect.collidepoint(x, y):
            return None;

        top = 42;
        if y < top:
            return None;

        row = (y - top) // self.row_height();
        idx = self.scroll_top + row;
        if idx < 0 or idx >= len(self.entries):
            return None;
        return idx;


    def draw_list(self) -> None:
        rect = self.list_rect();
        pygame.draw.rect(self.screen, COL_PANEL, rect);

        title_font = self.font(16, bold=True);
        title = title_font.render(str(self.current_dir), True, COL_TEXT);
        clip = self.screen.get_clip();
        self.screen.set_clip(rect);
        self.screen.blit(title, (10, 10));
        self.screen.set_clip(clip);

        font = self.font(18);
        row_h = self.row_height();
        y = 42;
        rows = self.visible_rows();

        current_resolved = absolute_path(self.current_image_path) if self.current_image_path else None;

        for visual_row in range(rows):
            idx = self.scroll_top + visual_row;
            if idx >= len(self.entries):
                break;

            entry = self.entries[idx];
            row_rect = pygame.Rect(0, y, rect.width, row_h);

            if idx == self.selected:
                pygame.draw.rect(self.screen, COL_SELECT, row_rect);
            elif (
                entry.kind == "image" and
                current_resolved is not None and
                absolute_path(entry.path) == current_resolved
            ):
                pygame.draw.rect(self.screen, COL_CURRENT, row_rect);

            if entry.kind in ("dir", "up"):
                prefix = "[DIR] ";
                color = COL_ACCENT if idx == self.selected else COL_TEXT;
            else:
                prefix = "      ";
                color = COL_TEXT;

            text = font.render(prefix + entry.label, True, color);
            self.screen.set_clip(row_rect);
            self.screen.blit(text, (9, y + ROW_PAD_Y));
            self.screen.set_clip(clip);
            y += row_h;

        pygame.draw.line(
            self.screen,
            COL_BORDER,
            (rect.right, 0),
            (rect.right, self.screen.get_height()),
            1,
        );

        if self.focus == FOCUS_LIST:
            pygame.draw.rect(self.screen, COL_ACCENT, rect, 2);


    def draw_image(self) -> None:
        area = self.content_rect();
        pygame.draw.rect(self.screen, COL_BG, area);

        if self.scaled is not None:
            old_clip = self.screen.get_clip();
            self.screen.set_clip(area);
            self.screen.blit(self.scaled, self.scaled_rect);
            self.screen.set_clip(old_clip);
        else:
            font = self.font(22);
            msg = font.render("Seleccione una imagen", True, COL_MUTED);
            r = msg.get_rect(center=area.center);
            self.screen.blit(msg, r);

        if self.focus == FOCUS_VIEW:
            pygame.draw.rect(self.screen, COL_ACCENT, area, 2);


    def button(self, x: int, y: int, w: int, h: int, label: str, action: str, danger: bool = False) -> int:
        rect = pygame.Rect(x, y, w, h);
        mouse = pygame.mouse.get_pos();
        col = COL_DANGER if danger else (COL_BUTTON_HOVER if rect.collidepoint(mouse) else COL_BUTTON);
        pygame.draw.rect(self.screen, col, rect);
        pygame.draw.rect(self.screen, COL_BORDER, rect, 1);
        font = self.font(15, bold=True);
        txt = font.render(label, True, COL_TEXT);
        self.screen.blit(txt, txt.get_rect(center=rect.center));
        self.buttons.append((rect, action, label));
        return x + w + 6;


    def draw_toolbar(self) -> None:
        self.buttons = [];
        lw = self.list_width();
        y = self.screen.get_height() - STATUS_H - TOOLBAR_H;
        rect = pygame.Rect(lw + 1, y, self.screen.get_width() - lw - 1, TOOLBAR_H);
        pygame.draw.rect(self.screen, COL_PANEL_ALT, rect);

        x = rect.left + 8;
        h = TOOLBAR_H - 12;
        yb = y + 6;

        x = self.button(x, yb, 78, h, "< Prev", "prev");
        x = self.button(x, yb, 78, h, "Next >", "next");
        x = self.button(x, yb, 84, h, "Play" if not self.slideshow else "Pause", "play");
        x = self.button(
            x,
            yb,
            92,
            h,
            "Random" if self.order_mode == ORDER_RANDOM else "Seq",
            "order",
        );
        x = self.button(x, yb, 54, h, "-t", "interval_down");
        x = self.button(x, yb, 54, h, "+t", "interval_up");
        x = self.button(x, yb, 62, h, "Fit", "fit");
        x = self.button(x, yb, 78, h, "Trash", "trash", danger=True);


    def draw_status(self) -> None:
        y = self.screen.get_height() - STATUS_H;
        rect = pygame.Rect(0, y, self.screen.get_width(), STATUS_H);
        pygame.draw.rect(self.screen, COL_PANEL, rect);

        font = self.font(15);
        now = pygame.time.get_ticks();

        if self.status and now < self.status_until:
            left_text = self.status;
        else:
            left_text = (
                f"{len(self.image_paths)} imágenes | "
                f"{self.order_mode} | "
                f"{self.interval_ms / 1000:.2f}s | "
                f"foco={self.focus} | repeat={self.repeat_delay_ms}ms/{self.repeat_rate_cps:.0f}cps"
            );

        right_text = (
            "j/k ↑/↓ lista  Enter abrir  Tab foco  Space siguiente  b anterior  "
            "s slideshow  r seq/random  z fit  Ctrl-D trash  q salir"
        );

        left = font.render(left_text, True, COL_TEXT);
        right = font.render(right_text, True, COL_MUTED);

        self.screen.blit(left, (10, y + 5));
        self.screen.set_clip(rect);
        self.screen.blit(right, (10, y + 23));
        self.screen.set_clip(None);


    def draw_confirm(self) -> None:
        if not self.confirm_trash:
            return;

        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA);
        overlay.fill((0, 0, 0, 150));
        self.screen.blit(overlay, (0, 0));

        w = min(680, self.screen.get_width() - 40);
        h = 170;
        box = pygame.Rect(0, 0, w, h);
        box.center = self.screen.get_rect().center;
        pygame.draw.rect(self.screen, COL_PANEL_ALT, box);
        pygame.draw.rect(self.screen, COL_DANGER, box, 2);

        font = self.font(18, bold=True);
        small = self.font(15);
        name = self.current_image_path.name if self.current_image_path else "";
        self.screen.blit(font.render("Mover a .Trash local ?", True, COL_TEXT), (box.x + 20, box.y + 20));
        self.screen.blit(small.render(name, True, COL_MUTED), (box.x + 20, box.y + 55));
        self.screen.blit(small.render("Y / Enter = sí     N / Esc = cancelar", True, COL_TEXT), (box.x + 20, box.y + 95));


    def draw(self) -> None:
        self.screen.fill(COL_BG);
        self.draw_list();
        self.draw_image();
        self.draw_toolbar();
        self.draw_status();
        self.draw_confirm();
        pygame.display.flip();


    def handle_button_action(self, action: str) -> None:
        if action == "prev":
            self.next_image(-1);
        elif action == "next":
            self.next_image(1);
        elif action == "play":
            self.toggle_slideshow();
        elif action == "order":
            self.toggle_order();
        elif action == "interval_down":
            self.change_interval(-1);
        elif action == "interval_up":
            self.change_interval(1);
        elif action == "fit":
            self.toggle_fit();
        elif action == "trash":
            self.request_trash();


    def handle_key(self, event: pygame.event.Event) -> bool:
        key = event.key;
        mods = event.mod;

        if self.confirm_trash:
            if key in (pygame.K_y, pygame.K_RETURN, pygame.K_KP_ENTER):
                self.do_trash();
            elif key in (pygame.K_n, pygame.K_ESCAPE):
                self.confirm_trash = False;
            return True;

        if key == pygame.K_q:
            return False;

        if key == pygame.K_F11 or (key == pygame.K_RETURN and (mods & pygame.KMOD_ALT)):
            if self.fullscreen:
                self.fullscreen = False;
                self.screen = pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE);
            else:
                self.windowed_size = self.screen.get_size();
                self.fullscreen = True;
                self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN);
            self.rebuild_scaled();
            return True;

        if (mods & pygame.KMOD_CTRL) and key == pygame.K_r:
            self.refresh();
            return True;

        if (mods & pygame.KMOD_CTRL) and key == pygame.K_d:
            self.request_trash();
            return True;

        if key in (pygame.K_TAB, pygame.K_ESCAPE):
            self.focus = FOCUS_VIEW if self.focus == FOCUS_LIST else FOCUS_LIST;
            return True;

        if key == pygame.K_s:
            self.toggle_slideshow();
            return True;

        if key == pygame.K_r:
            self.toggle_order();
            return True;

        if key == pygame.K_LEFTBRACKET:
            self.change_interval(-1);
            return True;

        if key == pygame.K_RIGHTBRACKET:
            self.change_interval(1);
            return True;

        if key == pygame.K_z:
            self.toggle_fit();
            return True;

        if key in (pygame.K_PLUS, pygame.K_KP_PLUS, pygame.K_EQUALS):
            self.zoom(ZOOM_STEP);
            return True;

        if key in (pygame.K_MINUS, pygame.K_KP_MINUS):
            self.zoom(-ZOOM_STEP);
            return True;

        if self.focus == FOCUS_LIST:
            rows = self.visible_rows();

            if key in (pygame.K_UP, pygame.K_k):
                self.move_selection(-1);
            elif key in (pygame.K_DOWN, pygame.K_j):
                self.move_selection(1);
            elif key == pygame.K_PAGEUP or ((mods & pygame.KMOD_CTRL) and key == pygame.K_u):
                self.move_selection(-rows);
            elif key == pygame.K_PAGEDOWN or ((mods & pygame.KMOD_CTRL) and key == pygame.K_v):
                self.move_selection(rows);
            elif key == pygame.K_HOME or ((mods & pygame.KMOD_CTRL) and key == pygame.K_a):
                self.select_first();
            elif key == pygame.K_END or ((mods & pygame.KMOD_CTRL) and key == pygame.K_e):
                self.select_last();
            elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.activate_selected();
            elif key == pygame.K_BACKSPACE:
                self.go_up();
            elif key == pygame.K_SPACE:
                self.next_image(1);
            elif key == pygame.K_b:
                self.next_image(-1);

        else:
            if key == pygame.K_SPACE:
                self.next_image(1);
            elif key == pygame.K_b:
                self.next_image(-1);
            elif key in (pygame.K_LEFT, pygame.K_h):
                self.pan(PAN_STEP, 0);
            elif key in (pygame.K_RIGHT, pygame.K_l):
                self.pan(-PAN_STEP, 0);
            elif key in (pygame.K_UP, pygame.K_k):
                self.pan(0, PAN_STEP);
            elif key in (pygame.K_DOWN, pygame.K_j):
                self.pan(0, -PAN_STEP);
            elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.focus = FOCUS_LIST;

        return True;


    def key_is_repeatable(self, key: int, mods: int) -> bool:
        if key in (pygame.K_LEFTBRACKET, pygame.K_RIGHTBRACKET):
            return True;
        if key in (pygame.K_PLUS, pygame.K_KP_PLUS, pygame.K_EQUALS, pygame.K_MINUS, pygame.K_KP_MINUS):
            return True;

        if self.focus == FOCUS_LIST:
            if key in (
                pygame.K_UP, pygame.K_DOWN, pygame.K_j, pygame.K_k,
                pygame.K_PAGEUP, pygame.K_PAGEDOWN, pygame.K_SPACE, pygame.K_b,
            ):
                return True;
            if (mods & pygame.KMOD_CTRL) and key in (pygame.K_u, pygame.K_v):
                return True;
            return False;

        return key in (
            pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN,
            pygame.K_h, pygame.K_j, pygame.K_k, pygame.K_l,
            pygame.K_SPACE, pygame.K_b,
        );


    def start_key_repeat(self, event: pygame.event.Event, now_ms: int) -> None:
        if not self.key_is_repeatable(event.key, event.mod):
            return;
        self.repeat_key = event.key;
        self.repeat_mods = event.mod;
        self.repeat_next_ms = now_ms + self.repeat_delay_ms;


    def stop_key_repeat(self, key: int) -> None:
        if self.repeat_key == key:
            self.repeat_key = None;
            self.repeat_mods = 0;
            self.repeat_next_ms = 0;


    def clear_key_repeat(self) -> None:
        self.repeat_key = None;
        self.repeat_mods = 0;
        self.repeat_next_ms = 0;


    def process_key_repeat(self, now_ms: int) -> bool:
        if self.repeat_key is None or now_ms < self.repeat_next_ms:
            return True;

        event = pygame.event.Event(
            pygame.KEYDOWN,
            key=self.repeat_key,
            mod=self.repeat_mods,
        );
        running = self.handle_key(event);
        self.repeat_next_ms = pygame.time.get_ticks() + self.repeat_interval_ms;
        return running;


    def handle_mouse_down(self, event: pygame.event.Event) -> None:
        if self.confirm_trash:
            return;

        if event.button == 1:
            now = pygame.time.get_ticks();

            for rect, action, _ in self.buttons:
                if rect.collidepoint(event.pos):
                    self.handle_button_action(action);
                    return;

            idx = self.row_index_at(event.pos);
            if idx is not None:
                self.focus = FOCUS_LIST;
                self.selected = idx;
                self.ensure_selected_visible();
                self.preview_selected();

                if idx == self.last_click_index and (now - self.last_click_ms) <= DOUBLE_CLICK_MS:
                    self.activate_selected();

                self.last_click_index = idx;
                self.last_click_ms = now;
                return;

            area = self.content_rect();
            if area.collidepoint(event.pos):
                self.focus = FOCUS_VIEW;
                x, y = event.pos;
                left_zone = area.left + int(area.width * 0.18);
                right_zone = area.right - int(area.width * 0.18);
                top_zone = area.top + int(area.height * 0.14);

                if y <= top_zone:
                    self.toggle_slideshow();
                elif x <= left_zone:
                    self.next_image(-1);
                elif x >= right_zone:
                    self.next_image(1);

        elif event.button == 3:
            self.request_trash();

        elif event.button == 4:
            if self.list_rect().collidepoint(event.pos):
                self.move_selection(-3);
            else:
                self.zoom(ZOOM_STEP);

        elif event.button == 5:
            if self.list_rect().collidepoint(event.pos):
                self.move_selection(3);
            else:
                self.zoom(-ZOOM_STEP);


    def handle_mouse_wheel(self, event: pygame.event.Event) -> None:
        pos = pygame.mouse.get_pos();
        if self.list_rect().collidepoint(pos):
            self.move_selection(-event.y * 3);
        elif self.content_rect().collidepoint(pos):
            self.zoom(ZOOM_STEP if event.y > 0 else -ZOOM_STEP);


    def handle_finger_down(self, event: pygame.event.Event) -> None:
        if self.confirm_trash:
            return;
        if self.touch_id is not None:
            return;

        sx, sy = self.screen.get_size();
        self.touch_id = event.touch_id;
        self.touch_down_ms = pygame.time.get_ticks();
        self.touch_down_pos = (event.x * sx, event.y * sy);
        self.touch_last_pos = self.touch_down_pos;
        self.touch_dragging = False;
        self.touch_longpress_handled = False;


    def handle_finger_motion(self, event: pygame.event.Event) -> None:
        if event.touch_id != self.touch_id:
            return;

        sx, sy = self.screen.get_size();
        pos = (event.x * sx, event.y * sy);
        dx = pos[0] - self.touch_last_pos[0];
        dy = pos[1] - self.touch_last_pos[1];
        self.touch_last_pos = pos;

        total_dx = pos[0] - self.touch_down_pos[0];
        total_dy = pos[1] - self.touch_down_pos[1];
        dist = math.hypot(total_dx, total_dy);

        if dist > TOUCH_TAP_TOLERANCE_PX:
            self.touch_dragging = True;

        if self.touch_dragging:
            if self.list_rect().collidepoint(int(pos[0]), int(pos[1])):
                if abs(dy) > 4:
                    self.move_selection(-1 if dy > 0 else 1);
            elif self.content_rect().collidepoint(int(pos[0]), int(pos[1])):
                self.pan(int(dx), int(dy));


    def handle_finger_up(self, event: pygame.event.Event) -> None:
        if event.touch_id != self.touch_id:
            return;

        sx, sy = self.screen.get_size();
        pos = (event.x * sx, event.y * sy);
        now = pygame.time.get_ticks();
        dt = now - self.touch_down_ms;
        dist = math.hypot(
            pos[0] - self.touch_down_pos[0],
            pos[1] - self.touch_down_pos[1],
        );

        if not self.touch_dragging and dist <= TOUCH_TAP_TOLERANCE_PX:
            if dt >= TOUCH_LONGPRESS_MS:
                self.request_trash();
            else:
                fake = type("Fake", (), {"button": 1, "pos": (int(pos[0]), int(pos[1]))});
                self.handle_mouse_down(fake);

        self.touch_id = None;
        self.touch_dragging = False;
        self.touch_longpress_handled = False;


    def run(self) -> int:
        running = True;

        while running:
            now = pygame.time.get_ticks();

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False;
                elif event.type == pygame.KEYDOWN:
                    running = self.handle_key(event);
                    if running:
                        self.start_key_repeat(event, now);
                elif event.type == pygame.KEYUP:
                    self.stop_key_repeat(event.key);
                elif (
                    hasattr(pygame, "WINDOWFOCUSLOST") and
                    event.type == pygame.WINDOWFOCUSLOST
                ):
                    self.clear_key_repeat();
                elif event.type == pygame.VIDEORESIZE and not self.fullscreen:
                    self.windowed_size = event.size;
                    self.screen = pygame.display.set_mode(event.size, pygame.RESIZABLE);
                    self.rebuild_scaled();
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self.handle_mouse_down(event);
                elif event.type == pygame.MOUSEWHEEL:
                    self.handle_mouse_wheel(event);
                elif event.type == pygame.FINGERDOWN:
                    self.handle_finger_down(event);
                elif event.type == pygame.FINGERMOTION:
                    self.handle_finger_motion(event);
                elif event.type == pygame.FINGERUP:
                    self.handle_finger_up(event);

            if running:
                running = self.process_key_repeat(now);

            if (
                self.slideshow and
                self.image_paths and
                now - self.last_switch_ms >= self.interval_ms
            ):
                self.slideshow_advance();
                self.last_switch_ms = now;

            self.draw();
            self.clock.tick(FPS);

        pygame.quit();
        return 0;


def self_test() -> int:
    with tempfile_project() as root:
        photos = root / "photos";
        sub = photos / "sub";
        photos.mkdir();
        sub.mkdir();

        image = photos / "image.jpg";
        image.write_bytes(b"not-a-real-image-but-fine-for-file-tests");
        target_file = sub / "target.jpg";
        target_file.write_bytes(b"target");
        link = photos / "link.jpg";
        link.symlink_to(target_file);

        created = ensure_media_markers(photos);
        assert created >= 4;
        assert (photos / ".nomedia").exists();
        assert (photos / ".no-media").exists();
        assert (sub / ".nomedia").exists();
        assert (sub / ".no-media").exists();

        moved = move_to_local_trash(image);
        assert moved.exists();
        assert not image.exists();
        assert moved.parent.parent == photos / ".Trash";

        moved_link = move_to_local_trash(link);
        assert moved_link.is_symlink();
        assert target_file.exists();
        assert not link.exists();

        assert fit_window_to_desktop((1280, 800), (1920, 1080)) == (1280, 800);
        assert fit_window_to_desktop((1280, 800), (1280, 800)) == (1248, 720);
        assert KEY_REPEAT_DELAY_MS == 500;
        assert KEY_REPEAT_RATE_CPS == 32.0;
        assert KEY_REPEAT_INTERVAL_MS == 31;

    print("imgviewer self-test: OK");
    return 0;


class tempfile_project:
    def __enter__(self) -> Path:
        import tempfile;
        self._tmp = tempfile.TemporaryDirectory();
        return Path(self._tmp.name);

    def __exit__(self, exc_type, exc, tb) -> None:
        self._tmp.cleanup();


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Visualizador de imágenes pygame de propósito general inspirado en xzgv: "
            "lista de archivos a la izquierda y una sola imagen a la derecha, sin miniaturas."
        )
    );
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Directorio o imagen inicial (por defecto: directorio actual).",
    );
    parser.add_argument(
        "--fullscreen",
        action="store_true",
        help="Iniciar en pantalla completa.",
    );
    parser.add_argument(
        "--interval",
        type=float,
        default=DEFAULT_INTERVAL_MS / 1000.0,
        help="Intervalo inicial del slideshow en segundos (mínimo 0.10).",
    );
    parser.add_argument(
        "--random",
        action="store_true",
        help="Usar orden random de slideshow inicialmente.",
    );
    parser.add_argument(
        "--repeat-delay",
        type=int,
        default=KEY_REPEAT_DELAY_MS,
        help="Retardo inicial de repetición de tecla en ms (por defecto: 500).",
    );
    parser.add_argument(
        "--repeat-rate",
        type=float,
        default=KEY_REPEAT_RATE_CPS,
        help="Velocidad de repetición en caracteres/segundo (por defecto: 32).",
    );
    parser.add_argument(
        "--media-markers",
        action="store_true",
        help="Crear .nomedia y .no-media recursivamente bajo la ruta inicial antes de abrir.",
    );
    parser.add_argument(
        "--markers-only",
        action="store_true",
        help="Crear .nomedia y .no-media recursivamente bajo la ruta inicial y salir.",
    );
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Ejecutar pruebas rápidas sin abrir la GUI.",
    );
    parser.add_argument(
        "--version",
        action="store_true",
        help="Mostrar versión y salir.",
    );
    return parser.parse_args();


def main() -> int:
    args = parse_args();

    if args.version:
        print(f"{APP_NAME} {VERSION}");
        return 0;

    if args.self_test:
        return self_test();

    start = normalize_path(args.path);
    if not start.exists():
        print(f"ERROR: no existe: {start}", file=sys.stderr);
        return 2;

    if args.media_markers or args.markers_only:
        created = ensure_media_markers(start);
        if args.markers_only:
            print(f"Media markers created: {created}");
            return 0;

    load_pygame();
    interval_ms = int(max(0.10, min(60.0, args.interval)) * 1000);
    viewer = Viewer(
        start=start,
        fullscreen=args.fullscreen,
        interval_ms=interval_ms,
        random_order=args.random,
        repeat_delay_ms=args.repeat_delay,
        repeat_rate_cps=args.repeat_rate,
    );
    return viewer.run();


if __name__ == "__main__":
    raise SystemExit(main());
