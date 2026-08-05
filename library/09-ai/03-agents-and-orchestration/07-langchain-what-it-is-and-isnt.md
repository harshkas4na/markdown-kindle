# LangChain: What It Is and Isn't

**Fast overview:** Eight of forty-four dossiers name LangChain or its relatives, and it is already on the resume from two projects. That makes this a chapter about having a defensible opinion rather than a tutorial — the version of the framework you learned has probably changed, and the useful thing is understanding what layer of the problem it addresses, what it costs, and how to answer "why did you use it" with reasoning instead of habit.

## What it actually is

LangChain is three separable things, and most confusion about it comes from treating them as one:

1. **A set of integrations.** Loaders for a hundred document sources, clients for every model provider, adapters for every vector store. This is the part that is genuinely tedious to write yourself and the part that ages fastest.
2. **A composition abstraction.** LCEL, the expression language, lets you pipe components together with `|` and get streaming, batching and async for free across the chain. This is the intellectually interesting part.
3. **A set of prebuilt patterns.** Retrieval chains, agents, memory implementations, output parsers.

Plus the surrounding ecosystem: **LangGraph** for stateful graphs (Chapter 8) and **LangSmith** for tracing and evaluation (Book 06).

## The composition idea

The core abstraction is the Runnable: anything with `invoke`, `batch`, `stream` and their async equivalents. Because everything implements the same interface, everything composes:

```python
chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | prompt
    | model
    | StrOutputParser()
)
chain.invoke("What is the refund window?")
```

The genuine benefit is that you write the chain once and get streaming, batching, async, and retry/fallback behaviour across the whole pipeline without writing any of it. That is real leverage, and it is the strongest technical argument for the framework.

The cost is that the pipeline becomes a data structure rather than code you can read top to bottom. When retrieval quality is bad, you want to see what came back, in what order, with what scores, and how it was rendered into the prompt. An abstraction that makes that require a debugger or a tracing tool is expensive exactly when you need it most.

## The honest criticism

Worth being able to articulate, because saying only good things about a widely-criticised framework reads as inexperience:

- **Abstraction over shallow operations.** A significant share of what the framework wraps is a dozen lines you would rather own. `PromptTemplate` is `str.format` with extra steps.
- **Debuggability.** Errors surface from several layers down with stack traces that describe the framework's internals rather than your logic.
- **Churn.** The API has changed substantially several times. Code and tutorials go stale fast, which is a real cost in a small team.
- **Leaky provider differences.** The abstraction over providers is thinnest exactly where they differ most: tool-calling formats, structured-output modes, caching semantics. Those are the details you care about.
- **It makes bad architectures easy.** A prebuilt agent in four lines is attractive and encourages skipping every question in Chapters 3 and 4.

And the honest defence:

- **Prototyping speed is real.** Getting to a working pipeline in an afternoon has genuine value when you are still deciding what to build.
- **The integration catalogue is large** and each item is a day you did not spend.
- **LangGraph is a different quality of thing** from the original chain abstractions, and deserves separate judgement (next chapter).
- **The ecosystem effect matters** at a company: shared vocabulary, shared tracing, people who already know it.

## The position to hold

**Own your orchestration; borrow your integrations.**

Concretely: write the agent loop, the retrieval pipeline and the prompt assembly yourself, where you can print every intermediate value. Use libraries for parsers, tokenisers, vector clients, rerankers and provider SDKs. Keep a thin adapter over providers so a fallback is a config change.

For a small team this loses very little — the orchestration is a few hundred lines — and it keeps the debugging path short, which is where the time actually goes once you have users.

**And hold it lightly.** If a company already runs LangChain across their stack, arguing to rip it out in week one is the wrong instinct and a bad interview answer. The right instinct is to understand what it is doing and be able to drop below it when a specific problem demands it.

## Answering "why did you use LangChain?"

The resume says LangChain in two projects. The question will come. A weak answer is "it's the standard". A strong answer is specific about what it bought and where it stopped:

> On REACTOR it was the fastest way to get a retrieval and prompt-chaining pipeline working while the actual product question was still open, and the integration surface meant I was not writing a vector store client and a document loader before I knew whether the feature was worth building. Where it stopped helping was diagnosis. When the pipeline started failing under concurrent load, what I wanted was to see each stage's input, output and timing, and that was harder through the abstraction than it should have been. If I built it again I would keep the orchestration in my own code and use the library for the parts that are genuinely commoditised.

That answer is honest, it names a real limitation from real use, and it converts a resume line into a judgement. It is also true, which matters more.

## The comparison landscape

Enough to hold a conversation:

| Tool | What it is for |
|---|---|
| **LangChain** | General LLM app composition, huge integration surface |
| **LangGraph** | Stateful, cyclic agent graphs with checkpointing (Chapter 8) |
| **LlamaIndex** | RAG-first: ingestion, indexing, query engines. Stronger on the retrieval pipeline specifically |
| **Provider SDKs + your own code** | Full control, no abstraction tax, more code to own |
| **Pydantic AI / Instructor-style** | Typed, structured-output-first agents. Lighter, more opinionated about types |
| **DSPy** | Programs over prompts: define signatures and metrics, optimise the prompts automatically. Only useful if you have a metric, which is the point |
| **Vendor agent SDKs** | Provider-specific agent loops. Simple, and you are on one provider |

The one worth knowing about beyond the obvious is **DSPy**, because its premise is the thesis of this whole shelf: if you have an eval metric, prompt engineering becomes an optimisation problem, and if you do not, no framework helps you.

## What to actually be able to do

For an interview at a company using LangChain, the useful preparation is not memorising the current API. It is:

1. **Explain what a Runnable is** and why uniform interfaces give you streaming and batching for free.
2. **Explain LCEL's pipe composition** and what it saves you writing.
3. **Name two things you would not use it for**, with reasons.
4. **Explain the LangChain/LangGraph/LangSmith split** — many people using it cannot.
5. **Have written the loop by hand**, so you can say what the framework is doing underneath.

Point 5 is the differentiator, and it is Chapter 2, which is why that chapter came first.

*Connect the dot:* the `x-ops` decision to demote a regex scorer from a gate to a ranking signal, after measuring that 12 posts produced 0 passes, is the same species of judgement this chapter asks for: use the tool where it measurably helps, and refuse to let it make decisions it is not good enough to make.

Next: LangGraph, which deserves more credit than the framework it grew out of.
