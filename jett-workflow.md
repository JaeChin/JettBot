# Jett Development Workflow

## Session Start

1. Always run `/jett-prime` first to load project context
2. Check `context/project_state.md` for current phase and status
3. Pick the next task from the current phase

## Development Cycle

```
/jett-prime → Understand context
     ↓
Pick task from current phase
     ↓
Implement (use relevant /jett-* command)
     ↓
/jett-test → Validate
     ↓
Update context/project_state.md
     ↓
Commit with descriptive message
```

## Context Updates

After every significant change, update the relevant context files:

- **New feature** → Update `project_state.md` (check off task, add new ones)
- **Model change** → Update `vram_budget.md` (measure actual VRAM)
- **Architecture change** → Update `architecture.md` + add ADR to `decisions.md`
- **Security change** → Update `security.md` + add ADR to `decisions.md`

## Commit Convention

```
feat(voice): add wake word detection with openWakeWord
fix(security): patch rate limiter bypass on concurrent requests
docs(context): update VRAM budget after faster-whisper measurement
refactor(llm): extract complexity classifier to separate module
test(security): add adversarial prompt injection tests
```

## Phase Progression

Move to the next phase only when:
1. All tasks in current phase are complete
2. Tests pass (`/jett-test`)
3. Context files are up to date
4. VRAM budget is validated

## Commands Reference

| Command | Purpose |
|---|---|
| `/jett-prime` | Load all project context |
| `/jett-voice` | Voice pipeline development |
| `/jett-llm` | LLM and hybrid routing |
| `/jett-security` | Security boundaries |
| `/jett-dashboard` | Dashboard development |
| `/jett-vps` | VPS infrastructure |
| `/jett-test` | Testing and validation |
