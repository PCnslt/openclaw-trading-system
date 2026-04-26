---
tags: [memory, curated, long-term]
---
# MEMORY.md — Long-Term Memory 🦞

## About the User
- **Name:** Shawn
- **Timezone:** America/New_York
- **Goal:** Build self-learning trading system for crypto, stocks, forex, options
- **Style:** Prefers sharp, analytical, zero-fluff communication with vault source citations
- **Capital preservation first** — never lose principal

## Projects
- **Trading System (active):** Vault-based self-learning trading AI. Memory systems, strategy development, mistake tracking, and performance metrics all live in the Obsidian vault.

## Decisions Log
| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-04-26 | Use vault-based paths for self-improving memory | Keeps everything in one searchable vault instead of split across ~/self-improving/ |
| 2026-04-26 | Install elite-longterm-memory | Adds WAL protocol (SESSION-STATE.md) and structured long-term memory |
| 2026-04-26 | Tag all vault files with frontmatter | Enables Obsidian Dataview queries and better semantic search |
| 2026-04-26 | Stick with DeepSeek (v4-flash default) | Cost-efficient. Escalation model: flash → chat → reasoner → v4-pro |

## Lessons Learned
- Hash-based fallback for embeddings works but isn't ideal — need Transformers.js model access or Python/sentence-transformers for real semantic search
- Self-improving skill's tiered memory (HOT/WARM/COLD) maps naturally to vault structure: 05_Meta/ → 03_Knowledge/ → 06_Archive/

## Preferences
- Default model: deepseek-v4-flash
- Cite vault sources in all answers
- Route corrections to 05_Meta/corrections.md immediately
- Compact reflections and corrections periodically (promote patterns after 3x)
- No fluff, no filler, just sharp analysis

---
*Curated memory — distill insights from daily logs here*
