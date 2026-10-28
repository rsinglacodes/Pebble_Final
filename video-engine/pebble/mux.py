"""ffprobe helpers plus per-scene muxing and the final concat stitch."""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

from pebble.errors import MuxError

logger = logging.getLogger(__name__)

# Extra seconds of picture after the narration ends, so a scene never cuts off
# on the last syllable.
HOLD = 0.35

EPSILON = 0.01
TAIL_LINES = 40

# A scene whose picture runs this far past its narration is a pacing defect.
OVERRUN_WARNING = 2.0


@dataclass(frozen=True)
class MediaInfo:
    duration: float
    has_video: bool
    has_audio: bool
    fps: float | None = None
    video_codec: str | None = None
    audio_codec: str | None = None
    sample_rate: int | None = None
    pix_fmt: str | None = None


def _parse_fps(raw: str | None) -> float | None:
    if not raw or "/" not in raw:
        return None
    num, _, den = raw.partition("/")
    try:
        numerator, denominator = float(num), float(den)
    except ValueError:
        return None
    if denominator == 0:
        return None
    return numerator / denominator


def ffprobe_info(path: Path) -> MediaInfo:
    """Probe duration, streams, fps and codecs. Raises MuxError on failure."""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    try:
        completed = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as exc:
        raise MuxError(f"ffprobe failed for {path}: {exc}") from exc

    if completed.returncode != 0:
        raise MuxError(f"ffprobe failed for {path}: {completed.stderr.strip()[-500:]}")

    try:
        payload = json.loads(completed.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise MuxError(f"ffprobe returned invalid JSON for {path}") from exc

    streams = payload.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)

    raw_duration = payload.get("format", {}).get("duration")
    if raw_duration is None:
        raw_duration = (video or audio or {}).get("duration")

    try:
        duration = float(raw_duration)
    except (TypeError, ValueError):
        duration = 0.0

    sample_rate = None
    if audio and audio.get("sample_rate"):
        try:
            sample_rate = int(audio["sample_rate"])
        except (TypeError, ValueError):
            sample_rate = None

    return MediaInfo(
        duration=duration,
        has_video=video is not None,
        has_audio=audio is not None,
        fps=_parse_fps((video or {}).get("r_frame_rate")),
        video_codec=(video or {}).get("codec_name"),
        audio_codec=(audio or {}).get("codec_name"),
        sample_rate=sample_rate,
        pix_fmt=(video or {}).get("pix_fmt"),
    )


def probe_duration(path: Path) -> float:
    return ffprobe_info(path).duration


def _stderr_tail(stderr: str) -> str:
    lines = [line for line in (stderr or "").strip().splitlines() if line.strip()]
    return "\n".join(lines[-TAIL_LINES:])


def _run_ffmpeg(cmd: list[str], label: str) -> None:
    try:
        completed = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    except (OSError, subprocess.SubprocessError) as exc:
        raise MuxError(f"{label} failed to run: {exc}") from exc
    if completed.returncode != 0:
        raise MuxError(f"{label} failed:\n{_stderr_tail(completed.stderr)}")


def mux_scene(video: Path, audio: Path, out: Path, hold: float = HOLD) -> Path:
    """Combine one silent scene video with its narration.

    The shorter stream is padded so picture and speech end together; the picture
    lingers `hold` seconds past the end of the narration.
    """
    video_info = ffprobe_info(video)
    audio_info = ffprobe_info(audio)
    if not video_info.has_video:
        raise MuxError(f"{video} has no video stream")
    if not audio_info.has_audio:
        raise MuxError(f"{audio} has no audio stream")

    video_duration = video_info.duration
    audio_duration = audio_info.duration
    target_audio = audio_duration + hold

    if video_duration > target_audio + OVERRUN_WARNING:
        logger.warning(
            "%s is %.1fs longer than its narration + hold (%.1fs vs %.1fs): "
            "the animation overruns its narration",
            video.name,
            video_duration - target_audio,
            video_duration,
            target_audio,
        )

    if target_audio > video_duration + EPSILON:
        pad = target_audio - video_duration
        video_filter = f"tpad=stop_mode=clone:stop_duration={pad:.3f}"
        audio_filter = "anull"
    elif video_duration > target_audio + EPSILON:
        pad = video_duration - target_audio
        video_filter = "null"
        audio_filter = f"apad=pad_dur={pad:.3f}"
    else:
        video_filter = "null"
        audio_filter = "anull"

    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video),
        "-i",
        str(audio),
        "-filter_complex",
        f"[0:v]{video_filter}[v];[1:a]{audio_filter}[a]",
        "-map",
        "[v]",
        "-map",
        "[a]",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-ar",
        "44100",
        "-ac",
        "2",
        "-movflags",
        "+faststart",
        str(out),
    ]
    _run_ffmpeg(cmd, f"muxing {video.name}")
    return out


def _concat_line(path: Path) -> str:
    # ffmpeg's concat demuxer uses single quotes; a literal quote becomes '\''
    escaped = str(path.resolve()).replace("'", "'\\''")
    return f"file '{escaped}'"


def stitch(muxed: list[Path], out: Path, tolerance: float = 1.0) -> Path:
    """Concatenate the muxed scenes with a stream copy and verify the result."""
    if not muxed:
        raise MuxError("cannot stitch: no muxed scenes")

    durations = [probe_duration(path) for path in muxed]
    expected = sum(durations)

    out.parent.mkdir(parents=True, exist_ok=True)
    list_path = out.with_name(out.name + ".concat.txt")
    list_path.write_text(
        "\n".join(_concat_line(path) for path in muxed) + "\n", encoding="utf-8"
    )

    try:
        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_path),
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            str(out),
        ]
        _run_ffmpeg(cmd, "concatenating scenes")
    finally:
        list_path.unlink(missing_ok=True)

    info = ffprobe_info(out)
    if not info.has_video or not info.has_audio:
        raise MuxError(
            f"{out} is missing a stream (video={info.has_video}, audio={info.has_audio})"
        )
    if abs(info.duration - expected) > tolerance:
        raise MuxError(
            f"{out} duration {info.duration:.2f}s differs from the sum of its scenes "
            f"{expected:.2f}s by more than {tolerance}s"
        )
    return out
