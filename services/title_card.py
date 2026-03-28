"""ASS 자막 기반 타이틀 카드 생성기"""
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_WHITE = "&H00FFFFFF"
_BLACK = "&H00000000"
_BG_SEMI = "&H80000000"
_TRANSPARENT = "&HFF000000"

_UNDERLINE_ALPHA = "&HB3&"

_CHAR_WIDTH_PX = 18


class TitleCardGenerator:
    """Shorts 영상 인트로에 들어갈 타이틀 카드 ASS 파일 생성"""

    def generate(
        self,
        title: str,
        artist_name: str,
        output_dir: Path,
        start_sec: float = 0.5,
        duration_sec: int = 4,
        fade_in_ms: int = 800,
        fade_out_ms: int = 800,
    ) -> Path:
        title_upper = self._escape_ass_text(title.upper())
        artist_upper = self._escape_ass_text(artist_name.upper())
        display_text = f"{title_upper} \u00b7 {artist_upper}"

        end_sec = start_sec + duration_sec
        underline_start = start_sec + 0.3
        underline_end = end_sec - 0.3
        underline_fade_in = max(0, fade_in_ms - 200)
        underline_fade_out = max(0, fade_out_ms - 200)
        underline_width = len(display_text) * _CHAR_WIDTH_PX

        underline_y = 1920 - 60 + 2

        content = (
            "[Script Info]\n"
            "ScriptType: v4.00+\n"
            "PlayResX: 1080\n"
            "PlayResY: 1920\n"
            "\n"
            "[V4+ Styles]\n"
            "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,"
            "OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,"
            "ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,"
            "Alignment,MarginL,MarginR,MarginV,Encoding\n"
            f"Style: TitleCard,Montserrat SemiBold,28,{_WHITE},{_WHITE},"
            f"{_BLACK},{_BG_SEMI},-1,0,0,0,100,100,2,0,1,2,0,1,20,0,60,1\n"
            f"Style: Underline,Montserrat SemiBold,28,{_WHITE},{_WHITE},"
            f"{_TRANSPARENT},{_TRANSPARENT},0,0,0,0,100,100,0,0,1,0,0,1,20,0,60,1\n"
            "\n"
            "[Events]\n"
            "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n"
            f"Dialogue: 0,{self._format_ass_time(start_sec)},"
            f"{self._format_ass_time(end_sec)},TitleCard,,20,0,60,,"
            f"{{\\fad({fade_in_ms},{fade_out_ms})}}{display_text}\n"
            f"Dialogue: 1,{self._format_ass_time(underline_start)},"
            f"{self._format_ass_time(underline_end)},Underline,,0,0,0,,"
            f"{{\\fad({underline_fade_in},{underline_fade_out})"
            f"\\pos(20,{underline_y})\\p1"
            f"\\1a{_UNDERLINE_ALPHA}\\3a&HFF&}}"
            f"m 0 0 l {underline_width} 0 l {underline_width} 1 l 0 1"
            "{\\p0}\n"
        )

        output_path = output_dir / "title_card.ass"
        output_path.write_text(content, encoding="utf-8")
        logger.info("타이틀 카드 ASS 생성: %s", output_path)
        return output_path

    @staticmethod
    def _escape_ass_text(text: str) -> str:
        return text.replace("{", "\\{").replace("}", "\\}")

    @staticmethod
    def _format_ass_time(seconds: float) -> str:
        total_cs = round(seconds * 100)
        cs = total_cs % 100
        total_s = total_cs // 100
        h = total_s // 3600
        m = (total_s % 3600) // 60
        s = total_s % 60
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"
