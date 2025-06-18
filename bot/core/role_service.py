import discord
from bot.config import log

class RoleService:
    def __init__(self, bot: discord.Client, guild_id: int, role_name: str):
        self.bot = bot
        self.guild_id = guild_id
        self.role_name = role_name
        self.guild = None
        self.role = None

    async def _fetch_guild_and_role(self) -> bool:
        self.guild = self.bot.get_guild(self.guild_id)
        if not self.guild:
            log.error(f"RoleService: Guild with ID {self.guild_id} not found.")
            return False
        self.role = discord.utils.get(self.guild.roles, name=self.role_name)
        if not self.role:
            log.error(f"RoleService: Role '{self.role_name}' not found in guild '{self.guild.name}'.")
            return False
        return True

    async def assign_role(self, discord_id: str) -> bool:
        if not await self._fetch_guild_and_role():
            log.error(f"RoleService: Failed to fetch guild or role for assign_role({discord_id}).")
            return False
        member = self.guild.get_member(int(discord_id))
        if not member:
            log.error(f"RoleService: Member with ID {discord_id} not found in guild '{self.guild.name}'.")
            return False
        if self.role in member.roles:
            log.info(f"RoleService: Member {member} already has role '{self.role_name}'.")
            return True
        try:
            await member.add_roles(self.role)
            log.info(f"RoleService: Assigned role '{self.role_name}' to member {member}.")
            return True
        except Exception as e:
            log.error(f"RoleService: Failed to assign role '{self.role_name}' to member {member}: {e}")
            return False

    async def remove_role(self, discord_id: str) -> bool:
        if not await self._fetch_guild_and_role():
            log.error(f"RoleService: Failed to fetch guild or role for remove_role({discord_id}).")
            return False
        member = self.guild.get_member(int(discord_id))
        if not member:
            log.error(f"RoleService: Member with ID {discord_id} not found in guild '{self.guild.name}'.")
            return False
        if self.role not in member.roles:
            log.info(f"RoleService: Member {member} does not have role '{self.role_name}'.")
            return True
        try:
            await member.remove_roles(self.role)
            log.info(f"RoleService: Removed role '{self.role_name}' from member {member}.")
            return True
        except Exception as e:
            log.error(f"RoleService: Failed to remove role '{self.role_name}' from member {member}: {e}")
            return False
