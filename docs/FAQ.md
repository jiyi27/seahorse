# FAQ

## How does user profile extraction work?

Every time `/memory/sessions` is called, the system pulls out all messages with the `user` role and sends them to an LLM along with the current user profile. The LLM outputs a patch — a diff describing which entries to add or remove.

`assistant`, `tool`, and `system` messages are all skipped at this stage. Only what the user says affects the profile.

The profile has three field types:

| Field | Meaning | Example |
|---|---|---|
| `facts` | Objective facts, tagged with a category (identity / personality / social / interests / values / life_situation / note) | Works as a backend engineer, based in Shanghai |
| `preferences` | Preferences | Prefers short answers, replies in English |
| `constraints` | Hard limits | Do not recommend paid subscription products |

The LLM returns a JSON patch, which is applied and persisted to the user profile.

---

## How is memory vectorized and recalled?

### Splitting into blocks

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

### Vectorization

Each block produces two things:

**Block content** (stored in every chunk's payload):
The full formatted text of all `user`, `assistant`, and `tool` messages in the block. `system` messages are excluded. Block 1's content looks like this:

```
[user]
Any new commits in the Axon repo recently?

[assistant]
Let me check.

[tool]
{"commits": [{"hash": "2abf025", "message": "refactor(tools): flatten tool store"}]}

[assistant]
One recent commit: 2abf025 — refactored the tool store, flattening the discovery flow.
```

**Child chunks** (the actual units sent to the embedding model):
Only `user` and `assistant` messages produce child chunks — `tool` messages are not embedded individually. Block 1 produces three child chunks: the user question, the first assistant reply, and the second assistant reply. Every chunk carries the full block content and a `parent_block_id` in its payload.

### Recall

At retrieval time, a query is embedded and matched against child chunks by vector similarity. The results are then deduplicated by `parent_block_id`, and the full block content is returned — not individual messages.

```
Query: "recent Axon changes"
  → hits the [user] chunk in Block 1 (closest match)
  → deduped to Block 1, returns the full content including the tool output and assistant's interpretation
```

Even if only one message in a block matched the query, the full conversation turn comes back — tool output included.
