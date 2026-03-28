# Title Card Overlay for YouTube Shorts

## Summary

Suno 음악 기반 YouTube Shorts 영상에 시네마틱 타이틀 카드를 추가한다.
영상 인트로에 곡 제목과 아티스트명이 한 줄로 페이드 인/아웃되며, 언더라인 악센트가 포함된다.

## Requirements

| 항목 | 결정 |
|------|------|
| 프로젝트 | youtube-shorts-music |
| 텍스트 포맷 | `곡 제목 · 아티스트명` (한 줄, 대문자) |
| 위치 | 좌하단 |
| 폰트 | Montserrat SemiBold, 28pt (1080x1920 기준) |
| 색상 | 흰색 텍스트, 검정 외곽선 2px |
| 언더라인 | 흰색 30% opacity, 텍스트 하단 |
| 타이밍 | 0.5초 후 등장, 총 4초 노출 |
| 애니메이션 | 페이드 인 0.8초, 페이드 아웃 0.8초 |
| 기본 아티스트명 | Eisenherz |

## Technical Approach: ASS Subtitle Filter

기존 `composer.py`의 SRT 자막 시스템을 확장하여 ASS(Advanced SubStation Alpha) 포맷으로 타이틀 카드를 렌더링한다.

### ASS Style Definition

```ass
[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: TitleCard,Montserrat-SemiBold,28,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,2,0,1,2,0,1,20,0,60

[Events]
Style: Underline,Montserrat-SemiBold,28,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,1,20,0,60

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
Dialogue: 0,0:00:00.50,0:00:04.50,TitleCard,,20,0,60,,{\fad(800,800)}SONG TITLE · EISENHERZ
```

- `Alignment=1`: 좌하단
- `MarginL=20, MarginV=60`: 좌측 20px, 하단 60px 여백
- `Spacing=2`: letter-spacing 효과
- `\fad(800,800)`: 0.8초 페이드인, 0.8초 페이드아웃
- `PlayResX/Y`: 1080x1920 기준 좌표계

### Underline (ASS Drawing)

```ass
Dialogue: 1,0:00:00.80,0:00:04.20,Underline,,0,0,0,,{\fad(600,600)\pos(20,1858)\p1\1a&H4D&\3a&HFF&}m 0 0 l {width} 0 l {width} 1 l 0 1{\p0}
```

- 텍스트보다 0.3초 늦게 등장, 0.3초 먼저 사라짐
- `\1a&H4D&`: 흰색 30% opacity (ASS alpha 표기)
- `\3a&HFF&`: 외곽선 투명
- `{width}`: 코드에서 텍스트 길이 기반으로 동적 계산 (글자수 x 약 18px)
- 별도 `Underline` 스타일 정의 필요 (외곽선/그림자 없음)

**Windows 경로 이슈**: 기존 SRT 코드의 드라이브 문자 이스케이핑 (`C:` → `C\:`) 로직을 ASS 필터에도 동일 적용.

### Font

- Montserrat SemiBold (Google Fonts, OFL license)
- `assets/fonts/Montserrat-SemiBold.ttf`로 프로젝트에 포함
- FFmpeg `fontsdir` 옵션으로 경로 지정

## Code Changes

### 1. `services/composer.py` 변경

#### 새 메서드: `generate_title_ass()`
- `project.json`에서 제목 읽기
- `title_card` 설정에서 아티스트명, 페이드 값 읽기
- ASS 파일 생성하여 `output/` 디렉토리에 저장

#### 새 메서드: `add_title_card()`
- FFmpeg 명령에 ASS 자막 필터 추가
- `ass` 필터 사용: `-vf "ass=title.ass:fontsdir=assets/fonts"`
- 기존 가사 자막과 체이닝: `ass=title.ass,subtitles=lyrics.srt`

#### `compose()` 수정
- 최종 비디오+오디오 머지 후, 타이틀 카드 합성 단계 추가
- `title_card.enabled`가 false면 스킵

### 2. `models/project.py` 변경

`project.json`에 `title_card` 필드 추가:

```json
{
  "title_card": {
    "enabled": true,
    "artist_name": "Eisenherz",
    "fade_in_ms": 800,
    "fade_out_ms": 800,
    "duration_sec": 4,
    "start_sec": 0.5
  }
}
```

- `artist_name`: 기본값 "Eisenherz" (프로젝트별 오버라이드 가능)
- `enabled`: 타이틀 카드 온/오프
- 나머지는 애니메이션 타이밍

### 3. `cli.py` 변경

`create` 명령에 `--artist` 옵션 추가 (기본값: Eisenherz).

### 4. Font Asset 추가

`assets/fonts/Montserrat-SemiBold.ttf` 파일 추가.

## FFmpeg Command Example

```bash
ffmpeg -y \
  -i merged_video.mp4 \
  -vf "ass=output/title.ass:fontsdir=assets/fonts" \
  -c:v libx264 -preset fast -crf 23 -pix_fmt yuv420p \
  -c:a copy \
  output/final_shorts.mp4
```

가사 자막이 있는 경우:

```bash
ffmpeg -y \
  -i merged_video.mp4 \
  -vf "ass=output/title.ass:fontsdir=assets/fonts,subtitles=output/lyrics.srt:force_style='FontSize=42,...'" \
  -c:v libx264 -preset fast -crf 23 -pix_fmt yuv420p \
  -c:a copy \
  output/final_shorts.mp4
```

## Out of Scope

- 장르별 다른 스타일/색상 (추후 확장 가능)
- 아웃트로 타이틀 카드
- 다중 텍스트 라인
- 배경 블러/박스
