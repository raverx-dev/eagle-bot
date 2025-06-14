import json
import os
import re
from datetime import datetime, timezone

# We assume EagleBrowser is a class we can import, even if its code isn't written yet.
from bot.eagle_browser import EagleBrowser

class IdentityService:
    def __init__(self, users_file_path: str, browser: EagleBrowser):
        self.users_file_path = users_file_path
        self.browser = browser
        # Ensure the file exists on initialization
        self._read_users()

    def _read_users(self) -> dict:
        """Reads the user data from the JSON file, keyed by SDVX_ID."""
        try:
            with open(self.users_file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # If file doesn't exist or is empty/corrupt, create it and return empty dict
            self._write_users({})
            return {}

    def _write_users(self, data: dict):
        """Writes the user data to the JSON file."""
        with open(self.users_file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def link_user(self, discord_id: str, sdvx_id: str) -> bool:
        """Links a Discord ID to an existing or new player profile."""
        # Validate SDVX ID format: "12345678" or "1234-5678"
        if not re.fullmatch(r"\d{8}|\d{4}-\d{4}", sdvx_id):
            return False
        
        normalized_id = sdvx_id.replace("-", "")
        users = self._read_users()

        # Check if another user has already linked this SDVX ID
        for player_data in users.values():
            if player_data.get("discord_id") == discord_id:
                # This user is trying to link a new ID, so unlink the old one
                player_data["discord_id"] = None

        # Find or create the player profile for the sdvx_id
        player_profile = users.get(normalized_id, {"sdvx_id": normalized_id})
        player_profile["discord_id"] = discord_id
        
        users[normalized_id] = player_profile
        self._write_users(users)
        return True

    async def update_player_cache(self) -> list:
        """Scrapes the leaderboard and updates the local user cache."""
        try:
            # This is where the call to the (currently abstract) browser happens
            scraped_players = await self.browser.scrape_leaderboard()
        except Exception:
            # If scraping fails, re-raise the exception for the error handler to catch
            raise

        users = self._read_users()
        newly_discovered_players = []
        
        now_iso = datetime.now(timezone.utc).isoformat()

        for player_data in scraped_players:
            sdvx_id = player_data.get("sdvx_id", "").replace("-", "")
            if not sdvx_id:
                continue

            # Get the existing profile or create a new one
            existing_profile = users.get(sdvx_id, {})
            
            # If the player is new, add them to our discovery list
            if not existing_profile:
                 newly_discovered_players.append(player_data.get("player_name"))

            # Update the profile with new data, preserving existing discord_id
            updated_profile = {
                "sdvx_id": sdvx_id,
                "discord_id": existing_profile.get("discord_id"), # Preserve link
                "player_name": player_data.get("player_name"),
                "volforce": player_data.get("volforce"),
                "rank": player_data.get("rank"),
                "last_updated": now_iso
            }
            
            users[sdvx_id] = updated_profile
            
        self._write_users(users)
        return newly_discovered_players