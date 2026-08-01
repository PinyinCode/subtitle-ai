#!/usr/bin/env python3
"""Push subtitles to GitHub Gist - Dùng API trực tiếp"""
import os, json, glob, requests

# Đọc cả 2 biến
token = os.environ.get('GH_TOKEN') or os.environ.get('GIST_TOKEN')

if not token:
    print('No token found, skipping Gist push')
    exit()

headers = {
    "Authorization": f"token {token}",
    "Accept": "application/vnd.github.v3+json"
}

vtt_files = glob.glob("output/*.vtt")

if not vtt_files:
    print('No VTT files found')
    exit()

for f in vtt_files:
    video_id = f.replace('output/', '').replace('.vtt', '')
    
    with open(f, 'r', encoding='utf-8') as fh:
        content = fh.read()
    
    print(f'Pushing Gist for: {video_id}')
    
    # Tạo Gist mới
    response = requests.post(
        'https://api.github.com/gists',
        headers=headers,
        json={
            "description": f"YouTube Subtitle - {video_id}",
            "public": True,
            "files": {
                f"{video_id}.vtt": {"content": content}
            }
        }
    )
    
    if response.status_code in [200, 201]:
        data = response.json()
        print(f'✅ Gist created: {data["html_url"]}')
    else:
        print(f'❌ Error {response.status_code}: {response.text[:200]}')

print('Done!')
