# ZazoomTek – Cloudflare Workers Cron Triggers

Schedules: every day at 12:30, 16:00, 19:30 Europe/Rome. Automatic retry attempts occur every 5 minutes, with cutoffs at 13:00, 16:30 and 20:00 (exclusive). Pending content remains in the editorial queue for a later slot if all attempts fail.

UTC cron candidates cover both CET and CEST; the Worker checks the
actual Europe/Rome clock and skips times outside the three recovery windows.
The GitHub workflow remains responsible for all importing, site builds,
verification, Cloudflare Pages deployment and per-slot deduplication.

## Configuration required in Cloudflare

1. Deploy this Worker with Wrangler using the Cloudflare account that owns
   the Pages project. Do not deploy before configuring the GitHub token.
2. Add the Worker secret: `wrangler secret put GITHUB_TOKEN` from this folder.
   Use a fine-grained GitHub token restricted to zazoomtek-site with
   **Actions: Read and write** permission. Never add it to GitHub files.
3. Deploy: `wrangler deploy` from this folder.
4. Check Cron Triggers and Cron Events in Cloudflare dashboard; verify that
   GitHub receives workflow_dispatch and that the editorial release receipt
   reflects the intended slot.
5. Only after successful end-to-end testing, disable the old GitHub schedule
   to prevent duplicate triggers. Keep workflow_dispatch enabled.

Cloudflare schedule propagation can take up to 15 minutes. The GitHub
workflow has its own time window and content digest protection.
