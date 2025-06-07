# ──────────────────────────────────────────────────────────────────────────────
# FILE: bot/discord_bot.py
# ──────────────────────────────────────────────────────────────────────────────

import asyncio
import datetime

import discord
from discord.ext import commands

# Import dependencies from other modules
from bot.config import DISCORD_BOT_TOKEN, ARCADE_ID, log
from bot.eagle_browser import BROWSER
from bot.scraper import scrape_profile_page, get_vf_from_arcade, scrape_leaderboard
from bot.checkin_store import USER_LINKS, CHECKIN_STORE

# ──────────────────────────────────────────────────────────────────────────────
# DISCORD BOT SETUP (prefix commands)
# ──────────────────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="/", intents=intents)


@bot.event
async def on_ready():
    log.info(f"Bot is online as {bot.user} (ID {bot.user.id})")

    if not USER_LINKS:
        log.warning("⚠️ No users linked (USER_LINKS is empty). Skipping OAuth login. Please run /linkid for at least one user and restart the bot.")
        return

    first_sdvx = next(iter(USER_LINKS.values()))
    loop = asyncio.get_event_loop()

    login_success = await loop.run_in_executor(None, BROWSER.run_oauth_login, first_sdvx)
    if not login_success:
        log.error("❌ OAuth login automation failed. The bot will not be able to scrape without a valid eagle.ac cookie.")
        return

    headless_success = await loop.run_in_executor(None, BROWSER.init_headless_chrome)
    if not headless_success:
        log.error("❌ Headless ChromeDriver initialization failed. Scraping commands will not work.")
    else:
        log.info("✅ Headless ChromeDriver is ready (authenticated).")


# ──────────────────────────────────────────────────────────────────────────────
# !linkid (Admin only) → map a Discord user → SDVX ID
# ──────────────────────────────────────────────────────────────────────────────
@bot.command(name="linkid")
@commands.has_permissions(administrator=True)
async def linkid(ctx: commands.Context, sdvx_id: str):
    """
    Usage (admin only): /linkid 95688187
    Saves your Discord user → SDVX ID mapping.
    """
    cleaned = sdvx_id.strip()
    USER_LINKS[ctx.author.id] = cleaned
    await ctx.send(f"✅ Saved your SDVX ID as **{cleaned}**. Now initializing OAuth & headless Chrome…")

    loop = asyncio.get_event_loop()
    login_success = await loop.run_in_executor(None, BROWSER.run_oauth_login, cleaned)
    if not login_success:
        await ctx.send("❌ OAuth login flow failed. Please check your Eagle credentials or rerun /linkid.")
        return

    headless_success = await loop.run_in_executor(None, BROWSER.init_headless_chrome)
    if not headless_success:
        await ctx.send("❌ Headless ChromeDriver initialization failed. Scraping commands will not work.")
    else:
        await ctx.send("✅ Headless ChromeDriver is ready. You may now use /checkin, /stats, /leaderboard.")


# ──────────────────────────────────────────────────────────────────────────────
# !stats → display Skill/Plays/Packet/Block/VF for the invoking user
# ──────────────────────────────────────────────────────────────────────────────
@bot.command(name="stats")
async def stats(ctx: commands.Context):
    user_id = ctx.author.id
    if user_id not in USER_LINKS:
        await ctx.send("⚠️ You have not linked Eagle yet. An admin must run `/linkid` for you.")
        return

    sdvx_id = USER_LINKS[user_id]
    await ctx.send("🔄 Fetching your SDVX profile… Please wait a moment.")

    data = scrape_profile_page(sdvx_id)
    vf_val = get_vf_from_arcade(sdvx_id)

    embed = discord.Embed(
        title=f"📊 Stats for {ctx.author.display_name} ({sdvx_id})",
        color=discord.Color.blue()
    )
    embed.add_field(name="Skill Level", value=data.get("skill", "—"), inline=True)
    embed.add_field(name="Total Plays", value=data.get("plays", "—"), inline=True)
    embed.add_field(name="Packet", value=data.get("packet", "—"), inline=True)
    embed.add_field(name="Block", value=data.get("block", "—"), inline=True)
    embed.add_field(name="Volforce (VF)", value=vf_val, inline=False)

    await ctx.send(embed=embed)


# ──────────────────────────────────────────────────────────────────────────────
# !checkin → same as !stats but with a green “Checked In” heading
# ──────────────────────────────────────────────────────────────────────────────
@bot.command(name="checkin")
async def checkin(ctx: commands.Context):
    user_id = ctx.author.id
    if user_id not in USER_LINKS:
        await ctx.send("⚠️ You have not linked Eagle yet. An admin must run `/linkid` for you.")
        return

    sdvx_id = USER_LINKS[user_id]
    await ctx.send("✅ Checked In. Fetching your data…")

    data = scrape_profile_page(sdvx_id)
    vf_val = get_vf_from_arcade(sdvx_id)

    embed = discord.Embed(
        title="✅ Checked In",
        description=(
            f"SDVX ID {sdvx_id} • Skill Level {data.get('skill','—')} • Total Plays {data.get('plays','—')} • VF {vf_val}"
        ),
        color=discord.Color.green()
    )

    try:
        plays_val = int(data.get("plays", "0"))
    except:
        plays_val = 0

    try:
        vf_float = float(vf_val) if vf_val != "—" else 0.0
    except:
        vf_float = 0.0

    CHECKIN_STORE[user_id] = {
        "time": datetime.datetime.now(datetime.timezone.utc),
        "plays": plays_val,
        "vf": vf_float
    }

    await ctx.send(embed=embed)


# ──────────────────────────────────────────────────────────────────────────────
# !checkout → compare to last check‐in, show Plays & VF gained + duration
# ──────────────────────────────────────────────────────────────────────────────
@bot.command(name="checkout")
async def checkout(ctx: commands.Context):
    user_id = ctx.author.id
    if user_id not in USER_LINKS:
        await ctx.send("⚠️ You have not linked Eagle yet. An admin must run `/linkid` for you.")
        return

    if user_id not in CHECKIN_STORE:
        await ctx.send("⚠️ You have not checked in yet. Use `/checkin` first.")
        return

    sdvx_id = USER_LINKS[user_id]
    await ctx.send("🏁 Checking out… Fetching your current stats…")

    data = scrape_profile_page(sdvx_id)
    vf_val_now = get_vf_from_arcade(sdvx_id)

    try:
        current_plays = int(data.get("plays", "0"))
    except:
        current_plays = 0

    try:
        current_vf = float(vf_val_now) if vf_val_now != "—" else 0.0
    except:
        current_vf = 0.0

    old = CHECKIN_STORE[user_id]
    elapsed = datetime.datetime.now(datetime.timezone.utc) - old["time"]
    plays_gained = current_plays - old["plays"]
    vf_gained = current_vf - old["vf"]

    embed = discord.Embed(
        title="🏁 Checked Out",
        description=(
            f"Plays at Check‐in {old['plays']} • Plays Now {current_plays} • Plays Gained {plays_gained}\n"
            f"VF at Check‐in {old['vf']:.3f} • VF Now {current_vf:.3f} • VF Gained {vf_gained:.3f}\n"
            f"Session Duration {str(elapsed).split('.')[0]}"
        ),
        color=discord.Color.blue()
    )
    del CHECKIN_STORE[user_id]
    await ctx.send(embed=embed)


# ──────────────────────────────────────────────────────────────────────────────
# !leaderboard → show the arcade’s Top‐10 VF leaderboard (Arcade #94 by default)
# ──────────────────────────────────────────────────────────────────────────────
@bot.command(name="leaderboard")
async def leaderboard(ctx: commands.Context):
    await ctx.send("🔄 Fetching Arcade Top-10 VF leaderboard…")
    board = scrape_leaderboard(ARCADE_ID)
    if not board:
        await ctx.send("⚠️ Could not find the ‘Arcade Top 10’ table on eagle.ac.")
        return

    lines = []
    for entry in board:
        lines.append(f"**{entry['rank']}.** {entry['name']} (`{entry['sdvx_id']}`) — {entry['vf']} VF")

    embed = discord.Embed(
        title="🏆 Electric Starship Arcade – SDVX Top 10",
        description="\n".join(lines),
        color=discord.Color.gold()
    )
    await ctx.send(embed=embed)
