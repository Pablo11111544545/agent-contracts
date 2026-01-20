"""Network troubleshooting knowledge base."""

from typing import Any

NETWORK_KB: dict[str, dict[str, Any]] = {
    "wifi": {
        "keywords": ["wifi", "wi-fi", "wireless", "signal", "hotspot"],
        "issues": {
            "no_connection": {
                "title": "WiFi Not Connecting",
                "steps": [
                    "1. Verify WiFi is enabled on your device",
                    "2. Check if other devices can connect to the same network",
                    "3. Restart your router/modem (unplug for 30 seconds)",
                    "4. Forget the network and reconnect",
                    "5. Check for wireless driver updates",
                    "6. Move closer to the router",
                    "7. Check if network is hidden and enter SSID manually",
                ],
                "follow_up": "Are you connected to WiFi now?",
            },
            "slow_wifi": {
                "title": "Slow WiFi Speed",
                "steps": [
                    "1. Run a speed test at speedtest.net",
                    "2. Check for interference from other devices",
                    "3. Try changing WiFi channel in router settings",
                    "4. Move router to a central location",
                    "5. Consider using 5GHz band if available",
                    "6. Check for bandwidth-heavy applications",
                    "7. Update router firmware",
                ],
                "follow_up": "Has your WiFi speed improved?",
            },
            "keeps_disconnecting": {
                "title": "WiFi Keeps Disconnecting",
                "steps": [
                    "1. Check WiFi signal strength",
                    "2. Update wireless network drivers",
                    "3. Disable power saving for WiFi adapter",
                    "4. Reset network settings",
                    "5. Check for router overheating",
                    "6. Try a different WiFi channel",
                ],
                "follow_up": "Is your WiFi connection stable now?",
            },
        },
    },
    "internet": {
        "keywords": ["internet", "online", "website", "connection", "no internet"],
        "issues": {
            "no_internet": {
                "title": "No Internet Access",
                "steps": [
                    "1. Check if WiFi/Ethernet is connected",
                    "2. Try accessing different websites",
                    "3. Restart router and modem (unplug for 30 seconds)",
                    "4. Run network troubleshooter",
                    "5. Flush DNS cache (ipconfig /flushdns)",
                    "6. Try using Google DNS (8.8.8.8)",
                    "7. Contact your ISP if problem persists",
                ],
                "follow_up": "Do you have internet access now?",
            },
            "intermittent": {
                "title": "Intermittent Internet Connection",
                "steps": [
                    "1. Check cable connections",
                    "2. Monitor connection during outages",
                    "3. Check for ISP outages in your area",
                    "4. Update network adapter drivers",
                    "5. Check router logs for errors",
                    "6. Consider replacing old network equipment",
                ],
                "follow_up": "Has your internet connection stabilized?",
            },
        },
    },
    "vpn": {
        "keywords": ["vpn", "virtual private network", "tunnel", "remote access"],
        "issues": {
            "vpn_not_connecting": {
                "title": "VPN Not Connecting",
                "steps": [
                    "1. Check your internet connection first",
                    "2. Verify VPN credentials are correct",
                    "3. Try a different VPN server",
                    "4. Check if firewall is blocking VPN",
                    "5. Update VPN client software",
                    "6. Try different VPN protocol (OpenVPN, IKEv2)",
                    "7. Contact VPN support or IT department",
                ],
                "follow_up": "Is your VPN connecting now?",
            },
            "vpn_slow": {
                "title": "Slow VPN Connection",
                "steps": [
                    "1. Try a server closer to your location",
                    "2. Switch to a faster VPN protocol",
                    "3. Check base internet speed without VPN",
                    "4. Close bandwidth-heavy applications",
                    "5. Try connecting via Ethernet instead of WiFi",
                ],
                "follow_up": "Has your VPN speed improved?",
            },
        },
    },
    "dns": {
        "keywords": ["dns", "domain", "name resolution", "can't find server"],
        "issues": {
            "dns_issues": {
                "title": "DNS Resolution Problems",
                "steps": [
                    "1. Flush DNS cache: ipconfig /flushdns (Windows)",
                    "2. Try using public DNS: 8.8.8.8 or 1.1.1.1",
                    "3. Check if issue is site-specific",
                    "4. Restart your router",
                    "5. Check hosts file for incorrect entries",
                    "6. Reset network settings",
                ],
                "follow_up": "Are websites loading properly now?",
            },
        },
    },
    "router": {
        "keywords": ["router", "modem", "gateway", "network device"],
        "issues": {
            "router_issues": {
                "title": "Router Problems",
                "steps": [
                    "1. Power cycle the router (unplug for 30 seconds)",
                    "2. Check all cable connections",
                    "3. Look for overheating (ensure ventilation)",
                    "4. Update router firmware",
                    "5. Reset to factory settings if needed",
                    "6. Check router logs for errors",
                ],
                "follow_up": "Is your router working properly now?",
            },
            "cant_access_settings": {
                "title": "Cannot Access Router Settings",
                "steps": [
                    "1. Confirm router IP address (usually 192.168.1.1 or 192.168.0.1)",
                    "2. Try different browsers",
                    "3. Clear browser cache",
                    "4. Connect via Ethernet instead of WiFi",
                    "5. Check if router is in bridge mode",
                    "6. Try default login credentials (check router label)",
                ],
                "follow_up": "Can you access router settings now?",
            },
        },
    },
    "ethernet": {
        "keywords": ["ethernet", "wired", "lan", "network cable", "rj45"],
        "issues": {
            "no_ethernet": {
                "title": "Ethernet Not Working",
                "steps": [
                    "1. Check if cable is firmly connected at both ends",
                    "2. Try a different Ethernet cable",
                    "3. Try a different port on your router",
                    "4. Check for link lights on network port",
                    "5. Update network adapter drivers",
                    "6. Run network troubleshooter",
                ],
                "follow_up": "Is your Ethernet connection working now?",
            },
        },
    },
}


def search_network_kb(query: str) -> dict[str, Any] | None:
    """Search the network knowledge base for relevant issues.

    Args:
        query: The user's query string.

    Returns:
        The most relevant issue data, or None if no match found.
    """
    query_lower = query.lower()

    # Search through all categories
    for category, data in NETWORK_KB.items():
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
