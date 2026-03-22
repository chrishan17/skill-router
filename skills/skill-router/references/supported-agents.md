# Supported Coding Agents

Complete registry of all coding agents that support the Skills format, sourced from
[vercel-labs/skills](https://github.com/vercel-labs/skills/blob/main/src/agents.ts).

Last verified against upstream `main`: 2026-03-22

## Architecture

Each agent has two skill directories:

- **Local (project-level)**: Relative to the project root (e.g., `.claude/skills/`). Skills here
  apply only to that project.
- **Global (user-level)**: Absolute path under `$HOME` or `$XDG_CONFIG_HOME`. Skills here apply
  to all projects.

Project-local detection should use the explicit local directories listed below. Do not infer local
paths from global ones because some agents use different layouts in each context, such as
`cortex` (`.cortex/skills` locally vs `~/.snowflake/cortex/skills` globally) and OpenClaw
(`skills/` locally vs `~/.openclaw/skills` globally).

### Universal vs Non-Universal

**Universal agents** use the shared `.agents/skills` directory for local project skills. They share
a common skill location and don't need symlinks between each other.

**Non-universal agents** use their own dedicated directory (e.g., `.claude/skills/`). These need
symlinks from the canonical source if you want skills shared across tools.

## Universal Agents

These agents all read local project skills from `.agents/skills/`:

| Agent | Display Name | Global Skills Dir | Detection |
|-------|-------------|-------------------|-----------|
| amp | Amp | `$XDG_CONFIG_HOME/agents/skills` | `$XDG_CONFIG_HOME/amp` exists |
| antigravity | Antigravity | `~/.gemini/antigravity/skills` | `~/.gemini/antigravity` exists |
| cline | Cline | `~/.agents/skills` | `~/.cline` exists |
| codex | Codex | `~/.codex/skills` | `~/.codex` or `/etc/codex` exists |
| cursor | Cursor | `~/.cursor/skills` | `~/.cursor` exists |
| deepagents | Deep Agents | `~/.deepagents/agent/skills` | `~/.deepagents` exists |
| gemini-cli | Gemini CLI | `~/.gemini/skills` | `~/.gemini` exists |
| github-copilot | GitHub Copilot | `~/.copilot/skills` | `~/.copilot` exists |
| kimi-cli | Kimi Code CLI | `$XDG_CONFIG_HOME/agents/skills` | `~/.kimi` exists |
| opencode | OpenCode | `$XDG_CONFIG_HOME/opencode/skills` | `$XDG_CONFIG_HOME/opencode` exists |
| replit | Replit | `$XDG_CONFIG_HOME/agents/skills` | `.replit` in cwd (hidden from universal list) |
| warp | Warp | `~/.agents/skills` | `~/.warp` exists |
| universal | Universal | `$XDG_CONFIG_HOME/agents/skills` | Virtual entry, never auto-detected (hidden from universal list) |

> `$XDG_CONFIG_HOME` defaults to `~/.config` on all platforms when unset.
> Upstream excludes `replit` and `universal` from the visible "universal list" via
> `showInUniversalList: false`, even though both still use `.agents/skills`.

## Non-Universal Agents

Each uses its own dedicated skill directory:

| Agent | Display Name | Local Skills Dir | Global Skills Dir | Detection |
|-------|-------------|-----------------|-------------------|-----------|
| adal | AdaL | `.adal/skills` | `~/.adal/skills` | `~/.adal` exists |
| augment | Augment | `.augment/skills` | `~/.augment/skills` | `~/.augment` exists |
| claude-code | Claude Code | `.claude/skills` | `~/.claude/skills` | `~/.claude` exists |
| codebuddy | CodeBuddy | `.codebuddy/skills` | `~/.codebuddy/skills` | `.codebuddy` or `~/.codebuddy` exists |
| command-code | Command Code | `.commandcode/skills` | `~/.commandcode/skills` | `~/.commandcode` exists |
| continue | Continue | `.continue/skills` | `~/.continue/skills` | `.continue` or `~/.continue` exists |
| cortex | Cortex Code | `.cortex/skills` | `~/.snowflake/cortex/skills` | `~/.snowflake/cortex` exists |
| crush | Crush | `.crush/skills` | `~/.config/crush/skills` | `~/.config/crush` exists |
| droid | Droid | `.factory/skills` | `~/.factory/skills` | `~/.factory` exists |
| goose | Goose | `.goose/skills` | `$XDG_CONFIG_HOME/goose/skills` | `$XDG_CONFIG_HOME/goose` exists |
| iflow-cli | iFlow CLI | `.iflow/skills` | `~/.iflow/skills` | `~/.iflow` exists |
| junie | Junie | `.junie/skills` | `~/.junie/skills` | `~/.junie` exists |
| kilo | Kilo Code | `.kilocode/skills` | `~/.kilocode/skills` | `~/.kilocode` exists |
| kiro-cli | Kiro CLI | `.kiro/skills` | `~/.kiro/skills` | `~/.kiro` exists |
| kode | Kode | `.kode/skills` | `~/.kode/skills` | `~/.kode` exists |
| mcpjam | MCPJam | `.mcpjam/skills` | `~/.mcpjam/skills` | `~/.mcpjam` exists |
| mistral-vibe | Mistral Vibe | `.vibe/skills` | `~/.vibe/skills` | `~/.vibe` exists |
| mux | Mux | `.mux/skills` | `~/.mux/skills` | `~/.mux` exists |
| neovate | Neovate | `.neovate/skills` | `~/.neovate/skills` | `~/.neovate` exists |
| openclaw | OpenClaw | `skills` | `~/.openclaw/skills` | `~/.openclaw` or `~/.clawdbot` or `~/.moltbot` exists |
| openhands | OpenHands | `.openhands/skills` | `~/.openhands/skills` | `~/.openhands` exists |
| pi | Pi | `.pi/skills` | `~/.pi/agent/skills` | `~/.pi/agent` exists |
| pochi | Pochi | `.pochi/skills` | `~/.pochi/skills` | `~/.pochi` exists |
| qoder | Qoder | `.qoder/skills` | `~/.qoder/skills` | `~/.qoder` exists |
| qwen-code | Qwen Code | `.qwen/skills` | `~/.qwen/skills` | `~/.qwen` exists |
| roo | Roo Code | `.roo/skills` | `~/.roo/skills` | `~/.roo` exists |
| trae | Trae | `.trae/skills` | `~/.trae/skills` | `~/.trae` exists |
| trae-cn | Trae CN | `.trae/skills` | `~/.trae-cn/skills` | `~/.trae-cn` exists |
| windsurf | Windsurf | `.windsurf/skills` | `~/.codeium/windsurf/skills` | `~/.codeium/windsurf` exists |
| zencoder | Zencoder | `.zencoder/skills` | `~/.zencoder/skills` | `~/.zencoder` exists |

## Notable Quirks

- **OpenClaw**: Legacy directory support — checks `~/.clawdbot` and `~/.moltbot` as fallbacks
- **Codex**: Also checks `/etc/codex` (system-wide install)
- **Trae / Trae CN**: Share the same local dir (`.trae/skills`) but different global dirs
- **Cortex**: Global dir is under `~/.snowflake/` (Snowflake product)
- **Windsurf**: Global dir is under `~/.codeium/` (Codeium product)
- **Antigravity**: Global dir is under `~/.gemini/` (Google product)
- **Crush**: Uses `$XDG_CONFIG_HOME` style path (`~/.config/crush/`)

## Environment Variables

| Variable | Default | Used by |
|----------|---------|---------|
| `CODEX_HOME` | `~/.codex` | Codex global skills path |
| `CLAUDE_CONFIG_DIR` | `~/.claude` | Claude Code global skills path |
| `XDG_CONFIG_HOME` | `~/.config` | Amp, Goose, Kimi CLI, OpenCode, Replit, Universal |

## Implications for Skill Manager

### Symlink Strategy

When managing skills at the source level (`~/.agents/skills/`), changes automatically propagate
to universal agents whose global path is also `~/.agents/skills/` or `$XDG_CONFIG_HOME/agents/skills/`
(Amp, Kimi CLI, Replit via XDG).

For all other agents — including Codex, Cursor, Gemini CLI, GitHub Copilot, OpenCode, and all
non-universal agents — symlinks must be created/updated in each agent's own global skills directory,
since each has a dedicated path (e.g., `~/.cursor/skills/`, `~/.codex/skills/`).

The key paths to manage:

```
~/.agents/skills/<skill>/  →  source of truth
~/.claude/skills/<skill>   →  symlink (Claude Code)
~/.cursor/skills/<skill>   →  symlink (Cursor)
~/.codex/skills/<skill>    →  symlink (Codex)
~/.openclaw/skills/<skill> →  symlink (OpenClaw)
...
```

### Universal Directory as Canonical Source

Since many agents natively read from `.agents/skills/`, this directory is the natural canonical
source for skill management. Router merges happening here benefit the most agents without
requiring symlink updates.
