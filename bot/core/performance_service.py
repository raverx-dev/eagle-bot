import json
from typing import Optional

class PerformanceService:
    # This data is sourced from a combination of the user's screenshot and community wikis for accuracy.
    VF_CLASSES = [
        {"name": "Sienna I", "vf": 0.000},
        {"name": "Sienna II", "vf": 2.500},
        {"name": "Sienna III", "vf": 5.000},
        {"name": "Sienna IV", "vf": 7.500},
        {"name": "Cobalt I", "vf": 10.000},
        {"name": "Cobalt II", "vf": 10.500},
        {"name": "Cobalt III", "vf": 11.000},
        {"name": "Cobalt IV", "vf": 11.500},
        {"name": "Dandelion I", "vf": 12.000},
        {"name": "Dandelion II", "vf": 12.500},
        {"name": "Dandelion III", "vf": 13.000},
        {"name": "Dandelion IV", "vf": 13.500},
        {"name": "Cyan I", "vf": 14.000},
        {"name": "Cyan II", "vf": 14.250},
        {"name": "Cyan III", "vf": 14.500},
        {"name": "Cyan IV", "vf": 14.750},
        {"name": "Scarlet I", "vf": 15.000},
        {"name": "Scarlet II", "vf": 15.250},
        {"name": "Scarlet III", "vf": 15.500},
        {"name": "Scarlet IV", "vf": 15.750},
        {"name": "Coral I", "vf": 16.000},
        {"name": "Coral II", "vf": 16.250},
        {"name": "Coral III", "vf": 16.500},
        {"name": "Coral IV", "vf": 16.750},
        {"name": "Argento I", "vf": 17.000},
        {"name": "Argento II", "vf": 17.250},
        {"name": "Argento III", "vf": 17.500},
        {"name": "Argento IV", "vf": 17.750},
        {"name": "Eldora I", "vf": 18.000},
        {"name": "Eldora II", "vf": 18.250},
        {"name": "Eldora III", "vf": 18.500},
        {"name": "Eldora IV", "vf": 18.750},
        {"name": "Crimson I", "vf": 19.000},
        {"name": "Crimson II", "vf": 19.250},
        {"name": "Crimson III", "vf": 19.500},
        {"name": "Crimson IV", "vf": 19.750},
        {"name": "Imperial I", "vf": 20.000},
        {"name": "Imperial II", "vf": 21.000},
        {"name": "Imperial III", "vf": 22.000},
        {"name": "Imperial IV", "vf": 23.000},
    ]

    def __init__(self, users_file_path: str):
        self.users_file_path = users_file_path
        # A direct dependency on IdentityService is better practice,
        # but for this change, we'll keep the current structure.
        self.identity_service = None

    def _read_users(self) -> dict:
        try:
            with open(self.users_file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def get_player_stats_from_cache(self, sdvx_id: str) -> dict | None:
        users = self._read_users()
        return users.get(sdvx_id)

    def get_arcade_leaderboard_from_cache(self, limit: int = 10) -> list:
        users = self._read_users()
        user_list = list(users.values())
        user_list = [u for u in user_list if "rank" in u]
        user_list.sort(key=lambda u: u["rank"])
        return user_list[:limit]

    def analyze_new_scores_for_records(self, recent_plays: list) -> list:
        if not recent_plays:
            return []
        return [play for play in recent_plays if play.get("is_new_record")]

    def check_for_vf_milestone(self, old_vf: Optional[float], new_vf: Optional[float]) -> str | None:
        """Checks if a player has crossed a VF threshold and returns the highest new class name."""
        # FIX: Add a guard clause to prevent crashing when VF values are None.
        if old_vf is None or new_vf is None:
            return None
            
        highest_achieved_class = None
        for vf_class in self.VF_CLASSES:
            if old_vf < vf_class["vf"] <= new_vf:
                highest_achieved_class = vf_class["name"]
        return highest_achieved_class