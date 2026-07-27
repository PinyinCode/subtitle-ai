#!/usr/bin/env python3
import os, json, glob
from pathlib import Path
from datetime import datetime
import whisper
from deep_translator import GoogleTranslator
from pypinyin import pinyin, Style

def format_time(s):
    h = int(s // 3600)
    m = int((s % 3600) // 60)
    s = int(s % 60)
    ms = int((s - int(s)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"

for audio in glob.glob("data/audio/*.m4a"):
    vid = Path(audio).stem
    out = Path("output") / f"{vid}.vtt"
    Path("output").mkdir(exist_ok=True)
    
    model = whisper.load_model("base")
    result = model.transcribe(audio)
    lang = result.get("language", "zh")
    segs = result.get("segments", [])
    
    to_zh = GoogleTranslator(source=lang, target="zh-CN") if not lang.startswith("zh") else None
    to_vi = GoogleTranslator(source="zh-CN", target="vi")
    
    lines = ["WEBVTT", "Kind: captions", "Language: zh-TW", "", ""]
    
    for seg in segs:
        text = seg["text"].strip()
        if not text: continue
        
        zh = to_zh.translate(text) if to_zh else text
        py = " ".join([p[0] for p in pinyin(zh, style=Style.TONE)])
        try:
            vi = to_vi.translate(zh)
        except:
            vi = ""
        
        lines.extend([
            f"{format_time(seg['start'])} --> {format_time(seg['end'])}",
            zh,
            py,
            vi,
            ""
        ])
    
    with open(out, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(lines))
    
    # Summary
    summary = {
        'video_id': vid,
        'language': lang,
        'segments': len(segs),
        'duration': segs[-1]['end'] if segs else 0,
        'output': str(out)
    }
    with open(Path("output") / f"{vid}_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
