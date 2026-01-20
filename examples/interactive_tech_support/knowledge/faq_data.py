"""General FAQ data for common tech questions."""

from typing import Any

FAQ_DATA: list[dict[str, Any]] = [
    {
        "keywords": ["password", "forgot password", "reset password", "change password"],
        "question": "How do I reset my password?",
        "answer": {
            "title": "Password Reset Guide",
            "content": (
                "To reset your password:\n"
                "1. Go to the login page\n"
                "2. Click 'Forgot Password' or 'Reset Password'\n"
                "3. Enter your email address\n"
                "4. Check your email for reset link\n"
                "5. Follow the link to create a new password\n"
                "\nTip: Use a strong password with letters, numbers, and symbols."
            ),
        },
    },
    {
        "keywords": ["backup", "data backup", "save data", "cloud backup"],
        "question": "How do I backup my data?",
        "answer": {
            "title": "Data Backup Options",
            "content": (
                "There are several ways to backup your data:\n\n"
                "1. Cloud Storage: Use services like Google Drive, Dropbox, or OneDrive\n"
                "2. External Drive: Copy files to an external hard drive or USB\n"
                "3. Built-in Backup: Use Windows Backup or Time Machine (Mac)\n"
                "4. Automated Backup: Set up scheduled backups\n"
                "\nRecommendation: Follow the 3-2-1 rule - 3 copies, 2 different media, "
                "1 offsite."
            ),
        },
    },
    {
        "keywords": ["screenshot", "screen capture", "print screen", "capture screen"],
        "question": "How do I take a screenshot?",
        "answer": {
            "title": "Screenshot Methods",
            "content": (
                "Windows:\n"
                "- Press PrtScn for full screen\n"
                "- Press Alt+PrtScn for active window\n"
                "- Press Win+Shift+S for Snipping Tool\n\n"
                "Mac:\n"
                "- Press Cmd+Shift+3 for full screen\n"
                "- Press Cmd+Shift+4 to select area\n"
                "- Press Cmd+Shift+5 for screenshot options"
            ),
        },
    },
    {
        "keywords": ["zoom", "zoom in", "zoom out", "magnify", "text size"],
        "question": "How do I zoom in or change text size?",
        "answer": {
            "title": "Zoom and Text Size",
            "content": (
                "Browser/Applications:\n"
                "- Ctrl + Plus (+) to zoom in\n"
                "- Ctrl + Minus (-) to zoom out\n"
                "- Ctrl + 0 to reset zoom\n\n"
                "System-wide (Windows):\n"
                "- Settings > Display > Scale and layout\n\n"
                "System-wide (Mac):\n"
                "- System Preferences > Displays > Resolution"
            ),
        },
    },
    {
        "keywords": ["copy", "paste", "cut", "clipboard"],
        "question": "How do I copy and paste?",
        "answer": {
            "title": "Copy and Paste Shortcuts",
            "content": (
                "Windows:\n"
                "- Ctrl+C to copy\n"
                "- Ctrl+X to cut\n"
                "- Ctrl+V to paste\n\n"
                "Mac:\n"
                "- Cmd+C to copy\n"
                "- Cmd+X to cut\n"
                "- Cmd+V to paste\n\n"
                "Tip: Win+V (Windows) shows clipboard history"
            ),
        },
    },
    {
        "keywords": ["dark mode", "night mode", "theme", "appearance"],
        "question": "How do I enable dark mode?",
        "answer": {
            "title": "Enabling Dark Mode",
            "content": (
                "Windows 11/10:\n"
                "Settings > Personalization > Colors > Choose your mode > Dark\n\n"
                "Mac:\n"
                "System Preferences > Appearance > Dark\n\n"
                "Browsers:\n"
                "Most browsers follow system settings, or check browser settings "
                "for appearance options."
            ),
        },
    },
    {
        "keywords": ["storage", "disk space", "free space", "full disk"],
        "question": "How do I free up disk space?",
        "answer": {
            "title": "Freeing Up Disk Space",
            "content": (
                "1. Empty Recycle Bin/Trash\n"
                "2. Run Disk Cleanup (Windows) or Optimize Storage (Mac)\n"
                "3. Uninstall unused programs\n"
                "4. Clear browser cache\n"
                "5. Move large files to external storage\n"
                "6. Clear temporary files\n"
                "7. Use Storage Sense (Windows) or Optimize Storage (Mac)"
            ),
        },
    },
    {
        "keywords": ["email", "outlook", "gmail", "mail", "email setup"],
        "question": "How do I set up my email?",
        "answer": {
            "title": "Email Setup Guide",
            "content": (
                "For most email providers:\n"
                "1. Open your email app (Outlook, Mail, etc.)\n"
                "2. Click Add Account\n"
                "3. Enter your email address\n"
                "4. Enter your password\n"
                "5. Follow automatic configuration\n\n"
                "For manual setup, you may need:\n"
                "- IMAP/POP server addresses\n"
                "- SMTP server for outgoing mail\n"
                "- Port numbers and security settings"
            ),
        },
    },
    {
        "keywords": ["restart", "reboot", "turn off", "shutdown"],
        "question": "How do I restart my computer properly?",
        "answer": {
            "title": "Proper Restart/Shutdown",
            "content": (
                "Windows:\n"
                "1. Click Start menu\n"
                "2. Click Power button\n"
                "3. Select Restart or Shut down\n\n"
                "Mac:\n"
                "1. Click Apple menu\n"
                "2. Select Restart or Shut Down\n\n"
                "Tip: Always close applications and save work before restarting."
            ),
        },
    },
    {
        "keywords": ["bluetooth", "pair", "connect device", "wireless device"],
        "question": "How do I connect a Bluetooth device?",
        "answer": {
            "title": "Bluetooth Pairing Guide",
            "content": (
                "Windows:\n"
                "1. Turn on Bluetooth device in pairing mode\n"
                "2. Settings > Bluetooth & devices > Add device\n"
                "3. Select your device from the list\n\n"
                "Mac:\n"
                "1. Turn on Bluetooth device in pairing mode\n"
                "2. System Preferences > Bluetooth\n"
                "3. Select your device and click Connect"
            ),
        },
    },
    {
        "keywords": ["task manager", "processes", "running programs", "force quit"],
        "question": "How do I open Task Manager or force quit an app?",
        "answer": {
            "title": "Task Manager / Force Quit",
            "content": (
                "Windows - Task Manager:\n"
                "- Press Ctrl+Shift+Esc\n"
                "- Or right-click taskbar > Task Manager\n"
                "- Select app and click End Task\n\n"
                "Mac - Force Quit:\n"
                "- Press Cmd+Option+Esc\n"
                "- Or Apple menu > Force Quit\n"
                "- Select app and click Force Quit"
            ),
        },
    },
    {
        "keywords": ["two factor", "2fa", "authentication", "verification"],
        "question": "What is two-factor authentication (2FA)?",
        "answer": {
            "title": "Two-Factor Authentication",
            "content": (
                "Two-factor authentication adds extra security by requiring:\n"
                "1. Something you know (password)\n"
                "2. Something you have (phone, security key)\n\n"
                "Common 2FA methods:\n"
                "- SMS codes\n"
                "- Authenticator apps (Google Authenticator, Authy)\n"
                "- Hardware security keys\n\n"
                "Recommendation: Enable 2FA on all important accounts."
            ),
        },
    },
]


def search_faq(query: str) -> dict[str, Any] | None:
    """Search the FAQ data for relevant answers.

    Args:
        query: The user's query string.

    Returns:
        The most relevant FAQ answer, or None if no match found.
    """
    query_lower = query.lower()

    # Search through all FAQs
    for faq in FAQ_DATA:
        keywords = faq.get("keywords", [])

        # Check if any keyword matches
        for keyword in keywords:
            if keyword in query_lower:
                return {
                    "question": faq.get("question", ""),
                    **faq.get("answer", {}),
                }

    return None


def get_all_faq_topics() -> list[str]:
    """Get a list of all FAQ topics.

    Returns:
        List of FAQ questions.
    """
    return [faq.get("question", "") for faq in FAQ_DATA]
