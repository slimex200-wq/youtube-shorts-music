"""Shranz/Schranz 서브스타일 풀.

12개 서브스타일 정의, 랜덤 선택, 이전 프로젝트 중복 회피를 제공한다.
"""

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class ShranzSubstyle:
    name: str
    label: str
    bpm_range: tuple[int, int]
    description: str
    kick_character: str
    synths: str
    percussion: str
    effects_chain: str
    texture: str
    structure: str
    mood: str
    exclude_styles: str
    weirdness_range: tuple[int, int]
    style_influence_range: tuple[int, int]


SUBSTYLES: list[ShranzSubstyle] = [
    ShranzSubstyle(
        name="classic_german",
        label="Classic German Schranz",
        bpm_range=(145, 155),
        description="극도로 compressed된 909 루프, 필터 스윕 중심, 멜로디 완전 부재, 16-32bar 루프 반복",
        kick_character="TR-909 kick through multi-stage distortion (AMP → Drum Buss → AMP), tight and punchy",
        synths="minimal — white noise filtered sweeps, atonal stabs only",
        percussion="metallic hi-hats in frantic 16th patterns, industrial clank percussion",
        effects_chain="limiter → AMP → delay → guitar pedal sim → limiter, 5-stack master compressor",
        texture="fried yet clean — extreme individual processing, clear mixdown",
        structure="relentless loop, filter-sweep breakdowns, LP cutoff automation builds",
        mood="cold, mechanical, hypnotic warehouse energy",
        exclude_styles="melodic, pop, trance, ambient, vocal",
        weirdness_range=(55, 70),
        style_influence_range=(75, 85),
    ),
    ShranzSubstyle(
        name="emo_schranz",
        label="Emo Schranz",
        bpm_range=(150, 158),
        description="감성적/드라마틱 분위기, 보컬 에디트, 거친 킥 위에 멜로디 레이어와 reese bass",
        kick_character="heavy distorted kick with sidechain-pumped melodic layers above",
        synths="Serum/Sylenth1 atmospheric pads, aggressive reese bassline, vocal chop processing",
        percussion="driving hi-hats with reverb automation, sparse but impactful claps",
        effects_chain="kick sidechain → melodic layer, reverb size automation, filter sweep emotional builds",
        texture="wide stereo atmospheric, cathartic tension-release cycles",
        structure="dramatic builds with euphoric peak → aggressive schranz drop alternation",
        mood="cathartic, dramatic, euphoria meets aggression",
        exclude_styles="minimal, ambient, lo-fi, acoustic",
        weirdness_range=(40, 60),
        style_influence_range=(60, 75),
    ),
    ShranzSubstyle(
        name="industrial_schranz",
        label="Industrial Schranz",
        bpm_range=(155, 170),
        description="메탈릭 스크랩, 기계 소음, 필드 레코딩 통합, 공장 텍스처, 극단적 디스토션",
        kick_character="noise kick — white noise through sampler → LP/HP filter → multi-distortion → limiter",
        synths="granular synth processing field recordings, ring modulation for inharmonic tones, comb filter metallic resonance",
        percussion="metallic scrap hits, contact mic recordings processed as percussion, machine rhythm",
        effects_chain="field recording → granular stretch → ring mod → comb filter → convolution reverb (industrial space IR)",
        texture="dystopian factory floor, threatening and inhuman",
        structure="noise wash breakdowns, mechanical rhythm builds, tension through texture density",
        mood="dystopian, factory, threatening, post-industrial",
        exclude_styles="melodic, clean, pop, trance, warm",
        weirdness_range=(70, 90),
        style_influence_range=(65, 80),
    ),
    ShranzSubstyle(
        name="acid_schranz",
        label="Acid Schranz",
        bpm_range=(148, 160),
        description="schranz driving force + TB-303 acid — 303이 주인공이 아니라 디스토션 레이어 중 하나",
        kick_character="classic 909 overdriven kick, punchy mid-range emphasis",
        synths="TB-303 through heavy distortion pedal chain (bubble → scream), resonance filter sweeps controlling harmonic tension",
        percussion="razor-sharp hi-hats, acid-tinged percussion accents",
        effects_chain="303 → multi-distortion → bitcrusher → bandpass filter → ping-pong delay",
        texture="psychedelic acid wash over mechanical drive, wet and squelchy",
        structure="hypnotic 303 pattern evolution, filter resonance peaks as climax, acid line as tension arc",
        mood="psychedelic, aggressive, hypnotic acid trance",
        exclude_styles="clean, minimal, ambient, vocal-heavy",
        weirdness_range=(60, 80),
        style_influence_range=(70, 85),
    ),
    ShranzSubstyle(
        name="hardgroove",
        label="Hardgroove Schranz",
        bpm_range=(138, 148),
        description="schranz보다 느리지만 퍼커션 복잡도 높음, tribal 요소, rolling 베이스라인, 펑크 스윙",
        kick_character="909 kick + 16th-note delay bass gallop (kick copy → filter down → sync delay → sidechain)",
        synths="minimal synth stabs, rolling 16th-note bassline with H-Delay 1/16",
        percussion="conga, bongo, tribal percussion, ride cymbal, 5-15ms grid offset for human swing",
        effects_chain="transient shaper for dry punchy hits, parallel compression on drum bus, swing offset groove pool",
        texture="groovy and hypnotic, funky machine with human feel",
        structure="percussion-led builds, tribal breakdown sections, groove-driven rather than texture-driven",
        mood="groovy, hypnotic, tribal-mechanical fusion",
        exclude_styles="melodic trance, pop, ambient, clean electronic",
        weirdness_range=(35, 55),
        style_influence_range=(65, 80),
    ),
    ShranzSubstyle(
        name="deep_hardtechno",
        label="Deep Hardtechno / Slow Schranz",
        bpm_range=(135, 145),
        description="schranz 텍스처 유지하면서 템포 낮춤, 끌리는(dragging) 투덜거리는(grumbling) 캐릭터",
        kick_character="sub-heavy rumble kick — long decay, reverb(warehouse IR) → distortion → LP filter → sidechain comp",
        synths="dark ambient pads, deep rumble bass, muffled texture from heavy LP filtering",
        percussion="minimal percussion, sparse hi-hats, emphasis on sub-frequency weight",
        effects_chain="long-tail kick → reverb → distortion → LP filter → sidechain, high-pass removal for muffled rumble",
        texture="overwhelming sub presence, dark cave, low-frequency dominant",
        structure="slow builds through sub-bass density, fake drops avoided, rolling bassline tension",
        mood="overwhelming, cavernous, subterranean pressure",
        exclude_styles="bright, fast, melodic, high-energy, trance",
        weirdness_range=(45, 65),
        style_influence_range=(70, 85),
    ),
    ShranzSubstyle(
        name="peak_time",
        label="Peak-Time Schranz",
        bpm_range=(155, 168),
        description="현대 하드테크노 교차점, schranz raw energy + 현대적 프로덕션 퀄리티",
        kick_character="layered kick — click layer + mid body + sub tail, each independently processed, surgical precision",
        synths="Serum 2 wavetable leads, FM synth short-envelope stabs, noise risers, cinematic impact FX",
        percussion="tight programmed hats, layered claps, noise-based percussion fills",
        effects_chain="bus saturation + limiting, sub tight center, mid-forward mix, parallel distortion on drum bus",
        texture="festival-grade production, maximum clarity at maximum intensity",
        structure="cinematic builds with noise risers → impact → full-force drop, stadium-scale energy arcs",
        mood="peak-time festival, unstoppable force, maximum energy",
        exclude_styles="minimal, ambient, lo-fi, chill, downtempo",
        weirdness_range=(50, 70),
        style_influence_range=(75, 90),
    ),
    ShranzSubstyle(
        name="tekk",
        label="Tekk / Hardtekk",
        bpm_range=(165, 180),
        description="극단적 고속 변형, gabber 교차점, shuffled hat + forward-leaning swing",
        kick_character="extremely compressed kick pushed to clipping, overdriven to distortion ceiling",
        synths="screaming lead synth, distorted mono leads, chopped vocal shouts",
        percussion="shuffled hi-hats with forward-leaning swing, aggressive clap rolls",
        effects_chain="kick → hard clipper → limiter, lead → multiband distortion → chorus → delay",
        texture="raw underground rave energy, total chaos",
        structure="relentless assault, minimal breakdown, speed builds through hi-hat density",
        mood="complete chaos, frenzy, underground rave",
        exclude_styles="melodic, slow, ambient, clean, polished",
        weirdness_range=(70, 90),
        style_influence_range=(60, 75),
    ),
    ShranzSubstyle(
        name="trancecore_hybrid",
        label="Schranz-Trance Hybrid",
        bpm_range=(150, 160),
        description="schranz 킥/퍼커션 + 90년대 레이브 유포리아 + 트랜스 멜로디",
        kick_character="distorted schranz kick as rhythmic foundation for euphoric layers above",
        synths="supersaw pads, arpeggio synths, rave stabs, 90s trance chord progressions over schranz percussion",
        percussion="schranz-style hi-hats and claps, trance-style builds and fills",
        effects_chain="trance-style buildup → schranz-style drop, euphoric melody × distortion layer crossover",
        texture="nostalgic yet modern, rave euphoria meets industrial grit",
        structure="trance build-up (16-32 bars) → schranz drop, euphoric peak with aggressive rhythmic foundation",
        mood="nostalgic rave euphoria, modern aggression",
        exclude_styles="minimal, dark ambient, downtempo, acoustic",
        weirdness_range=(45, 65),
        style_influence_range=(65, 80),
    ),
    ShranzSubstyle(
        name="noise_experimental",
        label="Noise/Experimental Schranz",
        bpm_range=(140, 170),
        description="전통적 구조 파괴, 노이즈 아트 경계, 필드 레코딩 중심, 비정형 리듬",
        kick_character="synthesized noise kick from modular, irregular kick patterns breaking 4/4 convention",
        synths="modular synth patches, feedback loops as tonal source, granular stretched textures",
        percussion="contact mic recordings as rhythm, non-traditional percussion sources",
        effects_chain="waveshaping → ring modulation → granular stretch → bitcrusher as expressive tool",
        texture="anxious, experimental, artistic noise as musical expression",
        structure="non-linear, unpredictable shifts between noise and rhythm sections",
        mood="anxiety, experimental, artistic noise-art",
        exclude_styles="pop, clean, structured, melodic, danceable",
        weirdness_range=(80, 100),
        style_influence_range=(40, 60),
    ),
    ShranzSubstyle(
        name="latin_schranz",
        label="Latin Schranz",
        bpm_range=(150, 165),
        description="Classic보다 그루비하고 바운시한 리듬, rolling 에너지, 텍스처보다 움직임 강조",
        kick_character="909 kick with bouncy groove, layered with tribal kick accents",
        synths="minimal synth elements, groove-driven bassline, tribal melodic fragments",
        percussion="heavy tribal percussion layers — congas, bongos, shakers, latin rhythm patterns with swing",
        effects_chain="percussion layers → parallel compression, swing applied to hats, reverb on tribal elements",
        texture="energetic ritual, percussive density over sonic density",
        structure="percussion-driven builds, tribal breakdown sections, groove intensification",
        mood="energetic ritual, aggressive yet danceable, tribal ceremony",
        exclude_styles="ambient, minimal, melodic trance, acoustic, soft",
        weirdness_range=(40, 60),
        style_influence_range=(65, 80),
    ),
    ShranzSubstyle(
        name="ebm_schranz",
        label="EBM-Schranz Fusion",
        bpm_range=(140, 155),
        description="Electronic Body Music의 바디 드라이브 + schranz의 인더스트리얼 펀치, 다크 보컬 에디트",
        kick_character="saturated punch kick — soft clipping → parallel distortion → mid-forward EQ emphasis",
        synths="analog-style mono bass sequences, dark minor-key arpeggios, EBM-style synth bass pulses",
        percussion="snappy snare hits, mechanical claps, 16th-note hat patterns with accent variation",
        effects_chain="parallel saturation on bass → sidechain → tape emulation → stereo width on reverb sends",
        texture="dark, body-moving, muscular low-mid presence, analog warmth meets digital aggression",
        structure="EBM-style verse-chorus with schranz-intensity drops, bass sequence as melodic anchor",
        mood="dark body music, muscular, controlled aggression",
        exclude_styles="bright, euphoric, trance, acoustic, lo-fi",
        weirdness_range=(45, 65),
        style_influence_range=(70, 85),
    ),
]

SUBSTYLE_MAP: dict[str, ShranzSubstyle] = {s.name: s for s in SUBSTYLES}

SHRANZ_ALIASES: set[str] = {
    "shranz", "schranz", "hard techno", "hard-techno", "hardtechno",
    "dark shranz", "new shrantz", "new shranz",
}


def is_shranz_genre(genre: str) -> bool:
    """장르 문자열이 shranz 계열인지 판별."""
    normalized = genre.lower().strip()
    return any(alias in normalized for alias in SHRANZ_ALIASES)


def pick_substyle(
    exclude_names: list[str] | None = None,
    preferred_name: str | None = None,
) -> ShranzSubstyle:
    """서브스타일 하나를 선택한다.

    preferred_name이 주어지면 해당 스타일 반환.
    exclude_names로 이전에 사용한 스타일을 제외할 수 있다.
    모두 제외되면 전체 풀에서 랜덤 선택.
    """
    if preferred_name and preferred_name in SUBSTYLE_MAP:
        return SUBSTYLE_MAP[preferred_name]

    pool = SUBSTYLES
    if exclude_names:
        pool = [s for s in SUBSTYLES if s.name not in set(exclude_names)]
        if not pool:
            pool = SUBSTYLES

    return random.choice(pool)


def get_used_substyles_from_projects(projects_dir) -> list[str]:
    """기존 프로젝트들에서 사용된 서브스타일 이름 목록을 반환."""
    import json
    from pathlib import Path

    used = []
    projects_path = Path(projects_dir)
    if not projects_path.exists():
        return used

    for d in projects_path.iterdir():
        pj = d / "project.json"
        if not pj.exists():
            continue
        try:
            data = json.loads(pj.read_text(encoding="utf-8"))
            sp = data.get("suno_prompt", {})
            if sp and sp.get("substyle"):
                used.append(sp["substyle"])
        except (json.JSONDecodeError, OSError):
            continue

    return used


def build_substyle_prompt_section(substyle: ShranzSubstyle) -> str:
    """서브스타일을 시스템 프롬프트에 삽입할 텍스트 블록으로 변환."""
    bpm_suggestion = random.randint(substyle.bpm_range[0], substyle.bpm_range[1])
    weirdness = random.randint(substyle.weirdness_range[0], substyle.weirdness_range[1])
    style_influence = random.randint(
        substyle.style_influence_range[0], substyle.style_influence_range[1]
    )

    return f"""## SELECTED SCHRANZ SUBSTYLE: {substyle.label}

{substyle.description}

- BPM target: {bpm_suggestion} (range: {substyle.bpm_range[0]}-{substyle.bpm_range[1]})
- Kick character: {substyle.kick_character}
- Synths: {substyle.synths}
- Percussion: {substyle.percussion}
- Effects chain: {substyle.effects_chain}
- Texture: {substyle.texture}
- Structure: {substyle.structure}
- Mood: {substyle.mood}
- Exclude styles: {substyle.exclude_styles}
- Weirdness target: {weirdness}
- Style influence target: {style_influence}

IMPORTANT: Use THESE specific characteristics. Do NOT fall back to generic "TR-909 kick, TB-303 acid, razor hi-hats" unless this substyle specifically calls for them. Each substyle has its own distinct sonic identity — honor it."""
