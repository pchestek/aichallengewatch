#!/usr/bin/env python3
"""
Detect changes to cases/analysis and post to Mastodon and BlueSky
"""

import os
import subprocess
import yaml
import re
import requests
from datetime import datetime
from atproto import Client as BlueskyClient

# Configuration
MASTODON_TOKEN = os.environ.get('MASTODON_TOKEN')
MASTODON_INSTANCE = os.environ.get('MASTODON_INSTANCE')
BLUESKY_HANDLE = os.environ.get('BLUESKY_HANDLE')
BLUESKY_PASSWORD = os.environ.get('BLUESKY_PASSWORD')
SITE_URL = os.environ.get('SITE_URL')


def get_changed_files():
    """Get list of files changed in latest commit"""
    result = subprocess.run(
        ['git', 'diff', '--name-only', 'HEAD~1', 'HEAD'],
        capture_output=True,
        text=True
    )
    return result.stdout.strip().split('\n')


def parse_case_yaml(filepath):
    """Parse YAML case file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def parse_analysis_md(filepath):
    """Parse markdown analysis file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract frontmatter
    match = re.match(r'^---\n(.*?)\n---\n(.*)$', content, re.DOTALL)
    if match:
        frontmatter = yaml.safe_load(match.group(1))
        body = match.group(2)
        return frontmatter, body
    return {}, content


def format_case_post(case_data, is_new=True):
    """Format post for a case (new or updated)"""
    title = case_data.get('title', 'Unknown Case')
    state = case_data.get('state', '')
    status = case_data.get('status_detail', case_data.get('status', ''))
    slug = case_data.get('slug', '')
    
    # Get law name (handle both single and multiple laws)
    law_name = ""
    if 'laws_challenged' in case_data and case_data['laws_challenged']:
        law_name = case_data['laws_challenged'][0].get('short_name', '')
    elif 'law_challenged_short' in case_data:
        law_name = case_data['law_challenged_short']
    
    case_url = f"{SITE_URL}/cases/{slug}/"
    
    if is_new:
        post = f"🚨 New case: {title}\n\n"
        post += f"📍 {state}\n"
        if law_name:
            post += f"⚖️ Challenges: {law_name}\n"
        post += f"\n{case_url}"
    else:
        post = f"📋 Case update: {title}\n\n"
        post += f"Status: {status}\n"
        post += f"\n{case_url}"
    
    return post


def format_analysis_post(frontmatter, slug):
    """Format post for new analysis"""
    title = frontmatter.get('title', 'New Analysis')
    date = frontmatter.get('date', datetime.now().strftime('%Y-%m-%d'))
    
    analysis_url = f"{SITE_URL}/analysis/{slug}/"
    
    post = f"📝 New analysis: {title}\n\n"
    post += f"{analysis_url}"
    
    return post


def post_to_mastodon(text):
    """Post to Mastodon"""
    if not MASTODON_TOKEN or not MASTODON_INSTANCE:
        print("Mastodon credentials not configured")
        return False
    
    url = f"{MASTODON_INSTANCE}/api/v1/statuses"
    headers = {
        'Authorization': f'Bearer {MASTODON_TOKEN}',
        'Content-Type': 'application/json'
    }
    data = {
        'status': text,
        'visibility': 'public'
    }
    
    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        print(f"✅ Posted to Mastodon: {response.json().get('url')}")
        return True
    except Exception as e:
        print(f"❌ Mastodon post failed: {e}")
        return False


def post_to_bluesky(text):
    """Post to BlueSky"""
    if not BLUESKY_HANDLE or not BLUESKY_PASSWORD:
        print("BlueSky credentials not configured")
        return False
    
    try:
        client = BlueskyClient()
        client.login(BLUESKY_HANDLE, BLUESKY_PASSWORD)
        
        response = client.send_post(text=text)
        print(f"✅ Posted to BlueSky")
        return True
    except Exception as e:
        print(f"❌ BlueSky post failed: {e}")
        return False


def main():
    changed_files = get_changed_files()
    
    for filepath in changed_files:
        if not filepath:
            continue
        
        # Check if it's a new or updated case
        if filepath.startswith('data/cases/') and filepath.endswith('.yaml'):
            # Check if file is new (added in this commit)
            is_new = subprocess.run(
                ['git', 'diff', '--diff-filter=A', '--name-only', 'HEAD~1', 'HEAD', filepath],
                capture_output=True,
                text=True
            ).stdout.strip() != ''
            
            try:
                case_data = parse_case_yaml(filepath)
                post_text = format_case_post(case_data, is_new=is_new)
                
                print(f"\n{'New' if is_new else 'Updated'} case detected: {filepath}")
                print(f"Post text:\n{post_text}\n")
                
                post_to_mastodon(post_text)
                post_to_bluesky(post_text)
                
            except Exception as e:
                print(f"Error processing {filepath}: {e}")
        
        # Check if it's new analysis
        elif filepath.startswith('content/analysis/') and filepath.endswith('.md'):
            is_new = subprocess.run(
                ['git', 'diff', '--diff-filter=A', '--name-only', 'HEAD~1', 'HEAD', filepath],
                capture_output=True,
                text=True
            ).stdout.strip() != ''
            
            if is_new:
                try:
                    frontmatter, body = parse_analysis_md(filepath)
                    slug = os.path.splitext(os.path.basename(filepath))[0]
                    post_text = format_analysis_post(frontmatter, slug)
                    
                    print(f"\nNew analysis detected: {filepath}")
                    print(f"Post text:\n{post_text}\n")
                    
                    post_to_mastodon(post_text)
                    post_to_bluesky(post_text)
                    
                except Exception as e:
                    print(f"Error processing {filepath}: {e}")


if __name__ == '__main__':
    main()
