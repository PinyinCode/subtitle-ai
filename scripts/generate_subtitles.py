#!/usr/bin/env python3
"""
YouTube Subtitle Generator - Faster Whisper
Tự động tìm video ID từ tên file
Hỗ trợ tất cả ngôn ngữ: Tiếng Việt, Tiếng Trung, Tiếng Anh, ...
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

# ===== KIỂM TRA VÀ CÀI YT-DLP =====
def ensure_yt_dlp():
    try:
        result = subprocess.run(['yt-dlp', '--version'], 
                               capture_output=True, timeout=5, text=True)
        if result.returncode == 0:
            print(f"✅ yt-dlp version: {result.stdout.strip()}")
            return True
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    
    print("📦 yt-dlp chưa được cài đặt, đang cài đặt...")
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', 'yt-dlp'], 
                      check=True, timeout=60)
        print("✅ yt-dlp đã được cài đặt thành công!")
        result = subprocess.run(['yt-dlp', '--version'], 
                               capture_output=True, timeout=5, text=True)
        if result.returncode == 0:
            print(f"✅ yt-dlp version: {result.stdout.strip()}")
            return True
        return False
    except Exception as e:
        print(f"❌ Không thể cài yt-dlp: {e}")
        return False

if not ensure_yt_dlp():
    print("⚠️ Cảnh báo: Không thể cài đặt yt-dlp")

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
    name = Path(filename).stem
    search_query = clean_search_query(name)
    print(f"🔍 Tìm kiếm YouTube: '{search_query}'")
    
    try:
        cmd = [
            'yt-dlp',
            f'ytsearch20:{search_query}',
            '--flat-playlist',
            '--print', '%(title)s|||%(id)s',
            '--no-warnings',
            '--no-playlist',
            '--no-check-certificates',
            '--default-search', 'ytsearch',
            '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            '--extractor-args', 'youtube:skip=hls,dash,player_js,webpage',
            '--ignore-errors',
            '--retries', '5',
            '--fragment-retries', '5'
        ]
        
        print(f"⏳ Đang tìm kiếm với yt-dlp...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        
        if result.returncode != 0 or not result.stdout:
            print(f"❌ Không tìm thấy video nào (return code: {result.returncode})")
            if result.stderr:
                print(f"   Lỗi: {result.stderr[:200]}")
            return None
        
        lines = result.stdout.strip().split('\n')
        lines = [l for l in lines if l.strip() and '|||' in l]
        
        if not lines:
            print("❌ Không tìm thấy video nào")
            return None
        
        print(f"✅ Tìm thấy {len(lines)} video")
        
        best_match = None
        best_score = 0
        
        for line in lines:
            if '|||' in line:
                parts = line.split('|||', 1)
                if len(parts) == 2:
                    title, video_id = parts
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
            print(f"❌ Không có video nào khớp (độ khớp cao nhất: {best_score:.2f})")
            return None
            
    except subprocess.TimeoutExpired:
        print("❌ Tìm kiếm quá thời gian (90s)")
        return None
    except Exception as e:
        print(f"❌ Lỗi tìm kiếm: {e}")
        return None


def clean_search_query(filename):
    """Làm sạch tên file để tìm kiếm - GIỮ NGUYÊN NGÔN NGỮ"""
    name = Path(filename).stem
    
    # Xóa emoji
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"
        u"\U0001F300-\U0001F5FF"
        u"\U0001F680-\U0001F6FF"
        u"\U0001F1E0-\U0001F1FF"
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        u"\U0001F900-\U0001F9FF"
        u"\U0001FA70-\U0001FAFF"
        "]+", flags=re.UNICODE)
    name = emoji_pattern.sub(r'', name)
    
    # GIỮ NGUYÊN CHỮ VÀ SỐ (KHÔNG XÓA KÝ TỰ ĐẶC BIỆT CỦA TIẾNG VIỆT/TRUNG)
    # Chỉ xóa các ký tự điều khiển và khoảng trắng thừa
    name = re.sub(r'\s+', ' ', name).strip()
    
    # Chỉ xóa các ký tự đặc biệt không cần thiết nhưng giữ lại dấu cách
    # \u00C0-\u024F: ký tự có dấu của tiếng Việt và các ngôn ngữ châu Âu
    # \u4E00-\u9FFF: ký tự tiếng Trung
    name = re.sub(r'[^\w\s\u00C0-\u024F\u4E00-\u9FFF]', ' ', name)
    
    # Xóa khoảng trắng thừa
    name = re.sub(r'\s+', ' ', name).strip()
    
    return name


def similarity_score(a, b):
    a = a.lower()
    b = b.lower()
    a = re.sub(r'[^\w\s\u00C0-\u024F\u4E00-\u9FFF]', ' ', a)
    b = re.sub(r'[^\w\s\u00C0-\u024F\u4E00-\u9FFF]', ' ', b)
    return SequenceMatcher(None, a, b).ratio()


def extract_video_id_from_filename(filename):
    """
    Tự động tìm video ID từ tên file
    Ưu tiên: 1. File .txt, 2. Tìm kiếm YouTube
    """
    name = Path(filename).stem
    folder = Path(filename).parent
    
    # CÁCH 1: ĐỌC TỪ FILE .TXT CÙNG TÊN
    txt_file = folder / f"{name}.txt"
    if txt_file.exists():
        try:
            with open(txt_file, 'r', encoding='utf-8') as f:
                content = f.read()
            match = re.search(r'(?:v=|\/)([a-zA-Z0-9_-]{11})', content)
            if match:
                video_id = match.group(1)
                print(f"✅ Đọc video ID từ file .txt: {video_id}")
                return video_id
            match = re.search(r'https?://(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})', content)
            if match:
                video_id = match.group(1)
                print(f"✅ Đọc link YouTube từ file .txt: {video_id}")
                return video_id
        except Exception as e:
            print(f"⚠️ Lỗi đọc file .txt: {e}")
    
    # CÁCH 2: Tìm kiếm trên YouTube
    print(f"🔍 Không có file .txt, tìm kiếm trên YouTube...")
    print(f"📝 Tên file gốc: {name}")
    video_id = search_video_id_from_filename(filename)
    
    if video_id:
        print(f"✅ Tìm thấy video ID từ YouTube: {video_id}")
        return video_id
    
    print(f"❌ Không thể tìm thấy video ID cho: {filename}")
    print(f"💡 Tạo file {name}.txt chứa link YouTube để xử lý nhanh hơn")
    return None


def get_youtube_link(video_id):
    if video_id:
        return f"https://youtube.com/watch?v={video_id}"
    return ""


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
        print(f"❌ Không tìm thấy video ID cho: {audio_file.name}")
        return None
    
    youtube_link = get_youtube_link(video_id)
    print(f"🔗 YouTube: {youtube_link}")
    
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
    
    # LOAD WHISPER
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
        vad_parameters=dict(
            min_silence_duration_ms=500,
            threshold=0.5
        )
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
    print(f"Transcription done in {elapsed:.1f}s")
    print(f"Segments: {len(segment_list)}")
    
    if not segment_list:
        print("No segments found!")
        return None
    
    # DỊCH
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
    
    # TẠO VTT
    print("\nGenerating subtitles...")
    
    vtt_lines = [
        "WEBVTT",
        "Kind: captions",
        "Language: zh-TW",
        "",
        ""
    ]
    
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
    
    # LƯU FILE
    print(f"\n💾 Saving to: {output_file}")
    vtt_content = '\n'.join(vtt_lines)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(vtt_content)
    
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
    
    # Xuất env
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


# ===== MAIN =====
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
