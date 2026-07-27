#!/usr/bin/env python3
"""Push generated subtitles to GitHub Gist"""

import os
import json
import glob
from pathlib import Path

try:
    from github import Github
except ImportError:
    os.system('pip install PyGithub -q')
    from github import Github


def main():
    token = os.environ.get('GIST_TOKEN')
    
    if not token:
        print("⚠️ GIST_TOKEN not set, skipping Gist upload")
        return
    
    print("📤 Connecting to GitHub...")
    g = Github(token)
    user = g.get_user()
    
    vtt_files = glob.glob("output/*.vtt")
    
    if not vtt_files:
        print("⚠️ No VTT files found")
        return
    
    print(f"📄 Found {len(vtt_files)} subtitle file(s)")
    
    for vtt_file in vtt_files:
        video_id = Path(vtt_file).stem
        filename = f"{video_id}_subtitle.vtt"
        
        print(f"\n📝 Processing: {video_id}")
        
        # Read content
        with open(vtt_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check existing Gist
        existing_gist = None
        for gist in user.get_gists():
            if filename in gist.files:
                existing_gist = gist
                break
        
        try:
            if existing_gist:
                print(f"   🔄 Updating Gist: {existing_gist.id}")
                existing_gist.edit(
                    description=f"YouTube Subtitle - {video_id}",
                    files={filename: {"content": content}}
                )
                gist_url = existing_gist.html_url
            else:
                print(f"   ✨ Creating new Gist")
                new_gist = user.create_gist(
                    public=True,
                    files={filename: {"content": content}},
                    description=f"YouTube Subtitle - {video_id}"
                )
                gist_url = new_gist.html_url
            
            print(f"   ✅ Gist URL: {gist_url}")
            
            # Save Gist info
            info_file = f"output/{video_id}_gist.json"
            with open(info_file, 'w') as f:
                json.dump({
                    'video_id': video_id,
                    'gist_url': gist_url,
                    'filename': filename
                }, f, indent=2)
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print("\n✅ Gist upload complete!")


if __name__ == "__main__":
    main()
