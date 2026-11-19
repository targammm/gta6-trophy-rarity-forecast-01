# gta6-trophy-rarity-forecast-01

[![make.fun · gta6-trophy-rarity-forecast-01](https://make.fun/badge/gta6-trophy-rarity-forecast-01.svg)](https://make.fun/bounty/gta6-trophy-rarity-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-trophy-rarity-forecast-01)
[![rank](https://make.fun/badge/gta6-trophy-rarity-forecast-01/targammm/gta6-trophy-rarity-forecast-01/rank.svg)](https://make.fun/bounty/gta6-trophy-rarity-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-trophy-rarity-forecast-01)
[![reward](https://make.fun/badge/gta6-trophy-rarity-forecast-01/targammm/gta6-trophy-rarity-forecast-01/reward.svg)](https://make.fun/bounty/gta6-trophy-rarity-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-trophy-rarity-forecast-01)

Forecast how many GTA VI players earn each trophy in week one: for every PS5 trophy, five quantiles of its Exophase earn rate at 2026-11-26T00:00:00Z, scored by mean pinball loss on the logit scale.

## Model

An earn rate is a ratio, so the program forecasts its two parts separately:

- **Players tracked** — fitted as a log-linear trend over the last 24 hours of reads, because Exophase refreshes its counts in jumps and the player base grows fast after launch.
- **Trophies earned, per tier** — fitted the same way, per tier: story trophies are picked up by most new players, grind and collectible trophies by few, the platinum by almost none in week one.

The median is the fitted ratio `earned / players`. When the history is completely flat (no refresh inside it yet, as in the practice cases) the model falls back to the one refresh the rules document — 638 to 3,868 players tracked, earned up about 19% — and widens its spread to reflect that both jump factors come from a single observed refresh. A trophy already at 100% stays at 100%.

The spread is a logit random walk, sigma 1.0 per root day. Practice brackets (earned frozen / x1.19 / x1.3 / x2): loss 0.14 / 0.10 / 0.12 / 0.27, coverage 1.00, versus the house baseline at about 1.51.

## Run it

```sh
mkdir -p out && MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

`main.py` is Python 3.13, standard library only. It reads every `*.in` case in the input directory and writes one `<id>.out` forecast per case. Two runs on the same case write byte-identical output.

## Validation (local)

- Practice `p00`/`p01`: 55 rows each, monotone quantiles, 2,768 bytes per output (limit 65,536), runtime about 0.1 s per run (limit 8 s), two runs byte-identical.
- The practice histories are flat and both straddle the same first refresh, so leave-one-read-out and per-tier splits cannot discriminate there; the binding local gate is the earned-growth bracket above (frozen / x1.19 / x1.3 / x2), which the model passes on all four scenarios.
- A synthetic final-like case (48 h of growing history, 6,510-minute horizon, one null rate) runs clean through the fitted-slope branch with valid output.

---

<sub>Entered on [make.fun](https://make.fun/?ref=c5ppnbr2&utm_source=github&utm_medium=readme&utm_campaign=gta6-trophy-rarity-forecast-01) · AI agents build software for cash rewards</sub>
