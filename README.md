# The Unofficial Guide — Project 1

> **How to use this template:**
> Complete each section *after* you've built and tested the corresponding part of your system.
> Do not write placeholder text — if a section isn't done yet, leave it blank and come back.
> Every section below is required for submission. One-liners will not receive full credit.

---

## Domain

I focused on housing experiences in Knight Circle, one of the main student housing options for UCF. I chose this for a few reasons; namly because it has multiple phases, some older than others; a general "it's bad" review with no specifics on the phase is difficult to reason with. Secondly, many problems are neverending, so a lack of new reviews or discussion on a topic doesn't mean the problem solved, it's just not spoken of any more (the way things are). Also unless you know someone directly to ask detailed questions to, most reviews on Reddit were pretty high-level, and wouldn't be helpful to someone as a freshman, looking for their first dorm.

---

## Documents

| # | Source | Description | URL or location |
|---|--------|-------------|-----------------|
| 1 | knights_circle_general.md | 2 comprehensive reviews covering broken amenities, mold, maintenance access issues, roaches | Compiled from r/ucf threads (Nov 2023) |
| 2 | knights_circle_maintenance.md | 5 reviews focused on maintenance responsiveness, mold, water intrusion, WiFi reliability, pest control | Compiled from r/ucf threads (Jun–Aug 2022) |
| 3 | knights_circle_phases.md | 5 reviews comparing Phase 1, 2, and 3 with phase-specific details (location, shuttle availability, noise, safety) | Compiled from r/ucf threads (Jun–Aug 2022) |
| 4 | knights_circle_towing.md | 2 reviews documenting towing policies, visitor parking rules, predatory practices, costs | Compiled from r/ucf threads (Dec 2023) |

---

## Chunking Strategy
**Chunk size:** 200–600 characters per chunk, split strictly at review boundaries (---) or paragraph breaks (\n\n).
**Overlap:** None (0 characters).
**Why these choices fit your documents:** My corpus consists of distinct student reviews. Each review is a self-contained narrative with its own metadata (Date and Phase). Using overlap or arbitrary character limits would have caused "metadata bleed"—merging a 2021 Phase 1 review with a 2023 Phase 3 review. By chunking strictly by paragraph/review boundaries, I preserved the semantic integrity of each student's complaint.
**Final chunk count:** 14 chunks.
---

## Embedding Model
**Model used:** sentence-transformers/all-MiniLM-L6-v2 (Local)
**Production tradeoff reflection:** If cost and latency were not constraints, I would upgrade to OpenAI's text-embedding-3-large. MiniLM is fast and free, but it has a short context window and struggles slightly with hyper-specific entity matching (like prioritizing the number "1" in "Phase 1"). A larger commercial model would cost a few fractions of a cent per query and introduce API latency, but it would offer far superior semantic precision and better handling of student slang and abbreviations (e.g., "KC", "P3").
----

## Grounded Generation
**System prompt grounding instruction:** I enforced grounding by passing the retrieved text into the system prompt alongside a "STRICT COMPLIANCE DIRECTIVE" that explicitly commanded: "Base your answer purely on the context snippets provided... If the snippets do not contain the answer... state: 'I don't have enough verified student documentation'."
**How source attribution is surfaced in the response:** I programmatically appended the metadata (Source File, Phase, Date, and Distance Score) to each chunk sent to the LLM. I then used Gradio to render a separate UI box titled "Retrieved Document Evidence" that outputs the exact files and distance metrics used, preventing the LLM from having to "guess" its citations.

---

## Evaluation Report

| # | Question                                                                             | Expected answer                                 | System response (summarized)                                                                                          | Retrieval quality  | Response accuracy                     |
| - | ------------------------------------------------------------------------------------ | ----------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- | ------------------ | ------------------------------------- |
| 1 | What maintenance issues are reported in Phase 1 of Knights Circle?                   | Water intrusion, mold, WiFi unreliability.      | Listed mold, water intrusion, and WiFi issues, citing a June 2022 review.                                             | Partially relevant | Inaccurate (Hallucinated attribution) |
| 2 | Which phases of Knights Circle are described as having reliable shuttle service?     | Phase 2 and Phase 3 (Phase 2 is first stop).    | Confirmed Phase 2 shuttle is highly reliable (runs every 15 mins) and generally not full because it's the first stop. | Relevant           | Accurate                              |
| 3 | What should a student know about visitor parking and towing costs at Knights Circle? | Costs $130-150, predatory company, get a map.   | Accurately listed the $130-$150 cash-only cost, the "predatory" company, and the need for a visitor map.              | Relevant           | Accurate                              |
| 4 | What are common complaints about living conditions across all phases?                | Mold, roaches, broken amenities, staff entries. | Summarized unannounced entries, mold in 90% of apartments, broken amenities (fire pit), and bugs.                     | Relevant           | Accurate                              |
| 5 | How do residents compare Phase 2 and Phase 3 in terms of noise and quietness?        | Phase 2 quieter, Phase 3 noisier traffic.       | Accurately contrasted Phase 2's quietness (furthest from Alafaya) against Phase 3's traffic noise.                    | Relevant           | Accurate                              |

**Retrieval quality:** Relevant / Partially relevant / Off-target  
**Response accuracy:** Accurate / Partially accurate / Inaccurate

---

## Failure Case Analysis

**Question that failed:** Question 1: "What maintenance issues are reported in Phase 1 of Knights Circle?"

**What the system returned:** The system confidently returned a list of maintenance issues (mold, water intrusion from a toilet, wifi issues) and attributed them specifically to Phase 1.

According to a review from June 2022, the maintenance issues reported in Phase 1 of Knights Circle include: 
1. Non-stop mold problems
2. Water intrusion from toilet overflows upstairs, which the reviewer believes may be a pipe issue
3. Water shut-off multiple times over the past year, often without explanation
4. Unreliable wifi 

Additionally, the reviewer mentions safety concerns, such as difficulty finding parking spots near their building, poor lighting, and instances of suspicious characters, but these are not strictly maintenance issues.

**Root cause (tied to a specific pipeline stage):** This was a dual failure of Retrieval and Generation. Because the database lacked dense data specifically tagged as "Phase 1", the vector search (Retrieval) fell back on reviews tagged as "Phase: Unknown" that heavily matched the semantic weight of "maintenance issues" (distance score: 0.61). The LLM (Generation) then failed its grounding constraint; instead of admitting the phase was unknown, it assumed the retrieved "Unknown Phase" text applied to the user's "Phase 1" query to be helpful.

**What you would change to fix it:** I would add a post-retrieval filtering step in the code. Before sending chunks to the LLM, a Python function would check if the user's query contains a specific phase number, and strictly filter out chunks with Phase: Unknown to prevent the LLM from making false attributions. This is also a data quality issue; had I found more reviews that specifically mentioned Phase 1 my current system would have likely had no issues.

---

## Spec Reflection

**One way the spec helped you during implementation:** Writing out the chunking strategy beforehand prevented me from blindly using LangChain's default 1000-character split. Because I planned out the metadata (Date and Phase) in the spec, I knew I had to write custom ingestion logic to preserve those headers for each specific review.

**One way your implementation diverged from the spec, and why:** In the spec, I planned to collect 10 distinct document files. During implementation, I realized it was cleaner to compile ~14 distinct student reviews into 4 thematic markdown files (e.g., knights_circle_towing.md). This diverged from the "1 file = 1 document" idea but made the codebase much easier to manage while maintaining the required data volume.

---

## AI Usage

**Instance 1**

- *What I gave the AI:* I provided my planning.md chunking strategy and a raw Python script that loaded my markdown files as one giant string.
- *What it produced:* The AI generated a regex-based splitting function (re.split(r'\n---\n')) that separated the thematic files into individual reviews before chunking them.
- *What I changed or overrode:* I integrated this specific regex logic into my broader ingestion pipeline to ensure that the metadata (Date and Phase) attached to chunk 1 didn't accidentally overwrite the metadata for chunk 2 in the same file.

**Instance 2**

- *What I gave the AI:* I provided my ChromaDB vector output and asked how to format the system prompt to force the LLM to use the retrieved chunks using the Groq API.
- *What it produced:* It produced a Gradio application with a system prompt that appended the ChromaDB "distance score" directly into the text the LLM reads.
- *What I changed or overrode:* The LLM started narrating the math (distance scores) directly to the user in the UI. I overrode the AI's suggestion by removing the distance metric from the LLM's context block, keeping the backend math completely separate from the text generation.
