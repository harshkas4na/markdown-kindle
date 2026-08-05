# The Question Bank

**Fast overview:** Reading with a question in mind produces retention that reading passively does not. This is the list of questions the rest of the shelf answers, grouped by book, drawn from what the dossiers say these companies care about. Use it two ways: skim it before starting a book so the reading has a target, and use it as a self-test afterwards — out loud, no notes, because the failure mode is recognising an answer rather than being able to produce one.

A question you can answer in two sentences with a number in it is done. A question that produces "something about chunking" is not.

## Book 01 — LLM Foundations

1. What is a token, and why is your English text roughly 1.3 tokens per word while your JSON is much worse?
2. Why does the same prompt at temperature 0 sometimes produce different outputs?
3. What actually happens to cost and latency when the context doubles? Which of the two scales worse and why?
4. Explain the difference between prefill and decode, and which one your streaming user sees.
5. What is "lost in the middle", and what does it imply about where you put retrieved context?
6. Top-k, top-p, temperature: what does each one do, and which would you change to reduce hallucinated tool arguments?
7. An embedding and a hidden state come out of the same family of machinery. What is the difference, and why can't you compare embeddings from two different models?
8. Why is cosine similarity the default distance, and when is it wrong?
9. How do you get guaranteed-valid JSON out of a model? Name three mechanisms and their trade-offs.
10. What does a system prompt actually do differently from a user message?
11. Give three reasons a longer prompt can make output *worse*.
12. When is a smaller model the correct engineering choice, not a compromise?

## Book 02 — RAG in Production

13. Draw the full RAG pipeline. Every stage. Now say which stage fails most often in practice.
14. Your RAG system gives a wrong answer. Walk through how you localise the fault to retrieval versus generation.
15. What is recall@k, and why is it a more important number than the answer quality score early on?
16. Fixed-size, recursive, semantic and document-structure chunking: pick one for a set of 60-page patent PDFs and defend it.
17. Why does chunk overlap help, and what does it cost?
18. What is hybrid search, why does BM25 still earn its place in 2026, and how does reciprocal rank fusion combine the two lists?
19. What is a cross-encoder reranker, why is it too slow to use as your retriever, and what does it buy you at k=50?
20. HNSW: what are `M` and `ef_search`, and what happens to recall and latency as you move each?
21. When is pgvector the right answer and when do you actually need a dedicated vector database?
22. What is metadata filtering, and why does it interact badly with approximate nearest-neighbour indexes?
23. Explain HyDE and query rewriting. When is a multi-query fan-out worth 3x the embedding cost?
24. Your corpus is 200 documents. Is RAG the right architecture at all?
25. What is contextual retrieval, and what problem with naive chunking does it fix?
26. How do you handle a question whose answer requires combining three documents?
27. How do you make a RAG answer citable, and why does that change the failure mode?
28. What breaks when the corpus updates hourly?

## Book 03 — Agents, Tools and Orchestration

29. What is the actual difference between a chain and an agent?
30. Write the tool-calling loop from memory. What terminates it?
31. What goes in a tool description, and why is the description a more common cause of failure than the code?
32. What is ReAct, and what is the honest case that it is overrated?
33. When does a state machine beat an agent loop? Give a concrete example from a product you know.
34. What does LangGraph give you that a while loop does not? Name three things and be specific.
35. What is a checkpointer, and what does it enable that is impossible without one?
36. How does human-in-the-loop approval actually work mid-graph, and where is the state while it waits?
37. What is MCP, what problem does it solve, and how is it different from just writing a tool?
38. Multi-agent: when does splitting into agents help, and what is the cost you always pay?
39. How do you keep an agent's context from growing without bound over 40 turns?
40. Short-term versus long-term memory in an agent. What are the real implementations of each?
41. Your agent calls the same tool six times in a row with the same arguments. Diagnose it.
42. What is the difference between an agent that failed and an agent that failed *safely*?

## Book 04 — Evals and Harnesses

43. Build me a golden set. How many examples, from where, labelled by whom?
44. Why is a test suite made only of cases that should pass close to worthless? (There is a story from his own repo here.)
45. When is exact match the right scorer, and when does it actively mislead you?
46. What is LLM-as-judge, what are its three known biases, and how do you measure the judge itself?
47. Pairwise comparison versus absolute scoring: which is more reliable and why?
48. What is a regression gate, what does it gate on, and where does it live in CI?
49. Explain per-slice reporting and give an example of a change that improves the average and is still a regression.
50. Offline eval versus online eval. What can each one see that the other cannot?
51. How do you A/B test an LLM feature, and what is the metric when there is no click?
52. What is drift here, and what specifically drifts when the model version bumps under you?
53. How do you evaluate an *agent*, where the final answer can be right for the wrong reasons?
54. What is trajectory evaluation and when do you need it?
55. Your golden set is six months old. What is wrong with it?
56. How many examples before a difference between two prompts is real rather than noise?

## Book 05 — Guardrails and Agent Safety

57. Define blast radius for an agent action, and give three ways to shrink it.
58. Why is a guardrail in the system prompt not a guardrail?
59. What is prompt injection, and why is indirect injection through retrieved content the harder case?
60. Design the confirmation layer for an LLM that can move money in a chat window.
61. Input guardrail, output guardrail, action guardrail: what does each catch that the others cannot?
62. How do you sandbox a tool that runs code?
63. What do you log so that "the agent did something" can be reconstructed afterwards?
64. Why do smart-contract habits transfer to agent design? Be specific about which ones.
65. How would you rate-limit an agent, and by what unit?

## Book 06 — LLMOps, Serving, Cost

66. What is in a trace for an LLM app, and what is a span?
67. Exact-match caching versus semantic caching: how does each key work, and what is the failure mode of the second?
68. Build a latency budget for a 700ms voice turn. Where does the time go?
69. What is prompt caching, how does it change the price, and what does it demand of your prompt layout?
70. What does batching do for throughput, and why does it hurt the individual request?
71. Why does vLLM exist? What is paged attention solving?
72. Self-hosting versus an API: give the crossover point in real numbers.
73. How do you roll out a prompt change safely to production traffic?
74. How do you attribute cost per feature, per customer, per request?
75. What do you alert on for an LLM feature, given that it never returns a 500 when it is wrong?

## Book 07 — Python, FastAPI and ML Fundamentals

76. Why is async the default shape for an LLM service, and where does the GIL actually bite?
77. What does pydantic buy you at an LLM boundary specifically?
78. How do you stream tokens out of FastAPI to a browser?
79. Precision, recall, F1 and precision@k: define each and pick the right one for a screening ranker.
80. What is nDCG and when do you need it over MRR?
81. When do you fine-tune instead of doing retrieval? Give the decision rule.
82. What is LoRA doing mathematically, and why does it need so much less memory?
83. What does quantisation cost you, and at what bit width does it start to show?
84. Sketch the latency budget of a voice agent: STT, model, TTS.
85. How would you evaluate a classifier you inherited with no labelled data?

## How to use this properly

Pick five questions, answer them out loud into a voice memo, then read the relevant chapters and answer the same five again. The delta between the two recordings is what the reading actually bought, and it is usually smaller than it feels and larger than nothing.

*Connect the dot:* questions 43, 44 and 49 are the ones most likely to decide a first-round call, per Chapter 1's finding that evals are the real bar in this corpus. If time is short, those three and nothing else.

Next: Book 01. Tokens, context, sampling, embeddings, and the handful of model facts that determine every architectural decision downstream.
