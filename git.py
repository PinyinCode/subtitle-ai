#!/usr/bin/env python3
"""Server tải audio + Upload bằng Git (không timeout) + Cloudflare Tunnel
MOBILE CHỈ KÍCH HOẠT - SERVER TỰ LÀM TẤT CẢ
ĐÃ SỬA: Force add file .m4a, log chi tiết để debug
"""

import os, sys, tempfile, time, subprocess, json, base64, threading, re, shutil
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import tkinter as tk
from tkinter import ttk, messagebox

# ===== TỰ ĐỘNG CÀI PSUTIL =====
try:
    import psutil
except ImportError:
    print("⚠️ psutil not found, installing...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "psutil"])
    import psutil

PORT = 8888
CONFIG_FILE = "server_config.json"

download_progress = {}
active_downloads = {}
active_processes = {}
download_history = []
server_config = {'token': ''}
gui_ref = None

def load_server_config():
    global server_config
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                server_config.update(json.load(f))
        except:
            pass

def kill_process_by_video_id(video_id):
    """Kill tất cả process liên quan đến video_id"""
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if video_id in cmdline or 'yt-dlp' in cmdline:
                    proc.kill()
                    print(f"[KILL] Killed process {proc.pid} for {video_id}")
            except:
                pass
    except Exception as e:
        print(f"[KILL] Error: {e}")
    
    if video_id in active_processes:
        try:
            if active_processes[video_id].poll() is None:
                active_processes[video_id].kill()
            del active_processes[video_id]
        except:
            pass
    
    for ext in ['m4a', 'webm', 'mp3']:
        tmp_file = os.path.join(tempfile.gettempdir(), f'audio_{video_id}.{ext}')
        if os.path.exists(tmp_file):
            try:
                os.remove(tmp_file)
                print(f"[CLEAN] Removed {tmp_file}")
            except:
                pass
        
        filepath = os.path.join('downloads', f"{video_id}.{ext}")
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
                print(f"[CLEAN] Removed {filepath}")
            except:
                pass

# ===== UPLOAD BẰNG GIT (FORCE ADD + PULL TRƯỚC + LOG CHI TIẾT) =====
def upload_to_github(file_path, video_id):
    """Upload file lên GitHub bằng Git - Force add, pull trước push, log chi tiết"""
    try:
        import subprocess
        import shutil
        
        print(f"\n{'='*50}")
        print(f"[UPLOAD-GIT] === BẮT ĐẦU UPLOAD: {video_id} ===")
        print(f"[UPLOAD-GIT] Thời gian: {time.strftime('%H:%M:%S')}")
        print(f"[UPLOAD-GIT] File path: {file_path}")
        
        if not os.path.exists(file_path):
            print(f"[UPLOAD-GIT] ❌ File không tồn tại: {file_path}")
            return False
        
        file_size = os.path.getsize(file_path)
        print(f"[UPLOAD-GIT] ✅ File size: {file_size/1024:.1f}KB / {file_size/1024/1024:.2f}MB")
        
        token = server_config.get('token', '')
        if not token:
            print(f"[UPLOAD-GIT] ❌ Không có token!")
            if gui_ref:
                gui_ref.root.after(0, gui_ref.update_progress, 0, "❌ Chưa cấu hình token!")
            return False
        
        repo_path = os.path.dirname(os.path.abspath(__file__))
        audio_dir = os.path.join(repo_path, 'data', 'audio')
        os.makedirs(audio_dir, exist_ok=True)
        
        dest_file = os.path.join(audio_dir, f"{video_id}.m4a")
        shutil.copy2(file_path, dest_file)
        print(f"[UPLOAD-GIT] ✅ Copied to: {dest_file}")
        
        # ✅ KIỂM TRA FILE ĐÃ COPY THÀNH CÔNG
        if os.path.exists(dest_file):
            print(f"[UPLOAD-GIT] ✅ File tồn tại: {dest_file} ({os.path.getsize(dest_file)/1024:.1f}KB)")
        else:
            print(f"[UPLOAD-GIT] ❌ File KHÔNG tồn tại sau khi copy!")
            return False
        
        if gui_ref:
            gui_ref.root.after(0, gui_ref.update_progress, 20, "📤 Git pull...")
        
        # ✅ 1. GIT PULL TRƯỚC
        print(f"[UPLOAD-GIT] 📤 Git pull (đồng bộ remote)...")
        pull_result = subprocess.run(
            ['git', 'pull', '--rebase'], 
            cwd=repo_path, 
            capture_output=True, 
            text=True
        )
        print(f"[UPLOAD-GIT] Git pull return code: {pull_result.returncode}")
        if pull_result.returncode != 0:
            print(f"[UPLOAD-GIT] ⚠️ Git pull warning: {pull_result.stderr[:200]}")
        
        if gui_ref:
            gui_ref.root.after(0, gui_ref.update_progress, 40, "📤 Git add -f...")
        
        # ✅ 2. GIT ADD - FORCE ADD (vượt qua .gitignore)
        print(f"[UPLOAD-GIT] 📤 Git add -f (force add)...")
        
        # Cách 1: Add file cụ thể với -f
        result = subprocess.run(
            ['git', 'add', '-f', dest_file], 
            cwd=repo_path, 
            capture_output=True, 
            text=True
        )
        print(f"[UPLOAD-GIT] Git add file return code: {result.returncode}")
        if result.returncode != 0:
            print(f"[UPLOAD-GIT] ⚠️ Git add file error: {result.stderr[:200]}")
        
        # Cách 2: Add cả thư mục với -f (để chắc chắn)
        result2 = subprocess.run(
            ['git', 'add', '-f', 'data/audio/'], 
            cwd=repo_path, 
            capture_output=True, 
            text=True
        )
        print(f"[UPLOAD-GIT] Git add folder return code: {result2.returncode}")
        if result2.returncode != 0:
            print(f"[UPLOAD-GIT] ⚠️ Git add folder error: {result2.stderr[:200]}")
        
        # ✅ KIỂM TRA STATUS SAU KHI ADD
        status_result = subprocess.run(
            ['git', 'status', '--porcelain'], 
            cwd=repo_path, 
            capture_output=True, 
            text=True
        )
        print(f"[UPLOAD-GIT] 📊 Git status sau khi add:")
        print(status_result.stdout)
        
        if gui_ref:
            gui_ref.root.after(0, gui_ref.update_progress, 60, "📤 Git commit...")
        
        # ✅ 3. GIT COMMIT
        print(f"[UPLOAD-GIT] 📤 Git commit...")
        result = subprocess.run(
            ['git', 'commit', '-m', f'Upload audio {video_id}'], 
            cwd=repo_path, 
            capture_output=True, 
            text=True
        )
        print(f"[UPLOAD-GIT] Git commit return code: {result.returncode}")
        if result.returncode != 0:
            print(f"[UPLOAD-GIT] Commit stderr: {result.stderr[:300]}")
        
        if result.returncode != 0 and 'nothing to commit' in result.stderr:
            print(f"[UPLOAD-GIT] ⚠️ Không có gì để commit (file đã tồn tại hoặc không thay đổi)")
            # Vẫn tiếp tục, có thể file đã được commit từ trước
        elif result.returncode != 0:
            print(f"[UPLOAD-GIT] ❌ Commit error: {result.stderr}")
            return False
        
        if gui_ref:
            gui_ref.root.after(0, gui_ref.update_progress, 80, "📤 Git push...")
        
        # ✅ 4. GIT PUSH
        print(f"[UPLOAD-GIT] 📤 Git push (không giới hạn thời gian)...")
        result = subprocess.run(
            ['git', 'push'], 
            cwd=repo_path, 
            capture_output=True, 
            text=True, 
            timeout=600
        )
        print(f"[UPLOAD-GIT] Git push return code: {result.returncode}")
        
        # ✅ 5. NẾU PUSH THẤT BẠI DO REJECTED, THỬ PULL + PUSH LẠI
        if result.returncode != 0 and 'rejected' in result.stderr:
            print(f"[UPLOAD-GIT] ⚠️ Push bị từ chối, thử pull và push lại...")
            
            subprocess.run(['git', 'pull', '--rebase'], cwd=repo_path, capture_output=True)
            
            result = subprocess.run(
                ['git', 'push'], 
                cwd=repo_path, 
                capture_output=True, 
                text=True, 
                timeout=600
            )
            print(f"[UPLOAD-GIT] Git push retry return code: {result.returncode}")
        
        if result.returncode != 0:
            print(f"[UPLOAD-GIT] ❌ Push error: {result.stderr[:300]}")
            return False
        
        print(f"[UPLOAD-GIT] ✅ Push thành công!")
        
        # ✅ 6. KÍCH HOẠT GITHUB ACTIONS
        try:
            import requests
            headers = {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json"
            }
            resp = requests.post(
                f"https://api.github.com/repos/PinyinCode/subtitle-ai/dispatches",
                headers=headers,
                json={"event_type": "process_audio", "client_payload": {"video_id": video_id}},
                timeout=30
            )
            if resp.status_code == 204:
                print(f"[UPLOAD-GIT] ✅ Actions triggered!")
            else:
                print(f"[UPLOAD-GIT] ⚠️ Actions trigger: {resp.status_code}")
        except Exception as e:
            print(f"[UPLOAD-GIT] ⚠️ Actions trigger error: {e}")
        
        if gui_ref:
            gui_ref.root.after(0, gui_ref.update_progress, 100, "✅ Hoàn tất! Đợi AI xử lý...")
            gui_ref.root.after(0, gui_ref.add_history, video_id, "✅ Upload thành công")
        
        print(f"[UPLOAD-GIT] === HOÀN TẤT: {video_id} ===")
        print(f"{'='*50}\n")
        return True
            
    except subprocess.TimeoutExpired:
        print(f"[UPLOAD-GIT] ❌ Push timeout (600s)!")
        return False
    except Exception as e:
        print(f"[UPLOAD-GIT] ❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()
        return False

def progress_hook_factory(video_id):
    def progress_hook(d):
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            downloaded = d.get('downloaded_bytes', 0)
            percent = round(downloaded/total*100, 1) if total > 0 else 0
            speed = d.get('_speed_str', 'N/A').strip()
            
            download_progress[video_id] = {
                'status': 'downloading',
                'downloaded': downloaded,
                'total': total,
                'speed': speed,
                'percent': percent
            }
            
            if gui_ref:
                d_mb = downloaded/1024/1024
                t_mb = total/1024/1024 if total > 0 else 0
                gui_ref.root.after(0, gui_ref.update_progress, 
                    percent, f"⬇️ Tải: {d_mb:.1f}/{t_mb:.1f}MB - {speed}")
    return progress_hook

# ===== HÀM XỬ LÝ NGẦM =====
def process_download_background(url, video_id):
    """Tải audio + Upload bằng Git (không timeout)"""
    tmp_file = None
    cancel_event = threading.Event()
    active_downloads[video_id] = cancel_event
    
    try:
        if gui_ref:
            gui_ref.root.after(0, gui_ref.update_progress, 0, f"⬇️ Đang tải: {video_id}...")
        
        tmp_file = os.path.join(tempfile.gettempdir(), f'audio_{video_id}.m4a')
        
        import yt_dlp
        
        ydl_opts = {
            'format': 'worstaudio[ext=m4a]/worstaudio',
            'outtmpl': tmp_file,
            'quiet': True,
            'no_warnings': True,
            'extractor_args': {'youtube': {'js_runtimes': ['deno']}},
            'progress_hooks': [progress_hook_factory(video_id)],
            'noplaylist': True
        }
        
        download_result = {'success': False, 'error': None}
        
        def do_download():
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                download_result['success'] = True
            except Exception as e:
                download_result['error'] = str(e)
        
        dl_thread = threading.Thread(target=do_download, daemon=True)
        dl_thread.start()
        active_processes[video_id] = dl_thread
        
        while dl_thread.is_alive():
            if cancel_event.is_set():
                kill_process_by_video_id(video_id)
                download_result['error'] = "Cancelled"
                break
            dl_thread.join(0.5)
        
        if cancel_event.is_set():
            if os.path.exists(tmp_file):
                os.remove(tmp_file)
            if gui_ref:
                gui_ref.root.after(0, gui_ref.update_progress, 0, "🚫 Đã hủy")
                gui_ref.root.after(0, gui_ref.add_history, video_id, "🚫 Đã hủy")
            return
        
        if not download_result['success']:
            raise Exception(download_result.get('error', 'Download failed'))
        
        if not os.path.exists(tmp_file) or os.path.getsize(tmp_file) == 0:
            raise Exception("File not created")
        
        print(f"Downloaded: {os.path.getsize(tmp_file)/1024:.0f}KB")
        
        # === UPLOAD BẰNG GIT ===
        upload_success = upload_to_github(tmp_file, video_id)
        
        # Dọn dẹp
        try:
            if os.path.exists(tmp_file):
                os.remove(tmp_file)
        except:
            pass
        
        if upload_success:
            download_history.append({
                'video_id': video_id,
                'status': 'success',
                'time': time.strftime('%H:%M:%S')
            })
            print(f"[COMPLETE] Success: {video_id}")
        else:
            download_history.append({
                'video_id': video_id,
                'status': 'failed',
                'time': time.strftime('%H:%M:%S')
            })
            if gui_ref:
                gui_ref.root.after(0, gui_ref.add_history, video_id, "❌ Upload thất bại")
            print(f"[COMPLETE] Failed: {video_id}")
                
    except Exception as e:
        print(f"Error: {e}")
        if gui_ref:
            gui_ref.root.after(0, gui_ref.update_progress, 0, f"❌ Lỗi: {e}")
            gui_ref.root.after(0, gui_ref.add_history, video_id, f"❌ Lỗi: {str(e)[:30]}")
    finally:
        if video_id in active_downloads:
            del active_downloads[video_id]
        if video_id in active_processes:
            del active_processes[video_id]
        if tmp_file and os.path.exists(tmp_file):
            try: os.remove(tmp_file)
            except: pass

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        p = urlparse(self.path)
        q = parse_qs(p.query)
        url = q.get('url', [None])[0]
        vid = q.get('id', [None])[0]
        
        if p.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            try:
                self.wfile.write(b'OK')
            except:
                pass
            return
        
        if p.path == '/progress':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            try:
                if vid and vid in download_progress:
                    self.wfile.write(json.dumps(download_progress[vid]).encode())
                else:
                    self.wfile.write(json.dumps({'status': 'done', 'percent': 100}).encode())
            except:
                pass
            return
        
        if p.path == '/cancel':
            if vid:
                kill_process_by_video_id(vid)
                if vid in active_downloads:
                    active_downloads[vid].set()
                    del active_downloads[vid]
                if vid in download_progress:
                    download_progress[vid] = {'status': 'cancelled'}
                if gui_ref:
                    gui_ref.root.after(0, gui_ref.update_progress, 0, "🚫 Đã hủy")
                    gui_ref.root.after(0, gui_ref.add_history, vid, "🚫 Đã hủy")
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            try:
                self.wfile.write(json.dumps({'status': 'cancelled'}).encode())
            except:
                pass
            return
        
        if p.path == '/download' and url:
            video_id = None
            try:
                match = re.search(r'(?:v=|\/)([\w-]{11})', url)
                video_id = match.group(1) if match else f"vid_{int(time.time())}"
                
                if not server_config.get('token', ''):
                    self.send_response(400)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    try:
                        self.wfile.write(json.dumps({
                            'status': 'error',
                            'message': 'Chưa cấu hình token!'
                        }).encode())
                    except:
                        pass
                    return
                
                if video_id in active_downloads or video_id in active_processes:
                    print(f"[SERVER] Video cũ đang chạy: {video_id}, hủy...")
                    kill_process_by_video_id(video_id)
                    if video_id in active_downloads:
                        active_downloads[video_id].set()
                        del active_downloads[video_id]
                    if gui_ref:
                        gui_ref.root.after(0, gui_ref.update_progress, 0, f"🔄 Đã hủy video cũ: {video_id}")
                        gui_ref.root.after(0, gui_ref.add_history, video_id, "🔄 Đã hủy (tải mới)")
                    time.sleep(0.5)
                
                self.send_response(202)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                try:
                    self.wfile.write(json.dumps({
                        'status': 'accepted',
                        'video_id': video_id,
                        'message': 'Download đã bắt đầu (upload bằng Git)'
                    }).encode())
                except:
                    pass
                
                threading.Thread(
                    target=process_download_background,
                    args=(url, video_id),
                    daemon=True
                ).start()
                
                if gui_ref:
                    gui_ref.root.after(0, gui_ref.add_history, video_id, "🔄 Đã bắt đầu")
                
            except Exception as e:
                try:
                    self.send_response(500)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps({'status': 'error', 'message': str(e)}).encode())
                except:
                    pass
            return
        
        self.send_response(404)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        try:
            self.wfile.write(b'Not Found')
        except:
            pass
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.end_headers()

class ServerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Subtitle AI Server")
        self.root.geometry("550x480")
        self.root.configure(bg='#0d1117')
        self.root.resizable(False, False)
        
        self.config = self.load_config()
        self.cloudflare_process = None
        
        self.bg = '#0d1117'
        self.card = '#161b22'
        self.text = '#c9d1d9'
        self.sub = '#8b949e'
        self.green = '#3fb950'
        self.red = '#f85149'
        self.purple = '#6e40c9'
        self.yellow = '#d2991d'
        self.blue = '#58a6ff'
        
        tk.Label(root, text="🎬 SUBTITLE AI SERVER", font=('Arial', 14, 'bold'),
                fg=self.purple, bg=self.bg).pack(pady=(15, 8))
        
        tk.Label(root, text="GitHub Token:", fg=self.sub, bg=self.bg,
                font=('Arial', 10)).pack(anchor='w', padx=30)
        
        tf = tk.Frame(root, bg=self.bg)
        tf.pack(fill='x', padx=30, pady=(5, 10))
        
        self.token_var = tk.StringVar(value=self.config.get('token', ''))
        self.token_entry = tk.Entry(tf, textvariable=self.token_var,
                                    font=('Arial', 10), show='*',
                                    bg='#0d1117', fg=self.text, relief='flat',
                                    insertbackground=self.text)
        self.token_entry.pack(side='left', fill='x', expand=True, ipady=8, ipadx=8)
        
        self.show_var = tk.BooleanVar(value=False)
        tk.Checkbutton(tf, text="👁", variable=self.show_var,
                      bg=self.bg, fg=self.sub, selectcolor=self.bg,
                      command=self.toggle_token).pack(side='right', padx=(5, 0))
        
        btn_frame = tk.Frame(root, bg=self.bg)
        btn_frame.pack(fill='x', padx=30, pady=(5, 5))
        
        tk.Button(btn_frame, text="💾 LƯU TOKEN", bg=self.green, fg='#0d1117',
                 font=('Arial', 9, 'bold'), relief='flat', pady=8,
                 command=self.save_token).pack(side='left', fill='x', expand=True, padx=(0, 5))
        
        tk.Button(btn_frame, text="🔍 TEST", bg=self.blue, fg='white',
                 font=('Arial', 9, 'bold'), relief='flat', pady=8,
                 command=self.test_connection).pack(side='left', fill='x', expand=True, padx=(5, 0))
        
        prog_frame = tk.Frame(root, bg=self.card)
        prog_frame.pack(fill='x', padx=30, pady=(10, 5))
        
        tk.Label(prog_frame, text="📊 TIẾN TRÌNH", font=('Arial', 9, 'bold'),
                fg=self.sub, bg=self.card).pack(anchor='w', padx=10, pady=(10, 5))
        
        self.progress_bar = ttk.Progressbar(prog_frame, mode='determinate')
        self.progress_bar.pack(fill='x', padx=10, pady=(0, 5))
        
        self.progress_label = tk.Label(prog_frame, text="Sẵn sàng",
                                       fg=self.sub, bg=self.card, font=('Arial', 9))
        self.progress_label.pack(anchor='w', padx=10, pady=(0, 10))
        
        history_frame = tk.Frame(root, bg=self.card)
        history_frame.pack(fill='x', padx=30, pady=(5, 5))
        
        tk.Label(history_frame, text="📜 LỊCH SỬ", font=('Arial', 9, 'bold'),
                fg=self.sub, bg=self.card).pack(anchor='w', padx=10, pady=(10, 5))
        
        self.history_label = tk.Label(history_frame, text="Chưa có hoạt động",
                                      fg=self.sub, bg=self.card, font=('Arial', 8))
        self.history_label.pack(anchor='w', padx=10, pady=(0, 10))
        
        cf_frame = tk.Frame(root, bg=self.card)
        cf_frame.pack(fill='x', padx=30, pady=(5, 5))
        
        tk.Label(cf_frame, text="🌐 CLOUDFLARE TUNNEL", font=('Arial', 10, 'bold'),
                fg=self.text, bg=self.card).pack(pady=(10, 5))
        
        url_frame = tk.Frame(cf_frame, bg=self.card)
        url_frame.pack(fill='x', pady=(5, 5))
        
        self.url_var = tk.StringVar(value="Chưa kết nối")
        url_entry = tk.Entry(url_frame, textvariable=self.url_var,
                            font=('Arial', 9), state='readonly',
                            bg='#0d1117', fg=self.green, relief='flat',
                            readonlybackground='#0d1117')
        url_entry.pack(side='left', fill='x', expand=True, ipady=6, ipadx=6)
        
        self.copy_btn = tk.Button(url_frame, text="📋 COPY",
                                  bg=self.blue, fg='white',
                                  font=('Arial', 9, 'bold'), relief='flat', pady=6, padx=12,
                                  command=self.copy_url, state='disabled')
        self.copy_btn.pack(side='right', padx=(5, 0))
        
        self.cf_btn = tk.Button(cf_frame, text="▶️ KẾT NỐI CLOUDFLARE",
                               bg=self.purple, fg='white',
                               font=('Arial', 10, 'bold'), relief='flat', pady=10,
                               command=self.toggle_tunnel)
        self.cf_btn.pack(fill='x', pady=(5, 10))
        
        self.status_label = tk.Label(root, text="🟢 Server đang chạy | http://localhost:8888",
                                     fg=self.green, bg=self.bg, font=('Arial', 9))
        self.status_label.pack(pady=(2, 0))
    
    def add_history(self, video_id, status):
        timestamp = time.strftime("%H:%M:%S")
        text = f"[{timestamp}] {video_id[:15]}... {status}"
        self.history_label.config(text=text)
        if not hasattr(self, 'history_list'):
            self.history_list = []
        self.history_list.append(text)
        if len(self.history_list) > 10:
            self.history_list.pop(0)
    
    def update_progress(self, value, text):
        self.progress_bar['value'] = value
        self.progress_label.config(text=text)
        self.root.update_idletasks()
    
    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {'token': ''}
    
    def save_token(self):
        token = self.token_var.get().strip()
        if not token:
            messagebox.showerror("Lỗi", "Vui lòng nhập token!")
            return
        with open(CONFIG_FILE, 'w') as f:
            json.dump({'token': token}, f)
        self.config['token'] = token
        load_server_config()
        messagebox.showinfo("OK", "Đã lưu Token!")
        self.status_label.config(text="✅ Token đã lưu", fg=self.green)
        self.root.after(2000, lambda: self.status_label.config(
            text="🟢 Server đang chạy | http://localhost:8888", fg=self.green))
    
    def test_connection(self):
        token = self.token_var.get().strip()
        if not token:
            messagebox.showerror("Lỗi", "Vui lòng nhập GitHub token!")
            return
        
        try:
            import requests
            headers = {"Authorization": f"token {token}"}
            resp = requests.get("https://api.github.com/user", headers=headers, timeout=10)
            if resp.status_code == 200:
                user = resp.json().get('login', 'Unknown')
                messagebox.showinfo("OK", f"✅ Kết nối thành công!\nUser: {user}")
                self.status_label.config(text=f"✅ Kết nối GitHub: {user}", fg=self.green)
            else:
                messagebox.showerror("Lỗi", f"❌ Token không hợp lệ!\nStatus: {resp.status_code}")
                self.status_label.config(text="❌ Token không hợp lệ", fg=self.red)
        except Exception as e:
            messagebox.showerror("Lỗi", f"❌ Không thể kết nối: {e}")
            self.status_label.config(text=f"❌ Lỗi kết nối", fg=self.red)
    
    def toggle_token(self):
        self.token_entry.config(show='' if self.show_var.get() else '*')
    
    def toggle_tunnel(self):
        if self.cloudflare_process and self.cloudflare_process.poll() is None:
            self.cloudflare_process.terminate()
            self.cloudflare_process = None
            self.url_var.set("Chưa kết nối")
            self.cf_btn.config(text="▶️ KẾT NỐI CLOUDFLARE", bg=self.purple, state='normal')
            self.copy_btn.config(state='disabled')
            self.status_label.config(text="🔴 Tunnel đã ngắt", fg=self.red)
        else:
            cf_paths = [
                r'C:\Users\Administrator\cloudflared.exe',
                os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cloudflared.exe'),
                'cloudflared.exe'
            ]
            
            cf_path = None
            for p in cf_paths:
                if os.path.exists(p):
                    cf_path = p
                    break
            
            if not cf_path:
                messagebox.showerror("Lỗi",
                    "Không tìm thấy cloudflared.exe!\n\n"
                    "Tải từ:\n"
                    "https://github.com/cloudflare/cloudflared/releases\n\n"
                    "Đặt file vào:\n"
                    "C:\\Users\\Administrator\\")
                return
            
            self.url_var.set("Đang kết nối...")
            self.cf_btn.config(text="⏳ ĐANG KẾT NỐI...", bg=self.yellow, state='disabled')
            self.status_label.config(text="🔄 Đang kết nối Cloudflare...", fg=self.yellow)
            
            def run_tunnel():
                try:
                    self.cloudflare_process = subprocess.Popen(
                        [cf_path, 'tunnel', '--url', f'http://localhost:{PORT}'],
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        text=True, bufsize=1
                    )
                    
                    for line in self.cloudflare_process.stdout:
                        match = re.search(r'https://[\w-]+\.trycloudflare\.com', line)
                        if match:
                            url = match.group(0)
                            self.root.after(0, self.set_url, url)
                            break
                            
                except Exception as e:
                    self.root.after(0, self.url_var.set, f"Lỗi: {e}")
                    self.root.after(0, self.cf_btn.config,
                                  {'text': '▶️ KẾT NỐI CLOUDFLARE', 'bg': self.purple, 'state': 'normal'})
                    self.root.after(0, self.status_label.config,
                                  {'text': f'❌ Lỗi tunnel', 'fg': self.red})
                    return
                
                self.root.after(0, self.cf_btn.config,
                              {'text': '⏹️ NGẮT KẾT NỐI', 'bg': self.red, 'state': 'normal'})
                self.root.after(0, self.status_label.config,
                              {'text': f'🌐 Tunnel đã kết nối', 'fg': self.green})
            
            threading.Thread(target=run_tunnel, daemon=True).start()
    
    def set_url(self, url):
        self.url_var.set(url)
        self.root.clipboard_clear()
        self.root.clipboard_append(url)
        self.copy_btn.config(state='normal')
        self.cf_btn.config(text="⏹️ NGẮT KẾT NỐI", bg=self.red, state='normal')
        self.status_label.config(text=f"🌐 Tunnel đã kết nối", fg=self.green)
    
    def copy_url(self):
        url = self.url_var.get()
        if url and 'trycloudflare.com' in url:
            self.root.clipboard_clear()
            self.root.clipboard_append(url)
            messagebox.showinfo("OK", "Đã copy URL vào clipboard!")

def start_server():
    load_server_config()
    print(f"Server: http://localhost:{PORT}")
    print("Mobile chỉ kích hoạt - Server tự làm tất cả!")
    print("⚡ Upload bằng Git (force add + log chi tiết)")
    HTTPServer(('0.0.0.0', PORT), Handler).serve_forever()

if __name__ == '__main__':
    load_server_config()
    threading.Thread(target=start_server, daemon=True).start()
    
    root = tk.Tk()
    gui = ServerGUI(root)
    gui_ref = gui
    root.protocol("WM_DELETE_WINDOW", lambda: (
        gui.cloudflare_process.terminate() if gui.cloudflare_process else None,
        root.destroy()
    ))
    root.mainloop()