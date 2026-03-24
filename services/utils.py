import json


def parse_claude_json(text: str) -> dict | list:
    """Claude API 응답에서 JSON 추출. markdown fence 처리 포함."""
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]

    try:
        return json.loads(text.strip())
    except json.JSONDecodeError as e:
        raise ValueError(f"Claude 응답에서 JSON 파싱 실패: {e}\n응답 내용: {text[:200]}") from e
