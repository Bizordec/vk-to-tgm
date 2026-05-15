from app.config import Settings


def get_settings_override() -> Settings:
    return Settings(
        VK_COMMUNITY_ID=123456,
        VK_COMMUNITY_TOKEN="vk-community-token",  # noqa: S106
        SERVER_URL="https://example.com",
        VK_SERVER_SECRET="vk-server-secret",  # noqa: S106
    )
