#!/usr/bin/env python3
"""
Check .social-post.txt locally BEFORE pushing, so you catch a too-long
message on your own computer instead of finding out after a push.

Usage (from the public/ folder):
    python check_social_post.py
"""
import os

SITE_URL = 'https://aichallengewatch.com'
BLUESKY_MAX_LENGTH = 300

def determine_post_type(slug):
    if os.path.exists(f'cases/{slug}/index.html'):
        return 'case'
    elif os.path.exists(f'analysis/{slug}/index.html'):
        return 'analysis'
    return None

def main():
    if not os.path.exists('.social-post.txt'):
        print("No .social-post.txt file found in this folder.")
        return

    with open('.social-post.txt', 'r', encoding='utf-8') as f:
        lines = f.readlines()

    if len(lines) < 2:
        print("ERROR: .social-post.txt needs at least 2 lines (slug, then message).")
        return

    slug = lines[0].strip()
    message = ''.join(lines[1:]).strip()

    print(f"Slug (line 1): {slug}")

    post_type = determine_post_type(slug)
    if not post_type:
        print(f"WARNING: Could not find a case or analysis page for slug '{slug}'.")
        print(f"  Checked: cases/{slug}/index.html and analysis/{slug}/index.html")
        print("  Run '.\\quick.bat' first if you just added this page, then check again.")
        print()

    if post_type == 'case':
        url = f"{SITE_URL}/cases/{slug}/"
    elif post_type == 'analysis':
        url = f"{SITE_URL}/analysis/{slug}/"
    else:
        # Best guess so we can still check length even if the page wasn't found
        url = f"{SITE_URL}/cases/{slug}/"

    post_text = f"{message}\n{url}"
    length = len(post_text)
    budget = BLUESKY_MAX_LENGTH - len(url) - 1  # -1 for the line break

    print(f"Message: {message}")
    print(f"URL: {url}")
    print()
    print(f"Total length (message + URL): {length} characters")
    print(f"BlueSky limit: {BLUESKY_MAX_LENGTH} characters")
    print(f"You have about {budget} characters available for your message text.")
    print()

    if length > BLUESKY_MAX_LENGTH:
        over = length - BLUESKY_MAX_LENGTH
        print(f"❌ TOO LONG by {over} characters. This will NOT post to Mastodon or BlueSky.")
        print("   Shorten your message and run this check again.")
    else:
        print(f"✅ OK - fits within the limit ({BLUESKY_MAX_LENGTH - length} characters to spare).")

if __name__ == '__main__':
    main()
