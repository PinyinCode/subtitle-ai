#!/usr/bin/env python3
"""
YouTube Subtitle Generator - Faster Whisper
Tự động tìm video ID từ tên file
"""

import os
import sys
import json
import glob
import re
import argparse
import time
from pathlib import Path
from datetime import datetime
from difflib import SequenceMatcher

# 👈 CÀI THÊM THƯ VIỆN TÌM KIẾM
try:
    from youtube_search import YoutubeSearch
except ImportError:
    os.system('pip install -q youtube-search-pytube')
    from youtube_search import YoutubeSearch

# ===== CÁC HÀM HIỆN CÓ =====
try:
    from faster_whisper import WhisperModel
except ImportError:
    os.system('pip install -q faster-whisper')
    from faster_whisper import WhisperModel

try:
    from deep_translator import GoogleTranslator
except ImportError:
    os.system('pip install -q deep-translator')
    from deep_translator import GoogleTranslator

try:
    from pypinyin import pinyin, Style
except ImportError:
    os.system('pip install -q pypinyin')
    from pypinyin import pinyin, Style


# ===== TÌM VIDEO ID TỪ TÊN FILE =====
def search_video_id_from_filename(filename):
    """
    Tìm video ID bằng cách tìm kiếm YouTube với tên file
    """
    # Lấy tên không extension
    name = Path(filename).stem
    
    # 👈 LÀM SẠCH TÊN FILE ĐỂ TÌM KIẾM
    search_query = clean_search_query(name)
    print(f"🔍 Tìm kiếm YouTube: '{search_query}'")
    
    try:
        # 👈 TÌM KIẾM TRÊN YOUTUBE
        results = YoutubeSearch(search_query, max_results=10).to_dict()
        
        if not results:
            print("❌ Không tìm thấy video nào")
            return None
        
        print(f"✅ Tìm thấy {len(results)} video")
        
        # 👈 SO KHỚP ĐỘ TƯƠNG ĐỒNG
        best_match = None
        best_score = 0
        
        for video in results:
            title = video.get('title', '')
            score = similarity_score(search_query, title)
            
            print(f"  📊 Độ khớp: {score:.2f} | {title[:50]}...")
            
            if score > best_score:
                best_score = score
                best_match = video
        
        # 👈 CHỈ CHỌN NẾU ĐỘ KHỚP > 0.3
        if best_match and best_score > 0.3:
            video_id = best_match.get('id')
            video_title = best_match.get('title', '')
            print(f"\n🏆 CHỌN: {video_title}")
            print(f"🔗 https://youtube.com/watch?v={video_id}")
            print(f"📊 Độ khớp: {best_score:.2f}")
            return video_id
        else:
            print(f"❌ Không có video nào khớp (độ khớp thấp nhất: {best_score:.2f})")
            return None
            
    except Exception as e:
        print(f"❌ Lỗi tìm kiếm: {e}")
        return None


def clean_search_query(filename):
    """Làm sạch tên file để tìm kiếm"""
    # Loại bỏ extension
    name = Path(filename).stem
    
    # Loại bỏ số thứ tự (nếu có)
    name = re.sub(r'^\d+[\s._-]+', '', name)
    
    # Loại bỏ các từ khóa không cần thiết
    remove_words = ['audio', 'video', 'subtitle', 'track', 'clip', 'full', 'hd', 
                    'official', 'music', 'song', 'lyric', 'cover', 'remix', 'live',
                    'mv', 'ft', 'feat', 'featuring', '128k', '320k']
    
    for word in remove_words:
        name = re.sub(r'\b' + word + r'\b', ' ', name, flags=re.IGNORECASE)
    
    # Xóa ký tự đặc biệt
    name = re.sub(r'[^\w\s]', ' ', name)
    
    # Xóa khoảng trắng thừa
    name = re.sub(r'\s+', ' ', name).strip()
    
    return name


def similarity_score(a, b):
    """Tính độ tương đồng giữa 2 chuỗi"""
    # Chuyển sang chữ thường
    a = a.lower()
    b = b.lower()
    
    # Loại bỏ ký tự đặc biệt
    a = re.sub(r'[^\w\s]', ' ', a)
    b = re.sub(r'[^\w\s]', ' ', b)
    
    # So khớp
    return SequenceMatcher(None, a, b).ratio()


def extract_video_id_from_filename(filename):
    """
    Tự động tìm video ID từ tên file
    Ưu tiên: 1. Tìm 11 ký tự, 2. Tìm kiếm YouTube
    """
    name = Path(filename).stem
    
    # 👈 CÁCH 1: Tìm 11 ký tự (nếu có)
    match = re.search(r'([a-zA-Z0-9_-]{11})', name)
    if match:
        video_id = match.group(1)
        # Kiểm tra không phải từ khóa
        if not any(k in name.lower() for k in ['audio', 'video', 'subtitle', 'track']):
            print(f"✅ Tìm thấy video ID trong tên: {video_id}")
            return video_id
    
    # 👈 CÁCH 2: Tìm kiếm trên YouTube
    print(f"🔍 Không tìm thấy ID trong tên, tìm kiếm trên YouTube...")
    video_id = search_video_id_from_filename(filename)
    
    if video_id:
        print(f"✅ Tìm thấy video ID từ YouTube: {video_id}")
        return video_id
    
    print(f"❌ Không thể tìm thấy video ID cho: {filename}")
    return None


def get_youtube_link(video_id):
    """Tạo link YouTube từ video ID"""
    if video_id:
        return f"https://youtube.com/watch?v={video_id}"
    return ""


def format_time(seconds):
    """Format seconds to VTT timestamp"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def generate_subtitle(audio_path, output_path=None):
    """Generate VTT subtitle from audio file"""
    
    audio_file = Path(audio_path)
    
    # 👈 TỰ ĐỘNG TÌM VIDEO ID TỪ TÊN FILE
    video_id = extract_video_id_from_filename(audio_file.name)
    
    if not video_id:
        print(f"❌ Không tìm thấy video ID cho: {audio_file.name}")
        print(f"💡 Vui lòng đặt tên file chứa YouTube ID (11 ký tự)")
        print(f"💡 Hoặc đảm bảo tên file có thể tìm kiếm trên YouTube")
        return None
    
    youtube_link = get_youtube_link(video_id)
    print(f"🔗 YouTube: {youtube_link}")
    
    # 👈 VẪN GIỮ NGUYÊN TÊN GỐC CHO FILE VTT
    original_name = audio_file.stem
    output_filename = original_name  # Giữ tên gốc
    
    # Tạo output path
    if output_path is None:
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        output_file = output_dir / f"{output_filename}.vtt"
    else:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"\n{'='*50}")
    print(f"📝 Tên gốc: {original_name}")
    print(f"🎯 Video ID: {video_id}")
    print(f"🔗 YouTube: {youtube_link}")
    print(f"📁 Output: {output_file}")
    print(f"{'='*50}\n")
    
    # 👈 PHẦN CÒN LẠI GIỮ NGUYÊN (WHISPER + TRANSLATE)
    # ... (giữ nguyên code Whisper của bạn)
    
    return str(output_file)


# ===== HÀM MAIN =====
def main():
    parser = argparse.ArgumentParser(description='Generate subtitles from audio')
    parser.add_argument('--audio', help='Path to audio file')
    parser.add_argument('--output', help='Path to output VTT file')
    parser.add_argument('--latest', action='store_true', help='Process latest file')
    
    args = parser.parse_args()
    
    if args.audio:
        audio_path = args.audio
        if not os.path.exists(audio_path):
            print(f"❌ Audio file not found: {audio_path}")
            return
        
        result = generate_subtitle(audio_path, args.output)
        if result:
            print(f"\n✅ Done: {result}")
        return
    
    print("\n🔍 Finding audio files...")
    audio_files = glob.glob("data/audio/*.m4a") + glob.glob("data/audio/*.mp3") + glob.glob("data/audio/*.wav")
    
    if not audio_files:
        print("❌ No audio files found in data/audio/")
        return
    
    audio_files.sort(key=os.path.getmtime, reverse=True)
    latest_audio = audio_files[0]
    
    print(f"📌 Processing latest: {latest_audio}")
    
    try:
        result = generate_subtitle(latest_audio)
        if result:
            print(f"\n✅ Done: {result}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
