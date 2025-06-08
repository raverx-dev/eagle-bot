# Eagle Bot v2.0 Requirements Document

This document outlines the high-level summary of the existing Eagle Bot codebase, the requested feature list for v2.0, and a plan for necessary module changes, new modules, and their suggested implementation order.

---

## 1. High-Level Summary of Existing Code

The Eagle Bot project on GitHub (`raverx-dev/eagle-bot`) is a Python-based Discord bot designed to integrate with `eagle.ac` for Sound Voltex (SDVX) player statistics and arcade leaderboard tracking. The bot utilizes Selenium for web scraping and manages user authentication securely. The codebase is structured into several modular Python files, promoting organization and maintainability.

* `main.py`: The primary entry point for the bot, responsible for initializing components and orchestrating the overall bot operation.
* `config.py`: Manages application-wide configuration settings, including API keys, Discord tokens, and other adjustable parameters.
* `eagle_browser.py`: Handles the web browsing interactions with `eagle.ac`, likely abstracting Selenium calls for tasks such as logging in, navigating pages, and basic element interactions.
* `scraper.py`: Focuses on the data extraction logic, specifically designed to pull player profiles, scores, and leaderboard information from `eagle.ac` via the `eagle_browser`.
* `checkin_store.py`: Manages the persistence and retrieval of player check-in data, potentially tracking active sessions and linked player IDs.
* `discord_bot.py`: Implements the core Discord bot functionality, including processing commands received from users, managing bot responses, and sending messages or rich embeds to Discord channels. It acts as the interface between Discord and the bot's internal logic.

---

## 2. Original Feature List for v2.0

* **Auto Session Detection**
    * Bot automatically detects when a linked player begins a new session
    * Uses polling of player profile pages (not VF changes) to detect new scores
    * If no new scores for 10+ minutes, session auto-ends

* **Session Summary Posting**
    * Auto-posts session summary in #genchat on session end
        * Shows:
            * Player name
            * Leaderboard rank
            * VF and any VF gain
            * Skill level (DAN rank)
            * New clears and upscores (song, chart, grade, score)
            * Best new score
            * Duration and number of songs played

* **VF Rank-Up Announcements**
    * If VF crosses a threshold (e.g., 15.000 → Scarlet I), post a rank-up embed
    * Uses **Exceed Gear official VF rank names**

* **“Now Playing” Status**
    * Adds temporary role or emoji to nickname while session is active
    * Removed when session ends
    * Optional fallback via manual /checkin

* **Manual Session Reminders**
    * Manual /checkin disables auto-start
    * If no scores after 2 hours → reminder ping
    * If still no checkout after 4 hours → force checkout and notify user

* **Top 10 Leaderboard Monitor**
    * Monitors arcade leaderboard page during polling
    * If new player appears → post alert and @admin for approval
    * New player must be added manually via /linkid

* **Persistent Linked Player Storage**
    * Linked players persist between reboots
    * Stored in JSON with Discord user ID, Eagle ID, and optionally, Discord tag

* **Arcade Hours Restriction**
    * Scraping only occurs during:
        * Wed/Thu: 3pm–11pm
        * Fri: 3pm–12am
        * Sat: 12pm–12am
        * Sun: 12pm–10pm
    * Disabled Mon/Tue

* **Health Check Monitoring**
    * Basic ping to kailua.eagle.ac and eagle.ac
    * If site is down for >3 polling attempts → alert in #genchat

* **Fallback Support**
    * Manual commands (/checkin, /checkout, /stats, /leaderboard) remain functional
    * Auto-tracking does not interfere with manual session flow

---

## 3. Proposed Module Changes and New Modules (with Implementation Order)

To implement the v2.0 features, several existing modules will require significant enhancements, and new modules will be introduced to encapsulate specific functionalities.

### Phase 1: Foundational Enhancements & Core Data Handling

1.  **`checkin_store.py` Enhancement (Persistent Linked Player Storage):**
    * **Change:** Ensure robust JSON-based persistence for linked players (Discord ID, Eagle ID, Discord tag) and session data (start/end times, scores). If it's currently in-memory, implement file-based JSON read/write.
    * **Reasoning:** Essential for all other features that rely on persistent player data and session tracking.

2.  **`config.py` Expansion:**
    * **Change:** Add new configuration parameters for session detection thresholds (e.g., inactivity timeout), Discord channel IDs for summaries/alerts, and other customizable settings.
    * **Reasoning:** Centralizes all configurable aspects for easier management.

3.  **`eagle_browser.py` & `scraper.py` Refactoring:**
    * **Change:** Enhance scraping capabilities to reliably extract all necessary data points: current VF, DAN rank, individual score details (song, chart, grade, score), and comprehensive leaderboard information. This may involve more robust parsing logic.
    * **Reasoning:** Provides the raw data required for session detection, summaries, rank-ups, and leaderboard monitoring.

### Phase 2: Core Automation & Scheduling

4.  **New Module: `Scheduler.py` (Arcade Hours Restriction):**
    * **New Module:** This module will encapsulate the logic for checking the current time against defined arcade hours. It will provide methods to determine if polling and scraping operations should be active.
    * **Integration:** `main.py` or the `SessionManager` will call this module before initiating polling loops.
    * **Reasoning:** Ensures bot activity aligns with arcade operating times, reducing unnecessary resource usage and potential issues.

5.  **New Module: `HealthMonitor.py` (Health Check Monitoring):**
    * **New Module:** A dedicated module to periodically ping `kailua.eagle.ac` and `eagle.ac`. It will track consecutive failures and provide status updates.
    * **Integration:** `main.py` will periodically trigger checks, and `discord_bot.py` will be used for alerts.
    * **Reasoning:** Proactive monitoring to alert admins if the data source is unavailable.

### Phase 3: Session Management & Event Triggers

6.  **New Module: `SessionManager.py` (Auto Session Detection, Manual Session Reminders, Auto Checkout System):**
    * **New Module:** This will be the central orchestrator for session logic. It will:
        * Poll `scraper.py` for new scores for linked players.
        * Detect session starts and ends based on score activity and inactivity timeouts.
        * Track manual check-ins and disable auto-detection for those sessions.
        * Manage inactivity timers for manual sessions and trigger reminders/force checkouts.
        * Interact with `checkin_store.py` to update session states.
        * Trigger `discord_bot.py` for "Now Playing" status, reminders, and summary postings.
    * **Reasoning:** Consolidates complex session tracking and management logic into a single, cohesive unit.

### Phase 4: Discord Output & Specialized Monitors

7.  **`discord_bot.py` Enhancement (Session Summary Posting, VF Rank-Up Announcements, “Now Playing” Status, Manual Session Reminders & Notifications):**
    * **Change:** Implement methods to:
        * Format and send detailed session summary embeds (utilizing data from `scraper.py` and `SessionManager`).
        * Format and send VF rank-up announcement embeds.
        * Add/remove temporary Discord roles or modify nicknames for "Now Playing" status.
        * Send direct messages or channel pings for manual session reminders and forced checkouts.
    * **Reasoning:** Centralizes Discord output formatting and interaction.

8.  **New Module: `VFMonitor.py` (VF Rank-Up Announcements):**
    * **New Module:** This module will specifically handle parsing VF values from `scraper.py`'s output, detecting when a player crosses a defined threshold, and identifying the correct "Exceed Gear official VF rank name."
    * **Integration:** `SessionManager` or a dedicated periodic task will trigger `VFMonitor` checks.
    * **Reasoning:** Isolates the specific logic for VF rank progression.

9.  **New Module: `LeaderboardMonitor.py` (Top 10 Leaderboard Monitor):**
    * **New Module:** This module will use `scraper.py` to retrieve the current arcade top 10 leaderboard. It will compare this to a persistently stored list of known top players and detect new IDs.
    * **Integration:** `main.py` or a dedicated task will periodically trigger this monitor. `discord_bot.py` will be used to post alerts.
    * **Reasoning:** Encapsulates the specific logic for leaderboard change detection.

### Phase 5: Integration & Finalization

10. **`main.py` Orchestration & Fallback Support:**
    * **Change:** Update `main.py` to integrate all new modules (`SessionManager`, `Scheduler`, `HealthMonitor`, `LeaderboardMonitor`, `VFMonitor`) into the main bot loop.
    * **Verification:** Thoroughly test all existing manual commands (`/checkin`, `/checkout`, `/stats`, `/leaderboard`) to ensure they remain fully functional and are not interfered with by the new automated systems.
    * **Reasoning:** Finalizes the architecture and ensures all components work together seamlessly, while preserving existing functionality.

---

## 4. Implementation Checklist

This checklist outlines the steps required to implement the v2.0 features, following the proposed module changes and order.

* **Phase 1: Foundational Enhancements & Core Data Handling**
    * [ ] Enhance `checkin_store.py` for robust JSON persistence of linked players (Discord ID, Eagle ID, Discord tag).
    * [ ] Implement logic in `checkin_store.py` to store and retrieve active session data (start/end times, associated scores).
    * [ ] Expand `config.py` to include new configuration parameters (e.g., session inactivity timeout, Discord channel IDs for summaries/alerts).
    * [ ] Refactor `eagle_browser.py` to handle necessary navigation for new data points.
    * [ ] Enhance `scraper.py` to reliably extract all required data: current VF, DAN rank, individual score details (song, chart, grade, score), and the full leaderboard.

* **Phase 2: Core Automation & Scheduling**
    * [ ] Create `Scheduler.py` module to encapsulate arcade hours logic (Wed/Thu: 3pm–11pm, Fri: 3pm–12am, Sat: 12pm–12am, Sun: 12pm–10pm, disabled Mon/Tue).
    * [ ] Integrate `Scheduler.py` into `main.py` or polling loops to restrict activity to arcade hours.
    * [ ] Create `HealthMonitor.py` module to ping `kailua.eagle.ac` and `eagle.ac`.
    * [ ] Implement failure tracking (e.g., >3 polling attempts down) within `HealthMonitor.py`.
    * [ ] Integrate `HealthMonitor.py` into `main.py` for periodic checks.

* **Phase 3: Session Management & Event Triggers**
    * [ ] Create `SessionManager.py` module.
    * [ ] Implement auto session detection logic within `SessionManager.py` based on `scraper.py` polling for new scores.
    * [ ] Implement auto-checkout logic within `SessionManager.py` when no new scores for 10+ minutes.
    * [ ] Add logic to `SessionManager.py` to track manual `/checkin` sessions and disable auto-start for them.
    * [ ] Implement 2-hour inactivity reminder for manual sessions in `SessionManager.py`.
    * [ ] Implement 4-hour inactivity force checkout for manual sessions in `SessionManager.py`.
    * [ ] `SessionManager.py` should trigger notifications/status changes via `discord_bot.py`.

* **Phase 4: Discord Output & Specialized Monitors**
    * [ ] Enhance `discord_bot.py` to format and send detailed session summary embeds (Player name, rank, VF, DAN, new clears/upscores, best score, duration, songs played).
    * [ ] Enhance `discord_bot.py` to format and send VF rank-up embeds with official Exceed Gear names.
    * [ ] Implement "Now Playing" status in `discord_bot.py` (add/remove temporary role or modify nickname).
    * [ ] Implement reminder ping and force checkout notifications in `discord_bot.py`.
    * [ ] Create `VFMonitor.py` to detect VF threshold crossings and identify rank names.
    * [ ] Create `LeaderboardMonitor.py` to monitor the arcade leaderboard for new players in the top 10.
    * [ ] `LeaderboardMonitor.py` should trigger alerts and @admin mentions via `discord_bot.py` for new players.

* **Phase 5: Integration & Finalization**
    * [ ] Update `main.py` to properly instantiate and integrate all new modules (`SessionManager`, `Scheduler`, `HealthMonitor`, `LeaderboardMonitor`, `VFMonitor`).
    * [ ] Implement the main bot loop to orchestrate polling, session management, and monitoring activities based on `Scheduler.py`.
    * [ ] Thoroughly test all existing manual commands (`/checkin`, `/checkout`, `/stats`, `/leaderboard`) to ensure continued functionality and no interference from new auto-tracking.
    * [ ] Conduct comprehensive end-to-end testing of all new features.
    * [ ] Review and update documentation (e.g., README) to reflect new features and usage.
