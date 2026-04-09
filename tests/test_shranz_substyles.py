import json
import tempfile
from pathlib import Path

from services.shranz_substyles import (
    SUBSTYLES,
    SUBSTYLE_MAP,
    build_substyle_prompt_section,
    get_used_substyles_from_projects,
    is_shranz_genre,
    pick_substyle,
)


class TestIsShranzGenre:
    def test_shranz_detected(self):
        assert is_shranz_genre("shranz") is True
        assert is_shranz_genre("Shranz") is True
        assert is_shranz_genre("schranz") is True
        assert is_shranz_genre("hard techno") is True
        assert is_shranz_genre("dark shranz") is True
        assert is_shranz_genre("new shrantz") is True

    def test_non_shranz_rejected(self):
        assert is_shranz_genre("lo-fi hip hop") is False
        assert is_shranz_genre("dark trap") is False
        assert is_shranz_genre("ambient") is False
        assert is_shranz_genre("k-pop") is False


class TestPickSubstyle:
    def test_returns_substyle(self):
        result = pick_substyle()
        assert result in SUBSTYLES

    def test_preferred_name(self):
        result = pick_substyle(preferred_name="acid_schranz")
        assert result.name == "acid_schranz"

    def test_preferred_name_unknown_falls_back(self):
        result = pick_substyle(preferred_name="nonexistent_style")
        assert result in SUBSTYLES

    def test_exclude_names(self):
        exclude = [s.name for s in SUBSTYLES[:-1]]
        result = pick_substyle(exclude_names=exclude)
        assert result.name == SUBSTYLES[-1].name

    def test_all_excluded_falls_back_to_full_pool(self):
        exclude = [s.name for s in SUBSTYLES]
        result = pick_substyle(exclude_names=exclude)
        assert result in SUBSTYLES

    def test_preferred_overrides_exclude(self):
        result = pick_substyle(
            exclude_names=["acid_schranz"],
            preferred_name="acid_schranz",
        )
        assert result.name == "acid_schranz"


class TestSubstyleData:
    def test_all_substyles_have_required_fields(self):
        for s in SUBSTYLES:
            assert s.name
            assert s.label
            assert s.bpm_range[0] < s.bpm_range[1]
            assert s.kick_character
            assert s.synths
            assert s.mood
            assert s.weirdness_range[0] <= s.weirdness_range[1]
            assert s.style_influence_range[0] <= s.style_influence_range[1]

    def test_all_names_unique(self):
        names = [s.name for s in SUBSTYLES]
        assert len(names) == len(set(names))

    def test_map_matches_list(self):
        assert len(SUBSTYLE_MAP) == len(SUBSTYLES)
        for s in SUBSTYLES:
            assert SUBSTYLE_MAP[s.name] is s

    def test_at_least_10_substyles(self):
        assert len(SUBSTYLES) >= 10


class TestBuildSubstylePromptSection:
    def test_contains_substyle_label(self):
        substyle = SUBSTYLE_MAP["acid_schranz"]
        section = build_substyle_prompt_section(substyle)
        assert "Acid Schranz" in section

    def test_contains_bpm_range(self):
        substyle = SUBSTYLE_MAP["peak_time"]
        section = build_substyle_prompt_section(substyle)
        assert "155" in section
        assert "168" in section

    def test_contains_important_instruction(self):
        substyle = SUBSTYLE_MAP["classic_german"]
        section = build_substyle_prompt_section(substyle)
        assert "Do NOT fall back" in section


class TestGetUsedSubstylesFromProjects:
    def test_empty_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = get_used_substyles_from_projects(tmp)
            assert result == []

    def test_nonexistent_dir(self):
        result = get_used_substyles_from_projects("/nonexistent/path")
        assert result == []

    def test_reads_substyle_from_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj_dir = Path(tmp) / "shranz-test"
            proj_dir.mkdir()
            data = {
                "suno_prompt": {"substyle": "acid_schranz", "style": "test"},
            }
            (proj_dir / "project.json").write_text(json.dumps(data))

            result = get_used_substyles_from_projects(tmp)
            assert result == ["acid_schranz"]

    def test_skips_projects_without_substyle(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj_dir = Path(tmp) / "shranz-old"
            proj_dir.mkdir()
            data = {"suno_prompt": {"style": "old style without substyle"}}
            (proj_dir / "project.json").write_text(json.dumps(data))

            result = get_used_substyles_from_projects(tmp)
            assert result == []
