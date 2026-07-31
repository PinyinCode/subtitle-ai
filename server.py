# -*- coding: utf-8 -*-
import os
import re
import sys
import threading
import json
import urllib.request
import urllib.error
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
from pypinyin import pinyin, Style
import yt_dlp
from deep_translator import GoogleTranslator
import whisper

# ===== CẤU HÌNH =====
COOKIE_FILE = "cookies.txt"

def get_ffmpeg_path():
    """Tự động tìm đường dẫn thư mục bin của FFmpeg"""
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
        bundled_ffmpeg = os.path.join(base_path, 'ffmpeg', 'bin')
        if os.path.exists(bundled_ffmpeg):
            return bundled_ffmpeg
    default_path = r'C:\ffmpeg\bin'
    return default_path

def extract_video_id(url):
    """Trích xuất Video ID từ đường dẫn YouTube"""
    match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', url)
    return match.group(1) if match else "unknown_video"

class SubtitleApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Phần Mềm Tạo Phụ Đề AI - iOS Style")
        self.root.geometry("620x820")
        self.root.minsize(560, 750)
        
        self.config_file = 'config.json'

        # --- CẤU HÌNH STYLE: IOS DARK MODE ---
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        BG_COLOR = "#000000"
        CARD_BG = "#121214"
        CARD_ELEMENT = "#1C1C1E"
        TEXT_PRIMARY = "#FFFFFF"
        TEXT_SECONDARY = "#8E8E93"
        
        self.root.configure(bg=BG_COLOR)
        
        # Style cơ bản
        self.style.configure('TFrame', background=BG_COLOR)
        self.style.configure('Card.TFrame', background=CARD_BG, relief='flat', borderwidth=0)
        self.style.configure('TLabel', background=BG_COLOR, foreground=TEXT_PRIMARY, font=('Segoe UI', 9))
        self.style.configure('Card.TLabel', background=CARD_BG, foreground=TEXT_PRIMARY, font=('Segoe UI', 9))
        self.style.configure('Title.TLabel', background=BG_COLOR, font=('Segoe UI', 16, 'bold'), foreground=TEXT_PRIMARY, anchor='center')
        self.style.configure('SectionTitle.TLabel', background=CARD_BG, font=('Segoe UI', 9, 'bold'), foreground=TEXT_SECONDARY)
        self.style.configure('Status.TLabel', background=CARD_BG, font=('Segoe UI', 9), foreground=TEXT_SECONDARY)
        self.style.configure('TCheckbutton', background=CARD_BG, foreground=TEXT_PRIMARY, font=('Segoe UI', 9))
        self.style.map('TCheckbutton', background=[('active', CARD_BG)], indicatorcolor=[('selected', '#0A84FF')])
        
        self.style.configure('TButton', font=('Segoe UI', 9, 'bold'), borderwidth=0, relief='flat')
        self.style.configure('Primary.TButton', background='#FFFFFF', foreground='#000000', padding=(12, 6))
        self.style.map('Primary.TButton',
            background=[('active', '#D1D1D6'), ('disabled', '#2C2C2E')],
            foreground=[('active', '#000000'), ('disabled', TEXT_SECONDARY)]
        )
        
        self.style.configure('Danger.TButton', background='#2C2C2E', foreground='#FF453A', padding=(12, 6))
        self.style.map('Danger.TButton',
            background=[('active', '#48484A'), ('disabled', '#1C1C1E')],
            foreground=[('active', '#FF6961'), ('disabled', TEXT_SECONDARY)]
        )
        
        self.style.configure('Square.TButton', background='#2C2C2E', foreground='#FFFFFF', padding=(8, 4))
        self.style.map('Square.TButton',
            background=[('active', '#3A3A3C'), ('disabled', '#1C1C1E')],
            foreground=[('active', '#FFFFFF'), ('disabled', TEXT_SECONDARY)]
        )
        
        self.style.configure('TEntry', fieldbackground=CARD_ELEMENT, foreground=TEXT_PRIMARY, insertcolor=TEXT_PRIMARY, borderwidth=0, relief='flat')
        self.style.configure('TProgressbar', background='#0A84FF', troughcolor=CARD_ELEMENT, borderwidth=0, thickness=6)

        self.cancel_event = threading.Event()
        self.current_output_file = None
        self.is_processing = False

        # --- FOOTER ---
        footer_frame = tk.Frame(root, bg=BG_COLOR, height=32)
        footer_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=24, pady=(0, 10))
        dev_label = tk.Label(footer_frame, text="Nhà phát triển: +84528484668  |  hoanginvest199@gmail.com", 
                            font=("Segoe UI", 8, "bold"), fg=TEXT_SECONDARY, bg=BG_COLOR)
        dev_label.pack(expand=True)

        # --- MAIN CONTAINER ---
        main_container = ttk.Frame(root, style='TFrame')
        main_container.pack(fill=tk.BOTH, expand=True, padx=24, pady=(20, 5))

        title_label = ttk.Label(main_container, text="AI Pinyin Subtitle", style='Title.TLabel', anchor='center')
        title_label.pack(fill=tk.X, pady=(0, 16))

        # ===== CARD 1: CẤU HÌNH TOKEN =====
        config_card = ttk.Frame(main_container, style='Card.TFrame', padding=16)
        config_card.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(config_card, text="⚙️ CẤU HÌNH GITHUB", style='SectionTitle.TLabel').pack(anchor=tk.W, pady=(0, 4))
        
        token_row = ttk.Frame(config_card, style='Card.TFrame')
        token_row.pack(fill=tk.X, pady=(4, 0))
        
        ttk.Label(token_row, text="Token:", style='Card.TLabel').pack(side=tk.LEFT, padx=(0, 8))
        
        self.token_var = tk.StringVar()
        self.token_entry = ttk.Entry(token_row, textvariable=self.token_var, font=('Segoe UI', 9), show='*')
        self.token_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4)
        
        self.btn_reset_token = ttk.Button(token_row, text="🔄 Reset", style='Square.TButton', command=self.reset_token)
        self.btn_reset_token.pack(side=tk.RIGHT, padx=(6, 0))
        
        self.btn_save_token = ttk.Button(token_row, text="💾 Lưu", style='Square.TButton', command=self.save_token)
        self.btn_save_token.pack(side=tk.RIGHT)
        
        self.token_status = ttk.Label(config_card, text="🔴 Token: Chưa có", style='Status.TLabel')
        self.token_status.pack(anchor=tk.W, pady=(6, 0))
        
        self.load_token_from_config()

        # ===== CARD 2: NHẬP LINK =====
        link_card = ttk.Frame(main_container, style='Card.TFrame', padding=16)
        link_card.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(link_card, text="🔗 ĐƯỜNG DẪN YOUTUBE", style='SectionTitle.TLabel').pack(anchor=tk.W, pady=(0, 4))
        ttk.Label(link_card, text="Tự động nhận diện và dịch sang Trung - Pinyin - Việt", style='Status.TLabel').pack(anchor=tk.W, pady=(0, 8))
        
        url_row = ttk.Frame(link_card, style='Card.TFrame')
        url_row.pack(fill=tk.X, pady=(0, 10))

        self.url_entry = ttk.Entry(url_row, font=('Segoe UI', 10))
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6, ipadx=6)

        self.btn_clear_url = ttk.Button(url_row, text="✕", style='Square.TButton', command=self.clear_url_entry)
        self.btn_clear_url.pack(side=tk.RIGHT, padx=(6, 0))

        # ===== CARD 3: THƯ MỤC LƯU =====
        save_card = ttk.Frame(main_container, style='Card.TFrame', padding=16)
        save_card.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(save_card, text="💾 THƯ MỤC LƯU FILE", style='SectionTitle.TLabel').pack(anchor=tk.W, pady=(0, 8))
        
        self.save_dir_var = tk.StringVar(value=os.getcwd())
        
        save_row = ttk.Frame(save_card, style='Card.TFrame')
        save_row.pack(fill=tk.X)
        
        self.save_entry = ttk.Entry(save_row, textvariable=self.save_dir_var, font=('Segoe UI', 9), state="readonly")
        self.save_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6, ipadx=6)
        
        self.btn_browse = ttk.Button(save_row, text="Duyệt...", style='Square.TButton', command=self.browse_save_dir)
        self.btn_browse.pack(side=tk.RIGHT, padx=(6, 0))

        # Checkbox GitHub
        self.upload_gh_var = tk.BooleanVar(value=False)
        self.chk_github = ttk.Checkbutton(save_card, text="☁️ Đồng bộ lên GitHub Gist", variable=self.upload_gh_var, style='TCheckbutton')
        self.chk_github.pack(anchor=tk.W, pady=(12, 0))

        # ===== CARD 4: NÚT TẠO PHỤ ĐỀ =====
        action_card = ttk.Frame(main_container, style='Card.TFrame', padding=16)
        action_card.pack(fill=tk.X, pady=(0, 10))
        
        self.btn_action = ttk.Button(action_card, text="🎬 TẠO PHỤ ĐỀ AI", style='Primary.TButton', command=self.handle_action_button)
        self.btn_action.pack(fill=tk.X, ipady=10)

        # ===== CARD 5: TIẾN TRÌNH =====
        progress_card = ttk.Frame(main_container, style='Card.TFrame', padding=16)
        progress_card.pack(fill=tk.X, pady=(0, 10))

        self.progress_label = ttk.Label(progress_card, text="📊 Trạng thái: Sẵn sàng", style='Status.TLabel')
        self.progress_label.pack(anchor=tk.W, pady=(0, 8))

        self.progress_bar = ttk.Progressbar(progress_card, orient="horizontal", mode="determinate")
        self.progress_bar.pack(fill=tk.X)

        # ===== CARD 6: NHẬT KÝ =====
        log_card = ttk.Frame(main_container, style='Card.TFrame', padding=16)
        log_card.pack(fill=tk.BOTH, expand=True, pady=(0, 4))
        
        ttk.Label(log_card, text="📋 NHẬT KÝ", style='SectionTitle.TLabel').pack(anchor=tk.W, pady=(0, 8))
        
        log_inner = tk.Frame(log_card, bg=CARD_ELEMENT, bd=0)
        log_inner.pack(fill=tk.BOTH, expand=True)
        
        self.log_area = scrolledtext.ScrolledText(
            log_inner, font=("Consolas", 8), bg=CARD_ELEMENT, fg=TEXT_PRIMARY, insertbackground=TEXT_PRIMARY,
            relief='flat', borderwidth=8, highlightthickness=0, wrap=tk.WORD
        )
        self.log_area.pack(fill=tk.BOTH, expand=True)

        # Hướng dẫn cookie
        self.log("="*50)
        self.log("🔑 HƯỚNG DẪN LẤY COOKIE YOUTUBE:")
        self.log("1. Cài extension 'Get cookies.txt LOCALLY' trên Chrome")
        self.log("2. Đăng nhập YouTube, export cookies.txt")
        self.log("3. Đặt file cookies.txt cùng thư mục với phần mềm")
        self.log("="*50)

    # ===== QUẢN LÝ TOKEN =====
    def load_token_from_config(self):
        config = self.load_config()
        token = config.get('gh_pat_token', '')
        if token:
            self.token_var.set(token)
            self.token_status.config(text="🟢 Token: Đã cấu hình", foreground="#30D158")
        else:
            self.token_status.config(text="🔴 Token: Chưa có", foreground="#FF453A")

    def save_token(self):
        token = self.token_var.get().strip()
        if not token:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập Token GitHub!")
            return
        
        config = self.load_config()
        config['gh_pat_token'] = token
        self.save_config(config)
        self.token_status.config(text="🟢 Token: Đã lưu", foreground="#30D158")
        self.log("✅ Đã lưu Token GitHub!")

    def reset_token(self):
        if messagebox.askyesno("Xác nhận", "Xóa token hiện tại?"):
            config = self.load_config()
            if 'gh_pat_token' in config:
                del config['gh_pat_token']
                self.save_config(config)
            self.token_var.set("")
            self.token_status.config(text="🔴 Token: Đã xóa", foreground="#FF453A")
            self.log("🔄 Đã reset Token!")

    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}

    def save_config(self, data):
        try:
            with open(self.config_file, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            self.log(f"Không thể lưu cấu hình: {e}")

    # ===== CÁC HÀM UI =====
    def clear_url_entry(self):
        self.url_entry.delete(0, tk.END)

    def browse_save_dir(self):
        dir_path = filedialog.askdirectory(title="Chọn thư mục lưu", initialdir=self.save_dir_var.get())
        if dir_path:
            self.save_dir_var.set(dir_path)

    def log(self, message):
        def _append():
            self.log_area.insert(tk.END, message + "\n")
            self.log_area.see(tk.END)
        self.root.after(0, _append)

    def set_progress(self, val, text=""):
        def _update():
            self.progress_bar['value'] = val
            if text:
                self.progress_label.config(text=text)
        self.root.after(0, _update)

    def check_cancel(self):
        if self.cancel_event.is_set():
            raise Exception("ĐÃ HỦY BỞI NGƯỜI DÙNG!")

    def ytdl_progress_hook(self, d):
        if self.cancel_event.is_set():
            raise yt_dlp.utils.DownloadError("Đã hủy")
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            downloaded = d.get('downloaded_bytes', 0)
            if total > 0:
                percent = (downloaded / total) * 100
                speed = d.get('_speed_str', '').strip()
                self.set_progress(percent, f"Đang tải: {percent:.1f}% ({speed})")

    def handle_action_button(self):
        if not self.is_processing:
            url = self.url_entry.get().strip()
            if not url:
                messagebox.showwarning("Cảnh báo", "Vui lòng dán link YouTube!")
                return
            
            if self.upload_gh_var.get():
                config = self.load_config()
                token = config.get('gh_pat_token', '')
                if not token:
                    token = self.token_var.get().strip()
                    if not token:
                        messagebox.showwarning("Cảnh báo", "Vui lòng nhập GitHub Token!")
                        return
                    config['gh_pat_token'] = token
                    self.save_config(config)
            
            self.cancel_event.clear()
            self.current_output_file = None
            self.is_processing = True
            
            self.btn_action.config(text="⏹ HỦY BỎ", style='Danger.TButton')
            self.log_area.delete(1.0, tk.END)
            self.set_progress(0, "Đang khởi tạo...")
            
            threading.Thread(target=self.process_video, args=(url,), daemon=True).start()
        else:
            if not self.cancel_event.is_set():
                self.cancel_event.set()
                self.log("⏹ Đang hủy tác vụ...")
                self.set_progress(0, "Đang dừng...")
                self.btn_action.config(state=tk.DISABLED)

    def cleanup_files(self):
        for f in os.listdir('.'):
            if f.startswith('temp_audio') or f.startswith('temp_sub'):
                try:
                    os.remove(f)
                except:
                    pass

    def upload_to_github_gist(self, file_path, video_id):
        self.log("📤 Đang đồng bộ lên GitHub Gist...")
        self.set_progress(95, "Đang đồng bộ GitHub...")
        config = self.load_config()
        token = config.get('gh_pat_token')
        
        if not token:
            self.log("❌ Không tìm thấy Token!")
            return

        target_filename = f"{video_id}.vtt"
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Tìm Gist cũ
            existing_gist_id = None
            page = 1
            while True:
                req = urllib.request.Request(f"https://api.github.com/gists?page={page}&per_page=100")
                req.add_header("Authorization", f"token {token}")
                try:
                    with urllib.request.urlopen(req) as resp:
                        gists = json.loads(resp.read().decode('utf-8'))
                        if not gists:
                            break
                        for g in gists:
                            if target_filename in g.get('files', {}):
                                existing_gist_id = g['id']
                                break
                        if existing_gist_id:
                            break
                        page += 1
                except:
                    break

            if existing_gist_id:
                self.log(f"📝 Cập nhật Gist cũ...")
                payload = {"description": f"Pinyin AI - {video_id}", "files": {target_filename: {"content": content}}}
                req = urllib.request.Request(f"https://api.github.com/gists/{existing_gist_id}", method="PATCH")
            else:
                self.log(f"📝 Tạo Gist mới...")
                payload = {"description": f"Pinyin AI - {video_id}", "public": True, "files": {target_filename: {"content": content}}}
                req = urllib.request.Request("https://api.github.com/gists", method="POST")

            req.add_header("Authorization", f"token {token}")
            req.add_header("Content-Type", "application/json")
            
            data = json.dumps(payload).encode('utf-8')
            response = urllib.request.urlopen(req, data=data)
            res_data = json.loads(response.read().decode('utf-8'))
            
            raw_url = res_data['files'][target_filename]['raw_url']
            self.log(f"✅ Đã đồng bộ!\n🔗 {raw_url}")
            
        except urllib.error.HTTPError as e:
            if e.code == 401:
                self.log("❌ Token không hợp lệ!")
                config.pop('gh_pat_token', None)
                self.save_config(config)
                self.load_token_from_config()
            else:
                self.log(f"❌ Lỗi HTTP: {e.code}")
        except Exception as e:
            self.log(f"❌ Lỗi: {str(e)}")

    def format_time(self, seconds):
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds - int(seconds)) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"

    def clean_filename(self, name):
        return re.sub(r'[\\/*?:"<>|]', "", name).strip()

    def align_texts(self, zh_text, translator):
        if not zh_text.strip():
            return "", ""
        p_list = pinyin(zh_text, style=Style.TONE, heteronym=False)
        pinyin_text = " ".join([item[0] for item in p_list])
        try:
            vi_text = translator.translate(zh_text)
            return pinyin_text, vi_text if vi_text else ""
        except:
            return pinyin_text, ""

    def is_valid_vtt(self, sub_file):
        try:
            with open(sub_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            if not content.startswith("WEBVTT"):
                return False
            blocks = re.split(r'\n\s*\n', content)
            for block in blocks:
                block = block.strip()
                if not block or 'WEBVTT' in block or 'Kind:' in block:
                    continue
                lines = block.split('\n')
                if not any('-->' in line for line in lines):
                    return False
                text_lines = [l for l in lines if '-->' not in l and not l.isdigit()]
                if len(text_lines) != 3:
                    return False
            return True
        except:
            return False

    # ===== XỬ LÝ CHÍNH =====
    def process_video(self, url):
        ffmpeg_path = get_ffmpeg_path()
        save_dir = self.save_dir_var.get()
        video_id = extract_video_id(url)
        
        # Cấu hình chung cho yt-dlp
        ydl_opts_base = {
            'ffmpeg_location': ffmpeg_path,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'ios'],  # Giả client mobile, tránh n challenge
                }
            }
        }
        
        if os.path.exists(COOKIE_FILE):
            ydl_opts_base['cookiefile'] = COOKIE_FILE
            self.log("✅ Đã tìm thấy cookies.txt")
        else:
            self.log("⚠️ Không có cookies.txt, có thể lỗi với video bị hạn chế")
        
        try:
            self.check_cancel()
            self.log("🔍 Lấy thông tin video...")
            self.set_progress(5, "Đang lấy thông tin...")
            
            with yt_dlp.YoutubeDL(ydl_opts_base) as ydl:
                info = ydl.extract_info(url, download=False)
                title = self.clean_filename(info.get('title', 'video'))
                self.current_output_file = os.path.join(save_dir, f"{title}.vtt")

            # Kiểm tra phụ đề có sẵn
            self.check_cancel()
            self.log("🔍 Kiểm tra phụ đề YouTube...")
            self.set_progress(10, "Đang kiểm tra phụ đề...")
            
            sub_file = None
            sub_lang = "zh"
            try:
                ydl_opts_sub = {
                    **ydl_opts_base,
                    'skip_download': True,
                    'writesubtitles': True,
                    'writeautomaticsub': True,
                    'subtitleslangs': ['zh', 'zh-Hans', 'zh-Hant', 'zh-CN', 'zh-TW', 'en'],
                    'outtmpl': 'temp_sub',
                }
                with yt_dlp.YoutubeDL(ydl_opts_sub) as ydl:
                    info_sub = ydl.extract_info(url, download=True)
                    sub_lang = list(info_sub.get('requested_subtitles', {}).keys())[0] if info_sub.get('requested_subtitles') else "zh"
                    
                for f in os.listdir('.'):
                    if f.startswith('temp_sub') and (f.endswith('.vtt') or f.endswith('.srt')):
                        sub_file = f
                        break
            except Exception as e:
                self.log(f"Không lấy được phụ đề: {str(e)[:80]}")

            if sub_file and self.is_valid_vtt(sub_file):
                self.check_cancel()
                self.log(f"✅ Phụ đề [{sub_lang.upper()}] hợp lệ, đang xử lý...")
                self.convert_subtitle(sub_file, self.current_output_file, sub_lang, video_id)
                self.cleanup_files()
                return
            
            if sub_file:
                self.log("Phụ đề không đạt chuẩn 3 dòng, dùng Whisper.")
                self.cleanup_files()

            # Tải audio chất lượng thấp nhất
            self.check_cancel()
            self.log("🎵 Tải audio chất lượng thấp...")
            self.set_progress(15, "Đang tải audio...")
            
            ydl_opts_audio = {
                **ydl_opts_base,
                'format': 'worstaudio/worst',  # ✅ CHẤT LƯỢNG THẤP NHẤT
                'outtmpl': 'temp_audio',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '32',  # 32kbps, đủ cho Whisper
                }],
                'progress_hooks': [self.ytdl_progress_hook],
            }
            
            with yt_dlp.YoutubeDL(ydl_opts_audio) as ydl:
                ydl.download([url])

            audio_file = None
            for f in os.listdir('.'):
                if f.startswith('temp_audio') and f.endswith('.mp3'):
                    audio_file = f
                    break

            self.check_cancel()
            self.log("🧠 Whisper đang nhận diện giọng nói...")
            self.set_progress(40, "AI đang xử lý...")
            
            model = whisper.load_model("base")
            result = model.transcribe(audio_file, language="zh")
            detected_lang = result.get("language", "zh")
            self.log(f"🌐 Ngôn ngữ: {detected_lang.upper()}")

            self.check_cancel()
            self.log("🔄 Đang dịch và tạo Pinyin...")
            
            to_zh = GoogleTranslator(source=detected_lang, target='zh-CN') if not detected_lang.startswith('zh') else None
            to_vi = GoogleTranslator(source='zh-CN', target='vi')
            
            segments = result.get("segments", [])
            total = len(segments)
            lines = ["WEBVTT\nKind: captions\nLanguage: zh-TW\n\n"]

            for i, seg in enumerate(segments, 1):
                self.check_cancel()
                start = self.format_time(seg["start"])
                end = self.format_time(seg["end"])
                raw = seg["text"].strip()
                if not raw:
                    continue

                zh_text = raw if detected_lang.startswith('zh') else (to_zh.translate(raw) or raw)
                pinyin_text, vi_text = self.align_texts(zh_text, to_vi)
                
                lines.append(f"{start} --> {end}\n{zh_text}\n{pinyin_text}\n{vi_text}\n\n")
                pct = 40 + (i / total) * 55
                self.set_progress(pct, f"Đang dịch: {i}/{total}")

            self.check_cancel()
            with open(self.current_output_file, 'w', encoding='utf-8') as f:
                f.writelines(lines)

            if self.upload_gh_var.get():
                self.upload_to_github_gist(self.current_output_file, video_id)

            self.cleanup_files()
            self.set_progress(100, "✅ Hoàn thành!")
            self.log(f"\n🎉 Thành công!\n📁 {self.current_output_file}")
            messagebox.showinfo("Thành công", f"Đã tạo phụ đề:\n{self.current_output_file}")

        except Exception as e:
            self.cleanup_files()
            if self.cancel_event.is_set():
                self.log("\n⏹ Đã hủy tác vụ.")
                self.set_progress(0, "Đã hủy.")
            else:
                self.log(f"❌ Lỗi: {str(e)}")
                self.set_progress(0, "Lỗi!")
                messagebox.showerror("Lỗi", str(e))
        finally:
            self.root.after(0, self.reset_ui)

    def convert_subtitle(self, sub_file, output_file, source_lang, video_id):
        with open(sub_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        blocks = re.split(r'\n\s*\n', content)
        lines = ["WEBVTT\nKind: captions\nLanguage: zh-TW\n\n"]
        
        is_zh = source_lang.startswith('zh')
        to_zh = GoogleTranslator(source=source_lang, target='zh-CN') if not is_zh else None
        to_vi = GoogleTranslator(source='zh-CN', target='vi')
        
        total = len(blocks)
        for i, block in enumerate(blocks, 1):
            self.check_cancel()
            if not block.strip() or 'WEBVTT' in block or 'Kind:' in block:
                continue
                
            block_lines = block.strip().split('\n')
            time_line = ""
            text_lines = []
            
            for line in block_lines:
                if '-->' in line:
                    time_line = line.replace(',', '.')
                elif not line.isdigit() and line.strip():
                    text_lines.append(line.strip())
            
            if time_line and text_lines:
                clean_text = re.sub(r'<[^>]+>', '', " ".join(text_lines))
                if clean_text:
                    zh_text = clean_text if is_zh else (to_zh.translate(clean_text) or clean_text)
                    pinyin_text, vi_text = self.align_texts(zh_text, to_vi)
                    lines.append(f"{time_line}\n{zh_text}\n{pinyin_text}\n{vi_text}\n\n")
            
            pct = (i / total) * 100
            self.set_progress(pct, f"Đang xử lý: {i}/{total}")

        with open(output_file, 'w', encoding='utf-8') as f:
            f.writelines(lines)

        if self.upload_gh_var.get():
            self.upload_to_github_gist(output_file, video_id)

        self.set_progress(100, "✅ Hoàn thành!")
        self.log(f"\n🎉 Thành công!\n📁 {output_file}")
        messagebox.showinfo("Thành công", f"Đã tạo phụ đề:\n{output_file}")

    def reset_ui(self):
        self.is_processing = False
        self.btn_action.config(text="🎬 TẠO PHỤ ĐỀ AI", style='Primary.TButton', state=tk.NORMAL)

if __name__ == "__main__":
    root = tk.Tk()
    app = SubtitleApp(root)
    root.mainloop()