#!/usr/bin/env python3
"""
YouTube Subtitle Generator - Faster Whisper
Tự động tìm video ID từ tên file (yt-dlp + fallback youtube-search-python)
"""

import os
import sys
import json
import glob
import re
import subprocess
import argparse
import time
from pathlib import Path
from datetime import datetime
from difflib import SequenceMatcher

# ============================================================
# IMPORT TRỰC TIẾP (KHÔNG CẦN SAFE_IMPORT)
# ============================================================

from faster_whisper import WhisperModel
from deep_translator import GoogleTranslator
from pypinyin import pinyin, Style
from youtube_search import YoutubeSearch

# ============================================================
# KIỂM TRA VERSION (DEBUG)
# ============================================================

print(f"✅ Faster-Whisper loaded")
print(f"✅ Deep-Translator loaded")
print(f"✅ Pypinyin loaded")
print(f"✅ Youtube-Search loaded")

# ============================================================
# PHẦN CÒN LẠI GIỮ NGUYÊN (KHÔNG THAY ĐỔI)
# ============================================================

def search_video_id_from_filename(filename):
    """
    Tìm video ID bằng yt-dlp, fallback sang youtube-search-python
    """
    name = Path(filename).stem
    search_query = clean_search_query(name)
    print(f"🔍 Tìm kiếm YouTube: '{search_query}'")
    
    # CÁCH 1: DÙNG YT-DLP
    try:
        cmd = [
            'yt-dlp',
            f'ytsearch10:{search_query}',
            '--print', '%(title)s|||%(id)s',
            '--no-warnings',
            '--no-playlist',
            '--ignore-errors'
        ]
        print("⏳ Đang tìm kiếm với yt-dlp...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0 and result.stdout:
            lines = [l for l in result.stdout.strip().split('\n') if l and '|||' in l]
            if lines:
                best_match = None
                best_score = 0
                for line in lines:
                    title, video_id = line.split('|||', 1)
                    score = similarity_score(search_query, title)
                    print(f"  📊 Độ khớp: {score:.2f} | {title[:50]}...")
                    if score > best_score:
                        best_score = score
                        best_match = {'title': title, 'id': video_id.strip()}
                if best_match and best_score > 0.3:
                    print(f"\n🏆 CHỌN: {best_match['title']}")
                    print(f"🔗 https://youtube.com/watch?v={best_match['id']}")
                    print(f"📊 Độ khớp: {best_score:.2f}")
                    return best_match['id']
                else:
                    print(f"ℹ️ Không có video khớp (độ khớp cao nhất: {best_score:.2f})")
            else:
                print("ℹ️ yt-dlp không trả về kết quả")
        else:
            if result.stderr:
                print(f"⚠️ yt-dlp lỗi: {result.stderr[:200]}")
            print("ℹ️ yt-dlp không tìm thấy, thử fallback...")
    except subprocess.TimeoutExpired:
        print("⏱️ yt-dlp timeout, thử fallback...")
    except Exception as e:
        print(f"⚠️ yt-dlp lỗi: {e}, thử fallback...")
    
    # CÁCH 2: FALLBACK DÙNG YOUTUBE-SEARCH-PYTHON
    print("🔄 Fallback: dùng youtube-search-python...")
    try:
        results = YoutubeSearch(search_query, max_results=10).to_dict()
        if not results:
            print("❌ Không tìm thấy video nào")
            return None
        
        print(f"✅ Tìm thấy {len(results)} video")
        best_match = None
        best_score = 0
        for video in results:
            title = video.get('title', '')
            score = similarity_score(search_query, title)
            print(f"  📊 Độ khớp: {score:.2f} | {title[:50]}...")
            if score > best_score:
                best_score = score
                best_match = video
        if best_match and best_score > 0.3:
            video_id = best_match.get('id')
            print(f"\n🏆 CHỌN: {best_match['title']}")
            print(f"🔗 https://youtube.com/watch?v={video_id}")
            print(f"📊 Độ khớp: {best_score:.2f}")
            return video_id
        else:
            print(f"❌ Không có video khớp (độ khớp cao nhất: {best_score:.2f})")
            return None
    except Exception as e:
        print(f"❌ Lỗi fallback: {e}")
        return None

# ... PHẦN CÒN LẠI GIỮ NGUYÊN ...
# (clean_search_query, similarity_score, extract_video_id_from_filename, 
#  get_youtube_link, format_time, generate_subtitle, main)
