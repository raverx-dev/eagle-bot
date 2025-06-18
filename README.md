# Eagle Bot

Eagle Bot is a Discord bot designed to integrate with `eagle.ac` for Sound Voltex (SDVX) players. It allows users to track their in-game statistics, manage check-ins, and view arcade leaderboards directly through Discord commands. The bot uses Selenium to automate interactions with `eagle.ac` for data scraping while maintaining secure OAuth authentication.

## Functionality Overview

The bot provides the following core functionalities:

* **SDVX ID Linking:** Users can link their Discord account to their `eagle.ac` SDVX ID.  
* **Profile Statistics:** Retrieve and display a user's current Skill Level, Total Plays, Packet, Block, and Volforce (VF) from their `eagle.ac` profile.  
* **Check-in/Check-out System:** Users can "check-in" to mark the start of a session and "check-out" to see their progress (plays and VF gained) during that session.  
* **Arcade Leaderboard:** Display the top 10 players by Volforce for a configured arcade.  
* **Automated Web Interaction:** Utilizes a headed Chrome instance for initial OAuth login (to capture authentication cookies) and a headless Chrome instance for subsequent data scraping, ensuring no manual browser interaction is needed after the initial setup.

## Commands

All commands are prefixed with `/`

* `/linkid <SDVX_ID>`  
  * **Admin only:** Associates your Discord user ID with a specific SDVX ID. This is required before other commands can be used.  
  * Example: `/linkid 95688187`

* `/stats`  
  * Displays your current Skill Level, Total Plays, Packet, Block, and Volforce (VF) from your linked `eagle.ac` profile.

* `/checkin`  
  * Marks the start of your gaming session, recording your current plays and VF.

* `/checkout`  
  * Compares your current stats to your last check-in, showing plays and VF gained, as well as the session duration.

* `/leaderboard`  
  * Displays the top 10 players by Volforce for the configured arcade.

## File Structure and Explanation

The bot’s code is modularized into several Python files within the `bot/` directory to enhance organization and maintainability:

```
.
├── bot/
│   ├── checkin_store.py
│   ├── config.py
│   ├── discord_bot.py
│   ├── eagle_browser.py
│   ├── main.py
│   ├── __pycache__/
│   └── scraper.py
└── requirements.txt
```

### `bot/main.py`
- This is the primary entry point for the bot application.  
- It imports the core `bot` instance from `discord_bot.py` and environment variables (like `DISCORD_TOKEN`) via `config.py`.  
- **Modification Notes:** Generally, you shouldn’t need to alter this file other than to ensure it correctly imports and runs the main Discord bot.

### `bot/config.py`
- Manages all global configuration settings, environment variables, and static paths.  
- Stores `DISCORD_TOKEN`, `EAGLE_EMAIL`, `EAGLE_PASSWORD`, `CHROME_DRIVER_PATH`, `CHROME_USER_DATA_DIR`, `CHROME_PROFILE_DIR`, and the `ARCADE_ID`.  
- **Modification Notes:** Update this file to change tokens, credentials, paths, logging levels, or default IDs.

### `bot/eagle_browser.py`
- Encapsulates all Selenium-related functionality for interacting with web pages.  
- Defines the `EagleBrowser` class, which handles:
  - `run_oauth_login()`: Launches a visible Chrome session for OAuth to capture cookies.  
  - `init_headless_chrome()`: Starts a headless Chrome instance for scraping.  
  - `quit_headless()`: Shuts down the headless browser.  
- **Modification Notes:** Adjust here if the Chrome options, login flow, or error handling need updates.

### `bot/scraper.py`
- Contains functions dedicated to scraping `eagle.ac` pages.  
- Includes:
  - `parse_html()`: Helper for BeautifulSoup parsing.  
  - `scrape_profile_page()`: Extracts user profile stats.  
  - `scrape_leaderboard()`: Fetches the arcade top-10 leaderboard.  
  - `get_vf_from_arcade()`: Retrieves a player’s VF from scraped data.  
- **Modification Notes:** Update selectors or parsing logic if `eagle.ac`’s HTML structure changes.

### `bot/checkin_store.py`
- Manages in-memory storage for linked users and check-in sessions.  
- Defines:
  - `USER_LINKS` (`{ discord_user_id: sdvx_id }`)  
  - `CHECKIN_STORE` (`{ discord_user_id: { "vf": float, "plays": int, "timestamp": datetime } }`)  
- **Modification Notes:** Change storage schemas here if you need to persist additional data.

### `bot/discord_bot.py`
- Implements the Discord bot’s behavior:
  - Configures `Intents` and `commands.Bot`.  
  - Defines `on_ready()` for initial setup.  
  - All `/linkid`, `/stats`, `/checkin`, `/checkout`, and `/leaderboard` commands.  
- **Modification Notes:** Add new commands or alter existing command logic in this file.

## Requirements

```text
discord.py
python-dotenv
selenium
beautifulsoup4
```
