-- netkeita chat schema migration
-- Run this in Supabase SQL Editor

-- Chat messages
CREATE TABLE IF NOT EXISTS chat_messages (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel      TEXT NOT NULL CHECK (channel IN ('global', 'jra', 'nar')),
    line_user_id TEXT NOT NULL,
    nickname     TEXT NOT NULL,
    avatar_key   TEXT NOT NULL DEFAULT 'horse1',
    content      TEXT CHECK (content IS NULL OR length(content) <= 100),
    stamp        TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_chat_channel_time
    ON chat_messages (channel, created_at DESC);

-- Chat user profiles (standalone table; no dependency on auth.users / user_stats)
CREATE TABLE IF NOT EXISTS chat_profiles (
    line_user_id     TEXT PRIMARY KEY,
    display_name     TEXT NOT NULL DEFAULT '',
    nickname         TEXT,
    avatar_key       TEXT DEFAULT 'horse1',
    custom_avatar_url TEXT,
    updated_at       TIMESTAMPTZ DEFAULT now()
);
