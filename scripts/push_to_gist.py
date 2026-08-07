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

# Lấy VIDEO_ID VÀ YOUTUBE_LINK TỪ ENV
video_id = os.environ.get('VIDEO_ID', '')
youtube_link = os.environ.get('YOUTUBE_LINK', '')

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
    # Lấy tên gốc (không extension)
    base_name = os.path.basename(f).replace('.vtt', '')
    vid = video_id or base_name
    
    print(f'\n📤 Processing: {vid}')
    
    # Đọc nội dung file VTT
    try:
        with open(f, 'r', encoding='utf-8') as fh:
            vtt_content = fh.read()
        print(f"✅ Read VTT: {len(vtt_content)} characters")
    except Exception as e:
        print(f"❌ Error reading VTT: {e}")
        continue
    
    # Tìm file info.txt
    info_file = f"output/{vid}.info.txt"
    info_content = None
    if os.path.exists(info_file):
        try:
            with open(info_file, 'r', encoding='utf-8') as fh:
                info_content = fh.read()
            print(f"✅ Found info file: {info_file}")
        except Exception as e:
            print(f"⚠️ Cannot read info file: {e}")
    
    # Nếu không có file info, tạo từ env
    if not info_content and youtube_link:
        info_content = f"""Video ID: {vid}
YouTube Link: {youtube_link}
Generated: {datetime.now().isoformat()}
"""
        print(f"ℹ️ Generated info from env")
    
    # Tạo metadata JSON
    metadata = {
        "video_id": vid,
        "youtube_link": youtube_link,
        "generated_at": datetime.now().isoformat(),
        "vtt_file": f"{vid}.vtt"
    }
    metadata_content = json.dumps(metadata, indent=2, ensure_ascii=False)
    
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
                files = gist.get('files', {})
                if f"{vid}.vtt" in files:
                    gist_exists = True
                    gist_id = gist['id']
                    print(f"✅ Found existing Gist (by file): {gist_id}")
                    break
    except Exception as e:
        print(f"⚠️ Error checking Gists: {e}")
    
    # Tạo dict chứa các file cần upload
    files_data = {
        f"{vid}.vtt": {"content": vtt_content}
    }
    
    # Thêm info.txt
    if info_content:
        files_data[f"{vid}.info.txt"] = {"content": info_content}
    elif youtube_link:
        info_content = f"""Video ID: {vid}
YouTube Link: {youtube_link}
Generated: {datetime.now().isoformat()}
"""
        files_data[f"{vid}.info.txt"] = {"content": info_content}
    
    # Thêm metadata.json
    files_data[f"{vid}.metadata.json"] = {"content": metadata_content}
    
    # 👈 SỬA: Tìm và thêm summary.json
    summary_file = None
    # Thử với tên đúng
    if os.path.exists(f"output/{vid}_summary.json"):
        summary_file = f"output/{vid}_summary.json"
    else:
        # Tìm bất kỳ file _summary.json nào
        summary_files = glob.glob("output/*_summary.json")
        if summary_files:
            summary_file = summary_files[0]
            print(f"ℹ️ Found summary file: {summary_file}")
    
    if summary_file and os.path.exists(summary_file):
        try:
            with open(summary_file, 'r', encoding='utf-8') as fh:
                summary_content = fh.read()
            files_data[f"{vid}_summary.json"] = {"content": summary_content}
            print(f"✅ Added summary file: {summary_file}")
        except Exception as e:
            print(f"⚠️ Cannot read summary: {e}")
    
    # Cập nhật description
    description = f"🎬 {youtube_link} - Pinyin AI Subtitle" if youtube_link else f"🎬 Pinyin AI Subtitle - {vid}"
    
    # Tạo payload
    data = {
        "description": description,
        "public": False,
        "files": files_data
    }
    
    # Tạo hoặc update Gist
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
        
        uploaded_files = result.get('files', {})
        print(f"📁 Uploaded files:")
        for filename in uploaded_files.keys():
            print(f"  - {filename}")
        
        # Lưu Gist URL
        with open(f"output/{vid}_gist_url.txt", 'w', encoding='utf-8') as gf:
            gf.write(f"Gist URL: {gist_url}\n")
            gf.write(f"YouTube: {youtube_link}\n")
            gf.write(f"Video ID: {vid}\n")
    else:
        print(f'❌ Error {response.status_code}: {response.text[:200]}')

print('\n✅ Done!')
