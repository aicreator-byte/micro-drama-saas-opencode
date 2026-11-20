"""Perakitan video berbasis FFmpeg dari klip yang SUDAH ADA (output Flow).

TIDAK generate video — hanya concat klip lokal + scale/pad vertikal
1080x1920 + burn subtitle (bila ada) + audio AAC (bila ada).
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from app.services.storage import resolve_storage_root

FFMPEG_TIMEOUT_SECONDS = 600
_DURATION_RE = re.compile(r"Duration:\s*(\d+):(\d+):([\d.]+)")


def _escape_concat_path(path: Path) -> str:
    # concat demuxer: file '...' — escape petik tunggal gaya shell ffmpeg
    return str(path).replace("'", "'\\''")


def _escape_filter_path(path: Path) -> str:
    # di dalam filter subtitles='...': escape \ : ' dan "
    s = str(path).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
    return s


def validate_inputs_within_storage(input_paths: list[Path | str],
                                   storage_root: Optional[Path] = None) -> list[Path]:
    """Validasi: semua input harus ada + berada di dalam direktori storage.

    Tolak path traversal / absolut di luar storage. Kembalikan path absolut.
    """
    root = (storage_root or resolve_storage_root()).resolve()
    resolved: list[Path] = []
    for raw in input_paths:
        p = Path(raw)
        abs_p = p.resolve() if p.is_absolute() else (root / p).resolve()
        if not abs_p.is_relative_to(root):
            raise ValueError(f"input path escapes storage directory: {raw!r}")
        if not abs_p.is_file():
            raise FileNotFoundError(f"input file not found: {raw!r}")
        resolved.append(abs_p)
    return resolved


def get_duration_seconds(path: Path | str) -> Optional[float]:
    """Durasi via ffprobe; None bila ffprobe tidak ada/gagal."""
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return None
    try:
        result = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(path)],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
    except (subprocess.TimeoutExpired, ValueError, OSError):
        return None
    return None


def _duration_from_ffmpeg_stderr(stderr: str) -> Optional[float]:
    m = _DURATION_RE.search(stderr)
    if not m:
        return None
    h, mnt, sec = int(m.group(1)), int(m.group(2)), float(m.group(3))
    return h * 3600 + mnt * 60 + sec


def assemble_video(input_paths: list[Path | str], output_path: Path | str,
                   subtitle_path: Optional[Path | str] = None,
                   audio_path: Optional[Path | str] = None,
                   resolution: str = "1080x1920",
                   storage_root: Optional[Path] = None,
                   timeout_seconds: int = FFMPEG_TIMEOUT_SECONDS) -> float:
    """Rakit klip jadi satu mp4 vertikal. Kembalikan durasi (detik).

    Raises: FileNotFoundError / ValueError (input tidak valid),
    RuntimeError (ffmpeg gagal / ffmpeg tidak ditemukan).
    """
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg not found in PATH")

    inputs = validate_inputs_within_storage(input_paths, storage_root)
    if not inputs:
        raise ValueError("at least one input file is required")

    root = (storage_root or resolve_storage_root()).resolve()
    out = Path(output_path)
    out = out.resolve() if out.is_absolute() else (root / out).resolve()
    if not out.is_relative_to(root):
        raise ValueError(f"output path escapes storage directory: {output_path!r}")
    out.parent.mkdir(parents=True, exist_ok=True)

    subtitle: Optional[Path] = None
    if subtitle_path is not None:
        subtitle = validate_inputs_within_storage([subtitle_path], storage_root)[0]
    audio: Optional[Path] = None
    if audio_path is not None:
        audio = validate_inputs_within_storage([audio_path], storage_root)[0]

    try:
        width, height = (int(x) for x in resolution.lower().split("x"))
    except ValueError:
        raise ValueError(f"invalid resolution: {resolution!r}")

    vf = (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,format=yuv420p"
    )
    if subtitle is not None:
        vf += f",subtitles='{_escape_filter_path(subtitle)}'"

    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                    dir=str(root), encoding="utf-8") as list_file:
        for p in inputs:
            list_file.write(f"file '{_escape_concat_path(p)}'\n")
        list_path = list_file.name

    try:
        cmd = [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", list_path]
        if audio is not None:
            cmd += ["-i", str(audio)]
        cmd += ["-vf", vf]
        if audio is not None:
            cmd += ["-map", "0:v:0", "-map", "1:a:0", "-c:a", "aac", "-shortest"]
        else:
            cmd += ["-an"]
        cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-movflags", "+faststart", str(out)]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True,
                                    timeout=timeout_seconds)
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(f"ffmpeg timed out after {timeout_seconds}s: {e}")
        if result.returncode != 0:
            raise RuntimeError(
                "ffmpeg failed (exit %d): %s" % (result.returncode, result.stderr[-2000:])
            )
        duration = get_duration_seconds(out)
        if duration is None:
            duration = _duration_from_ffmpeg_stderr(result.stderr or "")
        if duration is None:
            raise RuntimeError("could not determine output duration")
        return duration
    finally:
        try:
            Path(list_path).unlink(missing_ok=True)
        except OSError:
            pass
