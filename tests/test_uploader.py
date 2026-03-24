from services.uploader import YouTubeUploader


def test_build_body_category_id_is_music():
    """categoryId가 10 (Music)인지 확인"""
    uploader = YouTubeUploader()
    body = uploader._build_body(
        title="Test Song #Shorts",
        description="test desc",
        tags=["lofi", "Shorts"],
        privacy="private",
    )
    assert body["snippet"]["categoryId"] == "10"
    assert body["snippet"]["title"] == "Test Song #Shorts"
    assert body["snippet"]["tags"] == ["lofi", "Shorts"]
    assert body["status"]["privacyStatus"] == "private"
    assert body["status"]["selfDeclaredMadeForKids"] is False
