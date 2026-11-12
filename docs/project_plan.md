# Dota 2 Patch Meta Tracker: Project Plan

## Goal

Build an end-to-end analytics pipeline that shows how each Dota 2 patch changes professional play: which heroes are picked, banned and win; how games are played; how heroes perform; and which items are bought.

Python pulls professional match data from the OpenDota API into DuckDB. dbt Core turns it into a tested star schema and reporting tables. GitHub Actions keeps it up to date.

Audience: hiring managers and interviewers reviewing the repository, and Dota fans who want to understand the pro meta.

---

## 1. Questions

| # | Question | Main output |
|---|---|---|
| Q1 | How do each hero's pick, ban and win rates change between patches? | `rpt_hero_patch_meta` |
| Q2 | How does gameplay change after a patch: game length, kills, objectives? | `rpt_patch_gameplay` |
| Q3 | How does each hero's performance change after a patch: GPM, kills, deaths, assists? | `rpt_hero_patch_performance` |
| Q4 | Which items are bought most, and when in the game are they bought? | `rpt_item_patch_popularity` |

Team-level and player-level questions are out of scope: sampling (section 2) leaves too few matches per team per patch for reliable results.

---

## 2. Scope and sampling

| Decision | Choice | Reason |
|---|---|---|
| History | Patches 56 (7.37, released 2024-08-01) to 60 (7.41, current): five complete patches, defined by patch ID | Enough patches to compare change over time; every patch is covered from its release |
| Match list | Every pro match since 2024-08-01, via `/proMatches` paging | Cheap: about 100 matches per call, so hundreds of calls in total |
| Match details (history) | A fixed random sample per patch (size decided after counting matches per patch) | Detail is one call per match; the full history would take weeks on the free limit |
| Match details (new matches) | Every match, collected daily | About 45 matches a day, well within the limit |
| Leagues | Premium and professional tiers; a test on the match detail's `league.tier` flags any other tier | All 100 listed matches were professional tier, so no filtering is needed before fetching details |

Sampling rules:
- Stratified by patch, so every patch gets the same number of matches regardless of how long it ran.
- Reproducible: fixed random seed; sampled match IDs stored in a table with patch and sampled date.
- Every rate in the reports shows the number of matches it is based on.
- The method and its effect on precision are documented in the README.

---

## 3. Data source: OpenDota API

Free, no API key required. Free tier: about 60 requests per minute and 2,000 per day.

| Endpoint | Returns | Used for |
|---|---|---|
| `/proMatches` | 100 most recent pro matches; page back with `less_than_match_id` | Listing all matches since 2024-08-01 |
| `/matches/{match_id}` | Full detail for one match | Match, players, picks/bans, items, objectives |
| `/constants/heroes` | Every hero (object keyed by hero ID) | Hero dimension |
| `/constants/patch` | Patch names, IDs and release dates | Patch dimension |
| `/constants/items` | Every item, object keyed by internal name; each record includes its numeric `id` | Item dimension |
| `/constants/item_ids` | Object keyed by item ID, mapping to internal name | Cross-check only |
| `/teams`, `/proPlayers` | Teams and players | Names only; not central to the questions |

The `/explorer` endpoint (SQL against OpenDota's database) is deliberately not used.

---

## 4. Exploration findings (Stage 3)

| Topic | Finding |
|---|---|
| File shapes | `pro_matches`, `teams`, `pro_players`, `patches`, `leagues` are lists: one row per record. `heroes` is an object keyed by hero ID and must be reshaped to one row per hero |
| Match detail | One row per match, with many nested lists (players, picks_bans, teamfights, objectives, pauses and more) |
| Volume | About 45 pro matches a day (two-day sample; varies with tournaments) |
| Patch | Match `patch` is a patch ID (e.g. 60), which maps to a name in `patches.json` (60 = 7.41, released 2026-03-24) |
| Picks and bans | 24 per match (10 picks, 14 bans; 5 picks and 7 bans per side); never NULL in the samples. `team` 0 = Radiant, 1 = Dire: confirmed by matching picked heroes to players' `isRadiant` (30 of 30) |
| Player names | `name` comes from OpenDota's pro player register; unregistered players have NULL `name` but have `account_id` and `personaname`. Use `account_id` as the key |
| Kills | In all 3 sampled matches: sum of player kills <= team score <= opposing team's deaths. Likely cause: score includes creep/tower kills; deaths include neutrals, Roshan, denies (unverified) |
| Kill log | `kills_log` count matched `kills` for every player except one in match 982 (logged 5, reported 4). Cause not yet identified (possibly reincarnation, a hero copy or a deny) |
| Sides | `isRadiant` on each player (also `team_number` and `player_slot`) |
| League tier | `leagues.json` has `tier`: premium, professional, amateur, excluded. All 100 sampled matches were professional |
| Timestamps | `start_time` is a Unix timestamp (UTC); model as a plain UTC timestamp named `start_at_utc` |
| Patches in scope | 56 (7.37, 2024-08-01) to 60 (7.41, 2026-03-24, current) |
| Parsing | All 10 sampled (recent) matches have `objectives` and `teamfights`; all players have a non-empty `purchase_log`. Coverage for older matches to be measured in Stage 5 |
| Objectives | Each event has time, type, key, player_slot and a slot for the victim |
| Items | Inventory (`item_0`-`item_5`, backpack slots, `item_neutral`) holds item IDs. `items.json` is keyed by internal name and each record has its `id`; `item_ids.json` maps ID to name |
| Purchase log | Each purchase has `time` (seconds; can be negative), `key` (internal item name, joins to `items.json` keys) and `charges` (populated for 16 of 4,643 sampled purchases, about 0.3%; kept as a nullable column in staging, and reporting decides whether to count purchases or units) |

### Still to check
1. Recheck the kills relationships and the `kills_log` mismatch once more match data is loaded; identify what caused the extra logged kill in match 982.
2. Parse coverage (objectives, purchase logs) across the full sample, especially older patches (Stage 5).
3. Does `/proMatches` paging reach back to 2024-08-01? (Stage 4.)

---

## 5. Architecture

```
OpenDota API
     |
     v
Python ingestion  ->  DuckDB raw schema (JSON responses + load metadata)
     |
     v
dbt Core:  staging (views)  ->  intermediate  ->  marts (tables)  ->  reporting (tables)
     |
     v
GitHub Actions: scheduled ingestion + dbt build
```

Raw layer principles:
- Store each API response unchanged, as JSON, with `_loaded_at`, the endpoint and the request parameters.
- No transformation during ingestion; all reshaping and unnesting happens in dbt staging.
- Keep every response, so the warehouse can be rebuilt without calling the API again.
- Only the nested data the questions need is modelled; the rest stays in raw.

---

## 6. Data model

### Raw (DuckDB schema `raw_opendota`)

| Table | Grain |
|---|---|
| `pro_matches` | One row per match per listing call |
| `match_details` | One row per match detail response |
| `heroes`, `patches`, `items` | One row per load (whole response as JSON) |
| `match_sample` | One row per sampled match: match ID, patch, sampled at, seed |

### Staging (views, `stg_opendota__*`)

| Model | Grain |
|---|---|
| `stg_opendota__pro_matches` | One row per match (deduplicated listing) |
| `stg_opendota__matches` | One row per match |
| `stg_opendota__match_players` | One row per player per match |
| `stg_opendota__match_picks_bans` | One row per pick or ban per match |
| `stg_opendota__match_objectives` | One row per objective event per match (if available) |
| `stg_opendota__player_final_items` | One row per item slot per player per match |
| `stg_opendota__player_purchases` | One row per purchase per player per match (if available) |
| `stg_opendota__heroes` | One row per hero |
| `stg_opendota__patches` | One row per patch |
| `stg_opendota__items` | One row per item |

### Dimensions

| Model | Grain | Notes |
|---|---|---|
| `dim_heroes` | One row per hero | |
| `dim_patches` | One row per patch | `valid_from` = release date, `valid_to` = next release (half-open), `is_current` |
| `dim_items` | One row per item | Name, cost, category |
| `dim_date` | One row per day | |

### Facts

| Model | Grain | Measures |
|---|---|---|
| `fct_matches` | One row per match | Duration, winner, total kills, patch, league ID, name and tier (from the match detail's `league` struct) |
| `fct_picks_bans` | One row per pick or ban | Hero, side, order, is_pick, won (for picks) |
| `fct_player_match_stats` | One row per player per match | Kills, deaths, assists, GPM, XPM, damage, net worth |
| `fct_player_final_items` | One row per item per player per match | Item, slot |
| `fct_item_purchases` | One row per purchase | Item, purchase time (seconds into the game) |
| `fct_match_objectives` | One row per objective event | Type, time, side |

### Reporting

| Model | Grain | Answers |
|---|---|---|
| `rpt_hero_patch_meta` | One row per hero per patch | Q1 |
| `rpt_patch_gameplay` | One row per patch | Q2 |
| `rpt_hero_patch_performance` | One row per hero per patch | Q3 |
| `rpt_item_patch_popularity` | One row per item per patch | Q4 |

### Fan-out risks
- Picks/bans and player stats both have many rows per match; join on match and hero, or aggregate first.
- Purchases are many per player; aggregate before joining to player stats.
- Match-level measures (duration) must not be summed from player-level or item-level tables.

---

## 7. Metric definitions

All metrics are per patch, over sampled matches in scope.

| Metric | Definition |
|---|---|
| Matches in patch | Distinct sampled matches whose patch is P |
| Pick rate | Matches where the hero was picked / matches in patch |
| Ban rate | Matches where the hero was banned / matches in patch |
| Contest rate | Matches where the hero was picked or banned / matches in patch |
| Win rate | Picks where the picking side won / picks |
| Average game length | Mean match duration in minutes |
| Kills per minute | Total kills / total match minutes, where total kills = radiant_score + dire_score (includes creep and tower kills; can exceed the sum of player kills) |
| Hero GPM, kills, deaths, assists | Mean per player-match on that hero |
| Item purchase rate | Player-matches that bought the item / player-matches |
| Typical purchase time | Median purchase time in minutes |
| Change vs previous patch | This patch's value minus the previous patch's |
| Minimum sample | Hero win rate and performance shown only with at least N picks (decision D3) |

---

## 8. Testing plan

| Layer | Tests |
|---|---|
| Sources | Freshness on `match_details._loaded_at`; not_null on IDs |
| Staging | unique + not_null on each grain key; composite uniqueness (match + player slot, match + pick order); accepted_values for side, is_pick, league tier (premium, professional; warn otherwise) |
| Facts | Grain uniqueness; relationships to every dimension; exactly 10 player rows per match, 5 per side; 24 picks/bans per match (warn if different); warn if player kills > team score or team score > opposing deaths; warn if a player's kills_log differs from kills by more than 1 |
| Dimensions | Patch windows have no gaps or overlaps; one current patch |
| Sample | Sampled matches per patch equal the target; every sampled match has detail loaded; warn if the share of parsed matches (objectives and purchase logs present) falls below a threshold |
| Reporting | Rates between 0 and 1; contest rate >= pick rate and >= ban rate; pick counts reconcile to `fct_picks_bans` |

---

## 9. Build order

Each stage on its own Git branch, merged with a pull request.

| Stage | Deliverable |
|---|---|
| 1 | Setup (done) |
| 2 | Project plan (done) |
| 3 | Explore the API: answer the open checks in section 4 (done) |
| 4 | Ingestion part 1: reference data (heroes, patches, items) and the full match list since 2024-08-01, with paging, into DuckDB raw |
| 5 | Ingestion part 2: count matches per patch, draw the sample, fetch match details (rate limiting, retries, resumable); daily collection of new matches |
| 6 | dbt sources and staging, including JSON unnesting, with tests |
| 7 | Dimensions |
| 8 | Facts |
| 9 | Reporting models |
| 10 | Incremental models |
| 11 | Automation with GitHub Actions |
| 12 | Documentation, README, dbt docs; optional dashboard; optional Snowflake target |

---

## 10. Decisions

| # | Decision | Status |
|---|---|---|
| D1 | History window | Patches 56-60 (7.37 to 7.41), i.e. since 2024-08-01 |
| D2 | Leagues | Premium and professional, with a test for others. `/leagues` dropped: tier comes from each match detail's `league` struct |
| D3 | Minimum picks for hero win rate and performance | Recommended 20; confirm after counting the sample |
| D4 | Sample size per patch | Decide after counting matches per patch |
| D5 | Dashboard | Decide at Stage 12 |
| D6 | Where the database lives for scheduled runs | Decide at Stage 11 |
| D7 | Player SCD Type 2 dimension | Deferred: not needed by the chosen questions |
