# Skill Best Practices Checklist

Based on the [Agent Skills Specification](https://agentskills.io/specification) and
"The Complete Guide to Building Skills for Claude" by Anthropic.

## File Structure

- [ ] Folder named in kebab-case (e.g., `my-skill-name`)
- [ ] Contains `SKILL.md` (recommended casing; `skill.md` is also accepted)
- [ ] No `README.md` inside the skill folder
- [ ] Optional dirs: `scripts/`, `references/`, `assets/`

## YAML Frontmatter

Accepted top-level fields:

| Field | Required | Constraints |
|-------|----------|-------------|
| `name` | Yes | Max 64 chars. Lowercase alphanumeric + hyphens. No `--`, no leading/trailing `-`. Must match directory name. |
| `description` | Yes | Max 1024 chars. Non-empty. Describes what the skill does and when to use it. |
| `license` | No | License name or reference to a bundled license file. |
| `compatibility` | No | Max 500 chars. Environment requirements (intended product, system packages, etc.). |
| `metadata` | No | Arbitrary key-value mapping (`dict[str, str]`). Use for author, version, etc. |
| `allowed-tools` | No | Space-delimited list of pre-approved tools. Experimental. |
| `args` | No | Structured argument list for user-invokable skills. |
| `user-invokable` | No | Boolean flag for slash-command exposure. |
| `version` | No | Optional skill version string. |

Checklist:

- [ ] Starts and ends with `---` delimiters
- [ ] `name` matches the folder name exactly
- [ ] `name` is valid kebab-case: `^[a-z0-9]+(-[a-z0-9]+)*$`
- [ ] `name` ≤ 64 characters
- [ ] `description` present and non-empty
- [ ] `description` ≤ 1024 characters
- [ ] Description includes WHAT the skill does
- [ ] Description includes WHEN to use it (trigger conditions/phrases)
- [ ] Name does not start with "claude" or "anthropic" (reserved)
- [ ] No unknown top-level fields (only the accepted fields above)

## Description Quality

A good description answers two questions:
1. What does this skill enable the agent to do?
2. When should the agent load this skill?

### Good examples
- "Analyzes Figma design files and generates developer handoff documentation. Use when user uploads .fig files, asks for 'design specs', 'component documentation', or 'design-to-code handoff'."
- "Manages Linear project workflows including sprint planning, task creation, and status tracking. Use when user mentions 'sprint', 'Linear tasks', 'project planning', or asks to 'create tickets'."

### Bad examples
- "Helps with projects." (too vague)
- "Creates sophisticated multi-page documentation systems." (missing triggers)
- "Implements the Project entity model with hierarchical relationships." (too technical, no user triggers)

## Instructions Body

- [ ] Written in imperative form ("Run the script", not "You should run the script")
- [ ] Specific and actionable (not "validate things properly")
- [ ] Includes examples where helpful
- [ ] Error handling for common issues
- [ ] Under 500 lines (move detail to `references/`)
- [ ] References are clearly linked from the body with guidance on when to read them

## Progressive Disclosure

Three-level system:
1. **Metadata** (frontmatter): Always in context. Just name + description (~50-100 tokens)
2. **SKILL.md body**: Loaded when skill triggers. Core instructions (<5000 tokens recommended)
3. **Bundled resources**: Loaded on demand. Scripts, docs, assets (unlimited size)

Keep each level focused. Don't put everything in SKILL.md — use references for detailed docs.

## Validation

Use the official reference library to validate skills:

```bash
skills-ref validate ./my-skill
```

Or use the skill-manager validator, if your checkout includes `scripts/validate_skill.py`,
for extended checks (trigger quality, overlap detection):

```bash
python <skill-path>/scripts/validate_skill.py --all --json
```

## Common Issues

| Symptom | Fix |
|---------|-----|
| Skill never triggers | Make description more specific, add trigger phrases |
| Skill triggers too often | Add negative triggers ("Do NOT use for..."), be more specific |
| Instructions not followed | Put critical instructions at top, use ## Important headers, explain why |
| Slow / degraded responses | Move content to references, reduce SKILL.md size |
| Inconsistent results | Add explicit quality criteria, include validation steps |
