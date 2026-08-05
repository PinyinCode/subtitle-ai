#!/usr/bin/env python3
"""Push subtitles to GitHub Gist - Dùng API trực tiếp"""
import os
import sys
import json
import glob
import requests
from datetime import datetime

print("📤 Starting Gist upload...")

# Đọc token
token = os.environ.get('GIST_TOKEN') or os.environ.get('GH_TOKEN')

if not token:
    print('❌ No token found, skipping Gist push')
    sys.exit(0)

# Lấy VIDEO_ID và YOUTUBE_LINK từ env
video_id = os.environ.get('VIDEO_ID', '')
youtube_link = os.environ.get('YOUTUBE_LINK', '')
name_without_ext = os.environ.get('NAME_WITHOUT_EXT', '')

print(f"🎯 Video ID: {video_id}")
print(f"🔗 YouTube: {youtube_link}")
print(f"📝 Name: {name_without_ext}")

headers = {
    "Authorization": f"token {token}",
    "Accept": "application/vnd.github.v3+json"
}

# Tìm file VTT
vtt_files = glob.glob("output/*.vtt")

print(f"📁 Found {len(vtt_files)} VTT files:")
for f in vtt_files:
    print(f"  - {f}")

if not vtt_files:
    print('❌ No VTT files found')
    sys.exit(0)

for f in vtt_files:
    # Lấy tên gốc
    base_name = os.path.basename(f).replace('.vtt', '')
    
    # Ưu tiên VIDEO_ID từ env
    vid = video_id or base_name
    
    print(f'\n📤 Processing: {vid}')
    
    # Đọc VTT
    try:
        with open(f, 'r', encoding='utf-8') as fh:
            vtt_content = fh.read()
        print(f"✅ Read VTT: {len(vtt_content)} characters")
    except Exception as e:
        print(f"❌ Error reading VTT: {e}")
        continue
    
    # Tạo content cho Gist
    content = f"""# 🎬 YouTube Subtitle: {vid}

## 🔗 YouTube Link
{youtube_link or 'Not found'}

## 📝 Subtitles (VTT)
```vtt
{vtt_content}
