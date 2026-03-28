"""services/title_card.py 단위 테스트"""
from pathlib import Path

from services.title_card import TitleCardGenerator


class TestTitleCardGenerator:
    def test_generate_ass_contains_script_info(self, tmp_path: Path):
        gen = TitleCardGenerator()
        ass_path = gen.generate(
            title="MIDNIGHT ACID",
            artist_name="Eisenherz",
            output_dir=tmp_path,
        )
        content = ass_path.read_text(encoding="utf-8")
        assert "[Script Info]" in content
        assert "PlayResX: 1080" in content
        assert "PlayResY: 1920" in content

    def test_generate_ass_contains_title_dialogue(self, tmp_path: Path):
        gen = TitleCardGenerator()
        ass_path = gen.generate(
            title="DARK TRAP",
            artist_name="Eisenherz",
            output_dir=tmp_path,
        )
        content = ass_path.read_text(encoding="utf-8")
        assert "DARK TRAP" in content
        assert "EISENHERZ" in content
        assert "\u00b7" in content or "·" in content

    def test_generate_ass_contains_fade(self, tmp_path: Path):
        gen = TitleCardGenerator()
        ass_path = gen.generate(
            title="TEST",
            artist_name="Eisenherz",
            output_dir=tmp_path,
            fade_in_ms=800,
            fade_out_ms=800,
        )
        content = ass_path.read_text(encoding="utf-8")
        assert "\\fad(800,800)" in content

    def test_generate_ass_custom_timing(self, tmp_path: Path):
        gen = TitleCardGenerator()
        ass_path = gen.generate(
            title="TEST",
            artist_name="Eisenherz",
            output_dir=tmp_path,
            start_sec=1.0,
            duration_sec=5,
        )
        content = ass_path.read_text(encoding="utf-8")
        assert "0:00:01.00" in content
        assert "0:00:06.00" in content

    def test_generate_ass_uppercase_title(self, tmp_path: Path):
        gen = TitleCardGenerator()
        ass_path = gen.generate(
            title="midnight acid",
            artist_name="eisenherz",
            output_dir=tmp_path,
        )
        content = ass_path.read_text(encoding="utf-8")
        assert "MIDNIGHT ACID" in content
        assert "EISENHERZ" in content

    def test_generate_ass_underline_drawing(self, tmp_path: Path):
        gen = TitleCardGenerator()
        ass_path = gen.generate(
            title="TEST",
            artist_name="Eisenherz",
            output_dir=tmp_path,
        )
        content = ass_path.read_text(encoding="utf-8")
        assert "\\p1" in content
        assert "0:00:00.80" in content

    def test_generate_ass_output_filename(self, tmp_path: Path):
        gen = TitleCardGenerator()
        ass_path = gen.generate(
            title="TEST",
            artist_name="Eisenherz",
            output_dir=tmp_path,
        )
        assert ass_path.name == "title_card.ass"
        assert ass_path.parent == tmp_path

    def test_format_ass_time(self):
        gen = TitleCardGenerator()
        assert gen._format_ass_time(0.0) == "0:00:00.00"
        assert gen._format_ass_time(0.5) == "0:00:00.50"
        assert gen._format_ass_time(65.3) == "0:01:05.30"
        assert gen._format_ass_time(3661.5) == "1:01:01.50"
