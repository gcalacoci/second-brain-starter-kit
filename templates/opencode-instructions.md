# Second Brain Agent Shim — OpenCode

This workspace uses a shared knowledge base at `{{WORKSPACE_DIR}}`.

Before any operation on the brain:
1. Read `{{WORKSPACE_DIR}}/SCHEMA.md`
2. Follow its architecture, frontmatter conventions, operations, and conflict protocol
3. Do not edit SCHEMA.md without telling the user

Quick commands:
- "add this" → ingest a link/file/text (kb-ingest skill)
- "what do I know about ___" → query the knowledge base (kb-query skill)
- "save this session" → capture conversation takeaways (kb-session-capture skill)
- "save that" → persist current answer as a new page
- "dream sequence" → lint/health check (kb-dream skill)
- "weekly review" → maintenance report (kb-weekly-review skill)

Git is local-only. Never push this repo.
