# Three Guards Against a Lie

**Fast overview:** The way a memory system does real damage is not by being empty. It is by confidently telling a session something that used to be true. This chapter is about the three checks that stand between a stored memory and a session that would believe it, all three of which run without a model.

## The failure that matters

A session records: *the tracker parser lives in `scripts/lib/deadlines.mjs`*. True when written. Two weeks later someone refactors and the parser moves.

Now the memory is a lie, and it is the most dangerous possible kind of lie: specific, plausible, and delivered with authority at the exact moment a session is deciding where to look. The session trusts it, goes to the wrong file, finds nothing, and concludes something is broken.

An empty memory store costs nothing. A confidently wrong one costs more than never having built it.

## Guard one: the anchor still exists

Every entry carries anchors, which are the files the claim is about. At read time, those files are stat'ed. If one is gone, the entry is demoted out of the digest.

This is the cheapest possible check and it catches the most common way a memory goes bad. It costs a syscall per anchor.

**The demoted entry is not deleted.** It moves to a `stale` list with the reason recorded, where it can be reviewed, confirmed if it is still true elsewhere, or refuted with a correction attached. This is a deliberate inheritance from the findings register in the same portfolio, where the standing rule is that a row which turned out to be false keeps its place, because the correction is more valuable than the absence.

## Guard two: drift

Every entry also records the repo's HEAD commit at the moment it was written. At read time, the system asks git whether the anchored files have changed since that commit.

If they have, the entry is **not** demoted. It stays live and renders with a `verify` flag. The distinction matters: a changed file does not mean the memory is wrong, it means the memory has not been checked since the thing it describes moved. Flagging it as wrong would be as much of an invention as flagging it as fine.

There is one edge worth stating. If the recorded commit is unreachable, because of a rebase, a garbage collection, or a shallow clone, git cannot answer. In that case the system emits **no flag at all** rather than a clean bill of health. Unknown is not the same as unchanged, and quietly reporting the second when the truth is the first is the exact class of invented certainty the whole portfolio bans.

This guard fired for real within an hour of being written. A decision recorded before its supporting document was committed showed up in the next digest carrying `verify`, because the anchored file had changed underneath it. Not a test. The system catching its own staleness on live data.

## Guard three: decay, with no manual pin

Confidence falls with age unless the memory is reconfirmed. Each kind has its own half-life, and the ordering is not arbitrary:

- **state** decays fastest, around a week. An open loop nobody has touched in three weeks is almost always abandoned work, and pointing a new session down an abandoned path is the way this kind of entry does harm.
- **artifact**, then **map**, then **pref**, then **decision** in the middle.
- **lesson** decays slowest, around a year. A fact about how a tool actually behaves stays true until the tool changes, and guard one catches that case directly.

An entry that falls below a freshness floor leaves the digest and joins the stale list, with the reason recorded as having faded rather than as having broken.

**There is deliberately no way to pin an entry fresh by hand.** This is borrowed verbatim from the log that already runs on this machine, whose own documentation says: status decays on its own, do not add a way to pin something active by hand. The reasoning is that a manual pin is a vote by whoever was most enthusiastic on the day, and it never gets un-cast. Reconfirmation by use is the only honest signal, because it costs something to produce.

## The correction path

When a memory is wrong, the fix is not deletion. It is `refute`, which requires a reason: the correction is the point of keeping the entry at all.

The entry leaves the live set, stops being served to sessions as something to believe, and stays fully readable with its correction attached and its full provenance intact: which sessions saw it, when it was first and last seen, and what was said about it since.

The best entries in a register like this are the ones that turned out to be wrong and say so. They are the only ones that teach anything about how the mistake was made.
