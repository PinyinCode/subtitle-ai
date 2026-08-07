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

# 👈 LẤY VIDEO_ID, YOUTUBE_LINK VÀ CLEAN_NAME TỪ ENV
video_id = os.environ.get('VIDEO_ID', '')
youtube_link = os.environ.get('YOUTUBE_LINK', '')
clean_name = os.environ.get('CLEAN_NAME', '')  # 👈 THÊM

# Nếu không có clean_name, dùng video_id làm fallback
if not clean_name:
    clean_name = video_id
    print(f"⚠️ CLEAN_NAME not set, using video_id: {clean_name}")

print(f"🎯 Video ID: {video_id}")
print(f"📝 Clean Name: {clean_name}")
print(f"🔗 YouTube: {youtube_link}")

headers = {
    "Authorization": f"token {token}",
    "Accept": "application/vnd.github.v3+json"
}

# 👈 TÌM FILE VTT THEO CLEAN_NAME
vtt_file = f"output/{clean_name}.vtt"

print(f"📁 Looking for VTT file: {vtt_file}")

if not os.path.exists(vtt_file):
    print(f'❌ VTT file not found: {vtt_file}')
    # Thử tìm bất kỳ file .vtt nào
    vtt_files = glob.glob("output/*.vtt")
    if vtt_files:
        vtt_file = vtt_files[0]
        clean_name = os.path.basename(vtt_file).replace('.vtt', '')
        print(f"ℹ️ Found alternative VTT: {vtt_file}")
        print(f"ℹ️ Using clean_name: {clean_name}")
    else:
        print('❌ No VTT files found')
        sys.exit(0)

print(f"📄 Processing: {clean_name}")

# Đọc nội dung file VTT
try:
    with open(vtt_file, 'r', encoding='utf-8') as fh:
        vtt_content = fh.read()
    print(f"✅ Read VTT: {len(vtt_content)} characters")
except Exception as e:
    print(f"❌ Error reading VTT: {e}")
    sys.exit(1)

# Tìm file info.txt
info_file = f"output/{clean_name}.info.txt"
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
    info_content = f"""Video ID: {video_id}
YouTube Link: {youtube_link}
Clean Name: {clean_name}
Generated: {datetime.now().isoformat()}
"""
    print(f"ℹ️ Generated info from env")

# Tạo metadata JSON
metadata = {
    "video_id": video_id,
    "youtube_link": youtube_link,
    "clean_name": clean_name,
    "generated_at": datetime.now().isoformat(),
    "vtt_file": f"{clean_name}.vtt"
}
metadata_content = json.dumps(metadata, indent=2, ensure_ascii=False)

# Kiểm tra Gist đã tồn tại
gist_exists = False
gist_id = None

try:
    resp = requests.get('https://api.github.com/gists', headers=headers, params={'per_page': 100})
    if resp.status_code == 200:
        for gist in resp.json():
            # Kiểm tra description chứa video_id
            if gist.get('description', '').endswith(video_id):
                gist_exists = True
                gist_id = gist['id']
                print(f"✅ Found existing Gist: {gist_id}")
                break
            # Kiểm tra file trong gist
            files = gist.get('files', {})
            if f"{clean_name}.vtt" in files:
                gist_exists = True
                gist_id = gist['id']
                print(f"✅ Found existing Gist (by file): {gist_id}")
                break
except Exception as e:
    print(f"⚠️ Error checking Gists: {e}")

# Tạo dict chứa các file cần upload
files_data = {
    f"{clean_name}.vtt": {"content": vtt_content}
}

# Thêm info.txt
if info_content:
    files_data[f"{clean_name}.info.txt"] = {"content": info_content}
elif youtube_link:
    info_content = f"""Video ID: {video_id}
YouTube Link: {youtube_link}
Clean Name: {clean_name}
Generated: {datetime.now().isoformat()}
"""
    files_data[f"{clean_name}.info.txt"] = {"content": info_content}

# Thêm metadata.json
files_data[f"{clean_name}.metadata.json"] = {"content": metadata_content}

# Thêm summary.json
summary_file = f"output/{clean_name}_summary.json"
if os.path.exists(summary_file):
    try:
        with open(summary_file, 'r', encoding='utf-8') as fh:
            summary_content = fh.read()
        files_data[f"{clean_name}_summary.json"] = {"content": summary_content}
        print(f"✅ Added summary file: {summary_file}")
    except Exception as e:
        print(f"⚠️ Cannot read summary: {e}")
else:
    # Thử tìm bất kỳ _summary.json nào
    summary_files = glob.glob("output/*_summary.json")
    if summary_files:
        summary_file = summary_files[0]
        try:
            with open(summary_file, 'r', encoding='utf-8') as fh:
                summary_content = fh.read()
            files_data[f"{clean_name}_summary.json"] = {"content": summary_content}
            print(f"✅ Added summary file: {summary_file}")
        except Exception as e:
            print(f"⚠️ Cannot read summary: {e}")

# Cập nhật description
description = f"🎬 {youtube_link} - Pinyin AI Subtitle" if youtube_link else f"🎬 Pinyin AI Subtitle - {video_id}"

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
    print(f'🆕 Creating new Gist for: {clean_name}')
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
    with open(f"output/{clean_name}_gist_url.txt", 'w', encoding='utf-8') as gf:
        gf.write(f"Gist URL: {gist_url}\n")
        gf.write(f"YouTube: {youtube_link}\n")
        gf.write(f"Video ID: {video_id}\n")
        gf.write(f"Clean Name: {clean_name}\n")
else:
    print(f'❌ Error {response.status_code}: {response.text[:200]}')

print('\n✅ Done!')
