import os, json, glob
from github import Github

token = os.environ.get('GIST_TOKEN')
if not token:
    print('No GIST_TOKEN')
    exit()

g = Github(token)
user = g.get_user()

for f in glob.glob("output/*.vtt"):
    vid = f.replace('output/', '').replace('.vtt', '')
    with open(f, 'r', encoding='utf-8') as fh:
        content = fh.read()
    
    gist = user.create_gist(
        public=True,
        files={f"{vid}.vtt": {"content": content}},
        description=f"YouTube Subtitle - {vid}"
    )
    print(f"Gist: {gist.html_url}")
