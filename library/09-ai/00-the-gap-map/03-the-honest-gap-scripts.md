# The Honest-Gap Scripts

**Fast overview:** There are maybe eight questions in an AI interview where the true answer is "I have not done that." Improvising those eight answers under pressure is how good candidates talk themselves into sounding either dishonest or apologetic. This chapter writes them once, in the shape `learnings.md` already proved works: **name the gap in the first line, then spend the rest of the answer on what you would do about it.** Learn the shape, not the wording.

## Why the shape works, with evidence

The JobOps repo has already run this experiment. From `learnings.md`: naming the AWS gap openly in Certa's application, then re-framing it, worked well enough to become a rule — "name the gap in the first line before the reader finds it in the resume, then spend the rest on the adjacent thing that is real."

The mechanism is simple. An interviewer is not testing whether you have done everything on the list; nobody has. They are testing **calibration** — whether your confidence tracks your evidence. A candidate who says "yeah, I've done some fine-tuning" and then cannot name a learning rate has failed the calibration test, and everything else they said is now suspect. A candidate who says "no, and here is exactly where my knowledge of it ends" has passed it, and everything else they said just got more credible.

So the gap answers are not damage control. They are the highest-yield answers in the interview, because they are the only ones that make the *other* answers believable.

## The shape

Three moves, in this order:

1. **The flat no**, in one short sentence. No hedging, no "well, sort of".
2. **The nearest real thing**, with a number or an artifact in it.
3. **The move**, meaning what you would actually do in week one if handed the problem. This is where you spend most of the words, and it is the part that proves you understand the problem even without having solved it.

Never add a fourth move. "But I learn fast" undoes the first three.

## The eight scripts

### 1. "Have you built eval harnesses in production?"

> No. My LLM work has been shipping the pipeline, not measuring it, and that is the specific gap I have been closing. The closest real thing: my job pipeline had a keyword matcher that scored the word "storage" as a hit for "RAG" because it used a substring test, and it survived 178 leads before I caught it. The reason it survived is that every test I had written was a positive case, and every positive case still passed. The fix was a test asserting that a known-bad pair does not match.
>
> If I owned evals here, week one is a golden set, not a framework. Fifty to a hundred real inputs with expected outputs, labelled by whoever in the company is the actual authority on what right looks like. Then a regression run on every prompt and model change with a hard gate on the aggregate, and per-slice reporting so a change that improves the average while destroying one category is visible instead of invisible.

### 2. "Have you fine-tuned a model?"

> No. Not LoRA, not QLoRA, not full fine-tuning, and I have never run distributed inference.
>
> What I know is where the decision line sits. Fine-tuning buys you format, tone and a narrow task the base model keeps getting subtly wrong, and it does not buy you facts, because facts go stale and retrieval is how you keep them fresh. So for most product problems I would exhaust retrieval and prompt structure first and treat a fine-tune as the thing you do when you have an eval set that proves the ceiling is real and you can name what the base model is failing at.

### 3. "How much production Python do you have?"

> One service. Hashtro's ephemeris service is FastAPI in production, and everything else I have shipped is TypeScript. So my Python is real but it is one service deep, not five years deep.
>
> The part that transfers is the systems half: that service had per-IP rate limiting and TTL caching in front of it and ran alongside two other services. What I have been deliberately closing is the idiom gap, because being fluent in async, pydantic and the typing story is the difference between writing TypeScript with colons and writing Python.

### 4. "Have you trained or evaluated a ranking or classification model?"

> No. I have never trained, evaluated or shipped a scoring, ranking or classification model. My LLM work is retrieval, prompt chaining and vector stores. That is consuming models, not building them.
>
> What I would do first on a ranking problem is build the evaluation set before touching the model. A few hundred examples with known correct labels, then measure the current system's precision at k and recall against it, so that any change after that has a number attached instead of a vibe.

### 5. "What's your experience with agent frameworks? LangGraph, MCP?"

Careful with this one, because it is the closest to overclaiming. The truth is LangChain in two projects, and LangGraph and MCP as reading rather than shipping.

> LangChain in two shipped projects, for retrieval and prompt chaining. LangGraph I have read and built with, not shipped. MCP the same.
>
> Where I actually have production reps is the pattern underneath both, which is an agent taking a real action with a bounded blast radius. rc-agents is an agent paying $0.30 in USDC over x402 for an on-chain service with no human in the loop, and my job pipeline is an agent system where the human gate is architectural: nothing is ever sent or submitted automatically, and the constraint is enforced outside the model rather than requested inside the prompt.

### 6. "Have you worked with real-time voice or streaming audio?"

> No. No production real-time work and no voice stack.
>
> The part of that problem I do understand is the latency budget, because a voice agent is a p95 problem before it is an AI problem. If the whole turn has to land under a threshold, every component gets an allowance and you design retrieval and tool calls against that allowance rather than adding them and hoping.

### 7. "How deep is your ML background?"

> I am an engineer who builds systems around models, not someone who trains them. My degree is electronics and communication, not CS or ML, and I have no publications and no research background.
>
> The reason I think that is the right fit for this seat rather than a shortfall is that everything hard I have shipped has been a reliability problem: contracts that cannot be hotfixed after deploy, an AI pipeline moving real money that I pulled when I could not make it safe. That is the half of AI engineering that is currently unowned at most companies.

Use this one only if the seat is genuinely an engineering seat. If the JD wants research, per the EON and Ramain dossiers, the correct move is not a script; it is not applying to that particular role.

### 8. "Tell me about an AI system you built that failed."

Not a gap question, but it lives here because it is the same muscle and it is the strongest answer available.

> REACTOR. It was a conversational pipeline that turned natural language into deployed on-chain automations, and it worked in testing and under early use. Under real concurrent load it started failing in ways I could not bound, and it was sitting in front of contracts holding user funds.
>
> I removed the feature. Not hardened, removed. I had a $9,000 grant tied to that product and the conversational layer was the demo everybody remembered, and it was still the right call, because a flaky pipeline in front of money is worse than no pipeline.
>
> What I would do differently is entirely on the measurement side. I diagnosed it by reasoning rather than by instrumentation. There was no per-stage latency breakdown, no retrieval quality number, no load test that reproduced the concurrency. If I hit that today the first artifact would be a trace per request with timings per stage, so that "it breaks at scale" becomes a specific component and a specific number.

## The three rules behind all eight

1. **Never soften a no into a maybe.** "I've touched it a bit" is the worst available answer: it fails the calibration test and it invites the follow-up question you cannot answer.
2. **Every gap answer carries one checkable artifact.** A repo, a number, a named failure. This is the same rule the outreach skills already run under, and it works for the same reason.
3. **The move is the answer.** Whether you have done the thing is one bit of information. How you would approach it is the entire interview.

*Connect the dot:* every "the move" paragraph above is a compressed version of a chapter later on this shelf. Script 1 is Book 04, Chapter 2. Script 2 is Book 07's fine-tuning chapter. Script 6 is Book 06 on latency budgets. As the reading moves the line, the scripts get shorter, because more of them becomes "yes, here is what I found".

Next: the order to read the rest of the shelf in, and how long each part should take.
