import discord

THEME_COLORS = {
    "success": 0x2ECC71,  # Green (for check-ins)
    "error": 0xE74C3C,    # Red
    "default": 0x3498DB,  # Blue (for general stats)
    "summary": 0x95A5A6,  # NEW: Neutral Gray (for check-outs)
    "leaderboard": 0xF1C40F # NEW: Gold (for leaderboards)
}

def create_embed(title: str, description: str = "", theme: str = "default", fields: list = None):
    # Use a fallback to ensure a valid color is always used
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