from pathlib import Path
from services.composer import ShortsComposer


def test_match_assets(tmp_path):
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    (assets_dir / "scene_01.png").write_bytes(b"img")
    (assets_dir / "scene_02.mp4").write_bytes(b"vid")

    scenes = [
        {"id": 1, "asset_file": None},
        {"id": 2, "asset_file": None},
    ]
    composer = ShortsComposer()
    matched, missing = composer.match_assets(scenes, assets_dir)
    assert matched[0]["asset_file"] == "scene_01.png"
    assert matched[1]["asset_file"] == "scene_02.mp4"
    assert missing == []


def test_match_assets_partial(tmp_path):
    """일부 에셋만 있으면 있는 씬만 반환, missing 목록 포함"""
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    (assets_dir / "scene_01.png").write_bytes(b"img")

    scenes = [
        {"id": 1, "asset_file": None},
        {"id": 2, "asset_file": None},
    ]
    composer = ShortsComposer()
    matched, missing = composer.match_assets(scenes, assets_dir)
    assert len(matched) == 1
    assert matched[0]["asset_file"] == "scene_01.png"
    assert missing == ["scene_02"]


def test_match_assets_none_raises(tmp_path):
    """에셋이 하나도 없으면 FileNotFoundError"""
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()

    scenes = [{"id": 1, "asset_file": None}]
    composer = ShortsComposer()
    try:
        composer.match_assets(scenes, assets_dir)
        assert False, "Should raise"
    except FileNotFoundError:
        pass


def test_generate_srt_from_lyrics():
    scenes = [
        {"id": 1, "start_sec": 0.0, "end_sec": 5.0, "lyrics_line": "첫 번째 줄"},
        {"id": 2, "start_sec": 5.0, "end_sec": 10.0, "lyrics_line": "두 번째 줄"},
        {"id": 3, "start_sec": 10.0, "end_sec": 15.0, "lyrics_line": None},
    ]
    composer = ShortsComposer()
    srt = composer.generate_lyrics_srt(scenes)
    assert "첫 번째 줄" in srt
    assert "두 번째 줄" in srt
    assert "00:00:05" in srt
    lines = srt.strip().split("\n\n")
    assert len(lines) == 2


def test_generate_srt_all_none_returns_empty():
    scenes = [
        {"id": 1, "start_sec": 0.0, "end_sec": 5.0, "lyrics_line": None},
    ]
    composer = ShortsComposer()
    srt = composer.generate_lyrics_srt(scenes)
    assert srt == ""


def test_build_scene_cmd_image():
    composer = ShortsComposer()
    cmd = composer.build_scene_cmd(
        asset_path=Path("scene_01.png"),
        duration=5.0,
        output_path=Path("clip_01.mp4"),
    )
    cmd_str = " ".join(cmd)
    assert "1080" in cmd_str
    assert "1920" in cmd_str
    assert "zoompan" in cmd_str


def test_build_scene_cmd_video():
    composer = ShortsComposer()
    cmd = composer.build_scene_cmd(
        asset_path=Path("scene_01.mp4"),
        duration=5.0,
        output_path=Path("clip_01.mp4"),
    )
    cmd_str = " ".join(cmd)
    assert "1080" in cmd_str
    assert "zoompan" not in cmd_str


def test_subtitle_style():
    composer = ShortsComposer()
    style = composer.get_subtitle_style()
    assert "FontSize" in style
    assert "Alignment=10" in style


def test_build_audio_cmd_with_fade_out():
    """fade_out_sec > 0이면 오디오에 afade 필터 + 트리밍 적용"""
    composer = ShortsComposer()
    cmd = composer.build_audio_cmd(
        audio_path=Path("music.mp3"),
        duration=60.0,
        fade_out_sec=2.0,
        output_path=Path("trimmed.aac"),
    )
    cmd_str = " ".join(cmd)
    assert "afade=t=out" in cmd_str
    assert "60" in cmd_str


def test_build_audio_cmd_no_fade():
    """fade_out_sec == 0이면 필터 없이 그대로"""
    composer = ShortsComposer()
    cmd = composer.build_audio_cmd(
        audio_path=Path("music.mp3"),
        duration=40.0,
        fade_out_sec=0.0,
        output_path=Path("trimmed.aac"),
    )
    cmd_str = " ".join(cmd)
    assert "afade" not in cmd_str
