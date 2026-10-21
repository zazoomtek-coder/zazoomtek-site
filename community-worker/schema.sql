-- Persistent idempotent Community archive.
CREATE TABLE IF NOT EXISTS community_posts (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  category TEXT NOT NULL,
  published_iso TEXT NOT NULL DEFAULT '',
  source_url TEXT NOT NULL,
  updated_utc TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_community_recent
  ON community_posts(published_iso DESC, updated_utc DESC);
