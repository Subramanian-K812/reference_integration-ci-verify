# Complete Guide: Learning How to Learn
# (c) Qorix 2026

> **Target audience**: Software engineers returning to structured learning after a gap, or anyone
> struggling to learn, retain, and compete effectively in a corporate technical environment.
>
> **What this is**: A SMART-timeline-based, evidence-backed system for rebuilding your learning
> capability — covering meta-skills, domain-specific strategies, and sustainable habits.
>
> **What this is NOT**: Generic productivity advice or a course syllabus. Every recommendation is
> grounded in cognitive science and calibrated for software engineers.

---

## The Bootstrapping Problem: How to Remember This Guide While You Are Still Learning

This is the most common trap: you read a guide about learning, find it useful, close it,
and remember nothing a week later. Here is how to avoid that.

### The Rule: Do Not Try to Memorize the Guide

You do not need to remember the whole guide. You need to remember and act on **one thing at a time**.
The system is designed to be entered at any point.

### Minimum Viable Start (Today, 10 minutes)

Do this right now before reading further:

1. Open Anki (or a plain text file if you do not have Anki yet).
2. Make exactly **3 flashcards** from what you just read:
   - Q: *What is the 4-step learning loop?* → A: *Engage → Encode → Consolidate → Retrieve*
   - Q: *What does "desirable difficulty" mean?* → A: *Struggling before seeing the answer improves retention*
   - Q: *What is the #1 anti-pattern in studying?* → A: *Re-reading — it creates an illusion of knowing*
3. Review those 3 cards tomorrow morning. That is it for day 1.

### Why 3 Cards and Not 30

The forgetting curve starts immediately. 3 cards reviewed tomorrow beats 30 cards read
once and never revisited. You are building the habit first, not the knowledge base.
The deck grows naturally as you read more of the guide.

### The Progressive Unlock Pattern

Do not read the whole guide in one sitting. Treat each phase as something to unlock only
when you have acted on the previous one:

| Gate | What You Must Do Before Unlocking the Next Phase |
|---|---|
| Before Phase 1 | Read the TL;DR. Make 3 Anki cards. |
| Before Phase 2 | Finish at least one book from Phase 0. Have an Anki deck with ≥20 cards. |
| Before Phase 3 | Have applied one domain-specific strategy (Phase 2) to a real task at work. |
| Before Phase 4 | Have a daily Anki habit of at least 7 consecutive days. |

### The One Sentence to Tattoo on Your Brain

> **You do not remember what you read. You remember what you retrieve.**

Every time you feel like re-reading this guide, stop. Instead, close it and write from
memory what you know. Then check. The gap between what you wrote and what is here = your
actual learning target for today.

---

## TL;DR

You need a **meta-skill stack**:
1. Understand *how memory and learning actually work* (neuroscience foundation).
2. Pick a repeatable *learning operating system* (workflow).
3. Apply *domain-specific techniques* — because you do not learn a programming language the same
   way you learn an algorithm, a framework, or a soft skill.

The 12-week SMART timeline below gives you a concrete ramp.

---

## Phase 0 — Foundation Reading (Weeks 1–2)

**SMART Goal**: By end of Week 2, read or audio-listen to 2 core books and write a 1-page personal
summary of what you will change in your study habits.

### The 3 Non-Negotiable Books

| Priority | Book | Why It Matters |
|---|---|---|
| 1 | **"A Mind for Numbers"** — Barbara Oakley | Written for engineers. Covers focused vs. diffuse thinking, procrastination, chunking. Companion to the famous Coursera course. |
| 2 | **"Make It Stick"** — Brown, Roediger, McDaniel | Evidence-based. Destroys the myth of re-reading and highlighting. Teaches retrieval practice and interleaving. |
| 3 | **"Ultralearning"** — Scott Young | Practical project-based system. Shows how to design intense, self-directed learning sprints. |

### Secondary Reads (Weeks 6–12)

- *"The Art of Learning"* — Josh Waitzkin (mental models, deep practice)
- *"Thinking, Fast and Slow"* — Kahneman (understanding your own cognition)
- *"Deep Work"* — Cal Newport (protecting time and attention)

---

## Phase 1 — Your Learning Operating System (Weeks 2–4)

**SMART Goal**: By end of Week 4, have a working personal workflow set up in a tool of your choice
(Obsidian, Notion, or Anki) and complete one 2-hour learning session using the full system.

### The Core Workflow (4-Step Loop)

```
ENGAGE → ENCODE → CONSOLIDATE → RETRIEVE
```

#### Step 1: Engage (Active Input)

Never passively watch or read. Always have a question before you start.

Use the **SQ3R method**:
1. **Survey** — skim headings and structure before reading.
2. **Question** — convert each heading into a question you want answered.
3. **Read** — read to answer your questions, not to finish the chapter.
4. **Recite** — close the material and summarize from memory.
5. **Review** — check your summary against the source.

#### Step 2: Encode (Feynman Technique)

After learning a concept, write it in plain English as if teaching a 10-year-old.
Where you stumble = the exact gap in your understanding.
Return to the source only for the gap, then re-explain.

#### Step 3: Consolidate (Spaced Repetition)

- Tool: **Anki** (free, open source). Make one flashcard per atomic concept.
- The algorithm shows cards right before you would forget them — proven most time-efficient.
- Rule: 15–20 minutes of Anki *every morning* before any new learning.

#### Step 4: Retrieve (Active Recall)

- Close the book or IDE. Write down everything you know from memory.
- Use **Cornell Notes** format: main notes | cue column | summary at the bottom.
- Weekly: redo exercises from scratch without looking at solutions.

---

## Phase 2 — Domain-Specific Strategies (Weeks 4–8)

**SMART Goal**: By end of Week 8, apply the correct strategy to 3 different learning domains (one
technical, one conceptual, one tool/framework) and track progress in a learning log.

### You Do NOT Learn All Things the Same Way

---

### A. Learning a Programming Language

**Mental model**: A language is a *tool*, not knowledge. Muscle memory matters more than reading.

**Strategy**: Project-first, not tutorial-first.

1. Do the official 30-minute quickstart to understand syntax surface.
2. Immediately pick a *small real project* (a CLI tool, a test scenario, a script you need at work).
3. Get stuck → search → fix → document the pattern in Anki.
4. Read the standard library docs section by section once you have base fluency.
5. Read one idiomatic open-source codebase in the language.

**Anti-patterns to avoid**:
- Tutorial hell (watching 10+ hours of video before writing a line).
- Copy-pasting code without understanding it.
- Skipping or ignoring compiler/runtime error messages.

**SMART Checkpoint**: After 2 weeks of daily 45-minute sessions, you should be able to write a
working program that solves a real problem without looking up basic syntax.

---

### B. Learning a Framework or Library (e.g., Bazel, React, pytest)

**Mental model**: A framework is a *vocabulary and a set of conventions*.

**Strategy**: Mental model → guided project → source reading.

1. Read the *"Getting Started"* documentation in full — build a mental model of what problem the
   framework solves and what the key abstractions are.
2. Reproduce the official example from scratch (no copy-paste).
3. Modify the example in 3 increasingly complex ways.
4. Read the source code of 2–3 functions or rules that you use daily.
5. Card the vocabulary (rule names, flag names, common error messages) in Anki.

---

### C. Learning Theory / Concepts (Algorithms, Networking, OS, Math)

**Mental model**: Concepts have *dependencies*. You need the prerequisite graph before you start.

**Strategy**: Prerequisite mapping → chunking → problem sets.

1. Draw a prerequisite graph before starting (what must you know first?).
2. Study in **chunks** — understand one concept completely before moving to the next.
3. Solve problems *before* reading the solution. Even failure primes the brain ("desirable
   difficulty" — proven to improve retention).
4. Use the Feynman Technique aggressively — if you cannot teach it, you do not know it.
5. Cross-reference: for each concept, find 3 different explanations (book, blog, video). The
   overlapping intuitions produce durable understanding.

**For mathematics specifically**: Do every exercise. There is no substitute.

---

### D. Learning Soft Skills / Communication / Design Patterns

**Mental model**: Soft skills are *habits and heuristics*, not facts to memorize.

**Strategy**: Observe → reflect → practice → get feedback.

1. Find one practitioner you respect and study how they communicate or design.
2. Debrief after every meeting, code review, or design session: what worked, what did not?
3. Set micro-experiments per week, e.g.:
   *"This week I will ask one clarifying question per code review instead of immediately answering."*
4. Journal weekly, 10 minutes: what did I learn about working with people this week?

---

## Phase 3 — Retention and Anti-Forgetting System (Weeks 8–10)

**SMART Goal**: By end of Week 10, have a sustainable daily routine that takes no more than
30 minutes/day to maintain everything you have learned.

### The Daily Maintenance Stack (30 min/day)

| Time | Activity | Purpose |
|---|---|---|
| 15 min (morning) | Anki review | Spaced repetition — fight the forgetting curve |
| 10 min (after work) | Write one thing you learned today in your own words | Encoding and consolidation |
| 5 min (end of week) | Skim Cornell Notes from the week | Spaced re-exposure |

### The Weekly Review (30 min/week)

Every Sunday:
1. List 3 things you learned this week.
2. Identify 1 gap that showed up (something you thought you knew but did not).
3. Schedule the next week's learning sessions as time-blocks in your calendar.

---

## Phase 4 — Sustainable Long-Term Learning Identity (Weeks 10–12)

**SMART Goal**: By end of Week 12, publish or share one thing you learned — blog post, internal
wiki page, lunch-and-learn, or even a README. Teaching forces mastery.

### The Compound Learning Habits

- **Read 20 minutes/day** of technical material. In 1 year that equals 10+ books.
- **Build in public** — document what you learn. Writing forces clarity.
- **Use the 2-minute rule for Anki**: if you skip today, 2 cards become 4 tomorrow. Never skip
  twice in a row.
- **Interleave topics** — do not binge one subject for weeks. Mix language + theory + framework in
  the same week. Counter-intuitive but research-proven to improve long-term retention.

---

## Full 12-Week SMART Timeline

| Week | SMART Goal |
|---|---|
| 1 | Read *"A Mind for Numbers"* Chapters 1–10. Write 5 Anki flashcards per chapter. |
| 2 | Read *"Make It Stick"* in full. Install Anki. Set up first 20-card deck from Week 1 notes. |
| 3 | Read *"Ultralearning"* Chapters 1–6. Design your first Ultralearning project around a real work skill. |
| 4 | Set up Cornell Notes workflow. Complete one 2-hour deep learning session using the full 4-step loop. |
| 5 | Apply the programming-language strategy to one new language or tool. Log every blocker. |
| 6 | Apply the framework strategy to one framework you use at work but do not fully understand. |
| 7 | Apply the theory strategy to one conceptual area (e.g., deeply understand a data structure or a build system model). |
| 8 | Apply the soft-skill strategy: pick one communication habit to experiment with for 2 weeks. |
| 9 | Daily Anki + nightly note ritual established and tracked as a streak. |
| 10 | Weekly review habit in place. Identify top 3 learning gaps from the previous 9 weeks. |
| 11 | Read *"Deep Work"* Part 1. Schedule 2 deep-work blocks per week specifically for learning. |
| 12 | Share one thing you learned. Retrospect: what worked, what to adjust going forward. |

---

## Recommended Tools

| Tool | Purpose | Cost |
|---|---|---|
| **Anki** | Spaced repetition flashcard system | Free |
| **Obsidian** | Linked personal knowledge base ("second brain") | Free |
| **Coursera "Learning How to Learn"** | 4-week MOOC by Barbara Oakley — best free starting point | Free audit |
| **Readwise** | Re-surfaces your book highlights on a daily schedule | ~$8/month |
| **Excalidraw** | Drawing concept maps and prerequisite graphs | Free |

---

## Key Principles Summary

### Consistency vs. Intensity

45 minutes per day, 6 days per week beats an 8-hour weekend session.
Spaced practice is more effective than massed practice for long-term retention.

### Apply Within 48 Hours

The fastest path to retention is applying what you learn to a real work problem within
48 hours of learning it. Use your actual work tickets as learning vehicles.

### The Forgetting Curve

Ebbinghaus showed that you forget approximately 70% of new information within 24 hours
without review. Anki directly fights this curve. Starting with even 5 cards per day
compounds significantly over months.

### Interleaving Beats Blocking

Studying math, then switching to a programming concept, then to a design pattern in the
same session feels harder but produces stronger retention than blocking (studying only one
topic per session). Embrace the discomfort.

---

## Anti-Patterns Reference

| Anti-Pattern | Why It Fails | Replace With |
|---|---|---|
| Re-reading notes or highlighted text | Creates illusion of knowing; passive | Active recall: close the book and write from memory |
| Watching tutorial videos passively | No encoding; forgotten within 24h | Build a real project immediately after |
| Binge-studying one topic for days | No spaced repetition; high decay | Interleave and revisit with Anki |
| Collecting tools and frameworks | Tool-switching procrastination | Pick one tool per category and commit for 3 months |
| Learning without a goal project | Motivation collapses; no context | Always attach learning to a real deliverable |

---

*For further questions or refinement of any phase, consult the plan session memory or ask for
domain-specific expansions (e.g., Rust, C++, Bazel, system design).*
