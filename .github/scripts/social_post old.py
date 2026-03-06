#!/usr/bin/env python3
import os
import sys
import json
import subprocess
import requests
import re
from datetime import datetime

# Get environment variables
MASTODON_TOKEN = os.environ.get('MASTODON_TOKEN')
BLUESKY_PASSWORD = os.environ.get('BLUESKY_PASSWORD')
MASTODON_INSTANCE = 'https://techpolicy.social'
BLUESKY_USERNAME = 'aichallengewatch.bsky.app'
SITE_URL = 'https://aichallengewatch.com'

def get_changed_files():
    """Get list of files changed in the last commit"""
    try:
        result = subprocess.run(
            ['git', 'diff', '--name-only', 'HEAD~1', 'HEAD'],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip().split('\n')
    except subprocess.CalledProcessError:
        print("Error getting changed files")
        return []

def extract_title_from_html(filepath):
    """Extract the h1 title from an HTML file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            # Find first h1 tag
            match = re.search(r'<h1[^>]*>(.*?)</h1>', content, re.IGNORECASE | re.DOTALL)
            if match:
                # Strip any HTML tags from the title
                title = re.sub(r'<[^>]+>', '', match.group(1))
                return title.strip()
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
    return None

def extract_case_info_from_path(path):
    """Extract case slug from path like cases/case-name/index.html"""
    parts = path.split('/')
    if len(parts) >= 3 and parts[0] == 'cases' and parts[2] == 'index.html':
        return parts[1]
    return None

def extract_analysis_info_from_path(path):
    """Extract analysis slug from path like analysis/post-name/index.html"""
    parts = path.split('/')
    if len(parts) >= 3 and parts[0] == 'analysis' and parts[2] == 'index.html':
        return parts[1]
    return None

def post_to_mastodon(status):
    """Post to Mastodon"""
    if not MASTODON_TOKEN:
        print("Warning: MASTODON_TOKEN not set, skipping Mastodon post")
        return False
    
    url = f'{MASTODON_INSTANCE}/api/v1/statuses'
    headers = {'Authorization': f'Bearer {MASTODON_TOKEN}'}
    data = {'status': status}
    
    try:
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
        print(f"Posted to Mastodon: {status[:50]}...")
        return True
    except Exception as e:
        print(f"Error posting to Mastodon: {e}")
        return False

def post_to_bluesky(text):
    """Post to BlueSky"""
    if not BLUESKY_PASSWORD:
        print("Warning: BLUESKY_PASSWORD not set, skipping BlueSky post")
        return False
    
    # Login to BlueSky
    try:
        login_url = 'https://bsky.social/xrpc/com.atproto.server.createSession'
        login_data = {
            'identifier': BLUESKY_USERNAME,
            'password': BLUESKY_PASSWORD
        }
        login_response = requests.post(login_url, json=login_data)
        login_response.raise_for_status()
        access_token = login_response.json()['accessJwt']
        
        # Create post
        post_url = 'https://bsky.social/xrpc/com.atproto.repo.createRecord'
        headers = {'Authorization': f'Bearer {access_token}'}
        post_data = {
            'repo': BLUESKY_USERNAME,
            'collection': 'app.bsky.feed.post',
            'record': {
                'text': text,
                'createdAt': datetime.utcnow().isoformat() + 'Z',
                '$type': 'app.bsky.feed.post'
            }
        }
        
        response = requests.post(post_url, headers=headers, json=post_data)
        response.raise_for_status()
        print(f"Posted to BlueSky: {text[:50]}...")
        return True
    except Exception as e:
        print(f"Error posting to BlueSky: {e}")
        return False

def main():
    changed_files = get_changed_files()
    
    if not changed_files:
        print("No files changed")
        return
    
    print(f"Changed files: {changed_files}")
    
    # Detect case changes
    case_changes = {}
    for file in changed_files:
        if file.startswith('cases/') and file.endswith('/index.html'):
            case_slug = extract_case_info_from_path(file)
            if case_slug:
                title = extract_title_from_html(file)
                if title:
                    case_changes[case_slug] = title
    
    # Detect analysis changes
    analysis_changes = {}
    for file in changed_files:
        if file.startswith('analysis/') and file.endswith('/index.html'):
            analysis_slug = extract_analysis_info_from_path(file)
            if analysis_slug:
                title = extract_title_from_html(file)
                if title:
                    analysis_changes[analysis_slug] = title
    
    # Post about case changes
    for case_slug, case_title in case_changes.items():
        case_url = f"{SITE_URL}/cases/{case_slug}/"
        
        status = f"📋 Case update: {case_title}\n{case_url}"
        
        post_to_mastodon(status)
        post_to_bluesky(status)
    
    # Post about analysis changes
    for analysis_slug, analysis_title in analysis_changes.items():
        analysis_url = f"{SITE_URL}/analysis/{analysis_slug}/"
        
        status = f"📝 New analysis: {analysis_title}\n{analysis_url}"
        
        post_to_mastodon(status)
        post_to_bluesky(status)
    
    if not case_changes and not analysis_changes:
        print("No case or analysis changes detected")

if __name__ == '__main__':
    main()
