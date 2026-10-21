# ZazoomTek YouTube Community Worker — isolated staging

This is an independent publishing path, PREPARED BUT NOT ACTIVATED.
It does not alter the main Home, the Master gateway, Pages production builds, or editorial release slots.

## Architecture

- GitHub Actions `youtube-community-worker.yml`: best-effort five-minute schedule, every day, all hours, and manual retry/backfill.
- `scripts/community-worker-sync.py`: uses the existing official YouTube Community page acquisition/parser, combines new records with cached source IDs, and sends batches straight to the Worker. It does not commit or deploy the main site.
- Worker `src/index.js`: authenticated `POST /community/ingest`, D1 upserts keyed by YouTube post ID, public `GET /community/` and `GET /community/post/{post_id}`.
- D1 persistence survives failed master builds and GitHub commits. Retry is idempotent; a transient failure is retried in the next run.
- No Firebase dependency and no shared repository writer.

## Activation by an authorized Cloudflare account administrator

1. Confirm the domain `zazoomtek.it` is on the intended Cloudflare account.
2. In Cloudflare Workers & Pages, create a D1 database named `zazoomtek-community` using `npx wrangler d1 create zazoomtek-community`. Save the returned database ID privately.
3. Copy `wrangler.example.toml` to `wrangler.toml` and set `database_id`; do not commit real credentials. The D1 ID is not a password, but keep account configuration controlled.
4. Apply the schema: from `community-worker/`, `npx wrangler d1 execute zazoomtek-community --remote --file=./schema.sql`.
5. Generate a long random ingestion token. Save it as the Worker secret using `npx wrangler secret put INGEST_TOKEN`. Save the identical token as GitHub Actions secret `ZT_COMMUNITY_INGEST_TOKEN`. Never paste it into ChatGPT, logs, or code.
6. Deploy from `community-worker/` with `npx wrangler deploy` and first verify `https://<worker-subdomain>.workers.dev/community/health`.
7. In Workers → Triggers → Routes, route ONLY `zazoomtek.it/community/*` to this Worker (the custom domain must be active in the account). Never route `news-*`, `recensione-*`, `/*`, or the whole Home.
8. Add GitHub repository variable `ZT_COMMUNITY_WORKER_ENDPOINT=https://zazoomtek.it` (or the worker's workers.dev origin while testing).
9. After DNS/route, D1 and secret tests succeed, integrate the feature branch into `main` to activate its scheduler; alternatively manually run the workflow once with `backfill=true` to initialize the full cache.
10. Verify `/community/`, an individual article URL and D1 persisted count; test duplicate retries and a simulated main-site build failure.

## Credential scopes

Prefer Cloudflare Dashboard login through an explicitly connected authorized app.
If using a dedicated Cloudflare API token for Wrangler, scope it only to the intended account/zone with `Account: Workers Scripts: Edit`, `Account: D1: Edit`, `Zone: Workers Routes: Edit` as required; do not grant DNS editing or global account access unnecessarily.
GitHub requires permissions to manage two repository settings: the secret `ZT_COMMUNITY_INGEST_TOKEN` and variable `ZT_COMMUNITY_WORKER_ENDPOINT`.

## Important limitations

- GitHub schedules are best effort, so exactly-on-the-minute checks and zero downtime cannot be guaranteed.
- YouTube Community has no supported public API endpoint for full posts; the existing HTML parser may need maintenance when YouTube changes its markup. The old D1 posts remain available during such incidents.
- D1/Worker outage, account quotas, authorization failures, or DNS can delay live publication. Retries protect against missed posts; no infrastructure can promise publication when Cloudflare is unavailable.
- The isolated Worker serves new pages under `/community/`. It deliberately does NOT inject them into the Home or the main News/Review category archives until a separately tested integration is approved. Category classification is basic and text is preserved verbatim; it is not a full rewritten long-form review.
- This branch contains NO Cloudflare account deployment and no production secrets.
