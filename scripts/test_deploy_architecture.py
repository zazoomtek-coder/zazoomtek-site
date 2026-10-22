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
    # The retired Firebase cleanup job is isolated from production and may
    # run on its own schedule to purge expired preview resources. A production
    # Hosting deploy remains forbidden.
if live_workflows!=[CANON]:
    errors.append(f'Exactly one canonical Firebase live publisher required, got {live_workflows}')
canonical=(WORKFLOWS/CANON).read_text(encoding='utf-8')
retired='if: false # Firebase Hosting retired; production is Cloudflare Pages' in canonical
if not retired:
    errors.append('Firebase canonical publisher MUST remain retired while Cloudflare is production')
    for required in (
        'zazoomtek-firebase-live-publishing','cancel-in-progress: false',
        'git fetch origin main','git reset --hard origin/main',
        'Refuse stale main snapshot just before deployment',
        "if: steps.freshness.outputs.current == 'true'",
    ):
        if required not in canonical:
            errors.append(f'Canonical Firebase deploy missing safety step: {required}')
# Production moved to Cloudflare Pages. The obsolete Firebase merge router was
# intentionally removed; do not fail every site audit for that retired file.
merge_path=WORKFLOWS/'firebase-hosting-merge.yml'
if merge_path.is_file():
    merge=merge_path.read_text(encoding='utf-8')
    if not retired and 'gh workflow run deploy-site-live.yml' not in merge:
        errors.append('GitHub push routing no longer queues canonical Firebase deploy')
elif not retired:
    errors.append('Active Firebase publishing requires a canonical push router')
if retired and merge_path.is_file():
    errors.append('Retired Firebase merge router unexpectedly restored')
# The atomic 19 October cutover retired cloudflare-controlled-release.yml.
# Production has exactly one Master workflow; do NOT restore legacy writers.
master=WORKFLOWS/'master-orchestrator-production.yml'
if not master.is_file():
    errors.append('Missing Master Cloudflare production publisher workflow')
else:
    production=master.read_text(encoding='utf-8')
    # Current publisher uses direct main, scheduled release at Italian local
    # times, conditional catch-up and Wrangler. Manual dispatch remains
    # available without resurrecting the old manual-request JSON mechanism.
    for required in (
        'workflow_dispatch:',
        "timezone: 'Europe/Rome'",
        "cron: '15 10,15,20 * * *'",
        "cron: '25,40 20 * * *'",
        "cron: '45 12 * * *'",
        "cron: '45 17 * * *'",
        'zazoomtek-master-sole-repository-and-pages-writer',
        'cancel-in-progress: false',
        'contents: write',
        'scripts/master-production-gateway.py --publish',
        "steps.master_release.outputs.deploy == 'true'",
        "steps.recovery.outputs.mode == 'retry_deploy'",
        'python3 scripts/cloudflare-build-site.py',
        'cloudflare/wrangler-action@v3',
        'pages deploy dist --project-name=',
        'scripts/verify-live-cloudflare.py',
    ):
        if required not in production:
            errors.append(f'Master Cloudflare production guard missing: {required}')
    if re.search(r'(?m)^  push:\\s*
if (WORKFLOWS/'cloudflare-controlled-release.yml').is_file():
    errors.append('Retired Cloudflare publisher unexpectedly restored')
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
print('PASS: direct-main Cloudflare Master, scheduled release/recovery and retired Firebase verified')
, production):
        errors.append('Scheduled Master unexpectedly publishes on every main push')
    if 'python3 scripts/master-production-gateway.py --publish --urgent' in production:
        errors.append('Scheduled Master unexpectedly bypasses the configured release windows')

if (WORKFLOWS/'cloudflare-controlled-release.yml').is_file():
    errors.append('Retired Cloudflare publisher unexpectedly restored')
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
print('PASS: Master Cloudflare publisher present with manual release; retired Firebase safe')
