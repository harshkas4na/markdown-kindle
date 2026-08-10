# 10 — Algorithm: trip matching & search

The route-finder (article 09) answered "how do I get there?" This article answers the question the *whole product* is built around: **"who else is travelling roughly where I'm going, around when I'm going?"** That word "roughly" is the entire challenge — exact matching is easy and useless; *fuzzy* matching is hard and is the product.

The mental model:

**Trip matching is a *ranking* problem, not a *pathfinding* problem. We don't need the shortest route; we need to score every candidate trip by how well it matches the searcher's trip — on location, time, and direction — then sort by that score and show the best. It's a mini search engine.**

The code lives in `app/api/search/route.ts` (the orchestration) and `lib/matching.ts` (the scoring primitives). Let me build it the way it actually runs.

---

## The reusable trick — the station index (`lib/matching.ts`)

Both this article and article 09 lean on `sequenceIndex`. Here, matching precomputes a lookup so distance checks are instant:

```ts
function buildStationIndex() {
  const index: Record<string, { line, seqIndex }[]> = {};
  for (const s of allStations) {
    (index[s.name] ??= []).push({ line: s.line, seqIndex: s.sequenceIndex });
  }
  return index;
}
const stationIndex = buildStationIndex();  // built ONCE at module load
```

So `stationIndex["Rajiv Chowk"]` gives every (line, position) that station sits at. Then "how far apart are two stations?" becomes pure arithmetic — no graph traversal needed:

```ts
export function getMinStationDistance(s1, s2): number {
  // for every line they SHARE, distance = |seqIndex difference|; take the minimum
  // returns Infinity if they share no line
}
```

`|seqIndex1 - seqIndex2|` on a shared line = number of stops between them. Taking the **minimum across shared lines** handles interchange stations correctly (two stations might be close on one line, far on another — we want the best). This is the same `sequenceIndex` insight as the route-finder, but used for *proximity* instead of *pathfinding*. One clean data model, two algorithms.

---

## The matching dimensions

A "good match" is fuzzy along three axes, and `matching.ts` has a primitive for each:

1. **Location proximity** — `getMinStationDistance`. Are the start/end stations *near* each other? We allow `±3 stations` (the `NEARBY_STATION_THRESHOLD`). Your companion doesn't have to board at your exact station — 2 stops away is still "on your way."
2. **Time proximity** — `getTimeDiffMinutes`. Are you travelling around the same time? We allow `±45 minutes` (`TIME_WINDOW_MINUTES`). Converts `HH:MM` to total minutes and diffs them.
3. **Direction** — `isSameDirection`. *This is the subtle, brilliant one.* Two people can both use the same line at the same time but travel **opposite ways** — useless as companions. We detect direction by the *sign* of the `seqIndex` difference: if my `end.seq - start.seq` is positive and yours is too on a shared line, we're going the same way.

```ts
const searchDir = se2.seqIndex - se1.seqIndex;   // my direction on this line
const tripDir   = te2.seqIndex - te1.seqIndex;   // their direction
if ((searchDir > 0 && tripDir > 0) || (searchDir < 0 && tripDir < 0)) return true;
```

A subtle product decision lives here: if two trips share **no line at all** (different parts of the network), `isSameDirection` returns `true` — *optimistic*. The reasoning: we can't prove they're incompatible, so don't filter them out; let the distance score decide. But if they *do* share a line and all shared directions are opposite, return `false` and drop them. That "be strict when you have evidence, lenient when you don't" rule is a genuinely good ranking-system instinct.

---

## The pipeline in `app/api/search/route.ts`

Now the orchestration. It's the article-05 pipeline (auth → rate-limit → validate) and then the matching, wrapped in the article-04 cache. Here's the flow:

### 1. Fetch the candidate pool (one smart query)

We don't fetch *all* trips. We let Postgres pre-filter to plausible candidates:

```ts
.neq("user_id", user.id)                              // not my own trips
.or("status.eq.active,status.is.null")                // only active
.or(`travel_date.eq.${travelDate},
     and(is_repeating.eq.true,repeat_days.cs.{${dayOfWeek}})`)  // same date OR a repeating trip on this weekday
```

That last `.or` is doing real work: it matches both **one-off trips on the exact date** *and* **recurring trips** whose `repeat_days` array contains this day of the week (`cs` = "contains"). So a daily 9am commuter shows up in searches for any weekday. Pushing this filter into SQL means we score dozens of candidates, not thousands.

### 2. Score every candidate

For each candidate trip, compute the three dimensions and fold them into one **sort score**:

```ts
const startDist = getMinStationDistance(searchStart, trip.start_station);
const endDist   = getMinStationDistance(searchEnd,   trip.end_station);
const timeDiff  = getTimeDiffMinutes(searchTime, trip.travel_time);

const routeScore = (startDist === Infinity ? 100 : startDist)
                 + (endDist   === Infinity ? 100 : endDist);   // location penalty
const timeScore  = timeDiff * 0.15;                             // time penalty (down-weighted)
const sortScore  = routeScore + timeScore;                      // LOWER is better
```

The weighting is a product judgment worth noticing: **location dominates, time is scaled down by 0.15.** Translation: "being on my route matters much more than being at the exact same minute." A 30-min time gap adds only 4.5 to the score; being 5 stations off adds 5. Infinity distances are capped at 100 so an unrelated trip gets a huge-but-finite penalty rather than breaking the math. This is exactly how a real ranking function is tuned — by deciding what matters most and encoding it as weights.

### 3. Filter, then two-tier results

After scoring and the direction filter, results are split into two tiers — and *this* is a great UX pattern:

```ts
// PRIMARY: strict — on-route AND reasonable time
results = scored.filter(strictMatch).sort(byScore);

// FALLBACK: only if primary is empty, relax the thresholds
if (results.length === 0) {
  suggestions = scored.filter(relaxedMatch).sort(byScore).slice(0, 10);
}
```

So if there are good matches, you see only good matches. If there are *none*, instead of a cold empty screen you get "no exact matches, but here are some nearby-ish ones" (relaxed to `±6 stations` / `±90 min`). **Never show an empty result if you can show a helpful almost-match** — that's product empathy expressed as code.

### 4. Enrich and cache

A final batched query fetches accepted-joiner counts for all result trips at once (no N+1 — one `.in(tripIds)` query), and the whole thing is wrapped in `cached(cacheKey, 120, ...)` from article 04, so repeating a search within 2 minutes skips the query *and* the scoring entirely.

---

## Why this is in Node and not SQL (a real design question)

You *could* push some of this into SQL. We deliberately don't, and the reasoning is interview-worthy:

- The station-distance and direction logic depends on `sequenceIndex` data that lives in `metro-data.ts`, **not** the database (CLAUDE.md: don't store metro data in the DB). So the scoring *has* to happen in app code where that data is.
- The candidate pool is small (filtered by date/status/direction first), so scoring a few dozen trips in JS is microseconds.
- Keeping the fuzzy logic in TypeScript makes it testable and tweakable without DB migrations.

The principle: **let the database do the cheap, set-based filtering (date, status, ownership); let the app do the rich, domain-specific scoring.** Right tool for each half.

---

## Route-finder vs matcher — same data, opposite problems

A nice way to cement both algorithm articles:

| | Route-finder (09) | Trip matcher (10) |
|---|---|---|
| Question | "best path A→B?" | "who's going near where I'm going?" |
| Type | pathfinding (Dijkstra) | ranking / search |
| Output | one optimal route | sorted list of candidates |
| Uses `sequenceIndex` for | edge weights / interchanges | proximity & direction |
| Lives in | `lib/metro/graph.ts` | `lib/matching.ts` + search route |

Same underlying data model (`sequenceIndex`), two completely different algorithm families. That contrast is a great thing to be able to articulate.

---

## The interview angle

- *"Describe a ranking/matching system you built."* → "A travel-companion matcher. I score every candidate trip on three axes — station proximity, time difference, and travel direction — fold them into a single weighted score where location dominates time, sort ascending, and return a two-tier result: strict matches, or relaxed fallback suggestions if there are none. I cache the whole thing for two minutes keyed by the search params."
- *"How do you detect 'same direction'?"* → "Each station has a sequence index along its line. The sign of (end − start) is the direction; if two trips share a line and have the same sign, they're going the same way. If they share no line, I'm optimistic and let distance decide."
- *"Why score in app code, not SQL?"* → "The domain data (station sequences) isn't in the DB, the candidate set is pre-filtered small, and keeping fuzzy logic in code makes it testable. DB does set filtering, app does domain scoring."
- *"How do you avoid empty-result frustration?"* → "Two tiers — show strict matches if any exist, otherwise relax the thresholds and label them suggestions."

---

## Concept checklist

- [ ] I can explain matching as a ranking problem, distinct from pathfinding.
- [ ] I can explain the station index and why `|seqIndex diff|` gives station distance.
- [ ] I can explain all three dimensions (proximity, time, direction) and the direction sign trick.
- [ ] I can explain the weighted `sortScore` and why location is weighted above time.
- [ ] I can explain the candidate SQL pre-filter, including the repeating-trip `repeat_days` match.
- [ ] I can explain the two-tier strict/fallback result design and why it's good UX.
- [ ] I can justify scoring in app code vs SQL.
- [ ] I can contrast the route-finder and matcher as two algorithms over one data model.

Next up: **[11 — Performance & the production checklist](./11-performance-and-production.md)** — pulling every perf thread together.
