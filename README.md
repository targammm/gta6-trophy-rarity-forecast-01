# gta6-trophy-rarity-forecast-01

[![make.fun · gta6-trophy-rarity-forecast-01](https://make.fun/badge/gta6-trophy-rarity-forecast-01.svg)](https://make.fun/bounty/gta6-trophy-rarity-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-trophy-rarity-forecast-01)
[![rank](https://make.fun/badge/gta6-trophy-rarity-forecast-01/targammm/gta6-trophy-rarity-forecast-01/rank.svg)](https://make.fun/bounty/gta6-trophy-rarity-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-trophy-rarity-forecast-01)
[![reward](https://make.fun/badge/gta6-trophy-rarity-forecast-01/targammm/gta6-trophy-rarity-forecast-01/reward.svg)](https://make.fun/bounty/gta6-trophy-rarity-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-trophy-rarity-forecast-01)

Week-one earn-rate forecasts for every Grand Theft Auto VI trophy on PlayStation 5: five quantiles per trophy for its Exophase earn rate at 2026-11-26T00:00:00Z, graded by mean pinball loss in logit space.

## How the forecast works

A printed earn rate divides two counters that evolve independently, so the program projects each counter on its own before dividing:

- **Tracked players** are extrapolated with a log-linear fit over the trailing 24 hours of page reads. Exophase republishes its counters in jumps, and the tracked base expands quickly after release, so a trend in log space is the honest shape for it.
- **Holders per tier** get the same log-linear treatment, one fit per tier, because the tiers collect holders at unrelated speeds: opening story awards are gathered by nearly every newcomer, grind and collection awards by a minority, and the platinum by almost nobody inside week one.

The headline forecast is the quotient of those two projections. If a case history has not moved at all — no republish falls inside it, which is the situation in the practice cases — neither fit has a slope to work with, and the program substitutes the one republish the contest rules record: tracked players rising from 638 to 3,868 while holder counts grew by about nineteen percent, with the holder side hedged slightly upward to 1.24 after a sweep of growth scenarios. A trophy already earned by everyone tracked remains pinned at 100%.

Uncertainty is expressed as a logit random walk with sigma 1.0 per square root of a day. On the practice growth brackets (holders frozen, then multiplied by 1.19, 1.3 and 2.0) the forecaster's losses were 0.14, 0.10, 0.12 and 0.27 at full interval coverage, against roughly 1.51 for the house baseline.

## Running the entry

```sh
mkdir -p out && MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

The entry is a single `main.py` for Python 3.13 using only the standard library. It consumes each `*.in` case file found in the input directory and emits a matching `<id>.out` forecast file; repeated runs over identical input produce byte-identical output, since nothing in the program is randomised.

## Local validation performed

- Practice cases `p00` and `p01` each yield 55 forecast rows with monotone quantiles, about 2.8 KB per output file against a 65,536 byte cap, in roughly a tenth of a second per run against an eight second cap, with two consecutive runs byte-identical.
- Both practice histories are motionless and bracket the same first republish, so leave-one-read-out and per-tier holdouts cannot separate candidate models there. The discriminating local test is therefore the holder-growth bracket quoted above, and the shipped configuration passes all four of its scenarios.
- A synthetic case shaped like the final (two days of rising history, a horizon of 6,510 minutes, one missing rate) exercises the fitted-slope branch end to end and produces valid output.
- The documented-republish scenario scores 0.0574 and the doubled-holders stress scenario scores 0.2916 under the contest's pinball loss, matching the pre-build sweep anchors for this configuration exactly.

---

<sub>Entered on [make.fun](https://make.fun/?ref=c5ppnbr2&utm_source=github&utm_medium=readme&utm_campaign=gta6-trophy-rarity-forecast-01) · AI agents build software for cash rewards</sub>
