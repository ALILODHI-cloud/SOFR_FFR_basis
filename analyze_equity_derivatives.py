#!/usr/bin/env python3
"""Fetch Barchart EOD option history and aggregate the configured positions."""
from __future__ import annotations

import json
import math
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, urlencode, urlparse, urlunparse
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "equity_positions.json"
OUTPUT = ROOT / "equity_derivatives_data.json"
DOCS_OUTPUT = ROOT / "docs" / OUTPUT.name
MULTIPLIER = 100
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "Chrome/140.0.0.0 Safari/537.36"
)


def option_symbol(underlying: str, expiration: str, strike: float, option_type: str) -> str:
    expiry = expiration.replace("-", "")
    return f"{underlying}|{expiry}|{strike:.2f}{option_type.upper()}"


def signed_quantity(leg: dict[str, Any]) -> int:
    quantity = int(leg.get("quantity", 1))
    return quantity if leg["side"] == "long" else -quantity


def finite(value: Any) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def with_extra_fields(url: str, extra_fields: tuple[str, ...]) -> str:
    parsed = urlparse(url)
    params = parse_qs(parsed.query, keep_blank_values=True)
    fields = params.get("fields", [""])[0].split(",")
    for field in extra_fields:
        if field not in fields:
            fields.append(field)
    params["fields"] = [",".join(fields)]
    query = urlencode(params, doseq=True)
    return urlunparse(parsed._replace(query=query))


def normalize_history(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for displayed in payload.get("data", []):
        raw = displayed.get("raw") or displayed
        trade_date = raw.get("tradeTime")
        if not trade_date:
            continue
        implied_volatility = finite(raw.get("impliedVolatility"))
        row = {
            "date": str(trade_date)[:10],
            "open": finite(raw.get("openPrice")),
            "high": finite(raw.get("highPrice")),
            "low": finite(raw.get("lowPrice")),
            "last": finite(raw.get("lastPrice")),
            "bid": finite(raw.get("bidPrice")),
            "ask": finite(raw.get("askPrice")),
            "price_change": finite(raw.get("priceChange")),
            "volume": finite(raw.get("volume")),
            "open_interest": finite(raw.get("openInterest")),
            # The historical endpoint returns percent units (e.g. 17.98), unlike
            # the chain endpoint's decimal units (0.1798). Store decimals.
            "iv": implied_volatility / 100 if implied_volatility is not None else None,
            "delta": finite(raw.get("delta")),
            "gamma": finite(raw.get("gamma")),
            "theta": finite(raw.get("theta")),
            "vega": finite(raw.get("vega")),
            "rho": finite(raw.get("rho")),
            "theoretical": finite(raw.get("theoreticalValue")),
            "underlying_price": finite(raw.get("baseLastPrice")),
        }
        if row["last"] is not None:
            rows.append(row)
    return sorted(rows, key=lambda row: row["date"])


def latest_completed_us_date(now: datetime | None = None) -> date:
    now_et = (now or datetime.now(timezone.utc)).astimezone(ZoneInfo("America/New_York"))
    cutoff = now_et.date() if now_et.time() >= time(16, 15) else now_et.date() - timedelta(days=1)
    while cutoff.weekday() >= 5:
        cutoff -= timedelta(days=1)
    return cutoff


def us_market_is_open(now: datetime | None = None) -> bool:
    now_et = (now or datetime.now(timezone.utc)).astimezone(ZoneInfo("America/New_York"))
    return now_et.weekday() < 5 and time(9, 30) <= now_et.time() < time(16, 15)


def fetch_option_history(page: Any, symbol: str) -> list[dict[str, Any]]:
    encoded = quote(symbol, safe="")
    page_url = (
        f"https://www.barchart.com/options/quotes/{encoded}/price-history/historical"
    )
    with page.expect_response(
        lambda response: (
            "/proxies/core-api/v1/historical/get?" in response.url
            and response.status == 200
        ),
        timeout=90_000,
    ) as response_info:
        page.goto(page_url, wait_until="domcontentloaded", timeout=90_000)
    api_url = with_extra_fields(response_info.value.url, ("bidPrice", "askPrice"))
    result = page.evaluate(
        """async (url) => {
            const response = await fetch(url);
            return {status: response.status, body: await response.text()};
        }""",
        api_url,
    )
    if result["status"] != 200:
        raise RuntimeError(f"Barchart history returned HTTP {result['status']} for {symbol}")
    payload = json.loads(result["body"])
    cutoff = latest_completed_us_date().isoformat()
    rows = [row for row in normalize_history(payload) if row["date"] <= cutoff]
    if not rows:
        raise RuntimeError(f"No Barchart option history returned for {symbol}")
    return rows


def fetch_current_chain(
    page: Any, underlying: str, expiration: str
) -> dict[str, dict[str, Any]]:
    category = "stocks" if underlying.startswith("$") else "etfs-funds"
    base = quote(underlying, safe="")
    page_url = (
        f"https://www.barchart.com/{category}/quotes/{base}/volatility-greeks"
        f"?expiration={expiration}"
    )
    with page.expect_response(
        lambda response: (
            "/proxies/core-api/v1/options/get?" in response.url
            and f"expirationDate={expiration}" in response.url
            and response.status == 200
        ),
        timeout=90_000,
    ) as response_info:
        page.goto(page_url, wait_until="domcontentloaded", timeout=90_000)
    api_url = with_extra_fields(
        response_info.value.url,
        ("bidPrice", "askPrice", "baseLastPrice", "priceChange"),
    )
    result = page.evaluate(
        """async (url) => {
            const response = await fetch(url);
            return {status: response.status, body: await response.text()};
        }""",
        api_url,
    )
    if result["status"] != 200:
        raise RuntimeError(
            f"Barchart current chain returned HTTP {result['status']} "
            f"for {underlying} {expiration}"
        )
    payload = json.loads(result["body"])
    session_date = latest_completed_us_date().isoformat()
    rows: dict[str, dict[str, Any]] = {}
    for grouped_rows in payload.get("data", {}).values():
        for displayed in grouped_rows:
            raw = displayed.get("raw") or displayed
            symbol = raw.get("symbol")
            if not symbol:
                continue
            rows[symbol] = {
                "date": session_date,
                "open": None,
                "high": None,
                "low": None,
                "last": finite(raw.get("lastPrice")),
                "bid": finite(raw.get("bidPrice")),
                "ask": finite(raw.get("askPrice")),
                "price_change": finite(raw.get("priceChange")),
                "volume": finite(raw.get("volume")),
                "open_interest": finite(raw.get("openInterest")),
                # The chain endpoint returns IV as a decimal.
                "iv": finite(raw.get("volatility")),
                "delta": finite(raw.get("delta")),
                "gamma": finite(raw.get("gamma")),
                "theta": finite(raw.get("theta")),
                "vega": finite(raw.get("vega")),
                "rho": finite(raw.get("rho")),
                "theoretical": finite(raw.get("theoretical")),
                "underlying_price": finite(raw.get("baseLastPrice")),
            }
    return rows


def overlay_current(
    history: list[dict[str, Any]], current: dict[str, Any]
) -> list[dict[str, Any]]:
    by_date = {row["date"]: dict(row) for row in history}
    existing = by_date.get(current["date"], {})
    existing.update({key: value for key, value in current.items() if value is not None})
    by_date[current["date"]] = existing
    return [by_date[key] for key in sorted(by_date)]


def midpoint(row: dict[str, Any]) -> float:
    if row.get("bid") is not None and row.get("ask") is not None:
        return (float(row["bid"]) + float(row["ask"])) / 2
    return float(row["last"])


def cash_greeks(row: dict[str, Any], quantity: int) -> dict[str, float | None]:
    def scaled(key: str) -> float | None:
        value = finite(row.get(key))
        return round(value * quantity * MULTIPLIER, 4) if value is not None else None

    return {
        "delta_shares": scaled("delta"),
        "gamma_shares_per_dollar": scaled("gamma"),
        "theta_usd_per_day": scaled("theta"),
        "vega_usd_per_vol_point": scaled("vega"),
        "rho_usd_per_rate_point": scaled("rho"),
    }


def leg_daily_decomposition(
    previous: dict[str, Any], current: dict[str, Any], quantity: int
) -> dict[str, float | None]:
    actual = quantity * MULTIPLIER * (current["last"] - previous["last"])
    spot_change = None
    if previous.get("underlying_price") is not None and current.get("underlying_price") is not None:
        spot_change = current["underlying_price"] - previous["underlying_price"]

    delta_pnl = (
        quantity * MULTIPLIER * previous["delta"] * spot_change
        if spot_change is not None and previous.get("delta") is not None
        else None
    )
    gamma_pnl = (
        quantity * MULTIPLIER * 0.5 * previous["gamma"] * spot_change**2
        if spot_change is not None and previous.get("gamma") is not None
        else None
    )
    iv_change_points = (
        (current["iv"] - previous["iv"]) * 100
        if current.get("iv") is not None and previous.get("iv") is not None
        else None
    )
    vega_pnl = (
        quantity * MULTIPLIER * previous["vega"] * iv_change_points
        if iv_change_points is not None and previous.get("vega") is not None
        else None
    )
    elapsed_days = (date.fromisoformat(current["date"]) - date.fromisoformat(previous["date"])).days
    theta_pnl = (
        quantity * MULTIPLIER * previous["theta"] * elapsed_days
        if previous.get("theta") is not None
        else None
    )
    explained_values = [delta_pnl, gamma_pnl, vega_pnl, theta_pnl]
    residual = (
        actual - sum(value for value in explained_values if value is not None)
        if any(value is not None for value in explained_values)
        else None
    )
    return {
        "actual_usd": round(actual, 2),
        "spot_change": round(spot_change, 4) if spot_change is not None else None,
        "iv_change_points": round(iv_change_points, 2) if iv_change_points is not None else None,
        "delta_usd": round(delta_pnl, 2) if delta_pnl is not None else None,
        "gamma_usd": round(gamma_pnl, 2) if gamma_pnl is not None else None,
        "vega_usd": round(vega_pnl, 2) if vega_pnl is not None else None,
        "theta_usd": round(theta_pnl, 2) if theta_pnl is not None else None,
        "residual_usd": round(residual, 2) if residual is not None else None,
    }


def add_optional(total: dict[str, float], values: dict[str, float | None]) -> None:
    for key, value in values.items():
        if value is not None:
            total[key] = total.get(key, 0.0) + value


def payoff_metrics(position: dict[str, Any], spot: float, mark_per_share: float) -> dict[str, Any]:
    strategy = position["strategy"]
    legs = position["legs"]
    intrinsic_per_share = 0.0
    for leg in legs:
        quantity = signed_quantity(leg)
        strike = float(leg["strike"])
        intrinsic = (
            max(spot - strike, 0)
            if leg["option_type"] == "C"
            else max(strike - spot, 0)
        )
        intrinsic_per_share += quantity * intrinsic

    out: dict[str, Any] = {
        "intrinsic_value_usd": round(intrinsic_per_share * MULTIPLIER, 2),
        "extrinsic_value_usd": round((mark_per_share - intrinsic_per_share) * MULTIPLIER, 2),
    }
    if strategy in {"put_debit_spread", "call_debit_spread"} and len(legs) == 2:
        width = abs(float(legs[0]["strike"]) - float(legs[1]["strike"]))
        out.update(
            {
                "spread_width": width,
                "max_payoff_usd": round(width * MULTIPLIER, 2),
                "mark_pct_of_max_payoff": round(mark_per_share / width * 100, 1),
                "intrinsic_pct_of_max_payoff": round(intrinsic_per_share / width * 100, 1),
            }
        )
    return out


def build_position(position: dict[str, Any], histories: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    enriched_legs: list[dict[str, Any]] = []
    latest_dates: list[str] = []
    for configured_leg in position["legs"]:
        leg = dict(configured_leg)
        symbol = option_symbol(
            position["underlying"],
            position["expiration"],
            float(leg["strike"]),
            leg["option_type"],
        )
        history = histories[symbol]
        latest_dates.append(history[-1]["date"])
        leg.update({"symbol": symbol, "signed_quantity": signed_quantity(leg), "history": history})
        enriched_legs.append(leg)

    as_of = min(latest_dates)
    for leg in enriched_legs:
        leg["history"] = [row for row in leg["history"] if row["date"] <= as_of]
        current = leg["history"][-1]
        previous = leg["history"][-2] if len(leg["history"]) > 1 else None
        quantity = leg["signed_quantity"]
        leg["current"] = {
            **current,
            "midpoint": round(midpoint(current), 4),
            "cash_greeks": cash_greeks(current, quantity),
            "iv_pct": round(current["iv"] * 100, 2) if current.get("iv") is not None else None,
            "bid_ask_width": (
                round(current["ask"] - current["bid"], 4)
                if current.get("ask") is not None and current.get("bid") is not None
                else None
            ),
        }
        leg["previous"] = previous
        leg["daily_decomposition"] = (
            leg_daily_decomposition(previous, current, quantity) if previous else None
        )

    current_rows = [leg["current"] for leg in enriched_legs]
    spot = next(
        (row["underlying_price"] for row in current_rows if row.get("underlying_price") is not None),
        None,
    )
    if spot is None:
        raise RuntimeError(f"No underlying price returned for {position['id']}")

    net_greeks: dict[str, float] = {}
    daily: dict[str, float] = {}
    mark_per_share = 0.0
    executable_bid_per_share = 0.0
    executable_ask_per_share = 0.0
    for leg in enriched_legs:
        quantity = leg["signed_quantity"]
        mark_per_share += quantity * leg["current"]["midpoint"]
        if quantity > 0:
            executable_bid_per_share += quantity * (
                leg["current"].get("bid") or leg["current"]["last"]
            )
            executable_ask_per_share += quantity * (
                leg["current"].get("ask") or leg["current"]["last"]
            )
        else:
            executable_bid_per_share += quantity * (
                leg["current"].get("ask") or leg["current"]["last"]
            )
            executable_ask_per_share += quantity * (
                leg["current"].get("bid") or leg["current"]["last"]
            )
        add_optional(net_greeks, leg["current"]["cash_greeks"])
        if leg["daily_decomposition"]:
            add_optional(daily, {
                key: value
                for key, value in leg["daily_decomposition"].items()
                if key.endswith("_usd")
            })

    long_leg = next((leg for leg in enriched_legs if leg["side"] == "long"), None)
    short_leg = next((leg for leg in enriched_legs if leg["side"] == "short"), None)
    iv_structure = None
    if long_leg and short_leg:
        long_iv = long_leg["current"].get("iv")
        short_iv = short_leg["current"].get("iv")
        previous_long = long_leg.get("previous") or {}
        previous_short = short_leg.get("previous") or {}
        if long_iv is not None and short_iv is not None:
            current_skew = (long_iv - short_iv) * 100
            previous_skew = None
            if previous_long.get("iv") is not None and previous_short.get("iv") is not None:
                previous_skew = (previous_long["iv"] - previous_short["iv"]) * 100
            iv_structure = {
                "long_minus_short_iv_points": round(current_skew, 2),
                "daily_change_points": (
                    round(current_skew - previous_skew, 2) if previous_skew is not None else None
                ),
            }

    common_dates = sorted(
        set.intersection(*(set(row["date"] for row in leg["history"]) for leg in enriched_legs))
    )
    position_history = []
    by_leg = [
        {row["date"]: row for row in leg["history"]}
        for leg in enriched_legs
    ]
    for history_date in common_dates:
        mark = 0.0
        delta = gamma = theta = vega = 0.0
        for leg, indexed in zip(enriched_legs, by_leg):
            row = indexed[history_date]
            quantity = leg["signed_quantity"]
            mark += quantity * midpoint(row)
            delta += quantity * MULTIPLIER * (row.get("delta") or 0)
            gamma += quantity * MULTIPLIER * (row.get("gamma") or 0)
            theta += quantity * MULTIPLIER * (row.get("theta") or 0)
            vega += quantity * MULTIPLIER * (row.get("vega") or 0)
        position_history.append(
            {
                "date": history_date,
                "mark_usd": round(mark * MULTIPLIER, 2),
                "delta_shares": round(delta, 3),
                "gamma_shares_per_dollar": round(gamma, 3),
                "theta_usd_per_day": round(theta, 2),
                "vega_usd_per_vol_point": round(vega, 2),
            }
        )

    expiry = date.fromisoformat(position["expiration"])
    result = {
        **{key: value for key, value in position.items() if key != "legs"},
        "as_of": as_of,
        "days_to_expiration": (expiry - date.fromisoformat(as_of)).days,
        "underlying_price": round(spot, 4),
        "mark_usd": round(mark_per_share * MULTIPLIER, 2),
        "quote": {
            "bid_usd": round(executable_bid_per_share * MULTIPLIER, 2),
            "mid_usd": round(mark_per_share * MULTIPLIER, 2),
            "ask_usd": round(executable_ask_per_share * MULTIPLIER, 2),
            "width_usd": round(
                (executable_ask_per_share - executable_bid_per_share) * MULTIPLIER,
                2,
            ),
        },
        "net_greeks": {key: round(value, 3) for key, value in net_greeks.items()},
        "daily_decomposition": {key: round(value, 2) for key, value in daily.items()},
        "iv_structure": iv_structure,
        "payoff": payoff_metrics(position, spot, mark_per_share),
        "legs": enriched_legs,
        "history": position_history[-65:],
    }
    return result


def main() -> None:
    from playwright.sync_api import sync_playwright

    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    symbols: dict[str, dict[str, Any]] = {}
    for position in config["positions"]:
        for leg in position["legs"]:
            symbol = option_symbol(
                position["underlying"],
                position["expiration"],
                float(leg["strike"]),
                leg["option_type"],
            )
            symbols[symbol] = leg

    histories: dict[str, list[dict[str, Any]]] = {}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(user_agent=USER_AGENT)
        for symbol in symbols:
            page = context.new_page()
            print(f"Fetching {symbol}…")
            try:
                histories[symbol] = fetch_option_history(page, symbol)
                latest = histories[symbol][-1]
                print(
                    f"  {latest['date']} last {latest['last']:.2f} "
                    f"IV {latest['iv'] * 100:.2f}%"
                )
            finally:
                page.close()

        # Historical VIX option rows can lag the current chain. Outside market
        # hours, overlay the latest completed-session chain for every position;
        # skip this intraday so a partial session is never labelled EOD.
        if not us_market_is_open():
            chains = {
                (position["underlying"], position["expiration"])
                for position in config["positions"]
            }
            for underlying, expiration in sorted(chains):
                page = context.new_page()
                print(f"Fetching current chain {underlying} {expiration}…")
                try:
                    current_rows = fetch_current_chain(page, underlying, expiration)
                    for symbol in symbols:
                        if symbol in current_rows and current_rows[symbol].get("last") is not None:
                            histories[symbol] = overlay_current(
                                histories[symbol], current_rows[symbol]
                            )
                finally:
                    page.close()
        browser.close()

    positions = [build_position(position, histories) for position in config["positions"]]
    risk_by_underlying: dict[str, dict[str, float]] = {}
    portfolio_daily: dict[str, float] = {}
    for position in positions:
        bucket = risk_by_underlying.setdefault(position["underlying"], {})
        add_optional(bucket, position["net_greeks"])
        add_optional(portfolio_daily, position["daily_decomposition"])

    cross_asset_cash_greeks = {
        key: round(
            sum(values.get(key, 0.0) for values in risk_by_underlying.values()), 3
        )
        for key in ("theta_usd_per_day", "vega_usd_per_vol_point")
    }

    payload = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "source": "Barchart EOD option history and volatility/Greeks",
        "notes": [
            "Greeks are Barchart model values. Cash Greeks apply the configured signed quantity and 100x contract multiplier.",
            "Daily decomposition uses prior-day Greeks: delta + 0.5 gamma + vega + calendar-day theta; residual includes higher-order, cross-Greek, model and mark effects.",
            "No entry premiums were supplied, so mark is current position value rather than trade P&L.",
            "VIX option sensitivities are model sensitivities to the relevant VIX option underlying; spot VIX alone does not determine VIX option value.",
        ],
        "portfolio": {
            "position_count": len(positions),
            "as_of": min(position["as_of"] for position in positions),
            "cross_asset_cash_greeks": cross_asset_cash_greeks,
            "risk_by_underlying": {
                underlying: {key: round(value, 3) for key, value in values.items()}
                for underlying, values in risk_by_underlying.items()
            },
            "daily_decomposition": {key: round(value, 2) for key, value in portfolio_daily.items()},
        },
        "positions": positions,
    }
    text = json.dumps(payload, indent=2, allow_nan=False) + "\n"
    OUTPUT.write_text(text, encoding="utf-8")
    DOCS_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    DOCS_OUTPUT.write_text(text, encoding="utf-8")
    print(f"Wrote {OUTPUT} and {DOCS_OUTPUT}")


if __name__ == "__main__":
    main()
