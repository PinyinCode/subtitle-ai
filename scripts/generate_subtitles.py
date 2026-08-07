#!/usr/bin/env python3
"""
YouTube Subtitle Generator - Faster Whisper
Tự động tìm video ID từ tên file
CHỈ CẦN LẤY LINK, KHÔNG CẦN XÁC MINH VIDEO
HỖ TRỢ TẤT CẢ NGÔN NGỮ: TIẾNG VIỆT, TIẾNG TRUNG, TIẾNG ANH
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
    """Kiểm tra và cài yt-dlp nếu chưa có"""
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
        return True
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


# ============================================================
# HÀM LÀM SẠCH TÊN (GIỮ NGUYÊN TIẾNG TRUNG, TIẾNG VIỆT)
# ============================================================
def clean_filename_for_file(filename):
    """
    Làm sạch tên file để dùng làm tên file
    - GIỮ NGUYÊN tiếng Trung, tiếng Việt, tiếng Anh
    - Chỉ XÓA ký tự đặc biệt: 【】《》? , . - _ ( ) [ ] { } ...
    - Giữ nguyên dấu tiếng Việt (ă, â, ê, ơ, ...)
    - Giữ nguyên tiếng Trung (汉字)
    - Không dịch, không thay đổi từ
    """
    name = Path(filename).stem
    
    # XÓA KÝ TỰ ĐẶC BIỆT: 【】《》? , . - _ ( ) [ ] { } ...
    name = re.sub(r'[【】《》?.,!@#$%^&*+=~`|/\\<>"\'\-_]', ' ', name)
    name = re.sub(r'[\(\)\[\]\{\}]', ' ', name)
    
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
    
    # Xóa các từ khóa không cần thiết
    remove_words = ['audio', 'video', 'subtitle', 'track', 'clip', 'full', 
                    'official', '128k', '320k', 'podcast']
    for word in remove_words:
        name = re.sub(r'\b' + word + r'\b', ' ', name, flags=re.IGNORECASE)
    
    # Xóa khoảng trắng thừa
    name = re.sub(r'\s+', ' ', name).strip()
    
    # Giới hạn độ dài (tối đa 100 ký tự)
    if len(name) > 100:
        name = name[:100]
    
    # Nếu tên rỗng, dùng video_id làm fallback
    if not name:
        return None
    
    return name


# ===== TÌM VIDEO ID TỪ TÊN FILE =====
def search_video_id_from_filename(filename):
    """
    Tìm video ID bằng yt-dlp search
    """
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
            '--retries', '5'
        ]
        
        print(f"⏳ Đang tìm kiếm với yt-dlp...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        
        if result.returncode != 0 or not result.stdout:
            print(f"❌ Không tìm thấy video nào")
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
                    video_id = video_id.strip()
                    if not re.match(r'^[a-zA-Z0-9_-]{11}$', video_id):
                        continue
                    
                    score = similarity_score(search_query, title)
                    print(f"  📊 Độ khớp: {score:.2f} | {title[:50]}...")
                    
                    if score > best_score:
                        best_score = score
                        best_match = {'title': title, 'id': video_id}
        
        # Ngưỡng khớp 0.4
        if best_match and best_score > 0.4:
            print(f"\n🏆 CHỌN: {best_match['title']}")
            print(f"🔗 https://youtube.com/watch?v={best_match['id']}")
            print(f"📊 Độ khớp: {best_score:.2f}")
            return best_match['id']
        else:
            print(f"❌ Không có video nào khớp (độ khớp cao nhất: {best_score:.2f})")
            return None
            
    except subprocess.TimeoutExpired:
        print("❌ Tìm kiếm quá thời gian")
        return None
    except Exception as e:
        print(f"❌ Lỗi tìm kiếm: {e}")
        return None


def clean_search_query(filename):
    """
    Làm sạch tên file để tìm kiếm YouTube
    - XÓA TẤT CẢ KÝ TỰ ĐẶC BIỆT
    - Giữ nguyên chữ cái, số, dấu tiếng Việt, tiếng Trung
    """
    name = Path(filename).stem
    
    # XÓA TẤT CẢ KÝ TỰ ĐẶC BIỆT
    name = re.sub(r'[\[\](){}.,;:!?@#$%^&*+=~`|/\\<>"\'\-_]', ' ', name)
    
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
    
    # Xóa các từ khóa không cần thiết
    remove_words = ['audio', 'video', 'subtitle', 'track', 'clip', 'full', 
                    'official', '128k', '320k', 'podcast']
    for word in remove_words:
        name = re.sub(r'\b' + word + r'\b', ' ', name, flags=re.IGNORECASE)
    
    # Xóa khoảng trắng thừa
    name = re.sub(r'\s+', ' ', name).strip()
    
    return name


def similarity_score(query, title):
    """
    Tính độ tương đồng - ƯU TIÊN CHUỖI LIỀN KỀ
    """
    # Xóa ký tự đặc biệt (bao gồm cả dấu gạch ngang)
    q = re.sub(r'[^a-zA-Z0-9\u00C0-\u024F\u4E00-\u9FFF\s]', ' ', query.lower()).strip()
    t = re.sub(r'[^a-zA-Z0-9\u00C0-\u024F\u4E00-\u9FFF\s]', ' ', title.lower()).strip()
    
    # Tách từ
    q_words = q.split()
    t_words = t.split()
    
    if not q_words or not t_words:
        return 0.0
    
    # Tìm chuỗi con chung dài nhất (theo thứ tự)
    def longest_common_subsequence(a, b):
        m, n = len(a), len(b)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if a[i-1] == b[j-1]:
                    dp[i][j] = dp[i-1][j-1] + 1
                else:
                    dp[i][j] = max(dp[i-1][j], dp[i][j-1])
        return dp[m][n]
    
    # Tìm chuỗi con liền kề dài nhất
    def longest_common_substring(a, b):
        m, n = len(a), len(b)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        max_len = 0
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if a[i-1] == b[j-1]:
                    dp[i][j] = dp[i-1][j-1] + 1
                    if dp[i][j] > max_len:
                        max_len = dp[i][j]
        return max_len
    
    # Tính điểm
    lcs_len = longest_common_subsequence(q_words, t_words)
    lcs_score = lcs_len / max(len(q_words), len(t_words)) if max(len(q_words), len(t_words)) > 0 else 0
    
    substr_len = longest_common_substring(q_words, t_words)
    substr_score = substr_len / len(q_words) if len(q_words) > 0 else 0
    
    common_words = set(q_words) & set(t_words)
    word_ratio = len(common_words) / len(q_words) if len(q_words) > 0 else 0
    
    # Trọng số: ưu tiên chuỗi liền kề
    total_score = (substr_score * 0.5) + (lcs_score * 0.3) + (word_ratio * 0.2)
    
    return min(total_score, 1.0)


def extract_video_id_from_filename(filename, video_id_override=None):
    """
    Tự động tìm video ID từ tên file
    ƯU TIÊN: video_id_override (từ payload) > file .txt > tìm kiếm YouTube
    """
    name = Path(filename).stem
    folder = Path(filename).parent
    
    # CÁCH 1: ƯU TIÊN VIDEO_ID TỪ PAYLOAD (NHẬP LINK)
    if video_id_override:
        if re.match(r'^[a-zA-Z0-9_-]{11}$', video_id_override):
            print(f"✅ Sử dụng Video ID từ payload: {video_id_override}")
            return video_id_override
        else:
            print(f"⚠️ Video ID từ payload không hợp lệ: {video_id_override}")
    
    # CÁCH 2: ĐỌC TỪ FILE .TXT CÙNG TÊN
    txt_file = folder / f"{name}.txt"
    if txt_file.exists():
        try:
            with open(txt_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            match = re.search(r'(?:v=|\/)([a-zA-Z0-9_-]{11})', content)
            if match:
                video_id = match.group(1)
                print(f"📄 Đọc video ID từ file .txt: {video_id}")
                return video_id
            
            match = re.search(r'https?://(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})', content)
            if match:
                video_id = match.group(1)
                print(f"📄 Đọc link YouTube từ file .txt: {video_id}")
                return video_id
        except Exception as e:
            print(f"⚠️ Lỗi đọc file .txt: {e}")
    
    # CÁCH 3: TÌM KIẾM TRÊN YOUTUBE
    print(f"🔍 Không có file .txt, tìm kiếm trên YouTube...")
    video_id = search_video_id_from_filename(filename)
    
    if video_id:
        print(f"✅ Tìm thấy video ID: {video_id}")
        return video_id
    
    print(f"❌ KHÔNG TÌM THẤY VIDEO NÀO CHO: {filename}")
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


def generate_subtitle(audio_path, output_path=None, video_id_override=None):
    audio_file = Path(audio_path)
    
    # Tìm video ID - ưu tiên từ payload
    video_id = extract_video_id_from_filename(audio_file.name, video_id_override)
    
    if not video_id:
        print(f"❌ Không tìm thấy video ID cho: {audio_file.name}")
        return None
    
    youtube_link = get_youtube_link(video_id)
    print(f"🔗 YouTube: {youtube_link}")
    
    # LÀM SẠCH TÊN (GIỮ NGUYÊN TIẾNG TRUNG, TIẾNG VIỆT)
    original_name = audio_file.stem
    clean_name = clean_filename_for_file(original_name)
    
    # Fallback: nếu tên sạch rỗng, dùng video_id
    if not clean_name:
        clean_name = video_id
        print(f"⚠️ Tên sau khi làm sạch rỗng, dùng video_id: {clean_name}")
    
    print(f"📝 Tên gốc: {original_name}")
    print(f"📝 Tên sạch: {clean_name}")
    
    if output_path is None:
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        output_file = output_dir / f"{clean_name}.vtt"
    else:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"\n{'='*50}")
    print(f"📝 Tên sạch: {clean_name}")
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
    
    # LƯU FILE VTT (FILE 1)
    print(f"\n💾 Saving VTT to: {output_file}")
    vtt_content = '\n'.join(vtt_lines)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(vtt_content)
    
    if output_file.exists():
        print(f"✅ VTT file written! Size: {output_file.stat().st_size} bytes")
    
    # ============================================================
    # FILE 2: SUMMARY (clean_name_summary.json)
    # ============================================================
    summary = {
        'video_id': video_id,
        'youtube_link': youtube_link,
        'clean_name': clean_name,
        'original_name': original_name,
        'language': detected_lang,
        'total_segments': len(segment_list),
        'success_segments': success_count,
        'duration': segment_list[-1]['end'] if segment_list else 0,
        'transcription_time': round(elapsed, 1),
        'output_file': str(output_file),
        'timestamp': datetime.now().isoformat()
    }
    
    summary_file = output_file.parent / f"{clean_name}_summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"💾 Saved summary to: {summary_file}")
    
    # ============================================================
    # FILE 3: METADATA (clean_name.metadata.json)
    # ============================================================
    metadata = {
        'video_id': video_id,
        'youtube_link': youtube_link,
        'clean_name': clean_name,
        'original_name': original_name,
        'language': detected_lang,
        'duration': segment_list[-1]['end'] if segment_list else 0,
        'segments': len(segment_list),
        'generated_at': datetime.now().isoformat()
    }
    
    metadata_file = output_file.parent / f"{clean_name}.metadata.json"
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    print(f"💾 Saved metadata to: {metadata_file}")
    
    # ============================================================
    # FILE 4: INFO (clean_name.info.txt)
    # ============================================================
    if youtube_link:
        info_file = output_file.parent / f"{clean_name}.info.txt"
        with open(info_file, 'w', encoding='utf-8') as f:
            f.write(f"Video ID: {video_id}\n")
            f.write(f"YouTube Link: {youtube_link}\n")
            f.write(f"Clean Name: {clean_name}\n")
            f.write(f"Original Name: {original_name}\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write(f"Language: {detected_lang}\n")
        print(f"💾 Saved info to: {info_file}")
    
    # ============================================================
    # XUẤT ENV AN TOÀN (CÓ DẤU NGOẶC KÉP)
    # ============================================================
    def escape_for_bash(value):
        if not value:
            return ''
        value = value.replace('\\', '\\\\')
        value = value.replace('"', '\\"')
        value = value.replace('$', '\\$')
        value = value.replace('`', '\\`')
        value = value.replace('\n', ' ')
        return value
    
    with open('video_id.env', 'w', encoding='utf-8') as f:
        f.write(f'VIDEO_ID="{video_id}"\n')
        f.write(f'YOUTUBE_LINK="{youtube_link}"\n')
        f.write(f'CLEAN_NAME="{clean_name}"\n')
        f.write(f'ORIGINAL_FILENAME="{escape_for_bash(original_name)}"\n')
    print(f"💾 Saved env to: video_id.env")
    
    print(f"\n{'='*50}")
    print(f"✅ COMPLETE!")
    print(f"{'='*50}")
    print(f"📁 Output folder: {output_file.parent}")
    print(f"📄 1. VTT: {output_file.name}")
    print(f"📄 2. INFO: {info_file.name if youtube_link else 'N/A'}")
    print(f"📄 3. METADATA: {metadata_file.name}")
    print(f"📄 4. SUMMARY: {summary_file.name}")
    print(f"📊 Success: {success_count}/{len(segment_list)}")
    print(f"🌐 Language: {detected_lang}")
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
    parser.add_argument('--video-id', help='Video ID from payload (ưu tiên)')
    
    args = parser.parse_args()
    
    if args.audio:
        audio_path = args.audio
        if not os.path.exists(audio_path):
            print(f"❌ Audio file not found: {audio_path}")
            return
        
        result = generate_subtitle(audio_path, args.output, args.video_id)
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
        video_id_override = os.environ.get('VIDEO_ID_OVERRIDE')
        result = generate_subtitle(latest_audio, video_id_override=video_id_override)
        if result:
            print(f"\n✅ Done: {result}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
