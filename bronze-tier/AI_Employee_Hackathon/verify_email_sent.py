#!/usr/bin/env python3
"""Verify email was sent successfully by checking Gmail using silver-tier client."""

import sys
from pathlib import Path

# Use silver-tier's Gmail client
silver_tier_path = Path(__file__).parent.parent / "silver-tier" / "AI_Employee_Hackathon"
sys.path.insert(0, str(silver_tier_path))

from backend.mcp_servers.gmail_client import GmailClient
from dotenv import load_dotenv
import os

# Load silver-tier config
load_dotenv(silver_tier_path / "config" / ".env")

CREDENTIALS_PATH = str(silver_tier_path / "config" / "credentials.json")
TOKEN_PATH = str(silver_tier_path / "config" / "token.json")

def main():
    """Check Gmail for the sent email."""
    print("=" * 60)
    print("GMAIL VERIFICATION - Checking Sent Email")
    print("=" * 60)
    print(f"Using silver-tier Gmail client from: {silver_tier_path}")
    print()

    # Initialize Gmail client
    print("Initializing Gmail client...")
    gmail = GmailClient(
        credentials_path=CREDENTIALS_PATH,
        token_path=TOKEN_PATH,
    )
    gmail.authenticate()
    print("[OK] Gmail authenticated")
    print()

    # Search for the specific message by subject
    print("Step 1: Searching for email by subject...")
    subject_query = 'subject:"Hello from my AI Employee!"'
    results = gmail.search_messages(subject_query, max_results=5)

    if results:
        print(f"[OK] Found {len(results)} email(s) with matching subject:")
        for i, msg in enumerate(results, 1):
            print(f"\n  {i}. Message ID: {msg['message_id']}")
            print(f"     Thread ID: {msg['thread_id']}")
            print(f"     From: {msg['from_address']}")
            print(f"     To: {msg['to_address']}")
            print(f"     Subject: {msg['subject']}")
            print(f"     Date: {msg['date']}")
            print(f"     Snippet: {msg['snippet'][:100]}")

            # Check if this is our specific message
            if msg['message_id'] == '19c77445d3463f90':
                print("     *** THIS IS THE EMAIL WE SENT FROM SILVER-TIER! ***")
    else:
        print("[WARNING] No emails found with that subject")

    print()
    print("Step 2: Searching in Sent folder...")
    sent_query = 'in:sent to:zartashakhan775@gmail.com'
    sent_results = gmail.search_messages(sent_query, max_results=5)

    if sent_results:
        print(f"[OK] Found {len(sent_results)} email(s) in Sent to zartashakhan775@gmail.com:")
        for i, msg in enumerate(sent_results, 1):
            print(f"\n  {i}. Message ID: {msg['message_id']}")
            print(f"     Subject: {msg['subject']}")
            print(f"     Date: {msg['date']}")

            # Check if this is our specific message
            if msg['message_id'] == '19c77445d3463f90':
                print("     *** CONFIRMED: Email exists in Sent folder! ***")
    else:
        print("[WARNING] No emails found in Sent to zartashakhan775@gmail.com")

    print()
    print("Step 3: Checking inbox for received emails...")
    inbox_query = 'in:inbox from:me after:2026/02/19'
    inbox_results = gmail.search_messages(inbox_query, max_results=5)

    if inbox_results:
        print(f"[OK] Found {len(inbox_results)} email(s) from self in inbox:")
        for i, msg in enumerate(inbox_results, 1):
            print(f"\n  {i}. Message ID: {msg['message_id']}")
            print(f"     Subject: {msg['subject']}")
            print(f"     Date: {msg['date']}")

            if msg['message_id'] == '19c77445d3463f90':
                print("     *** Email was received in inbox (sent to same account)! ***")
    else:
        print("[INFO] No emails from self in inbox (sent to different account)")

    print()
    print("=" * 60)
    print("VERIFICATION COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    main()
