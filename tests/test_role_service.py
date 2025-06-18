import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import discord # Needed for discord.utils.get and type hinting
from bot.core.role_service import RoleService

# --- Fixtures ---

@pytest.fixture
def mock_bot():
    """Provides a mock Discord bot instance."""
    bot = MagicMock(spec=discord.Client)
    return bot

@pytest.fixture
def guild_id():
    """Provides a dummy guild ID."""
    return 1234567890

@pytest.fixture
def role_name():
    """Provides a dummy role name."""
    return "Now Playing"

@pytest.fixture
def mock_guild(guild_id, role_name):
    """Provides a mock Discord Guild object."""
    guild = MagicMock(spec=discord.Guild)
    guild.id = guild_id
    guild.name = "Test Guild"

    # Create a mock role
    mock_role_obj = MagicMock(spec=discord.Role)
    mock_role_obj.name = role_name
    mock_role_obj.id = 9876543210

    guild.roles = [mock_role_obj] # Guild has the role
    return guild, mock_role_obj # Return both for convenience


@pytest.fixture
def mock_member():
    """Provides a mock Discord Member object."""
    member = MagicMock(spec=discord.Member)
    member.id = 1111111111
    member.display_name = "TestMember"
    member.add_roles = AsyncMock()
    member.remove_roles = AsyncMock()
    member.roles = [] # Start with no roles by default for tests to manipulate
    return member

# --- Tests ---

@pytest.mark.asyncio
async def test_fetch_guild_and_role_success(mock_bot, guild_id, mock_guild, role_name):
    """Tests successful fetching of guild and role."""
    mock_bot.get_guild.return_value = mock_guild[0] # mock_guild[0] is the guild object

    # Mock discord.utils.get as it's used internally
    with patch('discord.utils.get', return_value=mock_guild[1]) as mock_get_role: # mock_guild[1] is the role object
        service = RoleService(mock_bot, guild_id, role_name)
        result = await service._fetch_guild_and_role()

        assert result is True
        assert service.guild == mock_guild[0]
        assert service.role == mock_guild[1]
        mock_bot.get_guild.assert_called_once_with(guild_id)
        mock_get_role.assert_called_once_with(mock_guild[0].roles, name=role_name)

@pytest.mark.asyncio
async def test_fetch_guild_not_found(mock_bot, guild_id, role_name):
    """Tests failure when guild is not found."""
    mock_bot.get_guild.return_value = None

    service = RoleService(mock_bot, guild_id, role_name)
    result = await service._fetch_guild_and_role()

    assert result is False
    assert service.guild is None
    assert service.role is None
    mock_bot.get_guild.assert_called_once_with(guild_id)

@pytest.mark.asyncio
async def test_fetch_role_not_found(mock_bot, guild_id, mock_guild, role_name):
    """Tests failure when role is not found in guild."""
    mock_bot.get_guild.return_value = mock_guild[0]
    with patch('discord.utils.get', return_value=None) as mock_get_role:
        service = RoleService(mock_bot, guild_id, role_name)
        result = await service._fetch_guild_and_role()

        assert result is False
        assert service.guild == mock_guild[0]
        assert service.role is None
        mock_bot.get_guild.assert_called_once_with(guild_id)
        mock_get_role.assert_called_once_with(mock_guild[0].roles, name=role_name)

@pytest.mark.asyncio
async def test_assign_role_success(mock_bot, mock_guild, mock_member, guild_id, role_name):
    """Tests successful role assignment."""
    mock_bot.get_guild.return_value = mock_guild[0]
    mock_guild[0].get_member.return_value = mock_member

    mock_member.roles = [] # Ensure member does not initially have the role

    with patch('discord.utils.get', return_value=mock_guild[1]):
        service = RoleService(mock_bot, guild_id, role_name)
        result = await service.assign_role(str(mock_member.id)) # Pass ID as string

        assert result is True
        mock_member.add_roles.assert_awaited_once_with(mock_guild[1])

@pytest.mark.asyncio
async def test_assign_role_already_has_role(mock_bot, mock_guild, mock_member, guild_id, role_name):
    """Tests that no action is taken if member already has the role."""
    mock_bot.get_guild.return_value = mock_guild[0]
    mock_guild[0].get_member.return_value = mock_member

    mock_member.roles = [mock_guild[1]] # Ensure member already has the role

    with patch('discord.utils.get', return_value=mock_guild[1]):
        service = RoleService(mock_bot, guild_id, role_name)
        result = await service.assign_role(str(mock_member.id)) # Pass ID as string

        assert result is True
        mock_member.add_roles.assert_not_awaited() # Should not call add_roles

@pytest.mark.asyncio
async def test_assign_role_member_not_found(mock_bot, mock_guild, guild_id, role_name):
    """Tests failure when member is not found."""
    mock_bot.get_guild.return_value = mock_guild[0]
    mock_guild[0].get_member.return_value = None # Member not found, this bypasses int()

    with patch('discord.utils.get', return_value=mock_guild[1]):
        service = RoleService(mock_bot, guild_id, role_name)
        result = await service.assign_role("12345678901") # Use a valid-looking ID, but get_member returns None

        assert result is False
        mock_guild[0].get_member.assert_called_once_with(12345678901) # Check correct int conversion
        # No calls to add_roles

@pytest.mark.asyncio
async def test_remove_role_success(mock_bot, mock_guild, mock_member, guild_id, role_name):
    """Tests successful role removal."""
    mock_bot.get_guild.return_value = mock_guild[0]
    mock_guild[0].get_member.return_value = mock_member

    mock_member.roles = [mock_guild[1]] # Ensure member has the role initially

    with patch('discord.utils.get', return_value=mock_guild[1]):
        service = RoleService(mock_bot, guild_id, role_name)
        result = await service.remove_role(str(mock_member.id)) # Pass ID as string

        assert result is True
        mock_member.remove_roles.assert_awaited_once_with(mock_guild[1])

@pytest.mark.asyncio
async def test_remove_role_does_not_have_role(mock_bot, mock_guild, mock_member, guild_id, role_name):
    """Tests that no action is taken if member does not have the role."""
    mock_bot.get_guild.return_value = mock_guild[0]
    mock_guild[0].get_member.return_value = mock_member

    mock_member.roles = [] # Ensure member does not have the role

    with patch('discord.utils.get', return_value=mock_guild[1]):
        service = RoleService(mock_bot, guild_id, role_name)
        result = await service.remove_role(str(mock_member.id)) # Pass ID as string

        assert result is True
        mock_member.remove_roles.assert_not_awaited() # Should not call remove_roles

@pytest.mark.asyncio
async def test_remove_role_member_not_found(mock_bot, mock_guild, guild_id, role_name):
    """Tests failure when member is not found for role removal."""
    mock_bot.get_guild.return_value = mock_guild[0]
    mock_guild[0].get_member.return_value = None # Member not found, this bypasses int()

    with patch('discord.utils.get', return_value=mock_guild[1]):
        service = RoleService(mock_bot, guild_id, role_name)
        result = await service.remove_role("12345678901") # Use a valid-looking ID, but get_member returns None

        assert result is False
        mock_guild[0].get_member.assert_called_once_with(12345678901) # Check correct int conversion
        # No calls to remove_roles