# ZazoomTek Cloudflare migration — controlled static publishing

## Emergency deployment settings (tested 16 Oct 2026)

Git-connected Cloudflare Pages project for the already-live website:

- GitHub repository: `zazoomtek-coder/zazoomtek-site`
- Production branch: `main`
- Framework: **None**
- Project root: repository root (`/`)
- Build command: **`python3 scripts/cloudflare-build-site.py`**
- Output directory: **`dist`**
- No secrets or Firebase API keys required. No Functions or Workers deployed.
- The full staging build tested successfully on GitHub: 903 files / 29.93 MiB, including 200 YouTube player watch pages and the `/watch/` index.
- DO NOT configure build output as `.`: that would publish scripts and private files.
- Once the project exists, Cloudflare Pages > Settings > Build > Build watch paths must be **Include `cloudflare-release-trigger.txt` only**; exclude nothing. This is CRITICAL. `main` source changes alone must not trigger automatic builds.
- Disable automatic previews for non-production branches (Branch deployment controls).
- `.github/workflows/cloudflare-controlled-release.yml` checks content and batches releases every 2 hours, at most twelve a day, with a 31-day Git-history safety cap of 450 scheduled / 475 urgent markers. 31 days × 12 = 372, leaving a reserve for other builds or retries.
- This scheduled cap is NOT the Cloudflare official billing meter. Inspect Pages usage in the Cloudflare dashboard; avoid extra builds/deployments outside the controlled marker workflow.
- After a successful `*.pages.dev` URL is verified, attach `zazoomtek.it` and `www.zazoomtek.it` under **Pages project > Custom domains**; Cloudflare will handle Pages DNS records after confirmation. Never change nameservers again and never touch MX/TXT/email records.
- Preserve GitHub content, root article URLs, six-featured-card JSON, responsive navigation, reviews, 200 video embed pages, images, sitemaps and robots.
- Do NOT disable Firebase fallback or delete DNS records BEFORE a Pages preview is verified.


This branch prepares a static **snapshot** of the existing site, preserving original public pages, visual assets, editorial JSON, and SEO resources. It does not change the public domain, Cloudflare account, Firebase deployment, or editorial automations.

## Authorized automated functions
- YouTube Community/video synchronization via existing GitHub Actions.
- Six-slot News in evidenza refresh (existing editorial source).
- Editorial homepage / box refresh from existing published sources.

Those workflows currently dispatch `deploy-site-live.yml` (Firebase). Do **not** switch off Firebase or attach the Cloudflare custom domain until the publication router is migrated and checked. Avoid Pages auto-build on every 5-minute YouTube check unless it really changed content. Ensure serial deploys, test a preview, then switch the domain with a tested rollback path.

## Cloudflare staging
`python3 scripts/build-cloudflare-pages.py` makes `dist/`, filters internal build tools, preview/test pages, private state and the deprecated comments files, and checks a conservative 19,000-file / 25 MiB per-file budget. Configure Cloudflare Pages with output directory `dist` and build command `python3 scripts/cloudflare-build-site.py`; GitHub Actions verified it offline before the cutover.

## Before cutover
1. Test desktop/mobile navigation, images, feeds, search, article URLs, redirects, sitemap, robots and all three desired automation results at a Cloudflare preview URL.
2. Add health checks and a rollback to last known-good deployment. Check that a failed build does not replace production.
3. Stop triggering Firebase deploys only after Cloudflare is verified with the actual domain.
4. Never migrate the Firebase comments API; it is explicitly unwanted.
5. Do not promise 100% uptime: CDN, platform and DNS incidents remain possible.


## Publication quota: editorial content always wins

Cloudflare Pages Free allows 500 builds per month (account-wide). The monthly allowance renews in the next allowance period; verify the exact reset date/usage in the Cloudflare dashboard instead of assuming that it resets at midnight on the first.

**Priorities when nearing the quota:**

| Conservative recent build attempts | Automatic response |
| --- | --- |
| 0–349 | Allow YouTube, manual news and reviews, featured news and editorial-box refresh |
| 350–399 | Skip editorial-box refresh; keep YouTube, manual articles, featured |
| 400–484 | Skip editorial boxes AND featured carousel refresh; prioritize YouTube and manual news/reviews |
| 485–494 | Stop routine builds, reserve space for urgent editorial corrections |
| 495+ | Block all automatic publication until the quota resets or is verified/reconciled |

The guard `scripts/cloudflare-quota-guard.py` reads all Pages projects under the account, conservatively counting recent deployments across production and previews, including failed attempts. This is **an estimate, not the official Cloudflare build meter**; reconcile actual usage with the dashboard and keep a buffer. It uses a 31-day rolling window so it cannot undercount solely because an account's reset date is unknown; this may stop optional publications longer than strictly necessary. If credentials or usage are unavailable, it blocks publication instead of guessing.

Run `python3 scripts/cloudflare-quota-guard.py --kind editorial|featured|news|urgent` **at the single serialized deploy gate, immediately before building/deploying**. Provide Cloudflare API token and account ID as GitHub Actions secrets, never as website files. This gate does not yet control Firebase or Pages until the Cloudflare deployment pipeline is attached to it.

**Critical integration condition:** configure Cloudflare Pages to NOT automatically deploy on every push to `main` and disable unsolicited preview branch builds. Otherwise direct GitHub changes can bypass the quota guard and the 500-build budget could still be exhausted. The importer can keep committing news without a build; one controlled deploy must batch the changes.

**Video rule:** video data consists of YouTube IDs/metadata and embedded players; video bytes remain at YouTube. Do not copy MP4/WebM files into the site or Cloudflare artifacts.

**Continuity:** if a build is skipped, the last verified deployed site remains online and the article remains in GitHub for a later release. No unsafe partial deploy and no use of the old Firebase comments API.
