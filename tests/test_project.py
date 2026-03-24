import json
from models.project import Project


def test_create_project(tmp_path):
    project = Project.create(genre="lo-fi hip hop", base_dir=tmp_path)
    assert project.genre == "lo-fi hip hop"
    assert project.status == "created"
    assert project.instrumental is False
    assert (tmp_path / project.id / "project.json").exists()
    assert (tmp_path / project.id / "assets").is_dir()
    assert (tmp_path / project.id / "music").is_dir()
    assert (tmp_path / project.id / "output").is_dir()


def test_create_instrumental(tmp_path):
    project = Project.create(genre="ambient", base_dir=tmp_path, instrumental=True)
    assert project.instrumental is True
    assert project.lyrics is None


def test_create_with_lyrics(tmp_path):
    project = Project.create(genre="k-pop", base_dir=tmp_path, lyrics="가사 텍스트")
    assert project.lyrics == "가사 텍스트"


def test_load_project(tmp_path):
    project = Project.create(genre="jazz", base_dir=tmp_path)
    loaded = Project.load(project.id, base_dir=tmp_path)
    assert loaded.id == project.id
    assert loaded.genre == "jazz"


def test_save_and_load_preserves_data(tmp_path):
    project = Project.create(genre="trap", base_dir=tmp_path)
    project.bpm = 140.0
    project.beat_times = [0.0, 0.428, 0.857]
    project.save()

    loaded = Project.load(project.id, base_dir=tmp_path)
    assert loaded.bpm == 140.0
    assert loaded.beat_times == [0.0, 0.428, 0.857]


def test_list_all(tmp_path):
    Project.create(genre="jazz", base_dir=tmp_path)
    Project.create(genre="rock", base_dir=tmp_path)
    projects = Project.list_all(base_dir=tmp_path)
    assert len(projects) == 2


def test_update_status(tmp_path):
    project = Project.create(genre="pop", base_dir=tmp_path)
    project.update_status("music_registered", step_name="music")
    assert project.status == "music_registered"
    assert "music" in project.steps_completed


def test_set_error(tmp_path):
    project = Project.create(genre="pop", base_dir=tmp_path)
    project.set_error("compose", "FFmpeg 에러")
    assert project.last_error["step"] == "compose"
    assert "FFmpeg" in project.last_error["message"]
