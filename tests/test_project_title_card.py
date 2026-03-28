"""Project 모델 title_card 필드 테스트"""
import json
from pathlib import Path

from models.project import Project


def test_project_default_title_card(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("models.project.PROJECTS_DIR", tmp_path)
    project = Project.create(genre="lo-fi", base_dir=tmp_path)
    assert project.config["title_card"]["enabled"] is True
    assert project.config["title_card"]["artist_name"] == "Eisenherz"


def test_project_title_card_persists(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("models.project.PROJECTS_DIR", tmp_path)
    project = Project.create(genre="ambient", base_dir=tmp_path)
    project.config["title_card"]["artist_name"] = "CustomArtist"
    project.save()

    loaded = Project.load(project.id, base_dir=tmp_path)
    assert loaded.config["title_card"]["artist_name"] == "CustomArtist"


def test_project_title_card_custom_values(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("models.project.PROJECTS_DIR", tmp_path)
    project = Project.create(genre="techno", base_dir=tmp_path)
    tc = project.config["title_card"]
    assert tc["fade_in_ms"] == 800
    assert tc["fade_out_ms"] == 800
    assert tc["duration_sec"] == 4
    assert tc["start_sec"] == 0.5
