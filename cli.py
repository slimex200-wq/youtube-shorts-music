import click
import json
import shutil
from pathlib import Path

from config import PROJECTS_DIR
from models.project import Project


@click.group()
def cli():
    """YouTube Shorts Music 자동화 파이프라인"""
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)


@cli.command()
@click.option("--genre", required=True, help="음악 장르 (예: lo-fi hip hop, dark trap, shranz)")
@click.option("--style", default=None, help="비주얼 아트 스타일 (예: anime, cyberpunk, retro)")
@click.option("--instrumental", is_flag=True, help="인스트루멘탈 (가사 없음)")
@click.option("--lyrics", default=None, help="가사 텍스트")
@click.option("--bpm", type=int, default=None, help="원하는 BPM")
@click.option("--mood", default=None, help="분위기 (예: aggressive, dreamy)")
@click.option("--artist", default=None, help="아티스트명 (기본: Eisenherz)")
def create(genre, style, instrumental, lyrics, bpm, mood, artist):
    """프로젝트 생성 + Suno 프롬프트 생성"""
    project = Project.create(genre=genre, instrumental=instrumental, lyrics=lyrics, style=style)
    project.update_status("created", step_name="create")

    from config import Config
    cfg = Config.from_env()

    if cfg.anthropic_api_key:
        from services.suno_prompt import SunoPromptGenerator
        gen = SunoPromptGenerator(cfg.anthropic_api_key)
        click.echo(f"[Suno 프롬프트 생성] {genre}...")
        try:
            suno_prompt = gen.generate(
                genre=genre, bpm=bpm, mood=mood,
                lyrics=lyrics, instrumental=instrumental,
            )
            project.suno_prompt = suno_prompt
            click.echo(f"[Style] {suno_prompt['style']}")
            click.echo(f"[제목 제안] {suno_prompt.get('title_suggestion', '-')}")
            click.echo(f"[BPM 제안] {suno_prompt.get('bpm_suggestion', '-')}")
        except Exception as e:
            click.echo(f"[경고] Suno 프롬프트 생성 실패: {e}")
    else:
        click.echo("[스킵] ANTHROPIC_API_KEY 없음 — Suno 프롬프트 생성 스킵")

    if artist:
        project.config["title_card"]["artist_name"] = artist

    project.save()
    click.echo(f"\n[프로젝트 생성] {project.id}")
    click.echo(f"[장르] {project.genre}")
    if project.suno_prompt:
        click.echo(f"\nSuno에서 음악을 만든 후:")
    click.echo(f"다음: python cli.py music {project.id} --file <track.mp3>")


@cli.command()
@click.argument("project_id")
@click.option("--file", "music_path", required=True, type=click.Path(exists=True), help="음악 파일 경로")
@click.option("--beats-per-scene", type=int, default=None, help="씬당 비트 수 (기본: 자동)")
def music(project_id, music_path, beats_per_scene):
    """음악 파일 등록 + 비트 분석 + 씬 분할"""
    from services.beat_analyzer import BeatAnalyzer

    try:
        project = Project.load(project_id)
    except FileNotFoundError:
        click.echo(f"프로젝트를 찾을 수 없습니다: {project_id}")
        return

    src = Path(music_path)
    dst = project.project_dir / "music" / src.name
    shutil.copy2(src, dst)
    project.music_file = src.name

    click.echo(f"[비트 분석] {src.name}...")
    analyzer = BeatAnalyzer()
    try:
        analysis = analyzer.analyze(dst)
    except Exception as e:
        project.set_error("music", str(e))
        project.save()
        click.echo(f"[에러] 비트 분석 실패: {e}")
        return

    project.bpm = analysis["bpm"]
    project.duration_sec = analysis["duration_sec"]
    project.beat_times = analysis["beat_times"]

    # Shorts 60초 제한: 초과 시 트리밍 + fade out 2초
    trim = analyzer.trim_for_shorts(project.beat_times, project.duration_sec)
    if trim["trimmed"]:
        click.echo(f"[트리밍] {project.duration_sec:.0f}초 → {trim['duration_sec']:.0f}초 (fade out {trim['fade_out_sec']:.0f}초)")
        project.beat_times = trim["beat_times"]
        project.duration_sec = trim["duration_sec"]
    project.config["fade_out_sec"] = trim["fade_out_sec"]

    bps = beats_per_scene or analyzer.suggest_beats_per_scene(project.bpm, project.duration_sec)
    scenes = analyzer.split_scenes(project.beat_times, project.duration_sec, beats_per_scene=bps)
    project.scenes = scenes

    project.update_status("music_registered", step_name="music")
    project.save()

    click.echo(f"[BPM] {project.bpm}")
    click.echo(f"[길이] {project.duration_sec:.1f}초")
    click.echo(f"[비트 수] {len(project.beat_times)}")
    click.echo(f"[씬 분할] {len(scenes)}개 씬 ({bps}비트/씬)")
    for s in scenes:
        dur = round(s["end_sec"] - s["start_sec"], 1)
        click.echo(f"  씬 {s['id']}: {s['start_sec']:.1f}초~{s['end_sec']:.1f}초 ({dur}초, {s['beat_count']}비트)")
    click.echo(f"\n다음: python cli.py prompts {project_id}")


@cli.command()
@click.argument("project_id")
def prompts(project_id):
    """씬별 이미지/영상 프롬프트 생성"""
    from config import Config
    from services.prompt_generator import PromptGenerator

    cfg = Config.from_env()
    if not cfg.anthropic_api_key:
        click.echo("[에러] ANTHROPIC_API_KEY가 설정되지 않았습니다.")
        return

    try:
        project = Project.load(project_id)
    except FileNotFoundError:
        click.echo(f"프로젝트를 찾을 수 없습니다: {project_id}")
        return

    if not project.scenes:
        click.echo("[에러] 씬이 없습니다. 먼저 music 명령을 실행하세요.")
        return

    gen = PromptGenerator(cfg.anthropic_api_key)
    click.echo(f"[프롬프트 생성] {len(project.scenes)}개 씬...")

    try:
        project.scenes = gen.generate(
            genre=project.genre,
            scenes=project.scenes,
            lyrics=project.lyrics,
            instrumental=project.instrumental,
            suno_prompt=project.suno_prompt,
            style=project.style,
        )
    except Exception as e:
        project.set_error("prompts", str(e))
        project.save()
        click.echo(f"[에러] 프롬프트 생성 실패: {e}")
        return

    project.update_status("prompts_done", step_name="prompts")
    project.save()

    click.echo("[완료] 씬별 프롬프트:")
    for s in project.scenes:
        click.echo(f"\n  씬 {s['id']}:")
        click.echo(f"    이미지: {s['image_prompt'][:70]}...")
        click.echo(f"    영상:   {s['video_prompt'][:70]}...")
        if s.get("lyrics_line"):
            click.echo(f"    가사:   {s['lyrics_line']}")
    click.echo(f"\n에셋을 만들어서 {project.project_dir / 'assets'}/ 에 넣으세요.")
    click.echo(f"파일명: scene_01.png (또는 .mp4), scene_02.png, ...")
    click.echo(f"다음: python cli.py compose {project_id}")


@cli.command()
@click.argument("project_id")
def compose(project_id):
    """비트 싱크 영상 조립 (9:16)"""
    from services.composer import ShortsComposer

    try:
        project = Project.load(project_id)
    except FileNotFoundError:
        click.echo(f"프로젝트를 찾을 수 없습니다: {project_id}")
        return

    if not project.music_file:
        click.echo("[에러] 음악 파일이 없습니다. 먼저 music 명령을 실행하세요.")
        return

    composer = ShortsComposer()
    fade_out = project.config.get("fade_out_sec", 0.0)
    click.echo(f"[영상 조립] {len(project.scenes)}개 씬, 비트 싱크...")
    if fade_out > 0:
        click.echo(f"[fade out] {fade_out:.0f}초")

    # 제목 결정: metadata > suno_prompt > genre
    title = None
    if project.metadata:
        title = project.metadata.get("title")
    if not title and project.suno_prompt:
        title = project.suno_prompt.get("title_suggestion")
    if not title:
        title = project.genre

    try:
        final_path = composer.compose_full(
            project_dir=project.project_dir,
            scenes=project.scenes,
            music_file=project.music_file,
            fade_out_sec=fade_out,
            title=title,
            title_card_config=project.config.get("title_card"),
        )
    except FileNotFoundError as e:
        click.echo(f"[에러] {e}")
        return
    except Exception as e:
        project.set_error("compose", str(e))
        project.save()
        click.echo(f"[에러] 영상 조립 실패: {e}")
        return

    from config import Config
    cfg = Config.from_env()
    if cfg.anthropic_api_key and not project.metadata:
        from services.metadata import MetadataGenerator
        meta_gen = MetadataGenerator(cfg.anthropic_api_key)
        try:
            project.metadata = meta_gen.generate(
                genre=project.genre,
                title_suggestion=project.suno_prompt.get("title_suggestion", "") if project.suno_prompt else "",
                lyrics=project.lyrics,
                instrumental=project.instrumental,
            )
            click.echo(f"[메타데이터] {project.metadata['title']}")
        except Exception as e:
            click.echo(f"[경고] 메타데이터 생성 실패: {e}")

    project.update_status("composed", step_name="compose")
    project.save()

    click.echo(f"[완료] {final_path}")
    click.echo(f"다음: python cli.py upload {project_id}")


@cli.command()
@click.argument("project_id")
def upload(project_id):
    """YouTube Shorts 업로드"""
    from services.uploader import YouTubeUploader

    try:
        project = Project.load(project_id)
    except FileNotFoundError:
        click.echo(f"프로젝트를 찾을 수 없습니다: {project_id}")
        return

    output_dir = project.project_dir / "output"
    final_files = list(output_dir.glob("*_shorts.mp4"))
    if not final_files:
        click.echo("[에러] 최종 영상이 없습니다. 먼저 compose를 실행하세요.")
        return

    video_path = final_files[0]
    metadata = project.metadata or {}
    title = metadata.get("title", f"{project.genre} #Shorts")
    description = metadata.get("description", "")
    tags = metadata.get("tags", ["Shorts"])
    privacy = project.config.get("upload_privacy", "private")

    uploader = YouTubeUploader()
    click.echo(f"[업로드] {title} ({privacy})")

    try:
        response = uploader.upload(
            video_path=video_path,
            title=title,
            description=description,
            tags=tags,
            privacy=privacy,
        )
    except Exception as e:
        project.set_error("upload", str(e))
        project.save()
        click.echo(f"[에러] 업로드 실패: {e}")
        return

    video_id = response["id"]
    project.update_status("uploaded", step_name="upload")
    project.save()

    click.echo(f"[완료] https://youtube.com/shorts/{video_id}")


@cli.command()
@click.argument("project_id")
def status(project_id):
    """프로젝트 상태 확인"""
    try:
        project = Project.load(project_id)
    except FileNotFoundError:
        click.echo(f"프로젝트를 찾을 수 없습니다: {project_id}")
        return

    click.echo(f"[ID] {project.id}")
    click.echo(f"[장르] {project.genre}")
    click.echo(f"[상태] {project.status}")
    click.echo(f"[완료 단계] {', '.join(project.steps_completed) or '없음'}")
    if project.bpm:
        click.echo(f"[BPM] {project.bpm} | [길이] {project.duration_sec:.1f}초 | [씬] {len(project.scenes)}개")
    if project.metadata:
        click.echo(f"[제목] {project.metadata.get('title', '-')}")
    if project.last_error:
        click.echo(f"[에러] {project.last_error['step']}: {project.last_error['message']}")


@cli.command("list")
def list_projects():
    """모든 프로젝트 목록"""
    projects = Project.list_all()
    if not projects:
        click.echo("프로젝트 없음")
        return
    for p in projects:
        bpm_str = f" {p.bpm}bpm" if p.bpm else ""
        click.echo(f"  {p.id}  [{p.status}]{bpm_str}  {p.genre}")


@cli.command()
@click.option("--songs", required=True, type=click.Path(exists=True), help="음악 파일 폴더")
@click.option("--images", required=True, type=click.Path(exists=True), help="이미지 파일 폴더")
@click.option("--output", default="./editor_output", type=click.Path(), help="출력 폴더 (기본: ./editor_output)")
@click.option("--shuffle", is_flag=True, help="이미지 순서 랜덤")
def editor(songs, images, output, shuffle):
    """이미지 + 음악 → 풀 길이 비디오 (Shorts 제한 없음)"""
    from services.editor import EditorComposer

    songs_dir = Path(songs)
    images_dir = Path(images)
    output_dir = Path(output)

    from services.editor import SUPPORTED_AUDIO_EXTS
    from services.composer import SUPPORTED_IMAGE_EXTS

    composer = EditorComposer()

    song_files = composer.discover_files(songs_dir, SUPPORTED_AUDIO_EXTS)
    image_files = composer.discover_files(images_dir, SUPPORTED_IMAGE_EXTS)

    click.echo(f"[에디터] 노래 {len(song_files)}개 × 이미지 {len(image_files)}개")

    try:
        results = composer.compose_all(songs_dir, images_dir, output_dir, shuffle=shuffle)
    except FileNotFoundError as e:
        click.echo(f"[에러] {e}")
        return
    except Exception as e:
        click.echo(f"[에러] 영상 생성 실패: {e}")
        return

    click.echo(f"\n[완료] {len(results)}개 영상 생성:")
    for r in results:
        click.echo(f"  {r}")


if __name__ == "__main__":
    cli()
