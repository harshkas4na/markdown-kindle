# Start Here

You already know how to win hackathons — seven times, $16K, and a job that came out of one. What you don't have is a way to know *which* hackathon deserves next week before you've already spent it. HackOps is that, compiled into software. It lives at `PROJECTS/Me/hack-ops`, and this manual is about operating it.

## The one idea underneath everything

JobOps and HackOps look like siblings and are built on opposite economics. Job hunting is high-volume and low-cost-per-unit: you apply to forty, you need one, and the machinery exists to make each application cheap. Hackathons invert that completely. You can hold **one serious build at a time**, each costs three to twenty days, and there is no version of this where volume saves you.

So the machinery sits almost entirely *before* the build decision. HackOps spends its effort on selection, and the value it returns is measured in **weeks it stopped you from wasting**, not in events it found. Finding hackathons is trivial — there are ninety-odd open right now across four sources, and the scout pulls them in eleven seconds.

Which means the system's default answer is **no**. A scoring run that recommends nothing is a successful run, not a broken one. The first live run graded the entire open field and told you to build nothing that week, and it was right.

## What you own vs what the system owns

The system owns the mechanical and research work: sweeping four APIs twice a day, computing expected value per *track*, reading the rules for the disqualifier buried on page three, mining past submissions for the gap nobody attacked, building the day-by-day plan, drafting the README and the demo script and the grant application. It also owns the tracking — deadlines, calendar, the alarm on your phone at three days out — which is the part you asked to stop carrying.

You own three things:

1. **The truth about you.** `profile/edge.md`, `prior-art.md`, `velocity.md`, `record.yaml`. Everything the scorer concludes traces back to these four files. Identity and the public record come from `../job-ops/profile/facts.yaml` — one source, no drift.
2. **The judgment.** Whether a score matches your gut, whether a week is worth it, and what you're willing to cut on day one. Chapter 2 maps the seven moments the system stops and waits.
3. **The outcomes.** What actually happened, losses included. Chapter 5 explains why that's the only food the learning loop eats.

## How to read this

Chapter 1 is the theory your own record proves — read it first, because every scoring decision descends from it and it corrects something you probably still believe. Chapter 2 is the operating rhythm. Chapter 3 walks one hackathon end to end. Chapter 4 covers what to build and how the gap-mining works. Chapter 5 is the learning loop and the automation that runs while your laptop is closed. Chapter 6 is the downstream layer — the chapter about where the money actually is, which is not the prize.
