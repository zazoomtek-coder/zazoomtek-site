# ZazoomTek — Cloudflare Workers Cron Triggers

Three daily Europe/Rome slots: **12:30, 16:00, 19:30**.

- **15 minutes before each slot** Cloudflare requests an editorial workflow run.
- Cloudflare checks every **5 minutes**, retrying until **60 minutes after** the slot start.
- The Worker reads `data/editorial_release_state.json` on `main` and skips subsequent requests when that slot was already deployed.
- The GitHub workflow imports Community, videos, RSS and queued Studio posts, builds the site, and performs the Cloudflare Pages deploy only within an authorized slot.
- If a run fails, queued Studio posts and unimported YouTube content are not intentionally deleted; they can be retried or imported at the next slot.
- Site updates around **12:35, 16:05 and 19:35** are targets, not hard cutoffs.
- Cron is configured as a single UTC expression `*/5 * * * *`. The Worker gates against actual Europe/Rome local time including DST.

## Activate safely

1. Merge tested Worker files into `main`.
2. In Cloudflare Workers, create `zazoomtek-editorial-cron` using this directory's `wrangler.toml`.
3. Configure **GITHUB_TOKEN** as a secret in Cloudflare. Use a restricted fine-grained token with GitHub Actions write and Contents read on the single repo. Never paste tokens into chat or commit them.
4. Deploy the Worker. Check Cloudflare Cron Events, GitHub workflow_dispatch, and release receipt on `main`.
5. **Only after an end-to-end success**, disable GitHub's legacy scheduled trigger. Keep `workflow_dispatch` enabled.

The Worker does not replace Cloudflare Pages and does not deploy directly. It schedules the existing protected GitHub build-and-deploy workflow. Do not claim the trigger is active until verified in the Cloudflare account.
