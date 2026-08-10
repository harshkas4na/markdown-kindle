# 09 — Algorithm: the metro route-finder

This is the article where the app stops being "CRUD + chat" and becomes a real computer-science problem. When a user asks "how do I get from Rajiv Chowk to Botanical Garden, fastest?", we run an actual graph algorithm. Let me build it from the ground up, because this is *the* interview algorithm and we have a real, production implementation of it sitting in `lib/metro/graph.ts`.

The mental model:

**The Delhi Metro is a graph. Stations are nodes, the track between two adjacent stations is an edge, and each edge has a weight (how long it takes, how far it is). "Find the best route" is just "find the shortest weighted path between two nodes" — which is exactly what Dijkstra's algorithm does.**

Once you see the metro *as a graph*, the whole thing becomes a textbook problem with a known answer. The art is in (a) building the graph correctly from messy real-world data, and (b) choosing the right weights.

---

## Step 1 — modeling the data (`lib/metro-data.ts`)

Before any algorithm, you need the graph. Our station data is hardcoded (CLAUDE.md: *"Do not fetch from DB — always use this file"*) and shaped like this:

```ts
interface MetroStation {
  name: string;
  line: MetroLine;          // an enum: Red, Yellow, Blue, Pink, ...14 lines
  sequenceIndex: number;    // position along its line (0,1,2,...) — THIS is the key
  isInterchange: boolean;
  interchangeLines?: MetroLine[];
}
```

The crucial field is **`sequenceIndex`** — a station's position along its line. Why it matters: two stations on the *same* line with sequence indices 4 and 9 are `|9 - 4| = 5` stations apart. That single integer lets us compute distances without any graph traversal, and it's the backbone of *both* this article (building edges) and article 10 (matching).

A station like Rajiv Chowk appears **multiple times** in `allStations` — once per line it sits on (it's a Blue/Yellow interchange). That's how interchanges are represented: the same station name, different `line` + `sequenceIndex` rows. Hold that thought, it's how line-changes get modeled.

---

## Step 2 — building the graph (`buildGraph()`)

Now turn that flat list into a graph: a `Map<stationName, GraphNode>` where each node knows its neighbors.

```ts
interface GraphNode {
  stationName: string;
  neighbors: { stationName, line, weightTime, weightDistance, weightStations, isNetworkTransfer? }[];
  lines: MetroLine[];
}
```

Three kinds of edges get added — and each represents a real-world thing:

**1. Adjacent stations on the same line.** Walk each line in order; connect station `i` to `i-1` and `i+1`, with the *real* travel time and distance between them (from `travel-times.ts` and `distances.ts`):

```ts
node.neighbors.push({
  stationName: stations[i + 1],
  line,
  weightTime: times[i] ?? 2.5,        // real minutes between these two stations
  weightDistance: distances[i] ?? 1.3, // real km
  weightStations: 1,
});
```

Note the fallbacks (`?? 2.5`, `?? 1.3`) — defensive coding for when real data is missing for a segment. This is the difference between a toy ("every edge = 1") and a real product (every edge is the actual measured time).

**2. Ring-line closure.** The Pink Line is a loop (`RING_LINES = [Pink]`). A normal line is a path (first ≠ last), but a ring's last station connects *back* to its first. So we add that closing edge manually — otherwise the algorithm would think you can't go "the short way around" the loop.

**3. Cross-network transfers.** Sometimes you walk between two physically-close stations on different *networks* (e.g. DMRC ↔ Noida Aqua Line). Those get edges with a penalty:

```ts
const NETWORK_TRANSFER_PENALTY_TIME = 12;     // minutes for the walk + wait
const NETWORK_TRANSFER_PENALTY_DISTANCE = 0.5; // km
// weightStations: 0  ← a transfer doesn't count as "a station travelled"
```

That `weightStations: 0` is a lovely detail: a transfer is a connection, not a ride, so it adds time but not a station to the count.

**The graph is memoized** (`let _graph = null; if (!_graph) _graph = buildGraph()`) — built once on first use and reused for every search. Building it is expensive (hundreds of stations); doing it per-request would be wasteful. (Same lazy-singleton instinct as the WebSocket and the rate-limiter.)

---

## Step 3 — Dijkstra (`runDijkstra`)

Now the famous part. Dijkstra finds the shortest path from a start node to all others by **always expanding the cheapest-known frontier first.** The intuition:

**Imagine pouring water into the start station. It spreads outward, always filling the nearest unfilled station next. The moment water reaches the destination, you've found the shortest path — because water always took the cheapest route available.**

That "always pick the cheapest next" is why we need a **priority queue (min-heap)**. We hand-rolled one (`class MinHeap`) instead of pulling a library — `push` bubbles up, `pop` returns the minimum and sinks down, both `O(log n)`. (Worth being able to explain a binary heap: it's an array where node `i`'s children are `2i+1` and `2i+2`, and the parent is always ≤ its children.)

The core loop, annotated:

```ts
const dist = new Map();   // best known cost to reach each state
const prev = new Map();   // how we got there (for reconstructing the path)
const pq = new MinHeap();
pq.push(startState, 0);

while (pq.size > 0) {
  const { state: current, cost } = pq.pop()!;        // cheapest frontier node
  if (cost > dist.get(key)) continue;                 // stale entry, skip
  if (current.station === endName) { found = current; break; }  // done!

  for (const neighbor of node.neighbors) {
    const newCost = cost + edgeCost;                  // cost to reach neighbor via current
    if (newCost < (dist.get(nextKey) ?? Infinity)) {  // found a cheaper way?
      dist.set(nextKey, newCost);                     // record it
      prev.set(nextKey, { state: current, ... });     // remember the path
      pq.push(nextState, newCost);                    // explore from here later
    }
  }
}
```

This is **relaxation**: for each neighbor, "is going through me cheaper than your current best? If so, update you." Repeat, always from the cheapest frontier, until you pop the destination.

Two implementation details that are interview catnip:

- **The "stale entry" skip** (`if (cost > dist.get(key)) continue`). Because we never decrease-key in the heap (we just push duplicates with lower costs), the heap can contain outdated entries. When we pop one whose cost is worse than the best we already recorded, we skip it. This is the standard "lazy deletion" trick that lets you use a simple heap.
- **The `State` is `{ station, line }`, not just `station`.** This is the clever part. Why track the line you're *on*? Because changing lines has a cost (you have to walk to another platform and wait). By making the state include which line you arrived on, the algorithm can charge an **interchange penalty** when an edge switches lines:

```ts
const lineChanges = current.line !== null && current.line !== neighbor.line;
if (mode === "fastest" && lineChanges && !neighbor.isNetworkTransfer) {
  edgeCost += getInterchangeTime(current.station, current.line, neighbor.line);
}
```

So our Dijkstra isn't on a plain station-graph; it's on a **station-×-line state graph**, which correctly models the real cost of switching lines. That's the jump from "textbook Dijkstra" to "models reality."

---

## Step 4 — three modes from one algorithm

The slickest design choice: the *same* Dijkstra runs three ways, just by **changing what `edgeCost` means**:

```ts
if (mode === "fastest") {
  edgeCost = neighbor.weightTime;                 // minimize minutes
  if (lineChanges) edgeCost += getInterchangeTime(...);  // + real interchange time
} else if (mode === "cheapest") {
  edgeCost = neighbor.weightDistance;             // minimize km (fare ∝ distance)
  if (lineChanges) edgeCost += 0.2;               // tiny nudge against pointless changes
} else { // minimum-interchange
  edgeCost = neighbor.weightTime * 0.01;          // time only as a tiebreaker
  if (lineChanges) edgeCost += 100;               // HUGE penalty per line change
}
```

This is the lesson: **the algorithm is fixed; the *cost function* encodes the goal.** Want fewest interchanges? Make a line change cost 100 (so the algorithm avoids them almost at all costs) and let time be a whisper-thin tiebreaker. Want cheapest? Minimize distance because fare is distance-based. One algorithm, three products. `findRoutes()` runs all three and dedupes identical results (if fastest == cheapest, don't show it twice).

---

## Step 5 — reconstructing the path

Dijkstra found the *cost* and left a trail of `prev` pointers. To get the actual route, walk backwards from the destination through `prev` until you reach the start, then reverse:

```ts
let cursor = found;
while (cursor) {
  const edge = prev.get(stateKey(cursor));
  if (edge) { path.unshift({ station: cursor.station, line: edge.edgeLine, ... }); cursor = edge.state; }
  else { /* reached the start */ cursor = null; }
}
```

Then a second pass over `path` builds the human-friendly output: the `segments`, the `lineChanges` (where to switch and from/to which line), the running totals (`totalTravelTimeMinutes`, `totalDistanceKm`), and whether a cross-network walk is involved. *That's* what the UI shows as turn-by-turn directions.

---

## Complexity (have this ready)

- **Time:** `O((V + E) log V)` where V = states (stations × lines), E = edges. The `log V` is the heap operations.
- **Space:** `O(V)` for the `dist`, `prev`, and heap.
- Building the graph is a one-time `O(V + E)`, amortized to ~zero thanks to memoization.

And a classic follow-up: *"why Dijkstra and not BFS?"* → BFS finds the path with the fewest *edges*, which is only "shortest" if every edge has equal weight. Our edges have real, different weights (a 1-minute hop vs a 12-minute transfer), so we need Dijkstra. *"Why not A\*?"* → A\* is Dijkstra + a heuristic (e.g. straight-line distance) to explore fewer nodes; for a network this small (~300 stations) plain Dijkstra is instant, so the heuristic isn't worth the complexity. Knowing *when each applies* is the senior answer.

---

## The interview angle

- *"Tell me about a non-trivial algorithm you've shipped."* → "A metro route-finder. I model the network as a weighted graph — stations as nodes, track segments as edges weighted by real travel time and distance — and run Dijkstra with a hand-rolled min-heap. The interesting part: my state is (station, line), not just station, so I can charge an interchange penalty when an edge switches lines. And I get fastest/cheapest/fewest-interchanges from one algorithm just by swapping the cost function."
- *"Dijkstra vs BFS vs A\*?"* → "BFS for unweighted, Dijkstra for weighted non-negative edges, A\* when you have a good distance heuristic and a big graph. Mine has weighted edges and is small, so Dijkstra."
- *"Why a priority queue?"* → "To always expand the cheapest frontier node next in `O(log n)`; without it you'd scan all frontier nodes each step, making it `O(V²)`."

---

## Concept checklist

- [ ] I can explain "the metro is a weighted graph" and what nodes/edges/weights map to.
- [ ] I can explain the role of `sequenceIndex` and how interchanges are modeled (same name, multiple rows).
- [ ] I can describe the three edge types (adjacent, ring closure, network transfer) and `weightStations: 0`.
- [ ] I can explain Dijkstra with the "spreading water" intuition and the relaxation step.
- [ ] I understand the `(station, line)` state trick and why it enables interchange penalties.
- [ ] I can explain how one algorithm yields three modes via the cost function.
- [ ] I can explain the lazy-deletion "stale entry skip" and a binary min-heap's layout.
- [ ] I can state the time/space complexity and justify Dijkstra over BFS/A\*.

Next up: **[10 — Algorithm: trip matching & search](./10-algorithm-trip-matching.md)** — finding travel companions with fuzzy scoring.
