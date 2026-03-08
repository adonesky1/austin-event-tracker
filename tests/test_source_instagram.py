from src.sources.instagram import InstagramAdapter


def test_instagram_is_stub():
    adapter = InstagramAdapter()
    assert adapter.name == "instagram"
    assert adapter.is_enabled() is False
