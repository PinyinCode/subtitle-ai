#!/usr/bin/env python3
"""
YouTube Subtitle Generator - Faster Whisper
Tự động tìm video ID từ tên file
Hỗ trợ yt-dlp và fallback youtube-search-python
"""

import os
import sys
import json
import glob
import re
import subprocess
import argparse
from pathlib import Path
from datetime import datetime
from difflib import SequenceMatcher

# ============================================================
# KIỂM TRA VÀ CÀI DEPENDENCIES
# ============================================================

def ensure_package(package_name, import_name=None):
    """Kiểm tra và cài đặt package nếu chưa có"""
    if import_name is None:
        import_name = package_name
    try:
        __import__(import_name)
        return True
    except ImportError:
        print(f"📦 Đang cài {package_name}...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', package_name], 
                      check=True, timeout=60)
        print(f"✅ Đã cài {package_name}")
        return True

# Cài các thư viện cần thiết
ensure_package('faster-whisper')
ensure_package('deep-translator')
ensure_package('pypinyin')
ensure_package('youtube-search-python', 'youtube_search')

# Import các thư viện
from faster_whisper import WhisperModel
from deep_translator import GoogleTranslator
from pypinyin import pinyin, Style
from youtube_search import YoutubeSearch

# ============================================================
# HÀM TÌM VIDEO ID
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

def clean_search_query(filename):
    """Làm sạch tên file để tìm kiếm"""
    name = Path(filename).stem
    name = re.sub(r'^\d+[\s._-]+', '', name)
    remove_words = ['audio', 'video', 'subtitle', 'track', 'clip', 'full', 'hd', 
                    'official', 'music', 'song', 'lyric', 'cover', 'remix', 'live',
                    'mv', 'ft', 'feat', 'featuring', '128k', '320k', 'podcast']
    for word in remove_words:
        name = re.sub(r'\b' + word + r'\b', ' ', name, flags=re.IGNORECASE)
    name = re.sub(r'[^\w\s]', ' ', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name

def similarity_score(a, b):
    """Tính độ tương đồng giữa 2 chuỗi"""
    a = re.sub(r'[^\w\s]', ' ', a.lower())
    b = re.sub(r'[^\w\s]', ' ', b.lower())
    return SequenceMatcher(None, a, b).ratio()

def extract_video_id_from_filename(filename):
    """
    Tự động tìm video ID từ tên file
    Ưu tiên: 1. Tìm 11 ký tự, 2. Tìm kiếm YouTube
    """
    name = Path(filename).stem
    match = re.search(r'([a-zA-Z0-9_-]{11})', name)
    if match:
        video_id = match.group(1)
        if not any(k in name.lower() for k in ['audio', 'video', 'subtitle', 'track']):
            print(f"✅ Tìm thấy video ID trong tên: {video_id}")
            return video_id
    print("🔍 Không tìm thấy ID trong tên, tìm kiếm trên YouTube...")
    video_id = search_video_id_from_filename(filename)
    if video_id:
        print(f"✅ Tìm thấy video ID từ YouTube: {video_id}")
        return video_id
    print(f"❌ Không thể tìm thấy video ID cho: {filename}")
    return None

def get_youtube_link(video_id):
    return f"https://youtube.com/watch?v={video_id}" if video_id else ""

# ============================================================
# HÀM CHÍNH TẠO SUBTITLE
# ============================================================

def format_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"

def generate_subtitle(audio_path, output_path=None):
    audio_file = Path(audio_path)
    video_id = extract_video_id_from_filename(audio_file.name)
    if not video_id:
        return None
    youtube_link = get_youtube_link(video_id)
    original_name = audio_file.stem
    output_filename = original_name
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
    
    # Load Whisper model
    print("Loading Faster-Whisper model (base)...")
    model = WhisperModel("base", device="cpu", compute_type="int8")
    print("Model loaded")
    
    print("Transcribing audio...")
    start_time = datetime.now()
    segments, info = model.transcribe(
        audio_path,
        beam_size=5,
        language=None,
        task="transcribe",
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500, threshold=0.5)
    )
    detected_lang = info.language
    print(f"Detected language: {detected_lang}")
    
    segment_list = []
    for seg in segments:
        segment_list.append({
            'start': seg.start,
            'end': seg.end,
            'text': seg.text.strip()
        })
    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"Transcription done in {elapsed:.1f}s, segments: {len(segment_list)}")
    if not segment_list:
        print("No segments found!")
        return None
    
    # Dịch
    print("Setting up translators...")
    to_chinese = None
    if not detected_lang.startswith('zh'):
        try:
            to_chinese = GoogleTranslator(source=detected_lang, target='zh-CN')
            print(f"  Chinese: {detected_lang} -> zh-CN")
        except:
            print(f"⚠️ Cannot translate from {detected_lang} to Chinese")
    to_vietnamese = GoogleTranslator(source='zh-CN', target='vi')
    print("  Vietnamese: zh-CN -> vi")
    
    # Tạo VTT
    print("\nGenerating subtitles...")
    vtt_lines = ["WEBVTT", "Kind: captions", "Language: zh-TW", "", ""]
    success_count = 0
    total = len(segment_list)
    for i, seg in enumerate(segment_list, 1):
        try:
            start = format_time(seg['start'])
            end = format_time(seg['end'])
            text = seg['text']
            if not text:
                continue
            if to_chinese:
                try:
                    chinese_text = to_chinese.translate(text)
                except:
                    chinese_text = text
            else:
                chinese_text = text
            try:
                py_list = pinyin(chinese_text, style=Style.TONE, heteronym=False)
                pinyin_text = " ".join([item[0] for item in py_list])
            except:
                pinyin_text = chinese_text
            try:
                vietnamese_text = to_vietnamese.translate(chinese_text)
            except:
                vietnamese_text = ""
            vtt_lines.append(f"{start} --> {end}")
            vtt_lines.append(chinese_text)
            vtt_lines.append(pinyin_text)
            vtt_lines.append(vietnamese_text)
            vtt_lines.append("")
            success_count += 1
            if i % 20 == 0:
                print(f"   {i}/{total} ({100*i//total}%)")
        except Exception as e:
            print(f"   Error at segment {i}: {e}")
            continue
    
    # Lưu file VTT
    print(f"\n💾 Saving to: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(vtt_lines))
    if output_file.exists():
        print(f"✅ File written! Size: {output_file.stat().st_size} bytes")
    
    # Lưu summary
    summary = {
        'video_id': video_id,
        'youtube_link': youtube_link,
        'language': detected_lang,
        'total_segments': len(segment_list),
        'success_segments': success_count,
        'duration': segment_list[-1]['end'] if segment_list else 0,
        'transcription_time': round(elapsed, 1),
        'output_file': str(output_file),
        'timestamp': datetime.now().isoformat()
    }
    summary_file = output_file.parent / f"{output_filename}_summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    # Lưu info
    if youtube_link:
        info_file = output_file.parent / f"{output_filename}.info.txt"
        with open(info_file, 'w', encoding='utf-8') as f:
            f.write(f"Video ID: {video_id}\n")
            f.write(f"YouTube Link: {youtube_link}\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write(f"Language: {detected_lang}\n")
        print(f"💾 Saved info to: {info_file}")
    
    # Xuất env cho workflow
    with open('video_id.env', 'w', encoding='utf-8') as f:
        f.write(f"VIDEO_ID={video_id}\n")
        f.write(f"YOUTUBE_LINK={youtube_link}\n")
        f.write(f"ORIGINAL_FILENAME={output_filename}\n")
    
    print(f"\n{'='*50}")
    print(f"✅ COMPLETE!")
    print(f"{'='*50}")
    print(f"Output: {output_file}")
    print(f"Success: {success_count}/{len(segment_list)}")
    print(f"Language: {detected_lang}")
    if youtube_link:
        print(f"🔗 YouTube: {youtube_link}")
    print(f"{'='*50}\n")
    
    return str(output_file)

# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description='Generate subtitles from audio')
    parser.add_argument('--audio', help='Path to audio file')
    parser.add_argument('--output', help='Path to output VTT file')
    parser.add_argument('--latest', action='store_true', help='Process latest file')
    args = parser.parse_args()
    
    if args.audio:
        if not os.path.exists(args.audio):
            print(f"❌ Audio file not found: {args.audio}")
            return
        result = generate_subtitle(args.audio, args.output)
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
