import discord

THEME_COLORS = {
    "success": 0x2ECC71,
    "error": 0xE74C3C,
    "default": 0x3498DB,
}

def create_embed(title: str, description: str, theme: str = "default", fields: list = None):
    color = THEME_COLORS.get(theme, THEME_COLORS["default"])
    embed = discord.Embed(title=title, description=description, color=color)
    if fields:
        for field in fields:
            embed.add_field(
                name=field.get("name", ""),
                value=field.get("value", ""),
                inline=field.get("inline", False)
            )
    return embed