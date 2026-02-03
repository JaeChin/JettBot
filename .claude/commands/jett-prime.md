# Jett Prime

**Always run this first when starting work on Jett.**

## Load Project Context

Read these files in order:

1. `jett-workflow.md` - Overall project workflow and phases
2. `context/project_state.md` - Current phase and progress
3. `context/architecture.md` - System design decisions
4. `context/security.md` - Threat model and boundaries
5. `context/vram_budget.md` - GPU memory tracking
6. `context/decisions.md` - Technical choices with rationale

## After Loading, Report

Provide a brief status:

```markdown
## Jett Status

**Current Phase:** [1-6]
**Phase Progress:** [X of Y tasks complete]

**VRAM Status:**
- Allocated: X GB / 8 GB
- Headroom: Y GB

**Last Completed:**
- [most recent completed task]

**Next Up:**
- [immediate next task]

**Blockers:**
- [any issues from last session, or "None"]
```

## Rules

- Do NOT implement anything yet
- Do NOT assume context not in files
- If context files are missing, say so and offer to create them
- Flag any VRAM budget concerns immediately
