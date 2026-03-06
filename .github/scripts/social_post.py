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
BLUESKY_USERNAME = 'aichallengewatch.bsky.social'
SITE_URL = 'https://aichallengewatch.com'

def read_social_post_file():
    """Read .social-post.txt file if it exists"""
    if os.path.exists('.social-post.txt'):
        try:
            with open('.social-post.txt', 'r', encoding='utf-8') as f:
                lines = f.readlines()
                if len(lines) >= 2:
                    slug = lines[0].strip()
                    message = ''.join(lines[1:]).strip()
                    return slug, message
        except Exception as e:
            print(f"Error reading .social-post.txt: {e}")
    return None, None

def delete_social_post_file():
    """Delete .social-post.txt after processing"""
    if os.path.exists('.social-post.txt'):
        try:
            os.remove('.social-post.txt')
            print("Deleted .social-post.txt")
        except Exception as e:
            print(f"Error deleting .social-post.txt: {e}")

def determine_post_type(slug):
    """Determine if slug is a case or analysis post"""
    # Check if the slug corresponds to a case or analysis page
    if os.path.exists(f'cases/{slug}/index.html'):
        return 'case'
    elif os.path.exists(f'analysis/{slug}/index.html'):
        return 'analysis'
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
    """Post to BlueSky with clickable links"""
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
        
        # Find URL in text and create facet for it
        facets = []
        # Look for URLs starting with http
        url_match = re.search(r'https?://[^\s]+', text)
        if url_match:
            url = url_match.group(0)
            # Calculate byte positions (BlueSky uses UTF-8 byte positions)
            text_bytes = text.encode('utf-8')
            url_start = len(text[:url_match.start()].encode('utf-8'))
            url_end = len(text[:url_match.end()].encode('utf-8'))
            
            facets.append({
                'index': {
                    'byteStart': url_start,
                    'byteEnd': url_end
                },
                'features': [{
                    '$type': 'app.bsky.richtext.facet#link',
                    'uri': url
                }]
            })
        
        # Create post
        post_url = 'https://bsky.social/xrpc/com.atproto.repo.createRecord'
        headers = {'Authorization': f'Bearer {access_token}'}
        
        record = {
            'text': text,
            'createdAt': datetime.utcnow().isoformat() + 'Z',
            '$type': 'app.bsky.feed.post'
        }
        
        # Add facets if we found any URLs
        if facets:
            record['facets'] = facets
        
        post_data = {
            'repo': BLUESKY_USERNAME,
            'collection': 'app.bsky.feed.post',
            'record': record
        }
        
        response = requests.post(post_url, headers=headers, json=post_data)
        response.raise_for_status()
        print(f"Posted to BlueSky: {text[:50]}...")
        return True
    except Exception as e:
        print(f"Error posting to BlueSky: {e}")
        return False

def main():
    # Check for .social-post.txt file
    slug, custom_message = read_social_post_file()
    
    if not slug or not custom_message:
        print("No .social-post.txt file found or file is incomplete. No posts will be made.")
        print("To post to social media, create .social-post.txt with:")
        print("  Line 1: case-slug or analysis-slug")
        print("  Line 2+: Your custom message")
        return
    
    # Determine if it's a case or analysis
    post_type = determine_post_type(slug)
    
    if not post_type:
        print(f"Warning: Could not find page for slug '{slug}'")
        print(f"Checked: cases/{slug}/index.html and analysis/{slug}/index.html")
        return
    
    # Build the URL
    if post_type == 'case':
        url = f"{SITE_URL}/cases/{slug}/"
    else:
        url = f"{SITE_URL}/analysis/{slug}/"
    
    # Build the post text: custom message + URL
    post_text = f"{custom_message}\n{url}"
    
    print(f"Posting about {post_type}: {slug}")
    print(f"Message: {custom_message}")
    print(f"URL: {url}")
    
    # Post to both platforms
    mastodon_success = post_to_mastodon(post_text)
    bluesky_success = post_to_bluesky(post_text)
    
    # Only delete the file if at least one post succeeded
    if mastodon_success or bluesky_success:
        delete_social_post_file()
        print("Social media posts completed successfully!")
    else:
        print("Warning: Posts failed. .social-post.txt was NOT deleted so you can retry.")

if __name__ == '__main__':
    main()
