import json
import re


def parse_claude_json(text: str) -> dict | list:
    """Claude API 응답에서 JSON 추출. markdown fence + mixed text 처리."""
    # 1) markdown fence
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]

    stripped = text.strip()

    # 2) direct parse
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    # 3) mixed text — find first { ... } or [ ... ] block
    for opener, closer in [("{", "}"), ("[", "]")]:
        start = stripped.find(opener)
        if start == -1:
            continue
        depth = 0
        for i in range(start, len(stripped)):
            if stripped[i] == opener:
                depth += 1
            elif stripped[i] == closer:
                depth -= 1
            if depth == 0:
                candidate = stripped[start : i + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    break

    raise ValueError(
        f"Claude 응답에서 JSON 파싱 실패: {stripped[:200]}"
    )
