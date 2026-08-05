#!/usr/bin/env python3
"""
YouTube Subtitle Generator - Faster Whisper
Tao phu de 3 dong: Chinese + Pinyin + Vietnamese
Encoding: UTF-8 (khong BOM)
CHI XU LY 1 FILE AUDIO MOI NHAT
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

# 👈 IMPORT TRỰC TIẾP (ĐÃ CÀI TRONG DOCKER)
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

try:
    from youtube_search import YoutubeSearch
except ImportError:
    os.system('pip install -q youtube-search-python')
    from youtube_search import YoutubeSearch

# ============================================================
# TÌM VIDEO ID TỪ TÊN FILE
# ============================================================

def search_youtube_video_id(query):
    """Tìm video YouTube từ query"""
    print(f"🔍 Searching YouTube: '{query}'")
    
    try:
        # Dùng yt-dlp nếu có
        cmd = [
            'yt-dlp',
            f'ytsearch5:{query}',
            '--print', '%(title)s|||%(id)s',
            '--no-warnings',
            '--no-playlist',
            '--ignore-errors'
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0 and result.stdout:
            lines = [l for l in result.stdout.strip().split('\n') if l and '|||' in l]
            if lines:
                best_match = None
                best_score = 0
                for line in lines:
                    title, video_id = line.split('|||', 1)
                    score = SequenceMatcher(None, query.lower(), title.lower()).ratio()
                    print(f"  📊 Score: {score:.2f} | {title[:50]}...")
                    if score > best_score:
                        best_score = score
                        best_match = {'title': title, 'id': video_id.strip()}
                
                if best_match and best_score > 0.3:
                    print(f"🏆 Selected: {best_match['title']}")
                    return best_match['id']
    except Exception as e:
        print(f"⚠️ yt-dlp error: {e}")
    
    # Fallback: youtube-search-python
    try:
        results = YoutubeSearch(query, max_results=5).to_dict()
        if results:
            for video in results:
                title = video.get('title', '')
                score = SequenceMatcher(None, query.lower(), title.lower()).ratio()
                print(f"  📊 Score: {score:.2f} | {title[:50]}...")
                if score > 0.3:
                    video_id = video.get('id')
                    print(f"🏆 Selected: {title}")
                    return video_id
    except Exception as e:
        print(f"⚠️ youtube-search error: {e}")
    
    return None

def format_time(seconds):
    """Format seconds to VTT timestamp: HH:MM:SS.mmm"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"

def generate_subtitle(audio_path, output_name=None, output_path=None):
    """Generate VTT subtitle from audio file using faster-whisper"""
    
    audio_file = Path(audio_path)
    
    # Sử dụng tên được truyền vào hoặc lấy từ file
    if output_name:
        video_id = output_name
    else:
        video_id = audio_file.stem
    
    # Kiểm tra file audio
    print(f"🔍 Audio file: {audio_path}")
    print(f"🔍 Audio exists: {os.path.exists(audio_path)}")
    print(f"🔍 Video ID: {video_id}")
    
    # Tạo output path
    if output_path is None:
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        output_file = output_dir / f"{video_id}.vtt"
    else:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"\n{'='*50}")
    print(f"Processing: {video_id}")
    print(f"Audio: {audio_path}")
    print(f"Output: {output_file}")
    if audio_file.exists():
        print(f"Size: {audio_file.stat().st_size / 1024:.0f} KB")
    print(f"{'='*50}\n")
    
    # 👈 TÌM VIDEO ID TRÊN YOUTUBE
    print("🔍 Searching for YouTube video...")
    youtube_video_id = search_youtube_video_id(video_id)
    youtube_link = f"https://youtube.com/watch?v={youtube_video_id}" if youtube_video_id else ""
    
    if youtube_video_id:
        print(f"🎯 Found video ID: {youtube_video_id}")
        print(f"🔗 {youtube_link}")
    else:
        print("⚠️ No YouTube video found")
    
    # 👈 LOAD FASTER-WHISPER MODEL
    print("\nLoading Faster-Whisper model (base)...")
    print("⏳ This may take 10-30 seconds to download model...")
    
    model = WhisperModel("base", device="cpu", compute_type="int8")
    print("✅ Model loaded")
    
    # 👈 TRANSCRIBE
    print("\nTranscribing audio...")
    start_time = datetime.now()
    
    segments, info = model.transcribe(
        audio_path,
        beam_size=5,
        language=None,
        task="transcribe",
        vad_filter=True,
        vad_parameters=dict(
            min_silence_duration_ms=500,
            threshold=0.5
        )
    )
    
    detected_lang = info.language
    print(f"✅ Detected language: {detected_lang}")
    
    segment_list = []
    for seg in segments:
        segment_list.append({
            'start': seg.start,
            'end': seg.end,
            'text': seg.text.strip()
        })
    
    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"✅ Transcription done in {elapsed:.1f}s")
    print(f"📊 Segments: {len(segment_list)}")
    
    if not segment_list:
        print("❌ No segments found!")
        return None
    
    # Initialize translators
    print("\nSetting up translators...")
    
    to_chinese = None
    if not detected_lang.startswith('zh'):
        try:
            to_chinese = GoogleTranslator(source=detected_lang, target='zh-CN')
            print(f"  ✅ Chinese: {detected_lang} -> zh-CN")
        except Exception as e:
            print(f"⚠️ Cannot translate to Chinese: {e}")
    
    to_vietnamese = GoogleTranslator(source='zh-CN', target='vi')
    print("  ✅ Vietnamese: zh-CN -> vi")
    
    # Generate VTT content
    print("\nGenerating subtitles...")
    
    vtt_lines = [
        "WEBVTT",
        "Kind: captions",
        "Language: zh-TW",
        "",
        ""
    ]
    
    success_count = 0
    error_count = 0
    total = len(segment_list)
    
    for i, seg in enumerate(segment_list, 1):
        try:
            start = format_time(seg['start'])
            end = format_time(seg['end'])
            text = seg['text']
            
            if not text:
                continue
            
            # Translate to Chinese if needed
            if to_chinese:
                try:
                    chinese_text = to_chinese.translate(text)
                except:
                    chinese_text = text
            else:
                chinese_text = text
            
            # Generate Pinyin
            try:
                py_list = pinyin(chinese_text, style=Style.TONE, heteronym=False)
                pinyin_text = " ".join([item[0] for item in py_list])
            except:
                pinyin_text = chinese_text
            
            # Translate to Vietnamese
            try:
                vietnamese_text = to_vietnamese.translate(chinese_text)
            except:
                vietnamese_text = ""
            
            # Add to VTT
            vtt_lines.append(f"{start} --> {end}")
            vtt_lines.append(chinese_text)
            vtt_lines.append(pinyin_text)
            vtt_lines.append(vietnamese_text)
            vtt_lines.append("")
            
            success_count += 1
            
            if i % 20 == 0:
                print(f"   {i}/{total} ({100*i//total}%)")
                
        except Exception as e:
            error_count += 1
            print(f"   ⚠️ Error at segment {i}: {e}")
            continue
    
    # Save VTT file
    print(f"\n💾 Saving to: {output_file}")
    
    vtt_content = '\n'.join(vtt_lines)
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(vtt_content)
        print(f"✅ File written successfully!")
    except Exception as e:
        print(f"❌ Error writing file: {e}")
        return None
    
    # Save info file
    info_file = output_file.parent / f"{video_id}.info.txt"
    with open(info_file, 'w', encoding='utf-8') as f:
        f.write(f"Video ID: {youtube_video_id or video_id}\n")
        f.write(f"YouTube Link: {youtube_link}\n")
        f.write(f"Original Name: {video_id}\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write(f"Language: {detected_lang}\n")
        f.write(f"Segments: {len(segment_list)}\n")
    print(f"💾 Saved info to: {info_file}")
    
    # Save summary
    summary = {
        'video_id': video_id,
        'youtube_video_id': youtube_video_id,
        'youtube_link': youtube_link,
        'language': detected_lang,
        'total_segments': len(segment_list),
        'success_segments': success_count,
        'error_segments': error_count,
        'duration': segment_list[-1]['end'] if segment_list else 0,
        'transcription_time': round(elapsed, 1),
        'output_file': str(output_file),
        'output_size': output_file.stat().st_size if output_file.exists() else 0,
        'timestamp': datetime.now().isoformat()
    }
    
    summary_file = output_file.parent / f"{video_id}_summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    # Xuất env cho workflow
    env_file = Path('video_id.env')
    with open(env_file, 'w', encoding='utf-8') as f:
        f.write(f"VIDEO_ID={youtube_video_id or video_id}\n")
        f.write(f"YOUTUBE_LINK={youtube_link}\n")
        f.write(f"ORIGINAL_FILENAME={video_id}\n")
    print(f"💾 Saved env to: {env_file}")
    
    print(f"\n{'='*50}")
    print(f"✅ COMPLETE!")
    print(f"{'='*50}")
    print(f"Output: {output_file}")
    if output_file.exists():
        print(f"Size: {output_file.stat().st_size / 1024:.1f} KB")
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
    parser.add_argument('--audio', required=True, help='Path to audio file')
    parser.add_argument('--name', help='Output name (without extension)')
    parser.add_argument('--output', help='Path to output VTT file')
    
    args = parser.parse_args()
    
    audio_path = args.audio
    if not os.path.exists(audio_path):
        print(f"❌ Audio file not found: {audio_path}")
        return
    
    try:
        result = generate_subtitle(audio_path, args.name, args.output)
        if result:
            print(f"\n✅ Done: {result}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
