# bot/core/identity_service.py
import json
import re
import asyncio
import os
from datetime import datetime, timezone
from bot.eagle_browser import EagleBrowser
from bot.config import log

class IdentityService:
    def __init__(self, users_file_path: str, browser: EagleBrowser):
        self.users_file_path = users_file_path
        self.browser = browser

    def _blocking_read_users(self) -> dict:
        try:
            with open(self.users_file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
        except Exception as e:
            log.error(f"!!! FAILED TO READ from {self.users_file_path}: {e}", exc_info=True)
            return {}

    def _blocking_write_users(self, data: dict):
        try:
            os.makedirs(os.path.dirname(self.users_file_path), exist_ok=True)
            with open(self.users_file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            log.error(f"!!! FAILED TO WRITE to {self.users_file_path}: {e}", exc_info=True)

    async def _read_users(self) -> dict:
        return await asyncio.to_thread(self._blocking_read_users)

    async def _write_users(self, data: dict):
        await asyncio.to_thread(self._blocking_write_users, data)

    async def get_user_by_discord_id(self, discord_id: str) -> dict | None:
        users = await self._read_users()
        for sdvx_id, user_data in users.items():
            if user_data.get("discord_id") == discord_id:
                return user_data
        return None

    async def link_user(self, discord_id: str, sdvx_id: str) -> bool:
        if not re.fullmatch(r"\d{8}|\d{4}-\d{4}", sdvx_id): return False
        
        normalized_id = sdvx_id.replace("-", "")
        users = await self._read_users()

        for player_data in users.values():
            if player_data.get("discord_id") == discord_id:
                player_data["discord_id"] = None

        player_profile = users.get(normalized_id, {"sdvx_id": normalized_id})
        
        profile_data = await self.browser.scrape_player_profile(normalized_id)
        if profile_data and profile_data.get("player_name"):
            player_profile["player_name"] = profile_data["player_name"]

        player_profile["discord_id"] = discord_id
        player_profile["last_updated"] = datetime.now(timezone.utc).isoformat()

        users[normalized_id] = player_profile
        await self._write_users(users)
        return True

    async def force_unlink(self, discord_id_to_unlink: str) -> bool:
        users = await self._read_users()
        user_profile = await self.get_user_by_discord_id(discord_id_to_unlink)
        if not user_profile: return False
        user_profile["discord_id"] = None
        await self._write_users(users)
        return True

    async def update_player_cache(self) -> list:
        try:
            leaderboard_players = await self.browser.scrape_leaderboard()
        except Exception as e:
            log.error(f"Leaderboard scraping failed in update_player_cache: {e}", exc_info=True)
            raise

        users = await self._read_users()
        newly_discovered_players = []
        now_iso = datetime.now(timezone.utc).isoformat()

        # Pass 1: Discover new players from the leaderboard and update core stats
        for lb_player_data in leaderboard_players:
            sdvx_id = lb_player_data.get("sdvx_id", "").replace("-", "")
            if not sdvx_id: continue

            if sdvx_id not in users:
                newly_discovered_players.append(lb_player_data.get("player_name"))
                users[sdvx_id] = { "sdvx_id": sdvx_id, "discord_id": None }
                log.info(f"IDENTITY_SERVICE: Discovered new player from leaderboard: {lb_player_data.get('player_name')}")
            
            user_profile = users[sdvx_id]
            user_profile["player_name"] = lb_player_data.get("player_name", user_profile.get("player_name"))
            user_profile["volforce"] = lb_player_data.get("volforce", user_profile.get("volforce"))
            user_profile["rank"] = lb_player_data.get("rank", user_profile.get("rank"))
            user_profile["last_updated"] = now_iso
            log.debug(f"IDENTITY_SERVICE: Updated existing player {user_profile.get('player_name')} from leaderboard.")

        # Pass 2: Enrich all known players with recent_plays from individual profile scrapes
        current_sdvx_ids = list(users.keys())
        for sdvx_id in current_sdvx_ids:
            user_profile = users[sdvx_id]
            profile_data_from_scrape = await self.browser.scrape_player_profile(sdvx_id)
            
            if profile_data_from_scrape:
                if profile_data_from_scrape.get("player_name") is not None:
                    user_profile["player_name"] = profile_data_from_scrape["player_name"]
                
                user_profile["recent_plays"] = profile_data_from_scrape.get("recent_plays", [])
                user_profile["last_updated"] = now_iso
                log.debug(f"IDENTITY_SERVICE: Enriched profile for {sdvx_id} with recent plays.")
            else:
                log.warning(f"IDENTITY_SERVICE: Failed to scrape individual profile for {sdvx_id}. Recent plays may be missing.")
                user_profile["recent_plays"] = user_profile.get("recent_plays", [])
                user_profile["last_updated"] = now_iso

        await self._write_users(users)
        log.info(f"IDENTITY_SERVICE: Completed player cache update. Discovered {len(newly_discovered_players)} new players.")
        return newly_discovered_players