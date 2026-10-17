# ZazoomTek — GitHub → Cloudflare Pages release guide

## What is automatic
- GitHub holds content changes; **not every GitHub commit should trigger a Pages build**.
- The scheduled release checks at :39, :44 and :54 (Europe/Rome minute).
  GitHub Actions cron is best effort; a minute-exact execution cannot be guaranteed.
- The normal release gate batches new public changes, with a rolling 30-minute
  cooldown. No content changes = no new Pages build.
- The Git-history guard stops normal releases after 450 watched-trigger commits
  within 31 days. Urgent manual releases stop at 475. This is **not** an official
  Cloudflare usage counter; check the dashboard for the real account-wide quota.
- A push to `.github/site-publish-request.txt` queues a **normal** release.
  Only an explicit workflow_dispatch with `urgent=true` consumes the urgent reserve.

## REQUIRED one-time Cloudflare configuration
Workers & Pages → ZazoomTek Pages project → Settings → Build:
1. Repository: `zazoomtek-coder/zazoomtek-site`; production branch `main`.
2. Build command: `python3 scripts/cloudflare-build-site.py`.
3. Build output directory: `dist`.
4. **Build watch paths include ONLY `cloudflare-release-trigger.txt`**;
   exclude list empty. The default include `*` is unsafe for this repository.
5. Ensure production branch automatic deployments are enabled.
6. Review the **official Cloudflare build counter** for the account; repository
   commit counts cannot detect builds on other projects or manual redeploys.

## Release success is checked, not assumed
- The release job first builds and validates the static site **without** changing
  the Cloudflare watched trigger.
- When tests pass, it updates only `cloudflare-release-trigger.txt`, consuming
  at most one intentionally requested Pages build.
- A successful Cloudflare build publishes `/zt-release-status.json` with the
  `source_commit` used to build the site, after all build-time checks pass.
- GitHub polls `https://zazoomtek.it/zt-release-status.json` and verifies that
  exact release plus ThermoMate's review video/editorial boxes and the current
  Home no-duplicates code. These are ordinary HTTP GETs (zero Pages builds).
- If the marker does not appear or a required page is missing in seven minutes,
  **the GitHub release job fails**. The initial Git push is only "requested",
  never "successfully published" until the checks pass.
- Note: this verifies the deployed static output. It cannot certify that all
  client browsers have cleared caches or that every article is flawless.

## If a release is missing
1. Inspect the `Cloudflare Pages - hourly batched publishing` GitHub Actions run.
   If preflight failed, read the failing script log. The old site is retained.
2. If the push succeeded but production verification failed, open Cloudflare
   Workers & Pages → Deployments for the precise build status and error.
3. Confirm the Git integration, production branch and Build watch paths above.
4. Compare the public `/zt-release-status.json` source SHA to the latest
   `source_commit=` in `cloudflare-release-trigger.txt`.
5. Do not repeatedly edit the trigger or redeploy blindly. Fix the failed
   preflight/Cloudflare configuration first, then request one controlled release.
