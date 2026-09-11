import unittest
from datetime import datetime, timezone

from analyze_equity_derivatives import (
    build_position,
    latest_completed_us_date,
    leg_daily_decomposition,
    normalize_history,
    option_symbol,
)


class EquityDerivativesTests(unittest.TestCase):
    def test_option_symbol_preserves_index_root(self):
        self.assertEqual(
            option_symbol("$VIX", "2026-10-21", 20, "c"),
            "$VIX|20261021|20.00C",
        )

    def test_historical_iv_percent_is_normalized_to_decimal(self):
        payload = {
            "data": [
                {
                    "raw": {
                        "tradeTime": "2026-09-08",
                        "lastPrice": 2.62,
                        "impliedVolatility": 17.98,
                    }
                }
            ]
        }
        self.assertAlmostEqual(normalize_history(payload)[0]["iv"], 0.1798)

    def test_eod_cutoff_does_not_label_premarket_data_as_today(self):
        before_open = datetime(2026, 9, 9, 12, 0, tzinfo=timezone.utc)
        after_close = datetime(2026, 9, 9, 21, 0, tzinfo=timezone.utc)
        self.assertEqual(str(latest_completed_us_date(before_open)), "2026-09-08")
        self.assertEqual(str(latest_completed_us_date(after_close)), "2026-09-09")

    def test_daily_decomposition_uses_signed_quantity_and_cash_multiplier(self):
        previous = {
            "date": "2026-09-07",
            "last": 2.0,
            "underlying_price": 100.0,
            "iv": 0.20,
            "delta": 0.5,
            "gamma": 0.1,
            "theta": -0.02,
            "vega": 0.1,
        }
        current = {
            "date": "2026-09-08",
            "last": 2.5,
            "underlying_price": 101.0,
            "iv": 0.21,
        }
        result = leg_daily_decomposition(previous, current, -1)
        self.assertEqual(result["actual_usd"], -50.0)
        self.assertEqual(result["delta_usd"], -50.0)
        self.assertEqual(result["gamma_usd"], -5.0)
        self.assertEqual(result["vega_usd"], -10.0)
        self.assertEqual(result["theta_usd"], 2.0)
        self.assertEqual(result["residual_usd"], 13.0)

    def test_vertical_aggregates_leg_greeks_and_executable_quote(self):
        position = {
            "id": "test",
            "label": "Test call spread",
            "underlying": "XYZ",
            "expiration": "2026-10-16",
            "strategy": "call_debit_spread",
            "legs": [
                {"side": "long", "quantity": 1, "strike": 100, "option_type": "C"},
                {"side": "short", "quantity": 1, "strike": 110, "option_type": "C"},
            ],
        }
        common = {
            "date": "2026-09-08",
            "open": None,
            "high": None,
            "low": None,
            "price_change": None,
            "volume": 10,
            "open_interest": 20,
            "gamma": 0.02,
            "theta": -0.03,
            "rho": 0.05,
            "theoretical": None,
            "underlying_price": 105.0,
        }
        histories = {
            "XYZ|20261016|100.00C": [
                {**common, "last": 8.0, "bid": 7.9, "ask": 8.1, "iv": 0.20, "delta": 0.7, "vega": 0.2}
            ],
            "XYZ|20261016|110.00C": [
                {**common, "last": 3.0, "bid": 2.9, "ask": 3.1, "iv": 0.25, "delta": 0.3, "vega": 0.15}
            ],
        }
        result = build_position(position, histories)
        self.assertEqual(result["mark_usd"], 500.0)
        self.assertEqual(result["quote"]["bid_usd"], 480.0)
        self.assertEqual(result["quote"]["ask_usd"], 520.0)
        self.assertAlmostEqual(result["net_greeks"]["delta_shares"], 40.0)
        self.assertAlmostEqual(result["net_greeks"]["vega_usd_per_vol_point"], 5.0)
        self.assertEqual(result["iv_structure"]["long_minus_short_iv_points"], -5.0)
        self.assertEqual(result["payoff"]["mark_pct_of_max_payoff"], 50.0)


if __name__ == "__main__":
    unittest.main()
