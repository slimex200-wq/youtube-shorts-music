import math
from pathlib import Path
from services.composer import ShortsComposer


# --- build_bounce_cmd ---

def test_build_bounce_cmd():
    """정방향+역방향 concat 필터 명령어 생성"""
    composer = ShortsComposer()
    cmd = composer.build_bounce_cmd(
        clip_path=Path("clip.mp4"),
        output_path=Path("bounce.mp4"),
    )
    cmd_str = " ".join(cmd)
    assert "reverse" in cmd_str
    assert "concat=n=2:v=1:a=0" in cmd_str
    assert "-map" in cmd_str


def test_build_bounce_cmd_preserves_quality():
    """바운스 루프에 libx264 인코딩 포함"""
    composer = ShortsComposer()
    cmd = composer.build_bounce_cmd(
        clip_path=Path("clip.mp4"),
        output_path=Path("bounce.mp4"),
    )
    cmd_str = " ".join(cmd)
    assert "libx264" in cmd_str


# --- build_stream_loop_cmd ---

def test_build_stream_loop_cmd():
    """stream_loop으로 N번 반복하는 명령어 생성"""
    composer = ShortsComposer()
    cmd = composer.build_stream_loop_cmd(
        clip_path=Path("bounce.mp4"),
        repeat=30,
        output_path=Path("long.mp4"),
    )
    cmd_str = " ".join(cmd)
    assert "-stream_loop" in cmd_str
    assert "30" in cmd_str
    assert "-c" in cmd_str


def test_build_stream_loop_cmd_default_repeat():
    """기본 반복 횟수 30"""
    composer = ShortsComposer()
    cmd = composer.build_stream_loop_cmd(
        clip_path=Path("bounce.mp4"),
        output_path=Path("long.mp4"),
    )
    cmd_str = " ".join(cmd)
    assert "30" in cmd_str


def test_build_stream_loop_cmd_uses_copy_codec():
    """stream_loop은 재인코딩 없이 copy"""
    composer = ShortsComposer()
    cmd = composer.build_stream_loop_cmd(
        clip_path=Path("bounce.mp4"),
        repeat=10,
        output_path=Path("long.mp4"),
    )
    cmd_str = " ".join(cmd)
    assert "copy" in cmd_str


# --- calc_bounce_repeats ---

def test_calc_bounce_repeats_exact():
    """2초 클립, 바운스 4초, 씬 8초 → 2회"""
    composer = ShortsComposer()
    assert composer.calc_bounce_repeats(clip_duration=2.0, scene_duration=8.0) == 2


def test_calc_bounce_repeats_partial():
    """3초 클립, 바운스 6초, 씬 10초 → ceil(10/6)=2"""
    composer = ShortsComposer()
    assert composer.calc_bounce_repeats(clip_duration=3.0, scene_duration=10.0) == 2


def test_calc_bounce_repeats_short_scene():
    """씬이 바운스 1회보다 짧아도 최소 1회"""
    composer = ShortsComposer()
    assert composer.calc_bounce_repeats(clip_duration=5.0, scene_duration=3.0) == 1


# --- build_scene_cmd with bounce ---

def test_build_scene_cmd_video_bounce():
    """비디오 에셋 + bounce=True → 스케일 + 바운스 filter_complex"""
    composer = ShortsComposer()
    cmd = composer.build_scene_cmd(
        asset_path=Path("scene_01.mp4"),
        duration=5.0,
        output_path=Path("clip_01.mp4"),
        bounce=True,
        asset_duration=2.0,
    )
    cmd_str = " ".join(cmd)
    assert "reverse" in cmd_str
    assert "concat" in cmd_str
    assert "-stream_loop" in cmd_str


def test_build_scene_cmd_image_bounce_ignored():
    """이미지 에셋은 bounce=True여도 zoompan 그대로"""
    composer = ShortsComposer()
    cmd = composer.build_scene_cmd(
        asset_path=Path("scene_01.png"),
        duration=5.0,
        output_path=Path("clip_01.mp4"),
        bounce=True,
    )
    cmd_str = " ".join(cmd)
    assert "zoompan" in cmd_str
    assert "reverse" not in cmd_str


def test_build_scene_cmd_video_no_bounce_unchanged():
    """bounce=False면 기존 동작 그대로"""
    composer = ShortsComposer()
    cmd = composer.build_scene_cmd(
        asset_path=Path("scene_01.mp4"),
        duration=5.0,
        output_path=Path("clip_01.mp4"),
        bounce=False,
    )
    cmd_str = " ".join(cmd)
    assert "reverse" not in cmd_str
    assert "scale=" in cmd_str
