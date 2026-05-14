# AI Learning Guide for Software Engineers (Domain-Agnostic)
# (c) Qorix 2026

> **Target audience**: Software engineers of any domain who want to be productive with AI tools and build
> AI-powered features — without becoming ML engineers or data scientists.
>
> **What this is NOT**: A path to becoming an AI/ML engineer, training models, or doing ML research.
>
> **What this IS**: A structured roadmap to build, integrate, evaluate, and maintain AI-powered software
> systems reliably in production.

---

## Preface: Challenge the Premise First

Before accepting that "every software engineer must learn AI," consider the counterarguments:

- Most engineers who panic-learned AI in 2023-2024 learned to write ChatGPT wrappers. These skills are
  now commodity. The marginal value of another engineer who can call `openai.chat.completions.create()`
  is near zero.
- "AI literacy" courses produce engineers who can talk about AI but cannot distinguish a genuinely useful
  AI integration from a hallucination-prone liability in a production system.
- Time spent on AI courses has opportunity cost — depth in your actual domain compounds faster than
  shallow AI breadth.

**However**, the counterargument fails for 2026 because:

1. AI is now infrastructure — like databases and networking. An engineer who cannot integrate an inference
   API, evaluate output quality, or debug why an AI system behaves unexpectedly is at a structural
   disadvantage.
2. The skill is not "train models" — it is **build reliable software systems that include AI components**.
   This is a software engineering discipline, not an ML discipline.
3. The floor of required knowledge is much lower than most think. 12-16 targeted weeks, not 18 months.

**Confidence: HIGH** on both the counterargument and the rebuttal.

---

## The North Star: What You Are Actually Trying to Achieve

You are becoming a **software engineer who can build, integrate, and maintain software systems that include
AI components reliably in production**.

| Skill | ML Engineer | You (SWE + AI) |
|---|---|---|
| Train models | Required | Never |
| Evaluate model outputs | No | Required |
| Integrate model APIs | Rarely | Required |
| Build reliable AI-powered features | Partially | Required |
| Understand model limitations | Partially | Required |
| Write prompts that produce consistent results | No | Required |
| Debug why AI output is wrong in production | Rarely | Required |
| Understand model costs and latency tradeoffs | No | Required |

Every item in your column is software engineering, not ML science.

---

## The Five Knowledge Layers (in order of priority)

---

## Layer 1 — AI Conceptual Literacy

**Time: 2-3 weeks | Effort: 1 hr/day**

This is the vocabulary and mental model layer. Without it, everything else is cargo-cult copy-pasting.

### 1.1 What a Model Is

A model is a mathematical function — trained offline on data, frozen, deployed as an artifact.
At runtime: `output = model(input)`. No memory between calls (unless you add it explicitly).
No reasoning. Pattern matching at enormous scale.

Types you will encounter as a software engineer:

| Model Type | What it does | Where you encounter it |
|---|---|---|
| **Large Language Model (LLM)** | Text in → text out. Predicts next tokens. | ChatGPT, Copilot, Claude, Llama |
| **Embedding Model** | Text/image in → vector (array of floats) out | Semantic search, RAG, recommendation |
| **Image Classification** | Image in → class label + confidence out | Moderation, tagging |
| **Object Detection** | Image in → bounding boxes + class labels out | ADAS, surveillance, retail |
| **Speech-to-Text (ASR)** | Audio in → transcript out | Whisper, meeting transcription |
| **Text-to-Speech** | Text in → audio out | Voice assistants |
| **Diffusion Model** | Noise + prompt → image out | Stable Diffusion, DALL-E |
| **Multimodal** | Image + text in → text out | GPT-4o, Gemini Vision |

As a SWE you will mostly work with LLMs and embedding models. Learn those two cold.

### 1.2 How LLMs Work Conceptually (No Math)

An LLM is trained to predict the next token (roughly, word-piece) given all previous tokens. That is the
entirety of what it learned to do. Emergent behaviors (reasoning, code generation, summarization) are
consequences of doing this prediction on trillions of tokens.

**Critical implications to internalize:**

- **It is not looking up facts.** It predicts what the next token should be. This produces fluent,
  confident-sounding output that is sometimes completely wrong. This is not a bug — it is the fundamental
  mechanism.
- **Context window is its working memory.** Everything the model "knows" about your conversation is in
  its context window. Nothing persists between calls unless you send it.
- **Temperature controls randomness.** Temperature=0 → deterministic (picks highest-probability token).
  Temperature=1 → normal sampling (creative, variable). Temperature>1 → chaotic. Use low temperature for
  structured tasks, higher for creative ones.
- **It cannot count, do arithmetic, or reason reliably without external tools.** Novel tasks that require
  systematic reasoning will often fail silently, with high confidence.

**Resources (all free):**
- [3Blue1Brown — But what is a GPT?](https://www.youtube.com/watch?v=wjZofJX0v4M) — 27 min. Best
  conceptual explanation that exists. Watch it.
- [Andrej Karpathy — Intro to Large Language Models](https://www.youtube.com/watch?v=zjkBMFhNj_g) —
  1 hour. Dense, precise, no hype. Watch it.

After these two videos you will understand LLMs better than 90% of people who "use AI" daily.

### 1.3 Tokens, Context Windows, and Costs

You will encounter these the moment you integrate any LLM API.

- **Token**: roughly 0.75 words in English. "software engineer" ≈ 3 tokens.
- **Context window**: maximum tokens in one API call (input + output combined).
  - GPT-4o: 128K tokens
  - Claude 3.5 Sonnet: 200K tokens
  - Llama 3.1 70B: 128K tokens
  - Exceeding this → error or truncation.
- **Cost**: charged per 1K tokens (input and output priced separately). Input is typically cheaper
  than output. At scale, this matters significantly.
- **Latency**: LLMs are slow. GPT-4o averages 1-3 seconds for short responses. Streaming hides
  latency for interactive use but does not reduce it.

**Resource**: Read the pricing pages for OpenAI API, Anthropic API, and Google Gemini API once.
Understand the structure. 20 minutes.

### 1.4 The Hard Reliability Problem

LLM outputs are **probabilistic, not deterministic**. The same input can produce different outputs
on different calls. In production software systems:

- You cannot unit test an LLM call the way you test a pure function
- Output can be wrong with high confidence (hallucination)
- Output format can deviate from what you specified (JSON that is not valid JSON, etc.)
- Output can change when the model is updated — same prompt, different behavior

Every production system that includes an LLM must answer: **"What happens when the model output is
wrong?"** If the answer is "the system silently does the wrong thing," you have a reliability problem.

Treat LLM calls as unreliable external services that require explicit validation and fallback logic.
This is what separates engineers who build working AI features from those who build demos that break
in production.

---

## Layer 2 — AI as a Daily Productivity Tool

**Time: 2 weeks initial setup, ongoing practice | Effort: Daily use**

### 2.1 GitHub Copilot — Using It Properly

Most engineers use Copilot as an autocomplete and accept/reject suggestions mechanically. This misses
70% of its value.

**Effective usage patterns:**

| Pattern | How to do it | Value |
|---|---|---|
| **Intent-first comments** | Write a comment describing what you want, then let Copilot write the code | Faster than typing, especially for boilerplate |
| **Test generation** | Write function signature + docstring, let Copilot generate unit tests | Forces you to think about contracts first |
| **Explain unfamiliar code** | Select code, ask Copilot Chat "explain this" | 10× faster than tracing through someone else's logic |
| **Suggest refactors** | Ask "what are the problems with this function?" | Good at spotting obvious issues |
| **Generate documentation** | Highlight a function, ask for docstring | Saves time, quality usually acceptable |
| **Shell commands** | Describe what you want in natural language, get the command | Never Google `find` flags again |

**Where Copilot fails (you must know this):**
- **Security-sensitive code**: SQL queries, auth code, crypto — often generated with subtle
  vulnerabilities. Always review manually.
- **Novel domain-specific logic**: If your domain is unusual, suggestions will be plausible-looking
  but wrong.
- **Large context**: On large files it loses coherence.

**Investment**: 2 weeks of deliberate usage. After that, patterns become habitual.

### 2.2 LLM Chat Tools for Engineering Work

Practical use patterns for ChatGPT / Claude / Gemini:

| Task | Prompt pattern | Notes |
|---|---|---|
| **Debug error messages** | "I'm getting this error: `[paste error]`. My code does: `[paste code]`. What is wrong?" | Faster than Google for most common errors |
| **Architecture decisions** | "I need to [describe requirement]. Options are A and B. What are the tradeoffs?" | Good for generating considerations; verify claims |
| **Code review** | "Review this code for: correctness, edge cases, security issues: `[paste code]`" | Good first pass; not a substitute for human review |
| **Writing tests** | "Write pytest unit tests for this function. Cover edge cases: `[paste function]`" | Very reliable; saves significant time |
| **Understanding standards** | "Explain ISO 26262 ASIL D in plain language with an example" | Excellent for dense technical documents |
| **Regex / complex queries** | "Write a regex that matches X but not Y" | Models are excellent at regex; always verify |
| **Format conversion** | "Convert this JSON schema to a Python dataclass" | Near-perfect reliability for mechanical transformations |

**Critical discipline**: Never trust code output without reading it. Never trust factual claims without
verification when accuracy matters. LLMs are a first-draft tool, not a final-answer tool.

### 2.3 Prompt Engineering — Minimum Viable Skillset

You do not need to become a "prompt engineer." You need the ~6 patterns that produce reliable outputs
for engineering tasks.

**The 6 patterns that matter:**

1. **Role + Task + Constraints**: `"You are a senior C++ engineer. Review this function for memory
   safety issues. Focus only on issues that can cause undefined behavior, not style."`

2. **Few-shot examples**: Provide 2-3 examples of input/output before asking for the real thing.
   Dramatically improves consistency for structured tasks.

3. **Chain-of-thought for reasoning tasks**: Add "Think step by step before answering." Improves
   accuracy on logic-heavy questions. Confidence: HIGH — one of the most replicated findings in LLM
   research.

4. **Structured output format**: `"Respond only with valid JSON in this schema: {field: type}"`.
   Reduces format deviation. Combine with output validation in code.

5. **Negative constraints**: `"Do not suggest adding logging. Do not refactor unrelated code."`
   Without negative constraints, models over-generalize.

6. **Persona-based consistency**: For repeated tasks, write a system prompt that establishes context
   once. Do not repeat it in every user message.

**Resource**: [Anthropic Prompt Engineering Guide](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview)
— the most rigorous publicly available guide. Read it in full. 2 hours.

---

## Layer 3 — Building AI-Powered Features in Software

**Time: 6-8 weeks | Effort: 1.5 hr/day**

### 3.1 LLM API Integration (Week 1-2)

**Concepts to understand:**

- **Chat completions API**: The standard interface. Send an array of messages (system, user, assistant
  roles) → receive a completion. This is the architecture of every LLM-powered feature.
- **System prompt**: Sets persistent behavior for the session. Put all behavioral constraints here.
- **Streaming**: Receive tokens as generated instead of waiting for the full response. Required for any
  interactive UI. Uses server-sent events (SSE) or WebSockets under the hood.
- **Function calling / tool use**: The model emits a structured "call this function with these args"
  output instead of free text. You execute the function, send result back to model. This is how AI
  agents work.
- **Structured outputs**: Some APIs guarantee valid JSON output conforming to a schema. Use this
  instead of parsing free text wherever possible.

**Practical exercise (2 weekends, in sequence):**

1. Get an OpenAI or Anthropic API key (both offer free tiers)
2. Write a Python script: send a user message, print the response — 10 lines
3. Add streaming: print tokens as they arrive
4. Add a system prompt: constrain the model to a specific persona/task
5. Add function calling: define a `get_weather(city)` function, let the model call it
6. Add output validation: parse the model's JSON output, handle validation errors with retry logic

Do it in Python first, then replicate the core in your primary language.

**Resources**:
- [OpenAI API Quickstart](https://platform.openai.com/docs/quickstart)
- [Anthropic API Quickstart](https://docs.anthropic.com/en/api/getting-started)
- [Ollama](https://ollama.com) — run Llama 3.1 8B locally, same API interface, zero cost

### 3.2 Embedding Models and Vector Search (Week 3-4)

**What embeddings are:**
An embedding model converts text into a high-dimensional vector of floats (e.g., 1,536 floats). Texts
that are semantically similar have vectors that are close together (measured by cosine similarity).
"car" and "automobile" will have very similar vectors. "car" and "furniture" will have distant vectors.

**Why you need this:**
- **Semantic search**: User queries "payment failures" → finds documents that mean that, even if they
  never use those exact words. Traditional keyword search fails here.
- **RAG**: Finding relevant context to inject into LLM prompts (see next section)
- **Duplicate detection**: Are these two bug reports describing the same issue?
- **Classification without training**: Compare to example embeddings instead of training a classifier

**Practical exercise:**
1. Use OpenAI `text-embedding-3-small` or `nomic-embed-text` via Ollama (free)
2. Embed 100 text strings
3. Implement cosine similarity in Python — 5 lines with NumPy
4. Build simple semantic search: given a query, find the most similar string from your set

**Vector databases** (you will encounter these in production):

| Tool | Type | When to use |
|---|---|---|
| **pgvector** | PostgreSQL extension | If you already use Postgres — best default choice |
| **Chroma** | Lightweight, local | Development, small collections, quick setup |
| **Weaviate** | Open source server | Larger production deployments |
| **Pinecone** | Hosted | When you need managed infrastructure |

**Rule**: For fewer than ~50,000 documents, cosine similarity over an in-memory array is faster, cheaper,
and simpler than a vector database. Do not over-engineer.

**Resource**: [Pinecone Learning Center — Vector Embeddings](https://www.pinecone.io/learn/vector-embeddings/)
— best free resource on embeddings and vector search. Read end-to-end. 3 hours.

### 3.3 RAG — Retrieval Augmented Generation (Week 5-6)

RAG is the pattern that makes LLMs useful in production for domain-specific knowledge. It is the most
common AI architecture you will be asked to build.

**The problem it solves**: An LLM has fixed knowledge from training. Your application has fresh,
proprietary, domain-specific documents the LLM cannot access.

**The RAG pattern:**
```
User query
  → Embed query (embedding model)
  → Search vector store for top-K relevant document chunks
  → Inject those chunks into LLM context: "Answer based on these documents: [chunks]"
  → LLM generates response grounded in your documents
  → Return response to user
```

**The three hard problems in RAG** (most tutorials skip these):

**1. Chunking strategy**: You cannot embed entire documents. Fixed 512-token chunks is the naive
approach — it often breaks mid-sentence, destroying context. Recursive character splitting with overlap
is better. Semantic chunking (split on topic boundaries) is best but complex.

**2. Retrieval quality**: Top-K retrieved chunks may not be the right chunks. Solutions:
- Hybrid search (combine keyword + semantic)
- Query rewriting (ask the LLM to rephrase the query before embedding)
- HyDE (generate a hypothetical answer and embed that for retrieval)

**3. Answer grounding and hallucination**: Even with context injected, models can hallucinate details
not in the context. Solutions:
- Require citations (ask model to quote the chunk that supports each claim)
- Implement answer verification (ask model "is this answer supported by the provided context?")
- Log failures for human review

**Practical exercise (1 weekend):**
1. Take 20-50 text documents from a domain you know
2. Chunk them into 512-token pieces with 50-token overlap
3. Embed all chunks using OpenAI or Ollama
4. Store in Chroma (3 lines of code to set up locally)
5. Given a user question: embed it, retrieve top 5 chunks, send to an LLM with instruction to answer
   based only on the provided context
6. Test with questions whose answers are in the documents, and questions whose answers are not. Observe
   behavior — especially where it fails.

**Resource**: [LangChain RAG Tutorial](https://python.langchain.com/docs/tutorials/rag/) — use as
implementation reference only. Do not adopt LangChain as your application framework (see the
"What to Avoid" section).

---

## Layer 4 — Production AI Systems: Reliability, Evaluation, and Agents

**Time: 4-6 weeks | Effort: 1.5 hr/day**

### 4.1 LLM Output Validation

In production, every LLM response must be validated before being acted upon.

| Output type | Validation approach |
|---|---|
| **Structured JSON** | JSON Schema validation; retry on parse failure with error fed back to model |
| **Classification** | Assert output is one of the allowed categories |
| **Code** | Syntax check; linting; sandbox execution for security-critical use |
| **Free text** | Use a second LLM call as a judge (LLM-as-judge pattern) |
| **Citations / facts** | Verify cited passages exist in source document |

**Retry with error feedback pattern:**

```python
for attempt in range(3):
    response = llm.call(prompt)
    validation_error = validate(response)
    if not validation_error:
        return response
    prompt = add_error_context(prompt, validation_error)
# fallback if all retries fail
```

Feed the validation error back to the model: "Your previous response was invalid JSON. The error was:
`[error]`. Try again." This works reliably for format errors.

### 4.2 Evaluation (The Discipline Nobody Wants to Do)

The single biggest quality gap in AI-powered software is the absence of systematic evaluation.
Engineers ship a demo, it looks good, they deploy — then it fails on real inputs they never tested.

**Minimum viable evaluation setup for any LLM feature:**

1. **Build a golden test set**: 50-100 representative input/expected output pairs. Do this before
   shipping. Keep it in version control. This is your regression test for model behavior.

2. **Define failure modes explicitly**: For your specific feature, what does failure look like?
   Wrong answer? Wrong format? Hallucinated citation? Missed constraint? You cannot measure what you
   have not defined.

3. **LLM-as-judge**: For subjective quality (is this summary accurate?), use a second LLM call with a
   scoring rubric: `"Rate the following answer on a scale of 1-5 for factual accuracy relative to the
   source document. Return only JSON: {score: int, reason: string}"`. Automate over your golden test set.

4. **Track model version changes**: When your LLM provider updates their model (which happens without
   notice for hosted APIs), your prompts may behave differently. Run your golden test set on every
   deployment.

**Resource**: [RAGAS](https://github.com/explodinggradients/ragas) — open-source RAG evaluation
framework. Implements standard metrics (faithfulness, answer relevance, context recall).

### 4.3 Cost and Latency Management

**Cost optimization patterns:**
- **Prompt caching**: Some APIs (Anthropic, OpenAI) cache repeated prefix tokens. Keep your system
  prompt identical across calls — you pay for input tokens only once.
- **Model tiering**: Use a small fast model (GPT-4o-mini, Claude Haiku) for classification/routing.
  Reserve expensive models for complex reasoning. Cost difference: 10-50×.
- **Response caching**: For deterministic queries, cache LLM output in Redis with TTL. Works well for
  FAQ-style features.
- **Batching**: For offline processing (document analysis, batch classification), batch requests where
  APIs allow.

**Latency patterns:**
- Streaming is always better for interactive UI — perceived latency drops dramatically
- For backend pipelines where the user does not wait: async + queue architecture. Do not block a web
  request on an LLM call.
- Pre-generation: For predictable queries, pre-generate responses and serve from cache.

### 4.4 AI Agents and Tool Use (Conceptual Understanding)

**What an agent is:**
An LLM that can take actions in a loop:

```
Observe (receive task + current state)
  → Plan (decide what tool to use next)
  → Act (call a tool: search, execute code, call API, read file)
  → Observe (receive tool result)
  → Repeat until task complete
  → Return final answer
```

**Why it fails and what to know:**
- Each loop iteration adds latency and cost
- Each LLM call can hallucinate, compounding errors across steps
- Non-deterministic — debugging is fundamentally harder than regular code
- Can produce runaway costs or take unintended actions if not sandboxed

**Current reliability (Confidence: MEDIUM-HIGH)**: Single-step LLM calls are reasonably reliable.
3-5 step agent chains are usable with careful engineering. 10+ step autonomous agents are still
research-grade for most domains. Do not bet production systems on long-horizon autonomous agents in 2026.

**What you need to know for SWE roles:**
- How the ReAct prompting pattern works (Reason + Act loops)
- How function/tool calling works in the API (covered in Layer 3)
- How to design tool APIs that agents use safely (idempotent operations, no side effects without
  confirmation)
- How to implement a basic agent loop from scratch — without a framework, in ~50 lines of code

**Resource**: [Simon Willison's LLM blog](https://simonwillison.net) — best single resource for
practical, engineering-focused AI coverage.

---

## Layer 5 — The Meta-Skill: Knowing When Not to Use AI

**Time: Ongoing — develops through experience**

The highest-leverage skill and the rarest one. Engineers with the most value correctly distinguish
when AI is the right tool and when it is the wrong one.

**Do NOT use AI when:**
- Output is safety-critical and there is no reliable validation layer
- Determinism is required — same input must always produce same output
- Latency budget is <100ms and you are not caching
- The problem has a deterministic algorithm that is well-understood (regex, parser, lookup, formula)
- Data is private/sensitive and using a hosted API is a compliance violation
- Cost-per-call would make the feature economically unviable at scale

**Use AI when:**
- Input space is too large for deterministic rules (natural language understanding, document analysis)
- "Good enough" is acceptable — perfection is not required or verifiable anyway
- Task is a first-draft / accelerator with human review downstream
- Problem is inherently fuzzy and rule-based systems have failed or are too expensive to maintain
- Latency tolerance is >500ms or async processing is acceptable

---

## The Complete Roadmap: Sequenced by Week

```
Weeks 1-2:   Layer 1 — AI Conceptual Literacy
             • 3Blue1Brown GPT video (27 min)
             • Karpathy LLM intro (1 hr)
             • Anthropic Prompt Engineering Guide (2 hr)
             • Read one API pricing page to understand token/cost model

Weeks 3-4:   Layer 2 — AI as Daily Tool
             • Set up GitHub Copilot (if not already)
             • Use it for every coding task for 2 weeks deliberately
             • Use ChatGPT/Claude for debugging, test writing, code review daily
             • Build the prompt pattern habits: role+task+constraints, few-shot, negative constraints

Weeks 5-6:   Layer 3a — LLM API Integration
             • Build the 6-step LLM integration project:
               chat → stream → system prompt → function calling → structured output → retry/validation
             • Python first, then replicate in your primary language

Weeks 7-8:   Layer 3b — Embeddings and Vector Search
             • Embed 100 strings, implement cosine similarity
             • Build simple semantic search
             • Read Pinecone learning center on embeddings

Weeks 9-10:  Layer 3c — RAG
             • Build the RAG project end-to-end on your own documents
             • Test for grounding failures
             • Implement the retry-with-error-feedback pattern

Weeks 11-12: Layer 4a — Evaluation and Production Reliability
             • Build a golden test set for your RAG project
             • Implement LLM-as-judge scoring
             • Implement prompt caching and response caching

Weeks 13-14: Layer 4b — Cost, Latency, Agents
             • Implement model tiering (small model for classification, large for complex tasks)
             • Build a minimal agent loop from scratch (~50 lines)
             • Read Simon Willison's agents posts

Weeks 15-16: Consolidation
             • Build one complete project integrating Layers 3-4 in a domain relevant to your work
             • Identify the Layer 5 boundaries: where did you NOT use AI and why?
```

**Total: 16 weeks at 1-1.5 hours/day.**

---

## What to Explicitly Avoid Wasting Time On

| Topic | Why to skip it |
|---|---|
| LLM fine-tuning | RAG solves the same problem better for most use cases |
| Training any model from scratch | Out of scope entirely |
| PyTorch / TensorFlow internals | Only needed for model development |
| "Prompt hacking" tricks and jailbreaks | Entertaining, zero career value |
| LangChain as a framework | High abstraction, hides important details, constantly breaking API. Use as reference, not as your application framework. Build core patterns yourself. |
| AutoML platforms | Business tool, not engineering skill |
| Hugging Face model hub browsing as a substitute for understanding | Downloading and running models does not teach you to use them reliably |
| AI certifications from online bootcamps | No engineering hiring manager is impressed by a Coursera AI certificate in 2026. Portfolio projects are the credential. |

---

## The Portfolio Project That Proves All of This

Build one end-to-end project you can walk through in an interview:

**"A domain-specific document Q&A system with production-grade reliability"**

**Spec:**
- Ingest 50-200 documents from a domain you know (technical specs, documentation, papers, code)
- Implement chunking with overlap
- Embed and store in Chroma or pgvector
- Build a query interface (CLI or simple web UI)
- Implement: streaming responses, citation grounding, retry on format errors, LLM-as-judge evaluation
- Measure: latency P50/P95, cost per query, accuracy on golden test set
- Document: where it fails and why (this matters more than showing it always works)

**What this demonstrates**: API integration, embedding/vector search, RAG, output validation, evaluation
methodology, cost analysis, and production mindset. All of Layers 3 and 4 in one artifact.

Put it on GitHub. Walk through every design decision in an interview.

---

## Key Resources

| Resource | URL | Layer |
|---|---|---|
| 3Blue1Brown — But what is a GPT? | https://www.youtube.com/watch?v=wjZofJX0v4M | 1 |
| Andrej Karpathy — Intro to LLMs | https://www.youtube.com/watch?v=zjkBMFhNj_g | 1 |
| Anthropic Prompt Engineering Guide | https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview | 2 |
| OpenAI API Quickstart | https://platform.openai.com/docs/quickstart | 3 |
| Anthropic API Quickstart | https://docs.anthropic.com/en/api/getting-started | 3 |
| Ollama (local model runner) | https://ollama.com | 3 |
| Pinecone Learning Center — Embeddings | https://www.pinecone.io/learn/vector-embeddings/ | 3 |
| RAGAS — RAG Evaluation Framework | https://github.com/explodinggradients/ragas | 4 |
| Simon Willison's LLM Blog | https://simonwillison.net | 4 |

---

## Confidence Assessment

| Claim | Confidence |
|---|---|
| This knowledge scope is sufficient to be a productive AI-enabled SWE | HIGH |
| 16 weeks at 1-1.5 hr/day is a realistic timeline | HIGH |
| LangChain should not be used as primary application framework | HIGH — high churn, over-abstraction is widely documented |
| Agents are not production-reliable for >5 steps in 2026 | MEDIUM-HIGH — actively improving; verify current state |
| LLM-as-judge is a valid evaluation methodology | HIGH — supported by academic literature (Zheng et al. 2023, MT-Bench) |

---

*Guide compiled May 2026. Target: software engineers of any domain seeking AI competence without
becoming ML engineers. Author: GitHub Copilot analysis.*
