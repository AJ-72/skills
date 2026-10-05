# skills

Agent skills I've built during development. They follow the [Agent Skills](https://agentskills.io) `SKILL.md` format and work in Claude Code, claude.ai, OpenCode, and other compatible agents.

## Install

```bash
npx skills add AJ-72/skills
```

## Skills

| Skill | What it does |
|-------|--------------|
| [architecture-canvas](skills/architecture-canvas/SKILL.md) | Traces how events flow through a codebase (web services, JSP/.NET monoliths, Godot/Unity games) and renders a zoomable, pannable canvas you can step through flow by flow. Each arrow cites the `file:line` it was traced from, and a validator checks that those references exist. |
