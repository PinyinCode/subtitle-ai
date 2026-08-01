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
    
    # Kiểm tra Gist đã tồn tại chưa
    gist_exists = False
    gist_id = None
    
    try:
        # Lấy danh sách Gist của user
        resp = requests.get('https://api.github.com/gists', headers=headers, params={'per_page': 100})
        if resp.status_code == 200:
            for gist in resp.json():
                if gist.get('description', '').endswith(video_id):
                    gist_exists = True
                    gist_id = gist['id']
                    break
    except:
        pass
    
    if gist_exists and gist_id:
        # Update Gist cũ
        print(f'Updating existing Gist: {gist_id}')
        response = requests.patch(
            f'https://api.github.com/gists/{gist_id}',
            headers=headers,
            json={
                "description": f"YouTube Subtitle - {video_id}",
                "files": {
                    f"{video_id}.vtt": {"content": content}
                }
            }
        )
    else:
        # Tạo Gist mới
        print(f'Creating new Gist for: {video_id}')
        response = requests.post(
            'https://api.github.com/gists',
            headers=headers,
            json={
                "description": f"YouTube Subtitle - {video_id}",
                "public": False,
                "files": {
                    f"{video_id}.vtt": {"content": content}
                }
            }
        )
    
    if response.status_code in [200, 201]:
        data = response.json()
        print(f'✅ Gist saved: {data["html_url"]}')
    else:
        print(f'❌ Error {response.status_code}: {response.text[:200]}')

print('Done!')
