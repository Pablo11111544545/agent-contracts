"""Software troubleshooting knowledge base."""

from typing import Any

SOFTWARE_KB: dict[str, dict[str, Any]] = {
    "crash": {
        "keywords": ["crash", "freeze", "not responding", "stopped working", "hung"],
        "issues": {
            "app_crash": {
                "title": "Application Crash",
                "steps": [
                    "1. Save your work in other applications",
                    "2. Force close the crashed application (Task Manager > End Task)",
                    "3. Restart the application",
                    "4. Check for application updates",
                    "5. Clear application cache/temporary files",
                    "6. Reinstall the application if problem persists",
                ],
                "follow_up": "Is the application working now?",
            },
            "system_freeze": {
                "title": "System Freeze",
                "steps": [
                    "1. Wait a few minutes - system may recover",
                    "2. Try pressing Ctrl+Alt+Delete",
                    "3. If possible, save work and restart",
                    "4. Check for driver updates after restart",
                    "5. Run Windows Memory Diagnostic",
                    "6. Check Event Viewer for error logs",
                ],
                "follow_up": "Has the freezing issue been resolved?",
            },
        },
    },
    "slow_computer": {
        "keywords": ["slow", "laggy", "performance", "takes forever", "sluggish"],
        "issues": {
            "general_slowness": {
                "title": "Slow Computer Performance",
                "steps": [
                    "1. Open Task Manager and check CPU/Memory usage",
                    "2. Close unnecessary background applications",
                    "3. Check available disk space (keep >10% free)",
                    "4. Run disk cleanup utility",
                    "5. Scan for malware using your antivirus",
                    "6. Disable unnecessary startup programs",
                    "7. Consider adding more RAM if consistently slow",
                ],
                "follow_up": "Has your computer speed improved?",
            },
            "slow_startup": {
                "title": "Slow Startup",
                "steps": [
                    "1. Open Task Manager > Startup tab",
                    "2. Disable unnecessary startup programs",
                    "3. Run disk cleanup",
                    "4. Check for Windows updates",
                    "5. Consider upgrading to SSD if using HDD",
                ],
                "follow_up": "Has startup time improved?",
            },
        },
    },
    "install": {
        "keywords": ["install", "installation", "setup", "can't install", "won't install"],
        "issues": {
            "install_failed": {
                "title": "Installation Failed",
                "steps": [
                    "1. Run installer as Administrator",
                    "2. Temporarily disable antivirus",
                    "3. Check available disk space",
                    "4. Download a fresh copy of the installer",
                    "5. Check if previous version needs uninstalling first",
                    "6. Check system requirements are met",
                ],
                "follow_up": "Were you able to install the software?",
            },
        },
    },
    "update": {
        "keywords": ["update", "updating", "update failed", "won't update"],
        "issues": {
            "update_failed": {
                "title": "Update Failed",
                "steps": [
                    "1. Restart your computer and try again",
                    "2. Check your internet connection",
                    "3. Ensure enough disk space is available",
                    "4. Run Windows Update Troubleshooter",
                    "5. Clear Windows Update cache",
                    "6. Try downloading update manually",
                ],
                "follow_up": "Did the update complete successfully?",
            },
        },
    },
    "error": {
        "keywords": ["error", "error message", "error code", "exception"],
        "issues": {
            "generic_error": {
                "title": "Application Error",
                "steps": [
                    "1. Note down the exact error message or code",
                    "2. Search for the specific error online",
                    "3. Restart the application",
                    "4. Check for application updates",
                    "5. Repair or reinstall the application",
                    "6. Check application logs for more details",
                ],
                "follow_up": "Has the error been resolved?",
            },
            "blue_screen": {
                "title": "Blue Screen Error (BSOD)",
                "steps": [
                    "1. Note the stop code displayed",
                    "2. Restart your computer",
                    "3. Check for recent driver or software changes",
                    "4. Run Windows Memory Diagnostic",
                    "5. Update all drivers",
                    "6. Run System File Checker (sfc /scannow)",
                ],
                "follow_up": "Has the blue screen error stopped occurring?",
            },
        },
    },
    "virus": {
        "keywords": ["virus", "malware", "infected", "antivirus", "security"],
        "issues": {
            "malware_suspected": {
                "title": "Suspected Malware Infection",
                "steps": [
                    "1. Disconnect from the internet",
                    "2. Run a full antivirus scan",
                    "3. Run Malwarebytes or similar anti-malware tool",
                    "4. Boot into Safe Mode for stubborn malware",
                    "5. Remove suspicious programs from Add/Remove Programs",
                    "6. Reset browser settings if affected",
                    "7. Change important passwords after cleaning",
                ],
                "follow_up": "Has the malware been removed?",
            },
        },
    },
    "browser": {
        "keywords": ["browser", "chrome", "firefox", "edge", "safari", "webpage"],
        "issues": {
            "browser_slow": {
                "title": "Slow Browser",
                "steps": [
                    "1. Clear browser cache and cookies",
                    "2. Disable unnecessary extensions",
                    "3. Update your browser",
                    "4. Check if issue is site-specific",
                    "5. Reset browser to default settings",
                    "6. Try a different browser",
                ],
                "follow_up": "Is your browser performing better?",
            },
            "page_not_loading": {
                "title": "Page Not Loading",
                "steps": [
                    "1. Check your internet connection",
                    "2. Try refreshing the page (Ctrl+F5)",
                    "3. Clear browser cache",
                    "4. Try incognito/private mode",
                    "5. Disable extensions temporarily",
                    "6. Check if site is down using isitdown.us",
                ],
                "follow_up": "Is the page loading now?",
            },
        },
    },
}


def search_software_kb(query: str) -> dict[str, Any] | None:
    """Search the software knowledge base for relevant issues.

    Args:
        query: The user's query string.

    Returns:
        The most relevant issue data, or None if no match found.
    """
    query_lower = query.lower()

    # Search through all categories
    for category, data in SOFTWARE_KB.items():
        keywords = data.get("keywords", [])

        # Check if any keyword matches
        for keyword in keywords:
            if keyword in query_lower:
                # Return the first relevant issue
                issues = data.get("issues", {})
                if issues:
                    # Try to find specific issue based on query
                    for issue_key, issue_data in issues.items():
                        issue_title = issue_data.get("title", "").lower()
                        if any(word in query_lower for word in issue_title.split()):
                            return {
                                "category": category,
                                "issue": issue_key,
                                **issue_data,
                            }

                    # Return first issue as default
                    first_issue = next(iter(issues.items()))
                    return {
                        "category": category,
                        "issue": first_issue[0],
                        **first_issue[1],
                    }

    return None
