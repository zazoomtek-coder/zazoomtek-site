# ZazoomTek – Cloudflare Workers Cron Triggers

Schedule: every five minutes, 24 hours a day. Each poll checks YouTube Community and video uploads; the site is rebuilt and deployed only when verified editorial data changes. If a workflow is queued or running, the Worker skips that poll to prevent overlapping imports.

The Cron Trigger uses `*/5 * * * *` and is timezone-independent. The Worker checks GitHub Actions for an active import before dispatching the next poll. The GitHub workflow imports YouTube Community posts and videos, verifies completeness and duplicates, builds the site, and deploys Cloudflare Pages only when the editorial content digest changes.

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
