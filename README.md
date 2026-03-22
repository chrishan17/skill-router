# skill-router

[![Version](https://img.shields.io/badge/version-1.0.0-black?style=flat-square)](skills/skill-router/SKILL.md)
[![Python](https://img.shields.io/badge/python-3.9%2B-black?style=flat-square)](skills/skill-router/scripts/)
[![License](https://img.shields.io/badge/license-MIT-black?style=flat-square)](LICENSE)
[![Agents](https://img.shields.io/badge/agents-40%2B-yellow?style=flat-square)](skills/skill-router/references/supported-agents.md)
[![GitHub Pages](https://img.shields.io/badge/docs-GitHub%20Pages-black?style=flat-square)](https://chrishan17.github.io/skill-router/)

An AI agent skill that organises related skills into a **single-entry-point router** — reducing context window bloat and routing conflicts when you have many skills installed.

---

## The Problem

Every skill's description is loaded into the agent's context window on every turn, whether relevant or not. With 30+ skills, this consumes thousands of tokens and causes the agent to route incorrectly — loading the wrong skill, missing the right one, or simply making poorer decisions across the board.

**skill-router** solves this by grouping related skills behind a single router skill. Instead of N individual descriptions occupying context, one router description covers all of them.

## How It Works

```
Before                          After
──────────────────────           ──────────────────────
.claude/skills/                  .claude/skills/
  animate/                         animate/        ← untouched
  polish/                          polish/         ← untouched
  critique/                        critique/       ← untouched
  adapt/                           adapt/          ← untouched
  bolder/                          bolder/         ← untouched
  colorize/                        colorize/       ← untouched
  (6 descriptions loaded)          ui-design/      ← router
                                     SKILL.md      ← routes to all 6
                                     _manifest.json
                                   (1 description loaded)
```

The router's `SKILL.md` contains:
- A synthesised description covering all sub-skills (WHAT + WHEN + NOT-WHEN)
- A Dispatch section with relative references to each original skill
- A Capabilities section listing each sub-skill's full description

**Original skills are never moved, merged, or modified.** They remain fully functional as direct slash commands and can still be invoked independently.

---

## Installation

Copy the `skills/skill-router/` folder into your agent's skills directory:

```bash
# Claude Code (local project)
cp -r skills/skill-router/ .claude/skills/skill-router/

# Claude Code (global)
cp -r skills/skill-router/ ~/.claude/skills/skill-router/

# Any universal agent (.agents/skills)
cp -r skills/skill-router/ .agents/skills/skill-router/
```

Then tell your agent: `/skill-router` or `run skill-router`.

---

## Quick Start

skill-router follows a 6-step workflow:

| Step | Action |
|------|--------|
| 1. Detect | Find which agent tool directories exist in the current project |
| 2. Determine | Identify which skills to group (user-specified or auto-suggested) |
| 3. Synthesize | Read sub-skill descriptions and write the router description |
| 4. Preview | Dry-run to generate the full `SKILL.md` before writing |
| 5. Create | Write the router skill to the skills directory |
| 6. Explain | Tell the user how to invoke the router and sub-skills |

```bash
# List skills in the detected agent
python skills/skill-router/scripts/skill_router.py --list-skills

# Preview a router (no files written)
python skills/skill-router/scripts/skill_router.py \
  --name ui-design \
  --skills animate,polish,critique,adapt \
  --description "Tools for reviewing and improving UI quality..." \
  --dry-run

# Create the router
python skills/skill-router/scripts/skill_router.py \
  --name ui-design \
  --skills animate,polish,critique,adapt \
  --description "Tools for reviewing and improving UI quality..."
```

---

## Command Reference

| Command | Usage |
|---------|-------|
| List skills | `skill_router.py --list-skills` |
| List ungrouped skills | `skill_router.py --list-skills --ungrouped` |
| List skills (full frontmatter) | `skill_router.py --list-skills-full --json` |
| List routers | `skill_router.py --list-routers` |
| List detected agents | `skill_router.py --list-agents` |
| Preview router (no write) | `skill_router.py --name <name> --skills <s1>,<s2> --description "..." --dry-run` |
| Create router | `skill_router.py --name <name> --skills <s1>,<s2> --description "..."` |
| Force overwrite | `skill_router.py --name <name> --skills <s1>,<s2> --force` |
| Refresh router | `skill_router.py --refresh <name> --description "..."` |
| Add skill to router | `skill_router.py --add-skill <name> <skill>` |
| Remove skill from router | `skill_router.py --remove-skill <name> <skill>` |
| Delete router | `skill_router.py --delete <name>` |
| Rename router | `skill_router.py --rename <old> <new>` |
| Save grouping strategy | `skill_router.py --save-strategy <name> --strategy-description "..."` |
| List saved strategies | `skill_router.py --list-strategies` |

Common options: `--tool <tool-id>` (target a specific agent), `--json` (structured output), `--skills-dir <path>` (override detected path).

---

## Supported Agents

skill-router auto-detects which agents are installed by checking their known skill directories.

### Universal Agents (use `.agents/skills/`)

| Agent | Global Skills Dir |
|-------|------------------|
| Amp | `$XDG_CONFIG_HOME/agents/skills` |
| Cline | `~/.agents/skills` |
| Codex | `~/.codex/skills` |
| Cursor | `~/.cursor/skills` |
| Deep Agents | `~/.deepagents/agent/skills` |
| Gemini CLI | `~/.gemini/skills` |
| GitHub Copilot | `~/.copilot/skills` |
| Kimi Code CLI | `$XDG_CONFIG_HOME/agents/skills` |
| OpenCode | `$XDG_CONFIG_HOME/opencode/skills` |
| Warp | `~/.agents/skills` |

### Non-Universal Agents (dedicated skill directories)

| Agent | Local Skills Dir | Global Skills Dir |
|-------|-----------------|------------------|
| Claude Code | `.claude/skills` | `~/.claude/skills` |
| Augment | `.augment/skills` | `~/.augment/skills` |
| Continue | `.continue/skills` | `~/.continue/skills` |
| Cortex Code | `.cortex/skills` | `~/.snowflake/cortex/skills` |
| Goose | `.goose/skills` | `$XDG_CONFIG_HOME/goose/skills` |
| OpenClaw | `skills/` | `~/.openclaw/skills` |
| OpenHands | `.openhands/skills` | `~/.openhands/skills` |
| Qwen Code | `.qwen/skills` | `~/.qwen/skills` |
| Roo Code | `.roo/skills` | `~/.roo/skills` |
| Windsurf | `.windsurf/skills` | `~/.codeium/windsurf/skills` |
| Zencoder | `.zencoder/skills` | `~/.zencoder/skills` |

And [many more](skills/skill-router/references/supported-agents.md) — 40+ agents total.

---

## References

- [`SKILL.md`](skills/skill-router/SKILL.md) — complete workflow guide for the skill itself
- [`references/supported-agents.md`](skills/skill-router/references/supported-agents.md) — full agent registry with path details
- [`references/best-practices.md`](skills/skill-router/references/best-practices.md) — skill quality checklist

---

## License

MIT
