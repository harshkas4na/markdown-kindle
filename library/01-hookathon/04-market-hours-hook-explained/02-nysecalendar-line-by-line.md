# 02 — NYSECalendar.sol, Line by Line

Goal: read the entire calendar library and come out knowing *why* every line is there — including the two civil-date algorithms that look like black magic and aren't.

## The header and the philosophy

```solidity
library NYSECalendar {
    uint256 internal constant DAY = 86400;

    // ET is UTC-5 (EST) in winter, UTC-4 (EDT) in summer
    uint256 internal constant EST_OFFSET = 5 hours;
    uint256 internal constant EDT_OFFSET = 4 hours;

    // NYSE core session, in seconds after ET midnight
    uint256 internal constant OPEN_SECONDS = 9 hours + 30 minutes; // 09:30 ET
    uint256 internal constant CLOSE_SECONDS = 16 hours; // 16:00 ET
```

It's a `library` with only `internal pure` functions — meaning the compiler inlines everything into the hook; there is no deployed calendar contract, no external calls, no state. **Everything that never changes is computed; nothing here can be configured.** Holidays — the one thing that does change — deliberately live in the hook, not here.

`OPEN_SECONDS`/`CLOSE_SECONDS` are "seconds after midnight *in New York*". The whole library is one long exercise in converting a UTC `block.timestamp` into "what time is it in New York, and what day."

## `civilFromDays` — day number → (year, month, day)

```solidity
function civilFromDays(uint256 z) internal pure returns (uint256 year, uint256 month, uint256 day) {
    unchecked {
        uint256 zz = z + 719468;
        uint256 era = zz / 146097;
        uint256 doe = zz - era * 146097;
        uint256 yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
        uint256 y = yoe + era * 400;
        uint256 doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
        uint256 mp = (5 * doy + 2) / 153;
        day = doy - (153 * mp + 2) / 5 + 1;
        month = mp < 10 ? mp + 3 : mp - 9;
        year = month <= 2 ? y + 1 : y;
    }
}
```

This is Howard Hinnant's `civil_from_days`, the standard algorithm behind C++'s `<chrono>` calendar and countless datetime libraries. You don't need to re-derive it, but the constants stop being spooky once named:

- **`719468`** shifts the epoch from 1970-01-01 to 0000-03-01. Why March 1st of year 0? Because if you start the year in March, the leap day (Feb 29) becomes the *last* day of the year — every month's length becomes a fixed function of its position, and leap-year handling drops out of the month math entirely. This is the algorithm's one weird trick.
- **`146097`** = days in a 400-year Gregorian cycle (the calendar exactly repeats every 400 years: 97 leap years, 303 normal). An `era` is one such cycle; `doe` is the day-of-era.
- **`yoe`** (year-of-era) divides out 365-day years while correcting for the leap-day pattern: `doe/1460` subtracts one day per 4-year leap, `doe/36524` adds back the skipped century leaps, `doe/146096` re-subtracts the 400-year exception. Integer division makes all three corrections exact.
- **`mp = (5*doy + 2)/153`** is a tiny linear model of month lengths in the March-first calendar: the pattern 31,30,31,30,31... averages 30.6 days, and `153/5 = 30.6` exactly. Same trick inverted for `day`.
- The last two lines translate "month 0 = March" back into human months, bumping the year for Jan/Feb.

`unchecked` is safe: all values are bounded by the input day number, and we only ever pass day numbers between 1970 and a few centuries out.

## `daysFromCivil` — the exact inverse

```solidity
function daysFromCivil(uint256 y, uint256 m, uint256 d) internal pure returns (uint256) {
    unchecked {
        uint256 yy = m <= 2 ? y - 1 : y;
        uint256 era = yy / 400;
        uint256 yoe = yy - era * 400;
        uint256 doy = (153 * (m > 2 ? m - 3 : m + 9) + 2) / 5 + d - 1;
        uint256 doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
        return era * 146097 + doe - 719468;
    }
}
```

Same constants, run backwards. We need this direction for exactly one job: DST requires "the second Sunday of March of year Y", and to find it you must first compute the day number of March 1st. The test suite fuzzes `daysFromCivil(civilFromDays(day)) == day` across 200,000 days (through the year ~2517) — the two functions are exact inverses or the whole calendar is broken.

## `weekdayOfDay` — three tokens of genius

```solidity
function weekdayOfDay(uint256 dayNumber) internal pure returns (uint256) {
    return (dayNumber + 4) % 7;
}
```

1970-01-01 (day 0) was a Thursday. If Sunday = 0, Thursday = 4, so shifting by 4 makes the modulo line up: day 0 → 4 (Thursday ✓). Convention used everywhere in this codebase: **0 = Sunday … 6 = Saturday.**

## `isDST` — the one function encoding US law

```solidity
function isDST(uint256 ts) internal pure returns (bool) {
    (uint256 year,,) = civilFromDays(ts / DAY);

    uint256 mar1 = daysFromCivil(year, 3, 1);
    uint256 secondSundayMarch = mar1 + ((7 - weekdayOfDay(mar1)) % 7) + 7;
    uint256 dstStart = secondSundayMarch * DAY + 7 hours;

    uint256 nov1 = daysFromCivil(year, 11, 1);
    uint256 firstSundayNov = nov1 + ((7 - weekdayOfDay(nov1)) % 7);
    uint256 dstEnd = firstSundayNov * DAY + 6 hours;

    return ts >= dstStart && ts < dstEnd;
}
```

Piece by piece:

- **Finding "the first Sunday on or after day X":** `(7 - weekday(X)) % 7` is the number of days until the next Sunday (and 0 if X already is one). Add 7 more for the *second* Sunday.
- **Why `+ 7 hours` and `+ 6 hours`?** The law says the switch happens at *2am local time*. In March, local time is still EST (UTC-5) at the moment of switching, so 2am EST = **07:00 UTC**. In November, local time is still EDT (UTC-4) at the switch, so 2am EDT = **06:00 UTC**. Getting these two constants wrong by an hour is the classic DST bug — our tests check the exact minutes on both sides of both 2026 switchovers (07:59 UTC vs 07:01 UTC on March 8; 05:59 vs 06:01 on November 1).
- **The year-boundary question:** we derive `year` from the timestamp itself, so a January timestamp uses January's own year's March — correct, since January is never DST anyway.

## The ET conversion helpers

```solidity
function etOffset(uint256 ts) internal pure returns (uint256) {
    return isDST(ts) ? EDT_OFFSET : EST_OFFSET;
}

function etDayNumber(uint256 ts) internal pure returns (uint256) {
    return (ts - etOffset(ts)) / DAY;
}

function isWeekend(uint256 etDay) internal pure returns (bool) {
    uint256 w = weekdayOfDay(etDay);
    return w == 0 || w == 6;
}
```

`etDayNumber` is the concept the whole hook is keyed on: **"which calendar day is it in New York right now."** Subtracting the offset before dividing means a Friday 11pm ET moment (which is already Saturday 3am UTC) still counts as Friday — trading days are New York days, not UTC days. Everything downstream (holidays, weekends, epochs) uses ET day numbers.

## Session boundaries — and the one deliberate approximation

```solidity
function sessionOpen(uint256 etDay) internal pure returns (uint256) {
    // sample the DST rule at ~noon UTC of that day; the 2am switchover never
    // lands inside the 09:30-16:00 session, so this is exact for our purposes
    uint256 offset = etOffset(etDay * DAY + 12 hours + 4 hours);
    return etDay * DAY + OPEN_SECONDS + offset;
}

function sessionClose(uint256 etDay) internal pure returns (uint256) {
    uint256 offset = etOffset(etDay * DAY + 12 hours + 4 hours);
    return etDay * DAY + CLOSE_SECONDS + offset;
}
```

To convert "09:30 ET on ET-day D" into a UTC timestamp, we need the UTC offset *in effect that day* — but the offset function takes a UTC timestamp, and we're mid-construction of one. Chicken and egg. The resolution: evaluate the offset at a **probe timestamp** in the middle of that day (`etDay*DAY + 16h` UTC ≈ noon ET). Is the probe ever wrong? Only if the DST switch happened between the probe and the session — but the switch is always at 2am ET on a *Sunday*, when there is no session, and even on the switch day itself 2am is hours before 09:30. So the approximation is exact for every timestamp the hook will ever care about. The test `test_dstTransition_sessionShiftsWithTheClocks` proves the consequence: Friday March 6, 2026 opens at 14:30 UTC (EST), and Monday March 9 — the first trading day after the switch — opens at 13:30 UTC (EDT). Same wall clock in New York, different UTC instant, no configuration anywhere.

## What is *not* here, and why

No holidays (they're law + committee decisions, not math — the hook's owner sets them). No half-days (Christmas Eve closes at 1pm — a known v2 refinement; add `CLOSE_SECONDS` per-day overrides). No pre-market/after-hours sessions (the hook treats them as CLOSED, which is the conservative choice for LP protection).

## The one sentence to keep

**The calendar is ~105 lines of pure integer math: Hinnant's two civil-date algorithms make "second Sunday of March" computable, the `(dayNumber+4)%7` trick gives weekdays, the 07:00/06:00-UTC constants encode US DST law exactly, and the noon-probe approximation in `sessionOpen`/`sessionClose` is provably safe because America never switches its clocks during a trading session.**
