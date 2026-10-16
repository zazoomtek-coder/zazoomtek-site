# ZazoomTek Cloudflare migration — staging only

This branch prepares a static **snapshot** of the existing site, preserving original public pages, visual assets, editorial JSON, and SEO resources. It does not change the public domain, Cloudflare account, Firebase deployment, or editorial automations.

## Authorized automated functions
- YouTube Community/video synchronization via existing GitHub Actions.
- Six-slot News in evidenza refresh (existing editorial source).
- Editorial homepage / box refresh from existing published sources.

Those workflows currently dispatch `deploy-site-live.yml` (Firebase). Do **not** switch off Firebase or attach the Cloudflare custom domain until the publication router is migrated and checked. Avoid Pages auto-build on every 5-minute YouTube check unless it really changed content. Ensure serial deploys, test a preview, then switch the domain with a tested rollback path.

## Cloudflare staging
`python3 scripts/build-cloudflare-pages.py` makes `dist/`, filters internal build tools, preview/test pages, private state and the deprecated comments files, and checks a conservative 19,000-file / 25 MiB per-file budget. Configure Cloudflare Pages with output directory `dist` and this build command only after the production publishing logic has been refactored, preferably on an isolated preview branch first.

## Before cutover
1. Test desktop/mobile navigation, images, feeds, search, article URLs, redirects, sitemap, robots and all three desired automation results at a Cloudflare preview URL.
2. Add health checks and a rollback to last known-good deployment. Check that a failed build does not replace production.
3. Stop triggering Firebase deploys only after Cloudflare is verified with the actual domain.
4. Never migrate the Firebase comments API; it is explicitly unwanted.
5. Do not promise 100% uptime: CDN, platform and DNS incidents remain possible.
