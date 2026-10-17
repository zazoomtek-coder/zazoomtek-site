#!/usr/bin/env python3
"""Read-only hosting guard: Cloudflare production, retired Firebase cannot deploy."""
from pathlib import Path
import json
import re

ROOT=Path(__file__).resolve().parents[1]
WORKFLOWS=ROOT/'.github'/'workflows'
CANON='deploy-site-live.yml'
ALLOWED_PREVIEW='firebase-hosting-pull-request.yml'
errors=[]
live_workflows=[]
for path in sorted(WORKFLOWS.glob('*.yml')):
    body=path.read_text(encoding='utf-8')
    hosting_action='FirebaseExtended/action-hosting-deploy@v0' in body
    live_action=bool(re.search(r'^\s*channelId:\s*live\b',body,re.M))
    direct_cli=bool(re.search(
        r'\bfirebase(?:-tools)?\s+deploy\b[^\n]*--only\s+(?:hosting|hosting:[^\s]+)',
        body,re.I,
    ))
    if direct_cli:
        errors.append(f'{path.name}: Firebase Hosting CLI deploy bypasses canonical publisher')
    if live_action:
        live_workflows.append(path.name)
        if path.name!=CANON:
            errors.append(f'{path.name}: direct live Hosting deploy is forbidden')
    if hosting_action and path.name not in (CANON,ALLOWED_PREVIEW):
        errors.append(f'{path.name}: direct Firebase Hosting action is forbidden')
    if path.name==ALLOWED_PREVIEW and live_action:
        errors.append('PR previews must never deploy to live')
    if path.name=='prune-firebase-news-previews-once.yml' and (
        re.search(r'^\s*schedule:\s*$',body,re.M)
        or re.search(r'^\s*push:\s*$',body,re.M)
    ):
        errors.append('Expired preview cleanup must be manually triggered')
if live_workflows!=[CANON]:
    errors.append(f'Exactly one canonical Firebase live publisher required, got {live_workflows}')
canonical=(WORKFLOWS/CANON).read_text(encoding='utf-8')
for required in (
    'zazoomtek-firebase-live-publishing','cancel-in-progress: false',
    'git fetch origin main','git reset --hard origin/main',
    'Refuse stale main snapshot just before deployment',
    "if: steps.freshness.outputs.current == 'true'",
    'Validate existing YouTube news, reviews and video pages',
    'Verify no unstyled or wrapping navigation reaches Firebase',
    'Verify editorial box thumbnails and typography on all article pages',
):
    if required not in canonical:
        errors.append(f'Canonical deploy missing safety step: {required}')
# Production moved to Cloudflare Pages. The obsolete Firebase merge router was
# intentionally removed; do not fail every site audit for that retired file.
merge_path=WORKFLOWS/'firebase-hosting-merge.yml'
retired='if: false # Firebase Hosting retired; production is Cloudflare Pages' in canonical
if merge_path.is_file():
    merge=merge_path.read_text(encoding='utf-8')
    if not retired and 'gh workflow run deploy-site-live.yml' not in merge:
        errors.append('GitHub push routing no longer queues canonical Firebase deploy')
elif not retired:
    errors.append('Active Firebase publishing requires a canonical push router')
if retired and merge_path.is_file():
    errors.append('Retired Firebase merge router unexpectedly restored')
if not (WORKFLOWS/'cloudflare-controlled-release.yml').is_file():
    errors.append('Missing Cloudflare production publisher workflow')
firebase=json.loads((ROOT/'firebase.json').read_text(encoding='utf-8'))
hosting=firebase.get('hosting',{})
if hosting.get('target')!='zazoomtek' or hosting.get('public')!='.':
    errors.append('Firebase Hosting target/public changed; manual review required')
if not any(x=='.github/**' for x in hosting.get('ignore',[])):
    errors.append('Firebase ignore list does not exclude GitHub workflows')
if errors:
    raise SystemExit('FIREBASE ARCHITECTURE CHECK FAILED:\n'+'\n'.join('- '+x for x in errors))
print('PASS: legacy Firebase live workflow remains gated and retired')
print('PASS: PR previews and maintenance jobs cannot deploy live')
print('PASS: serialized, current-main checked, canonical layout and Firebase config protected')
