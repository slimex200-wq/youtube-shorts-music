"""Seed demo projects for first-time users."""
import json
from pathlib import Path

PROJECTS_DIR = Path(__file__).parent / "projects"

DEMO_PROJECTS = [
    {
        "id": "demo-shranz-001",
        "genre": "shranz",
        "status": "created",
        "aspect_ratio": "9:16",
        "created_at": "2026-04-01T12:00:00+00:00",
        "steps_completed": ["create"],
        "suno_prompt": {
            "style": "Industrial Schranz, TR-909 distorted kick, razor hi-hats, TB-303 acid line, bitcrushed percussion, sidechain compression, cavernous reverb",
            "prompt": "Relentless 160BPM schranz assault. Distorted kick pounds through a wall of noise. Acid bassline squelches underneath razor-sharp hi-hats. Dark industrial atmosphere with metallic textures. Immediate impact, no intro.",
            "title_suggestion": "Iron Protocol",
            "bpm_suggestion": 160,
            "exclude_styles": "pop, melodic, soft, ambient",
            "vocal_gender": None,
            "lyrics_mode": "Instrumental",
            "lyrics": None,
            "weirdness": 72,
            "style_influence": 80,
            "substyle": "industrial_schranz"
        },
        "video_prompts": [
            {"type": "zoom", "label": "Slow Zoom", "prompt": "Dark industrial warehouse interior, concrete walls with rust stains, single harsh spotlight cutting through smoke haze, slow zoom into the light source, cinematic, high quality, smooth motion, 9:16 vertical, 5 seconds", "motion_strength": 2, "camera": "slow zoom in", "duration": "5s"},
            {"type": "pan", "label": "Orbit", "prompt": "Dark industrial warehouse interior, massive steel machinery with spinning gears, camera orbits around the central mechanism, smoke particles drift through cold blue light, cinematic, high quality, smooth motion, 9:16 vertical, 5 seconds", "motion_strength": 3, "camera": "orbit around subject", "duration": "5s"},
            {"type": "subject", "label": "Subject Motion", "prompt": "Dark industrial warehouse interior, hooded figure standing before a wall of monitors displaying waveforms, figure slowly raises hand, screens flicker and pulse, cinematic, high quality, smooth motion, 9:16 vertical, 5 seconds", "motion_strength": 4, "camera": "static", "duration": "5s"},
            {"type": "atmosphere", "label": "Atmosphere", "prompt": "Dark industrial warehouse interior, sparks rain down from overhead welding, embers float upward through thick smoke, static camera captures the particle dance, orange and steel blue palette, cinematic, high quality, smooth motion, 9:16 vertical, 5 seconds", "motion_strength": 3, "camera": "static", "duration": "5s"}
        ],
        "metadata": {
            "title": "Iron Protocol | Industrial Schranz #shorts",
            "description": "160BPM industrial schranz. TR-909 + TB-303 acid. Pure warehouse energy.",
            "tags": ["schranz", "hardtechno", "industrial", "techno", "shorts"],
            "first_comment": "909 + 303 = destruction"
        },
        "mood_tags": ["steel", "void"],
        "motif_tags": ["industrial", "acid", "warehouse"],
        "instrumental": True,
    },
    {
        "id": "demo-lofi-002",
        "genre": "lo-fi hip hop",
        "status": "created",
        "aspect_ratio": "9:16",
        "created_at": "2026-04-02T14:00:00+00:00",
        "steps_completed": ["create"],
        "suno_prompt": {
            "style": "Lo-fi hip hop, dusty vinyl crackle, detuned Rhodes piano, mellow jazz guitar, tape hiss, SP-404 sampler character, boom-bap drums with swing",
            "prompt": "Warm late-night lo-fi beat. Vinyl crackle bed with gentle Rhodes chords cycling through a jazz progression. Muted boom-bap drums with lazy swing. Tape saturation on everything. Cozy and nostalgic.",
            "title_suggestion": "3AM Thoughts",
            "bpm_suggestion": 82,
            "exclude_styles": "aggressive, hard, industrial",
            "vocal_gender": None,
            "lyrics_mode": "Instrumental",
            "lyrics": None,
            "weirdness": 25,
            "style_influence": 60,
            "substyle": None
        },
        "video_prompts": [
            {"type": "zoom", "label": "Slow Zoom", "prompt": "Cozy bedroom at night, desk lamp casting warm golden light on scattered notebooks, rain on the window, slow zoom into the rain-streaked glass, cinematic, high quality, smooth motion, 9:16 vertical, 5 seconds", "motion_strength": 2, "camera": "slow zoom in", "duration": "5s"},
            {"type": "pan", "label": "Pan", "prompt": "Cozy bedroom at night, camera slowly pans across a cluttered desk with vinyl records, coffee cup steaming, notebook with handwritten notes, warm amber tones, cinematic, high quality, smooth motion, 9:16 vertical, 5 seconds", "motion_strength": 3, "camera": "slow pan right", "duration": "5s"},
            {"type": "subject", "label": "Subject Motion", "prompt": "Cozy bedroom at night, cat curled on a cushion by the window slowly opens its eyes and stretches, soft lamp light, rain outside, cinematic, high quality, smooth motion, 9:16 vertical, 5 seconds", "motion_strength": 4, "camera": "static", "duration": "5s"},
            {"type": "atmosphere", "label": "Atmosphere", "prompt": "Cozy bedroom at night, rain drops slowly slide down the window glass, city lights blur in the background, steam rises from a coffee cup, warm amber and cool blue palette, cinematic, high quality, smooth motion, 9:16 vertical, 5 seconds", "motion_strength": 3, "camera": "static", "duration": "5s"}
        ],
        "metadata": {
            "title": "3AM Thoughts | Lo-fi Hip Hop #shorts",
            "description": "Late night lo-fi vibes. Dusty vinyl, Rhodes piano, rain on glass.",
            "tags": ["lofi", "hiphop", "chill", "study", "shorts"],
            "first_comment": "put this on repeat and zone out"
        },
        "mood_tags": ["frost", "shadow"],
        "motif_tags": ["rain", "night", "vinyl"],
        "instrumental": True,
    },
]


def seed():
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)

    created = 0
    for proj in DEMO_PROJECTS:
        proj_dir = PROJECTS_DIR / proj["id"]
        if proj_dir.exists():
            continue
        proj_dir.mkdir(parents=True)
        (proj_dir / "assets").mkdir()
        (proj_dir / "music").mkdir()
        (proj_dir / "output").mkdir()
        (proj_dir / "refs").mkdir()

        data = {**proj}
        data.setdefault("music_file", None)
        data.setdefault("bpm", None)
        data.setdefault("duration_sec", None)
        data.setdefault("beat_times", None)
        data.setdefault("scenes", [])
        data.setdefault("visual_refs", [])
        data.setdefault("notes", "")
        data.setdefault("title_lock", None)
        data.setdefault("last_edited_at", None)
        data.setdefault("youtube_video_id", None)
        data.setdefault("youtube_stats", None)
        data.setdefault("thumbnail_url", None)
        data.setdefault("last_error", None)
        data.setdefault("lyrics", None)
        data.setdefault("style", None)
        data.setdefault("config", {
            "upload_privacy": "private",
            "title_card": {
                "enabled": True,
                "artist_name": "",
                "fade_in_ms": 800,
                "fade_out_ms": 800,
                "duration_sec": 4,
                "start_sec": 0.5,
            },
        })

        path = proj_dir / "project.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        created += 1

    print(f"Seeded {created} demo projects ({len(DEMO_PROJECTS) - created} already existed)")


if __name__ == "__main__":
    seed()
