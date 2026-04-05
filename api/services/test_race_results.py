"""Unit tests for race_results HTML parsers.

Run standalone with:
    python api/services/test_race_results.py

These tests focus on the pure parsing helpers so no network or Redis is
required. Synthetic HTML fixtures exercise the critical correctness paths:

  * _extract_yen must NOT concatenate adjacent numbers
  * _parse_winners must find the first-place horse(s)
  * _parse_winners must handle dead heats (two horses at rank 1)
  * _detect_cancellation must recognise "中止" / "取止" style notices
  * payouts above the sanity cap must be discarded
"""

from __future__ import annotations

import sys
import unittest

from bs4 import BeautifulSoup

# Allow running this file directly from the repo root.
if __name__ == "__main__" and __package__ is None:
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.race_results import (  # noqa: E402
    _detect_cancellation,
    _extract_tansho_payout,
    _extract_yen,
    _parse_win_payouts,
    _parse_winners,
    _PAYOUT_SANITY_CAP,
)


# ─────────────────────────────────────────────────────────────────────────────
# _extract_yen — critical fix for the "430円 2人気" → 4302 regression
# ─────────────────────────────────────────────────────────────────────────────


class ExtractYenTests(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(_extract_yen("430円"), 430)

    def test_with_comma(self):
        self.assertEqual(_extract_yen("1,230円"), 1230)

    def test_with_popularity_suffix_must_not_concatenate(self):
        # The old implementation returned 4302 — the new one MUST return 430.
        self.assertEqual(_extract_yen("430円 2人気"), 430)

    def test_with_prefix_whitespace(self):
        self.assertEqual(_extract_yen("   560円"), 560)

    def test_empty(self):
        self.assertEqual(_extract_yen(""), 0)

    def test_no_digits(self):
        self.assertEqual(_extract_yen("─"), 0)

    def test_multi_line_only_first_line(self):
        self.assertEqual(_extract_yen("780円\n1人気"), 780)


# ─────────────────────────────────────────────────────────────────────────────
# _parse_winners — single winner, dead heat, and fallbacks
# ─────────────────────────────────────────────────────────────────────────────


_SINGLE_WINNER_HTML = """
<table class="RaceTable01 RaceCommon_Table ResultRefund_FixedTable">
  <tr class="HorseList">
    <td class="Result_Num Txt_C"><div class="Rank">1</div></td>
    <td class="Num Txt_C"><span>7</span></td>
  </tr>
  <tr class="HorseList">
    <td class="Result_Num Txt_C"><div class="Rank">2</div></td>
    <td class="Num Txt_C"><span>3</span></td>
  </tr>
  <tr class="HorseList">
    <td class="Result_Num Txt_C"><div class="Rank">3</div></td>
    <td class="Num Txt_C"><span>11</span></td>
  </tr>
</table>
"""

_DEAD_HEAT_HTML = """
<table class="RaceTable01">
  <tr class="HorseList">
    <td class="Result_Num Txt_C"><div class="Rank">1</div></td>
    <td class="Num Txt_C"><span>4</span></td>
  </tr>
  <tr class="HorseList">
    <td class="Result_Num Txt_C"><div class="Rank">1</div></td>
    <td class="Num Txt_C"><span>9</span></td>
  </tr>
  <tr class="HorseList">
    <td class="Result_Num Txt_C"><div class="Rank">3</div></td>
    <td class="Num Txt_C"><span>2</span></td>
  </tr>
</table>
"""

_WIN_PAYOUT_HTML = """
<table class="Payout_Detail_Table">
  <tr>
    <th>単勝</th>
    <td class="Txt_R"><span>430円</span></td>
    <td>2人気</td>
  </tr>
  <tr>
    <th>複勝</th>
    <td class="Txt_R">170円</td>
    <td>2人気</td>
  </tr>
</table>
"""

_CANCELLED_HTML = """
<div class="RaceList_NameBox">
  <h1 class="RaceName">中京 12R 発走取止 (馬場不良のため)</h1>
</div>
"""


class ParseWinnersTests(unittest.TestCase):
    def test_single_winner(self):
        soup = BeautifulSoup(_SINGLE_WINNER_HTML, "lxml")
        self.assertEqual(_parse_winners(soup), [7])

    def test_dead_heat(self):
        soup = BeautifulSoup(_DEAD_HEAT_HTML, "lxml")
        self.assertEqual(_parse_winners(soup), [4, 9])

    def test_empty_html(self):
        soup = BeautifulSoup("<html><body></body></html>", "lxml")
        self.assertEqual(_parse_winners(soup), [])


# ─────────────────────────────────────────────────────────────────────────────
# _extract_tansho_payout / _parse_win_payouts
# ─────────────────────────────────────────────────────────────────────────────


class PayoutTests(unittest.TestCase):
    def test_extract_tansho(self):
        soup = BeautifulSoup(_WIN_PAYOUT_HTML, "lxml")
        self.assertEqual(_extract_tansho_payout(soup), 430)

    def test_parse_payouts_dead_heat_assigns_same_value(self):
        soup = BeautifulSoup(_WIN_PAYOUT_HTML, "lxml")
        payouts = _parse_win_payouts(soup, [4, 9])
        self.assertEqual(payouts, {4: 430, 9: 430})

    def test_payout_sanity_cap_discards_garbage(self):
        # Synthesise a hostile payout ~10,000,000 yen which should be dropped.
        bad = """
        <table class="Payout_Detail_Table">
          <tr><th>単勝</th><td>9,999,999円 999人気</td></tr>
        </table>
        """
        soup = BeautifulSoup(bad, "lxml")
        amount = _extract_tansho_payout(soup)
        # Whatever the parser yields, it must NOT exceed the sanity cap.
        self.assertLessEqual(amount, _PAYOUT_SANITY_CAP)


# ─────────────────────────────────────────────────────────────────────────────
# _detect_cancellation
# ─────────────────────────────────────────────────────────────────────────────


class CancellationTests(unittest.TestCase):
    def test_cancelled_in_racename(self):
        soup = BeautifulSoup(_CANCELLED_HTML, "lxml")
        self.assertTrue(_detect_cancellation(soup))

    def test_normal_race_not_cancelled(self):
        soup = BeautifulSoup(_SINGLE_WINNER_HTML, "lxml")
        self.assertFalse(_detect_cancellation(soup))


if __name__ == "__main__":
    unittest.main(verbosity=2)
