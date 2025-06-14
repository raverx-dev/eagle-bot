import pytest
from unittest.mock import patch, MagicMock

import bot.utils.embed_factory as embed_factory

@pytest.fixture(autouse=True)
def patch_discord_embed():
    with patch("bot.utils.embed_factory.discord.Embed", autospec=True) as mock_embed_cls:
        yield mock_embed_cls

def test_basic_embed_creation(patch_discord_embed):
    title = "Test Title"
    description = "Test Description"
    embed_factory.create_embed(title, description)
    patch_discord_embed.assert_called_once_with(
        title=title,
        description=description,
        color=embed_factory.THEME_COLORS["default"]
    )

def test_themed_embed_success(patch_discord_embed):
    title = "Success"
    description = "Operation completed"
    embed_factory.create_embed(title, description, theme="success")
    patch_discord_embed.assert_called_once_with(
        title=title,
        description=description,
        color=embed_factory.THEME_COLORS["success"]
    )

def test_embed_with_fields(patch_discord_embed):
    mock_embed_instance = MagicMock()
    patch_discord_embed.return_value = mock_embed_instance
    fields = [{"name": "Field1", "value": "Value1", "inline": True}]
    embed_factory.create_embed("Title", "Desc", fields=fields)
    mock_embed_instance.add_field.assert_called_once_with(
        name="Field1",
        value="Value1",
        inline=True
    )

def test_invalid_theme_fallback(patch_discord_embed):
    title = "Unknown Theme"
    description = "Should fallback"
    embed_factory.create_embed(title, description, theme="not_a_theme")
    patch_discord_embed.assert_called_once_with(
        title=title,
        description=description,
        color=embed_factory.THEME_COLORS["default"]
    )