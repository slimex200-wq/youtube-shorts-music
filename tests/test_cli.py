import json
import shutil
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from cli import cli


def test_list_empty(tmp_path, monkeypatch):
    monkeypatch.setattr("cli.PROJECTS_DIR", tmp_path)
    monkeypatch.setattr("models.project.PROJECTS_DIR", tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["list"])
    assert result.exit_code == 0
    assert "프로젝트 없음" in result.output


def test_create_requires_genre(tmp_path, monkeypatch):
    monkeypatch.setattr("cli.PROJECTS_DIR", tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["create"])
    assert result.exit_code != 0 or "Missing" in result.output or "genre" in result.output.lower()


def test_status_not_found(tmp_path, monkeypatch):
    monkeypatch.setattr("cli.PROJECTS_DIR", tmp_path)
    monkeypatch.setattr("models.project.PROJECTS_DIR", tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["status", "nonexistent"])
    assert "찾을 수 없습니다" in result.output


def test_create_with_genre_no_api_key(tmp_path, monkeypatch):
    """ANTHROPIC_API_KEY 없으면 프로젝트만 생성, suno prompt 스킵"""
    monkeypatch.setattr("cli.PROJECTS_DIR", tmp_path)
    monkeypatch.setattr("models.project.PROJECTS_DIR", tmp_path)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    runner = CliRunner()
    result = runner.invoke(cli, ["create", "--genre", "lo-fi hip hop"])
    assert result.exit_code == 0
    assert "프로젝트 생성" in result.output

    dirs = list(tmp_path.iterdir())
    assert len(dirs) == 1
    data = json.loads((dirs[0] / "project.json").read_text(encoding="utf-8"))
    assert data["genre"] == "lo-fi hip hop"


def test_create_instrumental(tmp_path, monkeypatch):
    monkeypatch.setattr("cli.PROJECTS_DIR", tmp_path)
    monkeypatch.setattr("models.project.PROJECTS_DIR", tmp_path)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    runner = CliRunner()
    result = runner.invoke(cli, ["create", "--genre", "ambient", "--instrumental"])
    assert result.exit_code == 0

    dirs = list(tmp_path.iterdir())
    data = json.loads((dirs[0] / "project.json").read_text(encoding="utf-8"))
    assert data["instrumental"] is True


def test_music_project_not_found(tmp_path, monkeypatch):
    monkeypatch.setattr("cli.PROJECTS_DIR", tmp_path)
    monkeypatch.setattr("models.project.PROJECTS_DIR", tmp_path)
    runner = CliRunner()
    # Create a dummy file for --file
    dummy = tmp_path / "track.mp3"
    dummy.write_bytes(b"fake audio")
    result = runner.invoke(cli, ["music", "nonexistent", "--file", str(dummy)])
    assert "찾을 수 없습니다" in result.output


def test_compose_no_music_file(tmp_path, monkeypatch):
    """music 등록 안 한 상태에서 compose 실행"""
    monkeypatch.setattr("cli.PROJECTS_DIR", tmp_path)
    monkeypatch.setattr("models.project.PROJECTS_DIR", tmp_path)

    runner = CliRunner()
    # Create project first
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = runner.invoke(cli, ["create", "--genre", "lo-fi"])
    project_id = None
    for line in result.output.split("\n"):
        if "프로젝트 생성" in line:
            project_id = line.split("] ")[1].strip()
            break

    result = runner.invoke(cli, ["compose", project_id])
    assert "음악 파일이 없습니다" in result.output


def test_upload_no_video(tmp_path, monkeypatch):
    """compose 안 한 상태에서 upload 실행"""
    monkeypatch.setattr("cli.PROJECTS_DIR", tmp_path)
    monkeypatch.setattr("models.project.PROJECTS_DIR", tmp_path)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    runner = CliRunner()
    result = runner.invoke(cli, ["create", "--genre", "jazz"])
    project_id = None
    for line in result.output.split("\n"):
        if "프로젝트 생성" in line:
            project_id = line.split("] ")[1].strip()
            break

    result = runner.invoke(cli, ["upload", project_id])
    assert "최종 영상이 없습니다" in result.output


def test_prompts_no_api_key(tmp_path, monkeypatch):
    """ANTHROPIC_API_KEY 없이 prompts 실행"""
    monkeypatch.setattr("cli.PROJECTS_DIR", tmp_path)
    monkeypatch.setattr("models.project.PROJECTS_DIR", tmp_path)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    runner = CliRunner()
    result = runner.invoke(cli, ["create", "--genre", "rock"])
    project_id = None
    for line in result.output.split("\n"):
        if "프로젝트 생성" in line:
            project_id = line.split("] ")[1].strip()
            break

    result = runner.invoke(cli, ["prompts", project_id])
    assert "ANTHROPIC_API_KEY" in result.output
