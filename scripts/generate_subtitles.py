#!/usr/bin/env python3
"""
YouTube Subtitle Generator - Faster Whisper
Tao phu de 3 dong: Chinese + Pinyin + Vietnamese
"""

import os
import sys
import json
import glob
import argparse
from pathlib import Path
from datetime import datetime

# ============================================================
# TẮT HOÀN TOÀN CẢNH BÁO
# ============================================================
os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['HF_HUB_ENABLE_HF_TRANSFER'] = '0'

import warnings
warnings.filterwarnings("ignore")

# Chuyển hướng stderr để bỏ qua cảnh báo
stderr_backup = sys.stderr
sys.stderr = open(os.devnull, 'w')
# ============================================================

try:
    from faster_whisper import WhisperModel
except ImportError:
    os.system('pip install -q faster-whisper')
    from faster_whisper import WhisperModel

# Khôi phục stderr
sys.stderr = stderr_backup

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


def format_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def generate_subtitle(audio_path, output_path=None):
    audio_file = Path(audio_path)
    video_id = audio_file.stem
    
    print(f"🔍 Audio: {audio_path}")
    print(f"🔍 Exists: {os.path.exists(audio_path)}")
    
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
    
    print("Loading Faster-Whisper model...")
    
    # 👈 KHÔNG IN CẢNH BÁO
    with open(os.devnull, 'w') as devnull:
        old_stderr = sys.stderr
        sys.stderr = devnull
        try:
            model = WhisperModel("medium", device="cpu", compute_type="int8")
        finally:
            sys.stderr = old_stderr
    
    print("✅ Model loaded")
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
    print(f"Language: {detected_lang}")
    
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
    
    print("Setting up translators...")
    
    to_chinese = None
    if not detected_lang.startswith('zh'):
        try:
            to_chinese = GoogleTranslator(source=detected_lang, target='zh-CN')
            print(f"  Chinese: {detected_lang} -> zh-CN")
        except Exception as e:
            print(f"⚠️ Cannot translate: {e}")
    
    to_vietnamese = GoogleTranslator(source='zh-CN', target='vi')
    print("  Vietnamese: zh-CN -> vi")
    
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
            error_count += 1
            print(f"   Error at segment {i}: {e}")
            continue
    
    print(f"\n💾 Saving to: {output_file}")
    
    vtt_content = '\n'.join(vtt_lines)
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(vtt_content)
        print(f"✅ File written successfully!")
    except Exception as e:
        print(f"❌ Error writing file: {e}")
        return None
    
    if output_file.exists():
        print(f"✅ File exists! Size: {output_file.stat().st_size} bytes")
    else:
        print(f"❌ File does NOT exist after write!")
        return None
    
    summary = {
        'video_id': video_id,
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
    
    print(f"\n{'='*50}")
    print(f"COMPLETE!")
    print(f"{'='*50}")
    print(f"Output: {output_file}")
    if output_file.exists():
        print(f"Size: {output_file.stat().st_size / 1024:.1f} KB")
    print(f"Success: {success_count}/{len(segment_list)}")
    print(f"Language: {detected_lang}")
    print(f"Duration: {summary['duration']:.1f}s")
    print(f"{'='*50}\n")
    
    return str(output_file)


def main():
    parser = argparse.ArgumentParser(description='Generate subtitles from audio')
    parser.add_argument('--audio', help='Path to audio file')
    parser.add_argument('--output', help='Path to output VTT file')
    
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
