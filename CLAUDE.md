# Claude Code Instructions

## Project Layout

```
skill-router/
├── skills/
│   └── skill-router/       ← the installable skill (this is what users install)
│       ├── SKILL.md        ← skill definition and workflow guide
│       ├── scripts/
│       │   ├── skill_router.py       ← main CLI
│       │   ├── scan_skills.py        ← agent detection and skill scanning
│       │   └── test_skill_router.py  ← unit tests
│       └── references/
│           ├── supported-agents.md   ← registry of 40+ supported agents
│           └── best-practices.md     ← skill quality guidelines
├── docs/
│   └── index.html          ← GitHub Pages landing page
└── .github/
    └── workflows/
        └── test.yml        ← CI
```

The `skills/` directory is just a container — **all changes go inside `skills/skill-router/`**.

## Running Tests

```bash
python -m pytest skills/skill-router/scripts/test_skill_router.py -v
```

## Testing the CLI

```bash
# Run from a project that has agent skill directories
python skills/skill-router/scripts/skill_router.py --list-skills
python skills/skill-router/scripts/skill_router.py --list-agents
```

## Code Style

- Python 3.9+, no external dependencies (stdlib only)
- Skill names must be kebab-case
- All CLI flags documented in `SKILL.md` command reference
