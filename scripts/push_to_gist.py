#!/usr/bin/env python3
"""Push subtitles to GitHub Gist - Dùng API trực tiếp"""
import os
import sys
import json
import glob
import requests

print("📤 Starting Gist upload...")

# Đọc token
token = os.environ.get('GIST_TOKEN') or os.environ.get('GH_TOKEN')

if not token:
    print('❌ No token found, skipping Gist push')
    sys.exit(0)

# 👈 LẤY VIDEO_ID TỪ ENV
video_id = os.environ.get('VIDEO_ID')

headers = {
    "Authorization": f"token {token}",
    "Accept": "application/vnd.github.v3+json"
}

vtt_files = glob.glob("output/*.vtt")

print(f"📁 Found {len(vtt_files)} VTT files:")
for f in vtt_files:
    print(f"  - {f}")

if not vtt_files:
    print('❌ No VTT files found')
    sys.exit(0)

for f in vtt_files:
    # 👈 Ưu tiên dùng VIDEO_ID từ ENV
    file_video_id = os.path.basename(f).replace('.vtt', '')
    vid = video_id or file_video_id
    
    print(f'\n📤 Processing: {vid}')
    
    # Đọc nội dung file
    try:
        with open(f, 'r', encoding='utf-8') as fh:
            content = fh.read()
        print(f"✅ Read {len(content)} characters")
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        continue
    
    # Kiểm tra Gist đã tồn tại
    gist_exists = False
    gist_id = None
    
    try:
        resp = requests.get('https://api.github.com/gists', headers=headers, params={'per_page': 100})
        if resp.status_code == 200:
            for gist in resp.json():
                if gist.get('description', '').endswith(vid):
                    gist_exists = True
                    gist_id = gist['id']
                    print(f"✅ Found existing Gist: {gist_id}")
                    break
    except Exception as e:
        print(f"⚠️ Error checking Gists: {e}")
    
    # Tạo hoặc update Gist
    data = {
        "description": f"Pinyin AI Subtitle - {vid}",
        "public": False,
        "files": {
            f"{vid}.vtt": {"content": content}
        }
    }
    
    if gist_exists and gist_id:
        print(f'🔄 Updating Gist: {gist_id}')
        response = requests.patch(
            f'https://api.github.com/gists/{gist_id}',
            headers=headers,
            json=data
        )
    else:
        print(f'🆕 Creating new Gist for: {vid}')
        response = requests.post(
            'https://api.github.com/gists',
            headers=headers,
            json=data
        )
    
    if response.status_code in [200, 201]:
        result = response.json()
        gist_url = result.get('html_url', '')
        print(f'✅ Gist saved: {gist_url}')
    else:
        print(f'❌ Error {response.status_code}: {response.text[:200]}')

print('\n✅ Done!')
