# Tokens and the Tokeniser

**Fast overview:** Tokens are the currency of this entire industry — the unit of price, of context limits, of rate limits, and of most of the surprising bugs. This chapter explains what a token actually is, why the tokeniser is a compression algorithm rather than a linguistic one, and the handful of consequences that will show up in your own systems: why code costs more than prose, why numbers behave strangely, why a model cannot reliably count the letters in a word, and why the first thing to build in the lab repo is a token counter.

## What a tokeniser is doing

A tokeniser converts a string into a list of integers drawn from a fixed vocabulary. The dominant approach is **byte-pair encoding (BPE)**, and its logic is pure compression, not grammar.

Training a BPE tokeniser works like this. Start with a vocabulary of individual bytes. Count every adjacent pair in a large corpus. Merge the most frequent pair into a single new symbol. Repeat until the vocabulary reaches its target size — typically 50k to 200k entries. The result is a vocabulary where frequent sequences (`the`, ` and`, `tion`, ` function`) are single tokens and rare sequences are assembled from smaller pieces.

Notice what this implies. The tokeniser has no idea what a word is. It learned that ` the` is common in its training corpus. Text that looks nothing like that corpus — a language it saw little of, an unusual identifier, a base64 blob — fragments badly, because none of its pairs were frequent enough to earn a merge.

Modern tokenisers are **byte-level**: they operate on UTF-8 bytes rather than Unicode characters, which means there is no such thing as an unrepresentable string. A character outside the vocabulary simply becomes several byte tokens. Nothing breaks; it just gets expensive.

## The leading-space detail that bites people

In most BPE vocabularies, ` hello` (with a leading space) and `hello` (without) are **different tokens**. Whitespace is attached to the following word rather than being separate.

This produces a real class of bug. If you build a prompt by joining strings and accidentally double a space, or strip a leading space in a few-shot example, the tokenisation shifts and the model's behaviour can shift with it. It is also why few-shot examples should be formatted exactly as you expect the real input to be formatted.

## Why your JSON costs three times your prose

Here is the practical hierarchy, roughly, for the same underlying information:

| Content type | Approximate tokens per 1,000 characters |
|---|---|
| English prose | ~250 |
| Technical English with jargon | ~280 |
| Markdown with structure | ~300 |
| Source code | ~350 |
| JSON with verbose keys | ~400+ |
| Base64 / hashes / UUIDs | ~700+ |

The reason is merge frequency. `the` earned a merge. `"customer_lifetime_value":` did not; it becomes something like `"`, `customer`, `_`, `life`, `time`, `_`, `value`, `":`. Every quote, brace, colon and underscore is paying rent.

**The engineering consequences are immediate:**

- If you pass retrieved documents to a model as JSON because that is how they came out of the database, you are paying a large tax for no benefit. Convert to a compact text or markdown representation. Halving your context tokens halves the input half of your bill.
- Long UUIDs in a prompt are pure cost. Map them to short local identifiers (`doc_1`, `doc_2`) before they reach the model, and map back afterwards.
- The same applies in the other direction. Asking a model to emit verbose JSON costs output tokens, which are the expensive kind. If you only need three fields, ask for three fields.

## Why the model cannot count the r's in "strawberry"

The famous failure is not a reasoning failure; it is a representation failure. The model never sees letters. It sees something like `str`, `aw`, `berry` — three integers. Asking how many `r`s are in that is like asking you how many times the letter `e` appears in the ASCII codes 104, 101, 108. The information is technically recoverable and is not present in the form the question assumes.

The same root cause explains several other behaviours:

- **Arithmetic is unreliable** partly because numbers tokenise inconsistently. `1234` might be one token or `12` + `34` depending on the vocabulary, so digit-position arithmetic has no clean representation. This is why "use a calculator tool" is the correct architecture rather than a workaround.
- **Reversing a string, counting characters, and precise text surgery** are all weak for the same reason.
- **Rhyme and syllable tasks** are weaker than you would expect from a system this fluent.

The engineering rule that falls out: **any task defined at the character level should be done in code, not by the model.** This is a good instinct to demonstrate in an interview because it shows you know where the boundary is.

## Special tokens and the chat template

Beyond the vocabulary of text, models have **special tokens** that mark structure: beginning of sequence, end of turn, and role markers. When you send a chat request, the API assembles your messages into a single token sequence using a **chat template** — something conceptually like:

```
<|system|>You are a helpful assistant.<|end|>
<|user|>What is a token?<|end|>
<|assistant|>
```

Three things follow from this. First, the "roles" you send are ultimately just text with delimiters; the model's differing treatment of a system message is a learned behaviour from training, not a hard architectural separation. That is why prompt injection through a user message is possible at all (Book 05). Second, every message carries a few tokens of template overhead, so a long conversation of tiny messages is less efficient than it looks. Third, if you self-host, applying the wrong chat template for a model produces mysteriously degraded output while everything appears to work.

## Counting tokens properly

Do not estimate. Count. In Python, for OpenAI-family models:

```python
import tiktoken

enc = tiktoken.get_encoding("o200k_base")   # or encoding_for_model(...)
tokens = enc.encode(text)
print(len(tokens))
print([enc.decode([t]) for t in tokens[:40]])   # see the actual pieces
```

That second line is the one worth running on your own content. Watching your dossier fragment, and then watching a JSON version of the same content fragment twice as badly, converts this chapter from a fact into an intuition in about thirty seconds.

Other providers ship their own counters (Anthropic exposes a token-counting endpoint; open models ship a tokeniser with the weights via `transformers.AutoTokenizer`). **Counts are not portable between model families.** A 100k-token document for one model is not 100k for another. If you have a hard context budget, count with the tokeniser of the model you are actually calling.

For a rough sanity check when you cannot count: `chars / 4` for English, `chars / 3` for code. Use it for back-of-envelope only.

## Where token counting shows up in a real system

Four places, all of which you will build eventually:

1. **Context budgeting.** Before assembling a RAG prompt you need to know how many retrieved chunks fit. This means counting chunks at index time and storing the count as metadata, so assembly is arithmetic rather than a re-tokenisation of the whole corpus on every request.
2. **Truncation.** When something overflows, *what* gets dropped is a product decision, not a library default. Dropping the oldest conversation turns, dropping the lowest-ranked chunks, and summarising the middle are three different behaviours with three different failure modes.
3. **Cost attribution.** Per-request token counts, aggregated per feature and per customer, is the only way to answer "which feature is burning the budget" (Book 06).
4. **Rate limits.** Providers limit tokens per minute as well as requests per minute, and the token limit is usually the one you hit first. A client that only counts requests will be surprised.

## The lab exercise

An hour, and it earns two interview answers:

```python
# tokens.py — point it at your own files
import sys, tiktoken
enc = tiktoken.get_encoding("o200k_base")

PRICES = {  # $ per 1M tokens, input — check current numbers before quoting
    "small": 0.15, "mid": 3.00, "large": 15.00,
}

for path in sys.argv[1:]:
    text = open(path).read()
    n = len(enc.encode(text))
    print(f"{path:40s} {len(text):>8,} chars  {n:>7,} tokens  "
          f"{len(text)/n:.2f} chars/token")
    for tier, price in PRICES.items():
        print(f"    {tier:6s} ${n/1e6*price:.4f} per call as input")
```

Run it over a dossier, a resume, a Solidity file, and the same dossier converted to JSON. The chars-per-token column is the whole lesson, and the price column is the reason it matters.

*Connect the dot:* the chunk-size decisions in Book 02, Chapter 3 are token decisions wearing a different hat, and the prompt-caching strategy in Book 06 depends entirely on which tokens sit at the front of your prompt.

Next: what happens to those integers once they are inside the model.
