"""Unit tests for articles service pure functions.

These tests exercise the stateless helpers (slug generation, validation,
URL scheme filtering, view serialisation, reading time) without touching
Redis or the network, so they run in ~0.01s with no external dependencies.

Run standalone with:
    python api/services/test_articles.py
"""

from __future__ import annotations

import os
import sys
import unittest

if __name__ == "__main__" and __package__ is None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.articles import (  # noqa: E402
    _estimate_reading_time,
    _safe_url,
    _slug_base_from_title,
    admin_view,
    generate_slug,
    is_valid_slug,
    public_summary,
    public_view,
)


class SlugValidationTests(unittest.TestCase):
    def test_simple_valid(self):
        self.assertTrue(is_valid_slug("hello-world"))
        self.assertTrue(is_valid_slug("article_42"))
        self.assertTrue(is_valid_slug("a"))

    def test_rejects_uppercase(self):
        self.assertFalse(is_valid_slug("Hello"))

    def test_rejects_spaces(self):
        self.assertFalse(is_valid_slug("hello world"))

    def test_rejects_japanese(self):
        self.assertFalse(is_valid_slug("こんにちは"))

    def test_rejects_leading_hyphen(self):
        self.assertFalse(is_valid_slug("-leading"))

    def test_rejects_slash(self):
        # Critical for Redis key injection protection
        self.assertFalse(is_valid_slug("foo/bar"))
        self.assertFalse(is_valid_slug("foo:bar"))

    def test_rejects_too_long(self):
        self.assertFalse(is_valid_slug("a" * 81))


class SlugGenerationTests(unittest.TestCase):
    def test_ascii_title(self):
        base = _slug_base_from_title("Derby Preview 2026")
        self.assertEqual(base, "derby-preview-2026")

    def test_japanese_title_falls_back(self):
        # NFKD-strip yields empty → fallback to "article"
        base = _slug_base_from_title("日本ダービー展望")
        self.assertEqual(base, "article")

    def test_mixed_title(self):
        base = _slug_base_from_title("G1 Race 2026 予想")
        self.assertEqual(base, "g1-race-2026")

    def test_generate_includes_timestamp_suffix(self):
        slug = generate_slug("Derby")
        # Format: derby-YYMMDDHHmm
        self.assertTrue(slug.startswith("derby-"))
        suffix = slug.rsplit("-", 1)[-1]
        self.assertEqual(len(suffix), 10)  # YYMMDDHHmm
        self.assertTrue(suffix.isdigit())

    def test_generate_from_japanese_title_not_empty(self):
        slug = generate_slug("日本ダービー展望")
        self.assertTrue(slug.startswith("article-"))
        self.assertTrue(is_valid_slug(slug))

    def test_generated_slug_always_passes_validation(self):
        for title in ["Hello", "日本語", "Mix 日本語 2026", "", "!!!"]:
            with self.subTest(title=title):
                self.assertTrue(is_valid_slug(generate_slug(title)))


class SafeUrlTests(unittest.TestCase):
    def test_accepts_https(self):
        self.assertEqual(_safe_url("https://example.com/a.jpg"), "https://example.com/a.jpg")

    def test_accepts_http(self):
        self.assertEqual(_safe_url("http://example.com/a.jpg"), "http://example.com/a.jpg")

    def test_rejects_data_uri(self):
        # XSS / referrer-leak vector
        self.assertEqual(_safe_url("data:image/png;base64,AAAA"), "")

    def test_rejects_javascript_scheme(self):
        self.assertEqual(_safe_url("javascript:alert(1)"), "")
        self.assertEqual(_safe_url("JavaScript:alert(1)"), "")  # case-insensitive

    def test_rejects_file_scheme(self):
        self.assertEqual(_safe_url("file:///etc/passwd"), "")

    def test_empty_is_empty(self):
        self.assertEqual(_safe_url(""), "")
        self.assertEqual(_safe_url("   "), "")


class ReadingTimeTests(unittest.TestCase):
    def test_empty_body(self):
        self.assertEqual(_estimate_reading_time(""), 1)

    def test_short_body(self):
        self.assertEqual(_estimate_reading_time("short"), 1)

    def test_exact_one_minute(self):
        body = "a" * 400  # 400 chars / 400 cpm = 1 minute
        self.assertEqual(_estimate_reading_time(body), 1)

    def test_two_minutes(self):
        body = "a" * 500
        self.assertEqual(_estimate_reading_time(body), 2)

    def test_ignores_whitespace(self):
        body = "a" * 400 + "\n\n\n   " + "b" * 400
        self.assertEqual(_estimate_reading_time(body), 2)


_SAMPLE_RECORD = {
    "slug": "derby-2026",
    "title": "Derby 2026",
    "description": "summary",
    "body": "a" * 500,
    "thumbnail_url": "https://example.com/a.jpg",
    "author": "netkeita",
    "author_id": "Uxxxxxxxxxxxxxxxxxxx",  # PRIVATE — must not leak publicly
    "status": "published",
    "created_at": "2026-04-05T10:00:00+09:00",
    "updated_at": "2026-04-05T10:00:00+09:00",
}


class ViewSerialisationTests(unittest.TestCase):
    def test_public_view_strips_author_id(self):
        v = public_view(_SAMPLE_RECORD)
        self.assertNotIn("author_id", v)
        self.assertEqual(v["title"], "Derby 2026")
        self.assertEqual(v["body"], "a" * 500)
        self.assertIn("reading_time_minutes", v)

    def test_public_summary_strips_body_and_author_id(self):
        v = public_summary(_SAMPLE_RECORD)
        self.assertNotIn("author_id", v)
        self.assertNotIn("body", v)
        self.assertEqual(v["title"], "Derby 2026")

    def test_admin_view_includes_author_id(self):
        v = admin_view(_SAMPLE_RECORD)
        self.assertIn("author_id", v)
        self.assertEqual(v["author_id"], "Uxxxxxxxxxxxxxxxxxxx")
        self.assertIn("reading_time_minutes", v)

    def test_public_view_on_empty_record(self):
        self.assertEqual(public_view({}), {})
        self.assertEqual(public_view(None), {})  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main(verbosity=2)
