# Agent Instructions

## What This Repo Is

This is **skill-router** — an AI agent skill that organises other skills into single-entry-point
routers. It reduces context window bloat and routing conflicts when many skills are installed.

The installable skill lives at `skills/skill-router/`. Everything else (docs, CI) supports
the repository, not the skill itself.

## Project Structure

```
skills/skill-router/        ← install this into your agent
  SKILL.md                  ← skill definition (frontmatter + workflow)
  scripts/
    skill_router.py         ← main CLI for creating/managing routers
    scan_skills.py          ← agent detection and skill directory scanning
    test_skill_router.py    ← unit tests
  references/
    supported-agents.md     ← 40+ supported agents with their skill paths
    best-practices.md       ← skill quality and naming guidelines
```

## Running Tests

```bash
python -m pytest skills/skill-router/scripts/test_skill_router.py -v
```

No external dependencies required — Python 3.9+ stdlib only.

## Contribution Notes

- Keep Python 3.9+ compatible (no walrus operator, no `match`)
- No external pip dependencies
- Skill names must be kebab-case: `^[a-z][a-z0-9]*(-[a-z0-9]+)*$`
- Test file lives alongside the scripts it tests
- All public-facing CLI flags must be documented in `skills/skill-router/SKILL.md`
