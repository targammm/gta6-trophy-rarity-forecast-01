"""Forecast GTA VI trophy earn rates on Exophase at the case target.

Model: split the earn rate into its two moving parts and forecast each
separately, because the rate is a ratio and the two parts move at very
different speeds after launch:

    rate_i(target) = earned_i(target) / players(target)

  * players(target): the number of players Exophase tracks. It grows fast
    after launch and jumps in steps, because Exophase only refreshes its
    counts every few hours: between refreshes the page is frozen, at a
    refresh it jumps to the true cumulative count.
  * earned_i(target): how many tracked players hold trophy i. It grows
    much slower than the player count, and at a different speed per tier:
    early story trophies are picked up by most new players, grind and
    collectible trophies by few, the platinum by almost none in week one.

Both factors are fitted from the case's own history: a least-squares line
of log players (and of log earned per tier) against time over the last
24 hours of reads, read at the target. When the history is completely
flat -- no refresh has happened inside it yet -- there is no slope to
fit, so the model falls back to the one refresh the competition's own
rules document: launch night went 638 -> 3,868 players tracked while
earned counts grew about 19%. That prior only fires on flat histories
(the practice cases); any history with real movement uses its own fit.

The median is the fitted ratio. The spread is a logit random walk,
sigma 1.0 per root day, wide enough that a refresh landing inside the
horizon does not blow up the pinball loss. A trophy already at 100% is
frozen at 100: everybody tracked holds it, and a refresh cannot move it.

Standard library only, no network, no randomness: two runs on the same
case write byte-identical output.
"""

import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path

LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]
NORMAL_Q = [-1.645, -0.674, 0.0, 0.674, 1.645]
SPREAD_PER_ROOT_DAY = 1.0
# Extra logit spread when the flat-history prior fires: both jump factors
# are estimated from a single observed refresh, so the median itself is
# uncertain by roughly half a logit on top of the random-walk spread.
FLAT_HISTORY_EXTRA_SPREAD = 0.45

# The single refresh the rules document, used only when a history is flat.
PRIOR_PLAYERS_JUMP = 6.06
PRIOR_EARNED_JUMP = 1.19

MAX_PLAYERS_FACTOR = 200.0
MAX_EARNED_FACTOR = 500.0
MAX_LOG_GROWTH_PER_HOUR = 0.40
FIT_WINDOW_HOURS = 24.0


def _clamp_pct(x):
    if x < 0.01:
        return 0.01
    if x > 99.99:
        return 99.99
    return x


def _logit(pct):
    p = _clamp_pct(pct) / 100.0
    return math.log(p / (1.0 - p))


def _inv_logit(lg):
    if lg > 35.0:
        return 100.0
    if lg < -35.0:
        return 0.0
    return 100.0 / (1.0 + math.exp(-lg))


def _round4(x):
    scaled = x * 10000.0
    whole = math.floor(scaled)
    if scaled - whole >= 0.5:
        whole += 1
    value = whole / 10000.0
    return int(value) if float(value).is_integer() else value


def _parse_when(text):
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def _hours_since(start, when):
    return (when - start).total_seconds() / 3600.0


def _fit_slope(hours, log_values):
    """Least-squares slope of log values against hours; 0 when unidentified."""
    n = len(hours)
    if n < 2:
        return 0.0
    mean_h = sum(hours) / n
    mean_v = sum(log_values) / n
    num = 0.0
    den = 0.0
    for h, v in zip(hours, log_values):
        dh = h - mean_h
        num += dh * (v - mean_v)
        den += dh * dh
    if den <= 0.0:
        return 0.0
    return num / den


def _last_known_rates(case):
    """Last read's rate per trophy, walking back over nulls."""
    trophies = case["trophies"]
    rates = [None] * len(trophies)
    for read in reversed(case["history"]):
        for i, value in enumerate(read["rates"]):
            if rates[i] is None and value is not None:
                rates[i] = value
        if all(v is not None for v in rates):
            break
    return [0.0 if v is None else v for v in rates]


def _earned_counts(read, rates):
    """Earned count per trophy; None where that read lacked the trophy."""
    players = read["players_tracked"]
    return [None if r is None else r * players / 100.0 for r in rates]


def _series_total(earned_by_read, members):
    """Tier total per read, carrying forward when a read lacks a trophy."""
    series = []
    carry = 0.0
    for earned in earned_by_read:
        values = [earned[i] for i in members if earned[i] is not None]
        if values:
            carry = sum(values)
        series.append(carry)
    return series


def forecast_case(case):
    trophies = case["trophies"]
    history = case["history"]
    if not history:
        raise ValueError("case has no history")
    if case["levels"] != LEVELS:
        raise ValueError("case asks for levels %s, not %s"
                         % (case["levels"], LEVELS))
    horizon_hours = case["horizon_minutes"] / 60.0
    horizon_days = case["horizon_minutes"] / 1440.0

    rates_last = _last_known_rates(case)

    # Fitting window: the last 24 hours of reads, or everything when fewer.
    times = [_parse_when(r["at"]) for r in history]
    end = times[-1]
    window = [r for r, t in zip(history, times)
              if _hours_since(t, end) <= FIT_WINDOW_HOURS]
    if len(window) < 3:
        window = history
    w_times = [_parse_when(r["at"]) for r in window]
    w_start = w_times[0]
    w_hours = [_hours_since(w_start, t) for t in w_times]

    # --- players factor -------------------------------------------------
    players_series = [r["players_tracked"] for r in window]
    history_flat = len(set(players_series)) <= 1
    if history_flat:
        players_factor = PRIOR_PLAYERS_JUMP
    else:
        slope = _fit_slope(w_hours, [math.log(max(p, 1)) for p in players_series])
        slope = min(max(slope, 0.0), MAX_LOG_GROWTH_PER_HOUR)
        players_factor = min(math.exp(slope * horizon_hours), MAX_PLAYERS_FACTOR)

    # --- earned factor per tier -----------------------------------------
    totals = []
    for read in window:
        earned = _earned_counts(read, read["rates"])
        totals.append(sum(e for e in earned if e is not None))
    global_slope = _fit_slope(w_hours, [math.log(max(t, 0.5)) for t in totals])
    global_slope = min(max(global_slope, 0.0), MAX_LOG_GROWTH_PER_HOUR)

    tiers = {}
    for idx, trophy in enumerate(trophies):
        tiers.setdefault(trophy["tier"], []).append(idx)
    tier_factor = {}
    for tier, members in tiers.items():
        earned_by_read = [_earned_counts(r, r["rates"]) for r in window]
        series = _series_total(earned_by_read, members)
        if len(set(series)) <= 1:
            tier_factor[tier] = PRIOR_EARNED_JUMP
            continue
        slope = _fit_slope(w_hours, [math.log(max(s, 0.5)) for s in series])
        slope = min(max(slope, 0.0), MAX_LOG_GROWTH_PER_HOUR)
        if len(members) < 3:
            slope = global_slope
        tier_factor[tier] = min(math.exp(slope * horizon_hours), MAX_EARNED_FACTOR)

    # --- assemble rows ---------------------------------------------------
    spread = SPREAD_PER_ROOT_DAY * math.sqrt(horizon_days)
    if history_flat:
        spread = math.sqrt(spread * spread
                           + FLAT_HISTORY_EXTRA_SPREAD ** 2)
    rows = []
    for idx, trophy in enumerate(trophies):
        last_rate = rates_last[idx]
        if last_rate >= 100.0:
            rows.append({"id": trophy["id"], "q": [100, 100, 100, 100, 100]})
            continue
        median = last_rate * tier_factor[trophy["tier"]] / players_factor
        centre = _logit(median)
        quantiles = []
        for z in NORMAL_Q:
            q = _inv_logit(centre + z * spread)
            quantiles.append(_round4(min(max(q, 0.01), 100.0)))
        for a, b in zip(quantiles, quantiles[1:]):
            if b < a:
                raise ValueError("quantiles out of order")
        rows.append({"id": trophy["id"], "q": quantiles})
    return {"trophies": rows}


def main():
    in_dir = Path(os.environ.get("MAKEFUN_INPUT_DIR") or "/input")
    out_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output")
    out_dir.mkdir(parents=True, exist_ok=True)
    for path in sorted(in_dir.glob("*.in")):
        with open(path, encoding="utf-8") as fh:
            case = json.load(fh)
        forecast = forecast_case(case)
        text = json.dumps(forecast, separators=(",", ":")) + "\n"
        with open(out_dir / (path.stem + ".out"), "w", encoding="utf-8") as fh:
            fh.write(text)


if __name__ == "__main__":
    main()
