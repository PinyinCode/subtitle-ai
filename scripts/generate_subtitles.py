#!/usr/bin/env python3
"""
YouTube Subtitle Generator - Whisper AI
Tạo phụ đề 3 dòng: Chinese + Pinyin + Vietnamese
"""

import os
import json
import glob
from pathlib import Path
from datetime import datetime

# Cài đặt whisper nếu chưa có
try:
    import whisper
except ImportError:
    os.system('pip install openai-whisper -q')
    import whisper

try:
    from deep_translator import GoogleTranslator
except ImportError:
    os.system('pip install deep-translator -q')
    from deep_translator import GoogleTranslator

try:
    from pypinyin import pinyin, Style
except ImportError:
    os.system('pip install pypinyin -q')
    from pypinyin import pinyin, Style


def format_time(seconds):
    """Format seconds to VTT timestamp"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def generate_subtitle(audio_path):
    """Generate VTT subtitle from audio file"""
    
    audio_file = Path(audio_path)
    video_id = audio_file.stem
    
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    output_file = output_dir / f"{video_id}.vtt"
    
    print(f"\n{'='*50}")
    print(f"🎬 Processing: {video_id}")
    print(f"📁 Audio: {audio_path}")
    print(f"📏 Size: {audio_file.stat().st_size / 1024:.0f} KB")
    print(f"{'='*50}\n")
    
    # Load Whisper model
    print("🤖 Loading Whisper model (base)...")
    model = whisper.load_model("base")
    print("✅ Model loaded")
    
    # Transcribe audio
    print("🎤 Transcribing audio...")
    start_time = datetime.now()
    
    result = model.transcribe(
        audio_path,
        language=None,  # Auto-detect
        task="transcribe",
        verbose=False
    )
    
    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"✅ Transcription done in {elapsed:.1f}s")
    
    # Get results
    detected_lang = result.get("language", "zh")
    segments = result.get("segments", [])
    
    print(f"📝 Language: {detected_lang}")
    print(f"📊 Segments: {len(segments)}")
    
    if not segments:
        print("❌ No segments found!")
        return None
    
    # Initialize translators
    print("🌐 Setting up translators...")
    
    to_chinese = None
    if not detected_lang.startswith('zh'):
        to_chinese = GoogleTranslator(source=detected_lang, target='zh-CN')
        print(f"   Chinese: {detected_lang} → zh-CN")
    
    to_vietnamese = GoogleTranslator(source='zh-CN', target='vi')
    print("   Vietnamese: zh-CN → vi")
    
    # Generate VTT content
    print("\n📝 Generating subtitles...")
    
    vtt_lines = [
        "WEBVTT",
        "Kind: captions",
        "Language: zh-TW",
        "",
        ""
    ]
    
    success_count = 0
    error_count = 0
    
    for i, segment in enumerate(segments, 1):
        try:
            start = format_time(segment["start"])
            end = format_time(segment["end"])
            text = segment["text"].strip()
            
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
            
            # Progress every 20 segments
            if i % 20 == 0:
                print(f"   ⏳ {i}/{len(segments)} segments ({100*i//len(segments)}%)")
                
        except Exception as e:
            error_count += 1
            print(f"   ⚠️ Error at segment {i}: {e}")
            continue
    
    # Save VTT file
    print(f"\n💾 Saving to: {output_file}")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(vtt_lines))
    
    # Save summary
    summary = {
        'video_id': video_id,
        'language': detected_lang,
        'total_segments': len(segments),
        'success_segments': success_count,
        'error_segments': error_count,
        'duration': segments[-1]['end'] if segments else 0,
        'transcription_time': round(elapsed, 1),
        'output_file': str(output_file),
        'output_size': output_file.stat().st_size,
        'timestamp': datetime.now().isoformat()
    }
    
    summary_file = output_dir / f"{video_id}_summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    # Print final summary
    print(f"\n{'='*50}")
    print(f"✅ COMPLETE!")
    print(f"{'='*50}")
    print(f"📄 Output: {output_file}")
    print(f"📏 Size: {output_file.stat().st_size / 1024:.1f} KB")
    print(f"🎯 Success: {success_count}/{len(segments)} ({100*success_count//len(segments)}%)")
    print(f"🌍 Language: {detected_lang}")
    print(f"⏱️ Duration: {summary['duration']:.1f}s")
    print(f"⚡ Speed: {summary['duration']/elapsed:.1f}x realtime")
    print(f"{'='*50}\n")
    
    return str(output_file)


def main():
    """Main function"""
    print("\n🔍 Tìm file audio...")
    
    audio_files = glob.glob("data/audio/*.m4a")
    
    if not audio_files:
        print("❌ Không tìm thấy file audio nào trong data/audio/")
        return
    
    print(f"📄 Tìm thấy {len(audio_files)} file(s):")
    for f in audio_files:
        print(f"   - {f}")
    
    results = []
    for audio_file in audio_files:
        try:
            result = generate_subtitle(audio_file)
            if result:
                results.append(result)
        except Exception as e:
            print(f"❌ Lỗi xử lý {audio_file}: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n✅ Đã xử lý {len(results)}/{len(audio_files)} file(s)")
    
    if results:
        print("Files đã tạo:")
        for r in results:
            print(f"   - {r}")


if __name__ == "__main__":
    main()
