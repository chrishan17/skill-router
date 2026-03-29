# skill-router

[![Version](https://img.shields.io/badge/version-1.0.1-black?style=flat-square)](skills/skill-router/SKILL.md)
[![Python](https://img.shields.io/badge/python-3.9%2B-black?style=flat-square)](skills/skill-router/scripts/)
[![License](https://img.shields.io/badge/license-MIT-black?style=flat-square)](LICENSE)
[![Agents](https://img.shields.io/badge/agents-40%2B-yellow?style=flat-square)](skills/skill-router/references/supported-agents.md)
[![GitHub Pages](https://img.shields.io/badge/docs-GitHub%20Pages-black?style=flat-square)](https://chrishan17.github.io/skill-router/)

An AI agent skill that wraps poorly-described skills in a **well-written router** — so your agent actually knows when to invoke them.

---

## The Problem

Skills only trigger when the agent understands their description well enough to match them to a user request. Most third-party skills are written without explicit trigger conditions: no *when to use*, no *when not to use*, just a vague summary of what the skill does.

The result: you install a skill and your agent never uses it — not because the skill is broken, but because the description doesn't tell the agent when it's relevant.

**skill-router** wraps one or more skills in a new router skill with a properly synthesized description following the **WHAT + WHEN + NOT-WHEN** pattern. The originals are untouched; the router makes them reliably invokable.

## How It Works

Third-party skills often ship with descriptions like this:

```
description: A tool for animating UI components.
```

No trigger conditions. No guidance on when to use it vs. something else. The agent sees it, doesn't know when it applies, and ignores it.

skill-router synthesizes a proper description and creates a router on top:

```
.claude/skills/
  animate/           ← original, untouched
  polish/            ← original, untouched
  critique/          ← original, untouched
  ui-design/         ← router created by skill-router
    SKILL.md         ← "Use when the user wants to improve visual quality,
    _manifest.json      add motion to interactions, or review UI before shipping.
                        Do NOT use for writing new components from scratch."
```

The router's `SKILL.md` contains:
- A synthesized description (WHAT + WHEN + NOT-WHEN) covering all sub-skills
- A Dispatch section with relative references to each original skill
- A Capabilities section listing each sub-skill's full description

**Original skills are never moved, merged, or modified.** They remain fully functional as direct slash commands and can still be invoked independently.

---

## Installation

```bash
npx skills install chrishan17/skill-router
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
| OpenClaw | `skills/` ¹ | `~/.openclaw/skills` |
| OpenHands | `.openhands/skills` | `~/.openhands/skills` |
| Qwen Code | `.qwen/skills` | `~/.qwen/skills` |
| Roo Code | `.roo/skills` | `~/.roo/skills` |
| Windsurf | `.windsurf/skills` | `~/.codeium/windsurf/skills` |
| Zencoder | `.zencoder/skills` | `~/.zencoder/skills` |

And [many more](skills/skill-router/references/supported-agents.md) — 40+ agents total.

> ¹ OpenClaw's `skills/` directory is a generic name shared by many projects. skill-router only detects OpenClaw when a `.openclaw/` directory is also present in the project root, to avoid false positives.

---

## References

- [`SKILL.md`](skills/skill-router/SKILL.md) — complete workflow guide for the skill itself
- [`references/supported-agents.md`](skills/skill-router/references/supported-agents.md) — full agent registry with path details
- [`references/best-practices.md`](skills/skill-router/references/best-practices.md) — skill quality checklist

---

## License

MIT
