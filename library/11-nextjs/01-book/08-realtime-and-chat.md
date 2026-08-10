# 08 — Real-time & chat architecture

This is where it gets fun, because chat is the hardest thing in the app and the place where the most interesting engineering lives. Let me start with the realization that organizes everything:

**We have *two* separate realtime systems running side by side, and they exist for two different reasons. Knowing why there are two — instead of one — is the whole insight.**

1. **A raw WebSocket** to our own Node server (separate repo, on Render) → carries the *chat messages* themselves. Low-latency, high-frequency, bidirectional.
2. **Supabase Realtime** (a managed WebSocket to Postgres) → carries *notification events* (badge counts, "you got a message" pings). We don't run any server for this; Supabase pushes DB changes.

Why not one? Because they have different jobs. Chat needs a custom protocol (typing indicators, read receipts, reactions, optimistic acks) and high throughput — that's worth running our own socket server for. Notifications just need "the `notifications` table changed, refetch" — Supabase gives that for free. Using the right tool for each is the design, not laziness.

---

## System 1 — the singleton WebSocket (`lib/hooks/use-websocket.ts`)

The core problem a SPA has with WebSockets: **components mount and unmount constantly as you navigate, but you do NOT want to open/close a socket every time.** Opening a socket is expensive (handshake, auth), and our WS server is on Render's free tier which *cold-starts* (more on that horror below). So the connection must outlive any single component.

The solution is a **module-level singleton with reference counting**. This is genuinely senior-level code, so let me unpack the pattern:

```ts
// These live at MODULE scope — one set for the whole app, not per-component
let singletonWs: WebSocket | null = null;
let refCount = 0;                         // how many hooks currently want a connection
const handlers = new Set<MessageHandler>();
const messageQueue: object[] = [];        // messages sent while disconnected
```

Then the hook just *participates* in the singleton:

```ts
export function useWebSocket({ url, enabled }) {
  useEffect(() => {
    refCount++;                           // I want the connection
    if (enabled && (!singletonWs || closed)) connect();
    return () => {
      refCount--;                         // I no longer need it
      if (refCount === 0) teardown();     // last one out turns off the lights
    };
  }, [url, enabled]);
}
```

So if five components call `useWebSocket`, there's still **one** socket. The socket only tears down when the *last* consumer unmounts (`refCount === 0`). This is the **reference-counting pattern** — the same idea as smart pointers, or how a connection pool decides when to close. Beautiful, and worth being able to explain.

Other things this file gets right (each is an interview-grade concept):

- **`useSyncExternalStore`** to expose `isConnected` to React. This is the *correct* React 18+ way to subscribe a component to an external (non-React) data source — the WebSocket lives outside React's world, and this hook bridges it without tearing. (Most people would misuse `useState` + effects here and get stale reads.)
- **Exponential backoff reconnect:** `WS_RECONNECT_DELAYS = [1000, 2000, 4000, 8000, 16000, 30000]`. When the socket drops, it retries with growing delays instead of hammering the server. Capped at 30s.
- **A message queue with a max size:** messages sent while disconnected get queued (up to 100, dropping oldest), then *flushed on reconnect*. So you can hit send during a blip and it still goes out.
- **A heartbeat timeout:** if no message/pong arrives within 45s, it assumes a "zombie" connection and force-closes to trigger reconnect. (Detecting dead-but-not-closed sockets is a real distributed-systems problem.)
- **Token refresh handling:** it re-connects with a fresh token on Supabase `TOKEN_REFRESHED`, because the WS server authenticates via `?token=<jwt>` and an expired token would get rejected.

### The Render cold-start scar

Look at the retry logic in `use-ws-chat.ts`:

```ts
// 18 attempts × 10s = 180s — enough to survive Render's cold start (~2-3 min).
```

This is the single worst UX issue in the app, and it's *infrastructure*, not code: our WS server sleeps on Render's free tier, so the first message after idle can take **2–3 minutes** to deliver. The app's elaborate retry/queue machinery exists largely to *paper over* this. The real fix isn't more retry code — it's keeping the server warm (a paid tier, a health-check pinger, or rewriting it as a Go service on always-on infra). Good lesson: **sometimes the best code fix is an infra fix.**

---

## Optimistic chat — `use-ws-chat.ts`

Chat *feels* instant because we lie, carefully. This is optimistic UI taken to its logical end. When you hit send:

```
1. Create a temp message with a tempId, status "sending" → add to UI IMMEDIATELY
2. setSending(true)
3. Fire it over the WS
4. Server processes, persists to Supabase, broadcasts, and sends back an ACK
5. On "message_ack": swap tempId → realId, status → "sent"
6. If no ACK in 10s: retry (up to 18×). After that: status → "failed" (with a retry button)
```

The message exists on your screen the instant you press enter — the network round-trip happens *behind* that. The lifecycle of a message status is a little state machine:

```
sending ──ack──► sent ──read_receipt──► read
   │
   └──18 retries fail──► failed ──user taps retry──► sending
```

Other refined touches in here, each a real-time concept:

- **Cross-room bleed prevention:** when `roomId` changes, it clears messages immediately so the previous chat's messages don't flash in the new one.
- **Gap recovery:** on reconnect, it refetches messages newer than the latest one it has — so anything sent while you were disconnected gets filled in. (You can't trust a socket to never miss; you reconcile against the source of truth, the DB.)
- **Read receipts & typing:** throttled (`typing` at most every 2s) so you don't spam the socket on every keystroke.
- **Deduplication everywhere:** incoming messages are checked against existing ids before adding (`prev.some(m => m.id === newMsg.id)`), because the same message can arrive via both the WS broadcast *and* the gap-recovery fetch.

The deep principle: **the WebSocket is for *speed*, but Postgres is the *source of truth*.** The socket makes it feel live; the DB makes it correct. Every reconnect reconciles the fast-but-unreliable channel against the slow-but-authoritative one. That sentence is the whole architecture.

---

## System 2 — Supabase Realtime (`lib/hooks/use-notification-channel.ts`)

For notifications we don't run a server at all. Supabase Realtime lets us subscribe to Postgres changes over a managed WebSocket:

```ts
sharedChannel = supabase
  .channel(`notifications:${userId}`)
  .on("postgres_changes",
    { event: "*", schema: "public", table: "notifications", filter: `user_id=eq.${userId}` },
    () => { listeners.forEach((fn) => fn()); })   // tell hooks to revalidate
  .subscribe();
```

Notice it's the **same singleton + listener-set pattern** as the WebSocket — one shared channel per user, and both `useNotifications` and `useUnreadCount` subscribe to it. When a row in `notifications` for this user changes, Supabase pushes an event, and the listeners call SWR's `mutate()` to refetch (article 04's "push, don't poll").

The elegant connection: **`filter: user_id=eq.${userId}`** is enforced consistently with RLS — you can only subscribe to changes you're allowed to see. Realtime respects the same security model as queries (article 06).

---

## When to use which (the decision)

This is the part to actually remember:

| Need | Use | Why |
|---|---|---|
| High-frequency, bidirectional, custom protocol (chat, games, cursors) | **Own WebSocket server** | full control, low latency, custom message types |
| "A row changed, update the UI" (badges, live dashboards, presence) | **Supabase Realtime** | zero server to run, respects RLS, push-based |
| Occasional updates, simplicity matters | **Polling / SWR refresh** | no socket complexity at all |

We use the first two and deliberately avoid the third for these features. Picking per-feature is the skill — a junior reaches for one hammer; this codebase uses the right tool for each.

---

## The interview angle

- *"How do you keep a WebSocket alive across page navigations in a SPA?"* → "A module-level singleton with reference counting — components register/unregister via a hook, the socket only tears down when the last consumer unmounts. I expose its state to React with `useSyncExternalStore`, and handle reconnect with exponential backoff, a flush-on-reconnect queue, and a heartbeat to detect zombie connections."
- *"How does optimistic chat work?"* → "I render the message instantly with a temp id and 'sending' status, send over the socket, and reconcile on the server ACK by swapping in the real id. Retries with a cap, then a 'failed' state. The socket is for speed, Postgres is the source of truth — every reconnect refetches to fill gaps."
- *"WebSocket vs Supabase Realtime — when each?"* → "Own socket for high-frequency custom protocols like chat; Supabase Realtime for 'a DB row changed, revalidate' like notification badges — no server to run and it respects RLS."

---

## Concept checklist

- [ ] I can explain *why* we run two realtime systems and what each carries.
- [ ] I can implement a reference-counted singleton WebSocket and explain when it tears down.
- [ ] I know what `useSyncExternalStore` is for and why `useState` would be wrong here.
- [ ] I can explain backoff, the flush-on-reconnect queue, and the heartbeat/zombie-detection.
- [ ] I can draw the message status state machine (sending→sent→read, →failed→retry).
- [ ] I can explain "socket for speed, DB for truth" and how gap-recovery enforces it.
- [ ] I can explain the Render cold-start problem and why the fix is infra, not code.

Next up: **[09 — Algorithm: the metro route-finder](./09-algorithm-route-finder.md)** — modeling the network as a graph and running Dijkstra.
