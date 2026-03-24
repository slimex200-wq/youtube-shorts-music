import json
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
