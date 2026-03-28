"""composer 타이틀 카드 통합 테스트 (FFmpeg 없이 ASS 생성만 검증)"""
from pathlib import Path
from unittest.mock import patch, MagicMock

from services.composer import ShortsComposer


class TestComposerTitleCard:
    def test_add_title_card_generates_ass(self, tmp_path: Path):
        """타이틀 카드 ASS 파일이 생성되는지 확인"""
        composer = ShortsComposer()

        video_path = tmp_path / "input.mp4"
        video_path.write_bytes(b"fake")
        output_path = tmp_path / "output.mp4"
        fonts_dir = tmp_path / "fonts"
        fonts_dir.mkdir()

        title_card_config = {
            "enabled": True,
            "artist_name": "Eisenherz",
            "fade_in_ms": 800,
            "fade_out_ms": 800,
            "duration_sec": 4,
            "start_sec": 0.5,
        }

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr="")
            composer.add_title_card(
                video_path=video_path,
                output_path=output_path,
                title="Midnight Acid",
                title_card_config=title_card_config,
                fonts_dir=fonts_dir,
            )

        ass_files = list(tmp_path.glob("*.ass"))
        assert len(ass_files) == 1
        content = ass_files[0].read_text(encoding="utf-8")
        assert "MIDNIGHT ACID" in content
        assert "EISENHERZ" in content

    def test_add_title_card_ffmpeg_command(self, tmp_path: Path):
        """FFmpeg 명령에 ass 필터와 fontsdir가 포함되는지 확인"""
        composer = ShortsComposer()

        video_path = tmp_path / "input.mp4"
        video_path.write_bytes(b"fake")
        output_path = tmp_path / "output.mp4"
        fonts_dir = tmp_path / "fonts"
        fonts_dir.mkdir()

        title_card_config = {
            "enabled": True,
            "artist_name": "Eisenherz",
            "fade_in_ms": 800,
            "fade_out_ms": 800,
            "duration_sec": 4,
            "start_sec": 0.5,
        }

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr="")
            composer.add_title_card(
                video_path=video_path,
                output_path=output_path,
                title="Test Song",
                title_card_config=title_card_config,
                fonts_dir=fonts_dir,
            )

        cmd = mock_run.call_args[0][0]
        cmd_str = " ".join(cmd)
        assert "ass=" in cmd_str
        assert "fontsdir=" in cmd_str

    def test_add_title_card_disabled_skips(self, tmp_path: Path):
        """title_card.enabled=False면 스킵"""
        composer = ShortsComposer()

        video_path = tmp_path / "input.mp4"
        video_path.write_bytes(b"fake")
        output_path = tmp_path / "output.mp4"

        title_card_config = {"enabled": False}

        with patch("subprocess.run") as mock_run:
            result = composer.add_title_card(
                video_path=video_path,
                output_path=output_path,
                title="Test",
                title_card_config=title_card_config,
                fonts_dir=tmp_path,
            )

        mock_run.assert_not_called()
        assert result == video_path
