import json
import os
import re
from datetime import datetime, timezone
from bot.eagle_browser import EagleBrowser

class IdentityService:
    def __init__(self, users_file_path: str, browser: EagleBrowser):
        self.users_file_path = users_file_path
        self.browser = browser

    def _read_users(self) -> dict:
        try:
            with open(self.users_file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _write_users(self, data: dict):
        with open(self.users_file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def get_user_by_discord_id(self, discord_id: str) -> dict | None:
        users = self._read_users()
        for sdvx_id, user_data in users.items():
            if user_data.get("discord_id") == discord_id:
                return user_data
        return None

    def link_user(self, discord_id: str, sdvx_id: str) -> bool:
        if not re.fullmatch(r"\d{8}|\d{4}-\d{4}", sdvx_id):
            return False
        
        normalized_id = sdvx_id.replace("-", "")
        users = self._read_users()

        for player_data in users.values():
            if player_data.get("discord_id") == discord_id:
                player_data["discord_id"] = None

        player_profile = users.get(normalized_id, {"sdvx_id": normalized_id})
        player_profile["discord_id"] = discord_id
        
        users[normalized_id] = player_profile
        self._write_users(users)
        return True

    async def update_player_cache(self) -> list:
        try:
            scraped_players = await self.browser.scrape_leaderboard()
        except Exception:
            raise

        users = self._read_users()
        newly_discovered_players = []
        now_iso = datetime.now(timezone.utc).isoformat()

        for player_data in scraped_players:
            sdvx_id = player_data.get("sdvx_id", "").replace("-", "")
            if not sdvx_id:
                continue

            existing_profile = users.get(sdvx_id, {})
            
            if not existing_profile:
                 newly_discovered_players.append(player_data.get("player_name"))

            updated_profile = {
                "sdvx_id": sdvx_id,
                "discord_id": existing_profile.get("discord_id"),
                "player_name": player_data.get("player_name"),
                "volforce": player_data.get("volforce"),
                "rank": player_data.get("rank"),
                "last_updated": now_iso
            }
            
            users[sdvx_id] = updated_profile
            
        self._write_users(users)
        return newly_discovered_players