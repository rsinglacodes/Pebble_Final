"""Muxing and stitching with real ffmpeg clips."""

from __future__ import annotations

import pytest

from pebble.errors import MuxError
from pebble.mux import HOLD, ffprobe_info, mux_scene, stitch
from tests.conftest import make_color_video, make_sine_wav


def test_audio_longer_than_video_extends_the_picture(tmp_path):
    video = make_color_video(tmp_path / "v.mp4", 1.0)
    audio = make_sine_wav(tmp_path / "a.wav", 1.6)
    out = mux_scene(video, audio, tmp_path / "muxed.mp4")

    info = ffprobe_info(out)
    assert info.has_video and info.has_audio
    expected = 1.6 + HOLD
    assert abs(info.duration - expected) < 0.15

    video_info = ffprobe_info(out)
    assert video_info.video_codec == "h264"
    assert video_info.audio_codec == "aac"
    assert video_info.sample_rate == 44100
    assert video_info.fps is not None and video_info.fps > 0


def test_video_longer_than_audio_pads_the_sound(tmp_path):
    video = make_color_video(tmp_path / "v.mp4", 2.5)
    audio = make_sine_wav(tmp_path / "a.wav", 0.8)
    out = mux_scene(video, audio, tmp_path / "muxed.mp4")

    info = ffprobe_info(out)
    assert info.has_video and info.has_audio
    # picture is already longer than narration + hold, so the duration is unchanged
    assert abs(info.duration - 2.5) < 0.15


def test_mux_rejects_missing_streams(tmp_path):
    video = make_color_video(tmp_path / "v.mp4", 0.5)
    silent = make_color_video(tmp_path / "silent.mp4", 0.5)
    with pytest.raises(MuxError):
        mux_scene(video, silent, tmp_path / "out.mp4")


def test_stitch_concatenates_three_clips(tmp_path):
    muxed = []
    expected = 0.0
    for index, (video_len, audio_len) in enumerate(
        [(1.0, 0.8), (1.2, 1.4), (1.0, 0.6)], start=1
    ):
        video = make_color_video(tmp_path / f"v{index}.mp4", video_len)
        audio = make_sine_wav(tmp_path / f"a{index}.wav", audio_len)
        out = mux_scene(video, audio, tmp_path / f"muxed{index}.mp4")
        muxed.append(out)
        expected += ffprobe_info(out).duration

    final = stitch(muxed, tmp_path / "final.mp4")
    info = ffprobe_info(final)
    assert info.has_video and info.has_audio
    assert abs(info.duration - expected) < 1.0
    assert not (tmp_path / "final.mp4.concat.txt").exists()


def test_stitch_rejects_empty_list(tmp_path):
    with pytest.raises(MuxError):
        stitch([], tmp_path / "final.mp4")
