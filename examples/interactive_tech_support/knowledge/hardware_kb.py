"""Hardware troubleshooting knowledge base."""

from typing import Any

HARDWARE_KB: dict[str, dict[str, Any]] = {
    "printer": {
        "keywords": ["printer", "print", "printing", "paper jam", "ink", "toner"],
        "issues": {
            "not_printing": {
                "title": "Printer Not Printing",
                "steps": [
                    "1. Check if the printer is turned on and connected",
                    "2. Verify paper is loaded correctly",
                    "3. Check for paper jams",
                    "4. Ensure ink/toner levels are sufficient",
                    "5. Try restarting the printer",
                    "6. Reinstall printer drivers if needed",
                ],
                "follow_up": "Did these steps resolve your printing issue?",
            },
            "paper_jam": {
                "title": "Paper Jam",
                "steps": [
                    "1. Turn off the printer",
                    "2. Open all access doors",
                    "3. Gently remove jammed paper (pull in direction of paper path)",
                    "4. Check for torn paper pieces inside",
                    "5. Close all doors and restart the printer",
                ],
                "follow_up": "Is the paper jam cleared?",
            },
            "poor_quality": {
                "title": "Poor Print Quality",
                "steps": [
                    "1. Run the printer's built-in cleaning utility",
                    "2. Check ink/toner levels and replace if low",
                    "3. Ensure you're using the correct paper type",
                    "4. Clean the print heads manually if needed",
                    "5. Check print settings for quality options",
                ],
                "follow_up": "Has the print quality improved?",
            },
        },
    },
    "monitor": {
        "keywords": ["monitor", "screen", "display", "resolution", "blank", "flickering"],
        "issues": {
            "no_display": {
                "title": "No Display",
                "steps": [
                    "1. Check if monitor is powered on (look for LED indicator)",
                    "2. Verify cable connections (power and video)",
                    "3. Try a different video cable",
                    "4. Test with another monitor if available",
                    "5. Check graphics card seating",
                    "6. Try a different video port on your computer",
                ],
                "follow_up": "Is your display working now?",
            },
            "flickering": {
                "title": "Screen Flickering",
                "steps": [
                    "1. Check cable connections are secure",
                    "2. Try a different refresh rate in display settings",
                    "3. Update graphics drivers",
                    "4. Test with a different cable",
                    "5. Check for nearby electromagnetic interference",
                ],
                "follow_up": "Has the flickering stopped?",
            },
            "resolution": {
                "title": "Resolution Issues",
                "steps": [
                    "1. Right-click desktop and select Display Settings",
                    "2. Check if recommended resolution is selected",
                    "3. Update graphics drivers",
                    "4. Check cable supports your desired resolution",
                    "5. Verify monitor's native resolution in its manual",
                ],
                "follow_up": "Is the resolution issue resolved?",
            },
        },
    },
    "keyboard": {
        "keywords": ["keyboard", "keys", "typing", "key not working"],
        "issues": {
            "not_working": {
                "title": "Keyboard Not Working",
                "steps": [
                    "1. Check if keyboard is properly connected",
                    "2. Try a different USB port",
                    "3. Check if batteries are charged (wireless keyboards)",
                    "4. Test keyboard on another computer",
                    "5. Update or reinstall keyboard drivers",
                ],
                "follow_up": "Is your keyboard working now?",
            },
            "stuck_keys": {
                "title": "Stuck or Unresponsive Keys",
                "steps": [
                    "1. Turn keyboard upside down and gently shake out debris",
                    "2. Use compressed air to clean between keys",
                    "3. Carefully remove and clean affected keycap",
                    "4. Check for liquid damage",
                    "5. Consider keyboard replacement if issue persists",
                ],
                "follow_up": "Are the keys working properly now?",
            },
        },
    },
    "mouse": {
        "keywords": ["mouse", "cursor", "clicking", "scroll", "pointer"],
        "issues": {
            "not_moving": {
                "title": "Mouse Cursor Not Moving",
                "steps": [
                    "1. Check if mouse is properly connected",
                    "2. Try a different USB port",
                    "3. Replace batteries (wireless mouse)",
                    "4. Clean the optical sensor on the bottom",
                    "5. Try using a mouse pad",
                    "6. Update mouse drivers",
                ],
                "follow_up": "Is your mouse cursor moving now?",
            },
            "scroll_issues": {
                "title": "Scroll Wheel Issues",
                "steps": [
                    "1. Clean around the scroll wheel with compressed air",
                    "2. Check scroll settings in Mouse settings",
                    "3. Try updating mouse drivers",
                    "4. Test in different applications",
                ],
                "follow_up": "Is the scroll wheel working properly?",
            },
        },
    },
    "usb": {
        "keywords": ["usb", "port", "device not recognized", "usb drive"],
        "issues": {
            "not_recognized": {
                "title": "USB Device Not Recognized",
                "steps": [
                    "1. Try a different USB port",
                    "2. Restart your computer",
                    "3. Check Device Manager for unknown devices",
                    "4. Update USB drivers",
                    "5. Try the device on another computer",
                    "6. Check if the USB port is damaged",
                ],
                "follow_up": "Is the USB device now recognized?",
            },
        },
    },
    "power": {
        "keywords": ["power", "won't turn on", "battery", "charging", "shutdown"],
        "issues": {
            "wont_turn_on": {
                "title": "Computer Won't Turn On",
                "steps": [
                    "1. Check power cable is securely connected",
                    "2. Try a different power outlet",
                    "3. Check if power strip/surge protector is on",
                    "4. For laptops: remove battery, hold power for 30 seconds",
                    "5. Check for any LED indicators or sounds",
                    "6. Try a different power cable if available",
                ],
                "follow_up": "Is your computer powering on now?",
            },
            "random_shutdown": {
                "title": "Random Shutdowns",
                "steps": [
                    "1. Check for overheating - clean vents and fans",
                    "2. Run hardware diagnostics",
                    "3. Check power settings for sleep/hibernate",
                    "4. Update BIOS if available",
                    "5. Test RAM with memory diagnostic tool",
                ],
                "follow_up": "Has the random shutdown issue been resolved?",
            },
        },
    },
}


def search_hardware_kb(query: str) -> dict[str, Any] | None:
    """Search the hardware knowledge base for relevant issues.

    Args:
        query: The user's query string.

    Returns:
        The most relevant issue data, or None if no match found.
    """
    query_lower = query.lower()

    # Search through all categories
    for category, data in HARDWARE_KB.items():
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
