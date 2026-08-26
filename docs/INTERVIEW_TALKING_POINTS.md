# 🎤 Interview Talking Points

How to present this project in a 5-minute interview slot or a portfolio
review.

## 30-second elevator pitch

> "I built a production-grade RAG system over technical documentation. It
> ingests PDFs and Markdown, indexes them with hybrid search — BM25 plus
> dense embeddings — and re-ranks the top results with a cross-encoder
> before generating answers with Gemini. I evaluated it with RAGAS on 30
> hand-curated Q&A pairs and got [faithfulness: 0.91, context precision:
> 0.83, etc.]. The whole thing runs on free tiers and is dockerized."

## When they ask "What does this project do?"

> "It's a Q&A system over technical docs. You point it at a folder of
> Markdown or PDFs — say, the Databricks docs — and it lets you ask
> natural-language questions like 'how does the Medallion architecture
> work?' and get an answer with citations to the source chunks.
>
> What makes it production-grade rather than tutorial-grade is the
> evaluation piece. I have a set of 30 questions with ground-truth
> answers, and I run RAGAS after every change to track quality."

## When they ask "What did you learn?"

> "Three big things.
>
> First, retrieval quality is the bottleneck. I started with just dense
> embeddings and the answers were mediocre. Adding BM25 for exact-match
> queries — function names, error codes, config flags — was a clear win.
> Adding cross-encoder re-ranking on top was another big jump.
>
> Second, evaluation changes the conversation. Once I had RAGAS numbers
> I could tell which changes helped and which regressed. Without
> measurement I was just guessing.
>
> Third, chunking matters more than people think. The default of 512
> tokens worked for most docs but for code-heavy content I had to
> increase the overlap to keep functions from being split mid-body."

## When they ask "Why hybrid search?"

> "Dense embeddings capture semantic similarity — 'how do I deduplicate
> records' matches a chunk that talks about 'removing duplicate rows'.
> But for technical docs, users also search for exact terms — function
> names, SQL syntax, error messages. BM25 handles that. The two
> retrievers are complementary, and Reciprocal Rank Fusion lets you
> combine their rankings without calibrating their scores."

## When they ask "Why re-ranking?"

> "Bi-encoders embed the query and document independently, so they're
> fast but they don't model query-document interaction. A cross-encoder
> reads the pair together and is much more accurate — but ~100x slower.
> The pattern is: use the fast bi-encoder to get a candidate set of
> 20, then use the cross-encoder to pick the best 5. Best of both worlds."

## When they ask "How do you measure quality?"

> "RAGAS gives you four metrics. Faithfulness — is the answer grounded
> in the retrieved context, or is the model hallucinating? Context
> precision — are the retrieved chunks relevant? Context recall — did we
> retrieve everything we needed? Answer relevancy — does the answer
> actually address the question?
>
> The interesting failure mode is when one is high and another is low.
> High context recall but low faithfulness means the chunks were right
> but the prompt let the model stray. Low context recall with high
> precision means we got the right chunks but missed some — usually a
> chunking or top-k problem."

## When they ask "How would you scale this?"

> "The architecture is designed to swap pieces. Chroma runs in-process
> and is fine for ~100K chunks. Beyond that, the same wrapper interface
> works against pgvector or a managed service like Pinecone — the
> retrieval code doesn't change.
>
> The expensive piece is the cross-encoder re-ranker. At high QPS you'd
> serve it on a GPU pool or move to a smaller distilled re-ranker. The
> embeddings model can also be served as a microservice if ingest
> becomes a bottleneck.
>
> The pipeline itself is stateless and horizontally scalable — you can
> run 100 replicas behind a load balancer."

## When they ask "What would you improve?"

> "Three things on the near-term roadmap:
>
> 1. Streaming responses with server-sent events — better UX, no extra
>    cost.
> 2. Query caching — many users ask the same question, and serving
>    from Redis takes us from 800ms to 10ms on hot queries.
> 3. Langfuse tracing — I have the interface stubbed but not wired up.
>    Once it's in, I can see which queries get low scores and dig into
>    why.
>
> Longer term, conversational memory is the big one. Right now each
> query is independent. A multi-turn experience needs query
> reformulation — when a user says 'how do I configure that?' we need
> to know what 'that' refers to."

## When they ask "Why free tiers?"

> "The point of the project is the technique, not the bill. Gemini's
> free tier is generous enough to run a 30-question RAGAS evaluation
> many times. BGE-M3 and the reranker are open-source and run on
> commodity hardware. The whole thing is portable — you can clone it
> and run it without paying anyone.
>
> For production you'd swap to a paid tier or self-hosted model, but the
> architecture doesn't change."

## 5-minute demo flow (if you can show it live)

1. **Cold open**: open the Streamlit UI, ask a question about Databricks
   Medallion architecture. Show the answer with citations.
2. **Architecture**: open the diagram in `docs/ARCHITECTURE.md`, walk
   through the pipeline.
3. **Code**: show `app/core/hybrid_search.py` — 80 lines, easy to read,
   talks about RRF.
4. **Evaluation**: open `data/eval/results.json`, point out the metrics.
5. **What's next**: "the gap right now is Langfuse tracing and query
   caching — both straightforward to add."

## Common gotchas in interviews

- **Don't say "I used LangChain"** unless you actually understand what
  LangChain is doing for you. This project uses no framework — just
  sentence-transformers and the Gemini SDK. That's a feature, not a
  limitation.
- **Be ready to explain RRF on a whiteboard.** It's two minutes and
  shows you understand the fusion math.
- **Know the difference between bi-encoder and cross-encoder.** If
  you can't explain why re-ranking is slower, the rest of the project
  sounds memorized.
- **Have a real failure story.** "I started with 256-token chunks and
  context recall was 0.6. I increased to 512, added overlap, and got
  to 0.8. Here's the diff." That's the answer that gets you hired.
