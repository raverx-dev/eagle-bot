"""
Handles all web scraping and parsing of HTML content from the eagle.ac website.

This module contains functions responsible for extracting specific data
such as player statistics, leaderboard information, and Volforce (VF)
from the scraped web pages.
"""
import logging
from datetime import datetime, timedelta

from bs4 import BeautifulSoup

log = logging.getLogger(__name__)


def parse_html(html_content):
    """
    Parses HTML content using BeautifulSoup and returns a BeautifulSoup object.
    """
    return BeautifulSoup(html_content, "html.parser")


def scrape_profile_page(driver, sdvx_id: str):
    """
    Scrapes a user's profile page for skill level, total play count,
    and last 5 plays.

    Args:
        driver: The Selenium WebDriver instance.
        sdvx_id: The SDVX ID of the player to scrape.

    Returns:
        A dictionary containing 'skill_level', 'total_plays',
        and 'last_5_plays', or None if scraping fails.
    """
    log.info(f"Scraping profile page for SDVX ID: {sdvx_id}")
    profile_url = f"https://eagle.ac/game/sdvx/profile/{sdvx_id}"
    try:
        driver.get(profile_url)
        soup = parse_html(driver.page_source)

        skill_level_elem = soup.find("h3", class_="text-warning")
        skill_level = (
            skill_level_elem.text.strip()
            if skill_level_elem else "N/A"
        )

        total_plays_elem = soup.find(
            "h4",
            class_="display-4",
            string=lambda text: "total" in text.lower(),
        )
        if total_plays_elem:
            total_plays = int(
                "".join(filter(str.isdigit, total_plays_elem.text))
            )
        else:
            total_plays = 0

        last_5_plays = []
        last_plays_list = soup.find(
            "ul",
            class_="list-group list-group-flush "
                   "border-top border-dark",
        )
        if last_plays_list:
            for item in last_plays_list.find_all(
                "li", class_="list-group-item bg-dark"
            ):
                title_elem = item.find(
                    "h6", class_="text-warning"
                )
                title = (
                    title_elem.text.strip()
                    if title_elem else "Unknown Title"
                )

                difficulty_elem = item.find(
                    "small", class_="text-white-50"
                )
                if difficulty_elem:
                    parts = difficulty_elem.text.strip().split(" ")
                    difficulty = parts[0]
                    level = parts[1] if len(parts) > 1 else "N/A"
                else:
                    difficulty = "N/A"
                    level = "N/A"

                score_elem = item.find(
                    "small", class_="text-primary"
                )
                score = (
                    score_elem.text.strip()
                    if score_elem else "N/A"
                )

                timestamp_elem = item.find(
                    "small", class_="text-success"
                )
                time_ago = "N/A"
                if timestamp_elem:
                    full_timestamp_str = timestamp_elem.text.strip()
                    try:
                        date_part_str = full_timestamp_str.split(
                            " at "
                        )[0].strip()
                        try:
                            play_datetime = datetime.strptime(
                                date_part_str, "%b. %d, %Y"
                            )
                        except ValueError:
                            play_datetime = datetime.strptime(
                                date_part_str, "%b. %d"
                            )
                            play_datetime = (
                                play_datetime.replace(
                                    year=datetime.now().year
                                )
                            )

                        time_diff = datetime.now() - play_datetime
                        if time_diff < timedelta(minutes=60):
                            minutes = int(
                                time_diff.total_seconds() / 60
                            )
                            time_ago = (
                                f"{minutes} min ago"
                                if minutes > 1 else "1 min ago"
                            )
                        elif time_diff < timedelta(hours=24):
                            hours = int(
                                time_diff.total_seconds() / 3600
                            )
                            time_ago = (
                                f"{hours} h ago"
                                if hours > 1 else "1 h ago"
                            )
                        elif time_diff < timedelta(days=30):
                            days = time_diff.days
                            time_ago = (
                                f"{days} d ago"
                                if days > 1 else "1 d ago"
                            )
                        else:
                            months = int(time_diff.days / 30)
                            time_ago = (
                                f"{months} mo ago"
                                if months > 1 else "1 mo ago"
                            )
                    except ValueError:
                        log.warning(
                            f"Could not parse timestamp: "
                            f"{full_timestamp_str}"
                        )
                        time_ago = "N/A"

                last_5_plays.append({
                    "title": title,
                    "difficulty": difficulty,
                    "level": level,
                    "score": score,
                    "time_ago": time_ago,
                })

        return {
            "skill_level": skill_level,
            "total_plays": total_plays,
            "last_5_plays": last_5_plays,
        }
    except Exception as e:
        log.error(f"Error scraping profile page for {sdvx_id}: {e}")
        return None


def scrape_leaderboard(driver):
    """
    Scrapes the arcade's top-10 VF leaderboard.

    Args:
        driver: The Selenium WebDriver instance.

    Returns:
        A list of dictionaries, each containing 'rank', 'name', and 'vf'.
    """
    log.info("Scraping leaderboard page.")
    leaderboard_url = (
        "https://eagle.ac/arcade/leaderboard/sdvx/vf/1"
    )
    try:
        driver.get(leaderboard_url)
        soup = parse_html(driver.page_source)

        leaderboard_data_list = []
        table_rows = soup.find_all("tr")
        for row in table_rows:
            columns = row.find_all("td")
            if len(columns) >= 3:
                rank = int(columns[0].text.strip())
                name = columns[1].text.strip()
                vf_text = columns[2].text.replace(
                    ",", ""
                ).strip()
                vf = int(vf_text)
                leaderboard_data_list.append({
                    "rank": rank, "name": name, "vf": vf
                })
        return leaderboard_data_list[:10]
    except Exception as e:
        log.error(f"Error scraping leaderboard: {e}")
        return []


def get_vf_from_arcade(driver, sdvx_id: str):
    """
    Gets Volforce (VF) for a given SDVX ID from the arcade top-10 leaderboard.

    This function attempts to find the player's VF by looking them up
    in the scraped top-10 leaderboard data. Note that the leaderboard
    only provides player names, not SDVX IDs directly. A mapping or
    additional logic would be needed for a robust lookup.

    Args:
        driver: The Selenium WebDriver instance.
        sdvx_id: The SDVX ID of the player to find.

    Returns:
        The player's VF as an int if found in the top 10, otherwise 0.
    """
    log.info(
        f"Getting VF for SDVX ID: {sdvx_id} from arcade leaderboard."
    )
    _ = scrape_leaderboard(driver)
    # Placeholder behavior until mapping is implemented.
    return 0  # Default/not found VF
