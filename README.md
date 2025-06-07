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

All commands are prefixed with `/`.

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

The bot's code is modularized into several Python files within the `bot/` directory to enhance organization and maintainability.

.
├── bot
│   ├── checkin_store.py
│   ├── config.py
│   ├── discord_bot.py
│   ├── eagle_browser.py
│   ├── main.py
│   ├── __pycache__
│   └── scraper.py
└── requirements.txt

* **`bot/main.py`**
    * This is the primary entry point for the bot application.
    * It imports the core `bot` instance from `discord_bot.py` and the `DISCORD_BOT_TOKEN` from `config.py`.
    * **Modification Notes:** This file should generally not be modified beyond ensuring it correctly imports and runs the main Discord bot instance.

* **`bot/config.py`**
    * Manages all global configuration settings, environment variables, and static paths.
    * Stores `DISCORD_BOT_TOKEN`, `EAGLE_EMAIL`, `EAGLE_PASSWORD`, `CHROME_DRIVER_PATH`, `CHROME_USER_DATA_DIR`, `CHROME_PROFILE_DIR`, and the `ARCADE_ID`.
    * Also sets up the basic logging configuration.
    * **Modification Notes:** Modify this file to update API tokens, email/password for `eagle.ac`, ChromeDriver paths, user profile directories, logging levels, or the default `ARCADE_ID`.

* **`bot/eagle_browser.py`**
    * Encapsulates all Selenium-related functionalities for interacting with web pages.
    * Contains the `EagleBrowser` class, which handles:
        * `run_oauth_login()`: For the initial visible Chrome session to perform OAuth authentication and save cookies.
        * `init_headless_chrome()`: For launching the invisible headless Chrome instance for scraping.
        * `quit_headless()`: To properly close the headless browser.
    * Instantiates `BROWSER = EagleBrowser()` as a singleton object.
    * **Modification Notes:** Any changes related to how the bot interacts with Chrome (e.g., driver options, login flow adjustments, error handling during browser launch) should be made here.

* **`bot/scraper.py`**
    * Contains functions specifically responsible for scraping data from `eagle.ac`.
    * Includes:
        * `parse_html()`: A helper for parsing HTML with BeautifulSoup.
        * `scrape_profile_page()`: Extracts user profile statistics.
        * `scrape_leaderboard()`: Extracts the arcade top 10 leaderboard data.
        * `get_vf_from_arcade()`: Looks up a player's VF from the scraped leaderboard.
    * **Modification Notes:** If the HTML structure of `eagle.ac` changes, or if new data points need to be scraped, modifications will be necessary in this file.

* **`bot/checkin_store.py`**
    * Manages the in-memory data structures for linking Discord users to SDVX IDs and storing check-in information.
    * Contains the `USER_LINKS` dictionary (`{ discord_user_id (int) : sdvx_id (str) }`).
    * Contains the `CHECKIN_STORE` dictionary (`{ discord_user_id: { "time": datetime, "plays": int, "vf": float } }`).
    * **Modification Notes:** This file defines the in-memory storage schemas. If the structure of linked users or check-in data needs to change, update this file.

* **`bot/discord_bot.py`**
    * Defines the Discord bot's main functionalities, including:
        * Discord `Intents` and `commands.Bot` setup.
        * `on_ready()`: The event handler for when the bot comes online, including initial OAuth and headless browser setup.
        * All Discord command implementations (`@bot.command` decorators for `/linkid`, `/stats`, `/checkin`, `/checkout`, `/leaderboard`).
    * **Modification Notes:** This is where you would add new Discord commands, modify existing command logic, change bot permissions, or alter the Discord-specific responses and embeds.
