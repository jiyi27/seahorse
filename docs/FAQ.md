# FAQ

## 1. How does user profile extraction work?

Every time `/memory/sessions` is called, the system pulls out all messages with the `user` role and sends them to an LLM along with the current user profile. The LLM outputs a patch — a diff describing which entries to add or remove.

`assistant`, `tool`, and `system` messages are all skipped at this stage. Only what the user says affects the profile.

The profile has three field types:

| Field | Meaning | Example |
|---|---|---|
| `facts` | Objective facts, tagged with a category (identity / personality / social / interests / values / life_situation / note) | Works as a backend engineer, based in Shanghai |
| `preferences` | Preferences | Prefers short answers, replies in English |
| `constraints` | Hard limits | Do not recommend paid subscription products |

The LLM returns a JSON patch, which is applied and persisted to the user profile.

## 2. How is memory vectorized and recalled?

### 2.1. Splitting into blocks

The message list is first split into **blocks**, one block per conversation turn. The rule is simple: **a new block starts every time a `user` message appears**. A block typically covers a full turn — user question, agent reasoning, tool calls, and final reply.

The conversation below is split into two blocks:

```
Block 1:
  [user]      Any new commits in the Axon repo recently?
  [assistant] Let me check.
  [tool]      {"commits": [{"hash": "2abf025", "message": "refactor(tools): flatten tool store"}]}
  [assistant] One recent commit: 2abf025 — refactored the tool store, flattening the discovery flow.

Block 2:
  [user]      Was that a big change?
  [assistant] Not really. It was an internal restructure; the external interface stayed the same.
```

### 2.2. Storage: blocks to chunks

Each block is broken into **chunks** — the actual units stored in the vector database. One chunk is created per `user` or `assistant` message. `tool` and `system` messages are skipped; they are never embedded.

Block 1 from the example above produces three chunks:

```
Chunk 1-A  [user]      "Any new commits in the Axon repo recently?"
Chunk 1-B  [assistant] "Let me check."
Chunk 1-C  [assistant] "One recent commit: 2abf025 — refactored the tool store..."
```

Each chunk is stored with two things in its payload:

- **`parent_block_id`** — which block it came from
- **block content** — the full formatted text of every non-`system` message in that block, including `tool` output

So even though `tool` messages aren't embedded, their content is preserved inside every chunk that belongs to the same block.

### 2.3. Retrieval: chunks back to blocks

At query time, the query is embedded and matched against chunks by vector similarity. Results are then deduplicated by `parent_block_id`, and the full block content is returned — not the individual matching messages.

```
Query: "recent Axon changes"
  → matches Chunk 1-A (closest vector match)
  → looks up parent_block_id → Block 1
  → returns the full block content, including the tool output and both assistant replies
```

The design means a query only needs to match one message in a turn to get the whole turn back — tool output, reasoning, and all.
