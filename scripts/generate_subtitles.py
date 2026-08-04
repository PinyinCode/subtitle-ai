#!/usr/bin/env python3
"""
YouTube Subtitle Generator - Faster Whisper
Tao phu de 3 dong: Chinese + Pinyin + Vietnamese
Encoding: UTF-8 (khong BOM)
CHI XU LY 1 FILE AUDIO MOI NHAT
TU DONG TIM YOUTUBE LINK TU TEN FILE
"""

import os
import sys
import json
import glob
import re
import argparse
from pathlib import Path
from datetime import datetime

# 👈 CÀI FASTER-WHISPER
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


def extract_video_id_from_filename(filename):
    """
    Trích xuất video ID từ tên file
    Hỗ trợ nhiều định dạng:
    - abc123xyz.m4a (trực tiếp)
    - video_abc123xyz.m4a (có tiền tố)
    - abc123xyz_audio.m4a (có hậu tố)
    - https___youtube.com_watch_v=abc123xyz.m4a (link đã mã hóa)
    - watch?v=abc123xyz.m4a
    - youtu.be/abc123xyz.m4a
    """
    # Lấy tên file không extension
    name = Path(filename).stem
    
    # Pattern 1: Video ID chuẩn 11 ký tự
    match = re.search(r'([a-zA-Z0-9_-]{11})', name)
    if match:
        video_id = match.group(1)
        # Kiểm tra không chứa từ khóa
        if not any(keyword in name.lower() for keyword in ['audio', 'video', 'subtitle', 'track']):
            return video_id
    
    # Pattern 2: Link YouTube đã mã hóa (https___youtube.com_watch_v=abc123xyz)
    match = re.search(r'watch_v[=_]([a-zA-Z0-9_-]{11})', name)
    if match:
        return match.group(1)
    
    # Pattern 3: watch?v=abc123xyz
    match = re.search(r'watch\?v[=_]([a-zA-Z0-9_-]{11})', name)
    if match:
        return match.group(1)
    
    # Pattern 4: youtu.be/abc123xyz
    match = re.search(r'youtu\.be[/_]([a-zA-Z0-9_-]{11})', name)
    if match:
        return match.group(1)
    
    # Pattern 5: vid=abc123xyz
    match = re.search(r'vid[=_]([a-zA-Z0-9_-]{11})', name, re.IGNORECASE)
    if match:
        return match.group(1)
    
    # Pattern 6: Nếu không tìm thấy, lấy 11 ký tự cuối cùng
    if len(name) >= 11:
        last_11 = name[-11:]
        if re.match(r'^[a-zA-Z0-9_-]{11}$', last_11):
            if not any(keyword in last_11 for keyword in ['audio', 'video', 'subtitle', 'track']):
                return last_11
    
    return None


def get_youtube_link(video_id):
    """Tạo link YouTube từ video ID"""
    if video_id:
        return f"https://youtube.com/watch?v={video_id}"
    return ""


def format_time(seconds):
    """Format seconds to VTT timestamp: HH:MM:SS.mmm"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def generate_subtitle(audio_path, output_path=None):
    """Generate VTT subtitle from audio file using faster-whisper"""
    
    audio_file = Path(audio_path)
    
    # 👈 LẤY VIDEO_ID TỪ TÊN FILE (GIỮ NGUYÊN CÁCH CŨ)
    video_id = audio_file.stem
    
    # 👈 TỰ ĐỘNG TÌM YOUTUBE LINK
    extracted_id = extract_video_id_from_filename(audio_file.name)
    youtube_link = get_youtube_link(extracted_id) if extracted_id else ""
    
    if extracted_id:
        print(f"✅ Tự động tìm thấy YouTube link: {youtube_link}")
    else:
        print(f"ℹ️ Không tìm thấy YouTube link trong tên file")
    
    # Kiểm tra file audio
    print(f"🔍 Audio file: {audio_path}")
    print(f"🔍 Audio exists: {os.path.exists(audio_path)}")
    
    # 👈 VẪN GIỮ NGUYÊN CÁCH ĐẶT TÊN FILE VTT
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
    if youtube_link:
        print(f"🔗 YouTube: {youtube_link}")
    print(f"{'='*50}\n")
    
    # 👈 LOAD FASTER-WHISPER MODEL
    print("Loading Faster-Whisper model (base)...")
    print("⏳ This may take 10-30 seconds to download model...")
    
    # Dùng CPU với int8 để tiết kiệm RAM và tăng tốc
    model = WhisperModel("base", device="cpu", compute_type="int8")
    # 👆 Có thể đổi thành "small", "medium", "large-v3"
    # compute_type: "int8" (nhanh nhất), "float16" (cân bằng), "float32" (chính xác nhất)
    
    print("Model loaded")
    
    # 👈 TRANSCRIBE VỚI FASTER-WHISPER
    print("Transcribing audio...")
    start_time = datetime.now()
    
    segments, info = model.transcribe(
        audio_path,
        beam_size=5,              # 👈 Tăng độ chính xác
        language=None,            # 👈 Tự động phát hiện
        task="transcribe",        # 👈 Chỉ transcribe, không dịch
        vad_filter=True,          # 👈 Lọc im lặng để tăng tốc
        vad_parameters=dict(
            min_silence_duration_ms=500,
            threshold=0.5
        )
    )
    
    # Lấy thông tin ngôn ngữ
    detected_lang = info.language
    print(f"Detected language: {detected_lang}")
    
    # Chuyển segments sang list
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
    
    # Initialize translators
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
            print(f"   Error at segment {i}: {e}")
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
    
    # Kiểm tra file đã tạo
    if output_file.exists():
        print(f"✅ File exists! Size: {output_file.stat().st_size} bytes")
    else:
        print(f"❌ File does NOT exist after write!")
        return None
    
    # Save summary
    summary = {
        'video_id': video_id,
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
    
    # 👈 LƯU YOUTUBE LINK VÀO FILE INFO
    if youtube_link:
        info_file = output_file.parent / f"{video_id}.info.txt"
        with open(info_file, 'w', encoding='utf-8') as f:
            f.write(f"Video ID: {video_id}\n")
            f.write(f"YouTube Link: {youtube_link}\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write(f"Duration: {summary['duration']:.1f}s\n")
            f.write(f"Language: {detected_lang}\n")
        print(f"💾 Saved YouTube link to: {info_file}")
    
    # 👈 XUẤT VIDEO_ID RA FILE ENV CHO STEP SAU
    with open('video_id.env', 'w', encoding='utf-8') as f:
        f.write(f"VIDEO_ID={video_id}\n")
        f.write(f"YOUTUBE_LINK={youtube_link}\n")
    
    print(f"\n{'='*50}")
    print(f"COMPLETE!")
    print(f"{'='*50}")
    print(f"Output: {output_file}")
    if output_file.exists():
        print(f"Size: {output_file.stat().st_size / 1024:.1f} KB")
    print(f"Success: {success_count}/{len(segment_list)}")
    print(f"Language: {detected_lang}")
    print(f"Duration: {summary['duration']:.1f}s")
    if youtube_link:
        print(f"🔗 YouTube: {youtube_link}")
    print(f"{'='*50}\n")
    
    return str(output_file)


# ===== HÀM MAIN =====
def main():
    """Main function - Process audio file"""
    parser = argparse.ArgumentParser(description='Generate subtitles from audio')
    parser.add_argument('--audio', help='Path to audio file (specific file)')
    parser.add_argument('--output', help='Path to output VTT file')
    parser.add_argument('--latest', action='store_true', help='Process only the latest file')
    
    args = parser.parse_args()
    
    if args.audio:
        audio_path = args.audio
        if not os.path.exists(audio_path):
            print(f"❌ Audio file not found: {audio_path}")
            return
        
        output_path = args.output if args.output else None
        result = generate_subtitle(audio_path, output_path)
        if result:
            print(f"\n✅ Done: {result}")
        return
    
    print("\n🔍 Finding audio files...")
    audio_files = glob.glob("data/audio/*.m4a")
    
    if not audio_files:
        print("❌ No audio files found in data/audio/")
        return
    
    audio_files.sort(key=os.path.getmtime, reverse=True)
    latest_audio = audio_files[0]
    
    print(f"Found {len(audio_files)} file(s)")
    print(f"📌 Processing latest: {latest_audio}")
    
    if len(audio_files) > 1:
        print(f"   Skipping {len(audio_files)-1} old file(s)")
    
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
