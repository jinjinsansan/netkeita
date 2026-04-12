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

-- User profile extensions
ALTER TABLE users ADD COLUMN IF NOT EXISTS nickname   TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_key TEXT DEFAULT 'horse1';
