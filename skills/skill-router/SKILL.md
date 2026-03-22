---
name: skill-router
description: >
  Organises skills into a single-entry-point router that intelligently routes to a group of
  related sub-skills, reducing clutter and making large skill sets easier to invoke. Use when
  the user feels overwhelmed by too many skills, wants to combine related skills under one
  command, needs to tidy up after installing a skill suite, wants to refresh an existing router
  after sub-skills have changed, or wants to remove a router they no longer need. Do NOT use
  for creating brand-new skills (skill-creator), discovering or installing skills (find-skills),
  or general code review unrelated to skill organisation.
metadata:
  author: chrishan
  version: 1.0.1
  category: skill-management
  tags: "skills, router, merge, organize, group, multi-tool"
---

# Skill Router

Create skill routers — single-entry-point skills that route to a group of related sub-skills.

A router lives alongside its sub-skills in the agent's skills directory. It does not move
or modify the originals; it only adds a new routing skill on top.

## When to use

- User wants to reduce clutter from too many individual skills
- User wants to group related skills under a single router (e.g. skill-a + skill-b + skill-c → my-router)
- User wants to refresh a router after sub-skills have been updated
- User wants to remove a router they no longer need

## How routers work

```
.claude/skills/
  skill-a/        ← original, untouched
  skill-b/        ← original, untouched
  skill-c/        ← original, untouched
  my-router/      ← router created by skill-router
    SKILL.md      ← routes to ../skill-a, ../skill-b, ../skill-c
    _manifest.json
```

The router's `SKILL.md` contains:
- A synthesised description (WHAT + WHEN + NOT-WHEN) covering all sub-skills
- A Dispatch section with relative references (`../skill-name/SKILL.md`)
- A Capabilities section with each sub-skill's full description

## Workflow

**Step 1 — Detect agent tool directories.**

```bash
python <skill-path>/scripts/skill_router.py --list-skills
```

The script scans the current directory for known project-local skill directories
using the explicit `skillsDir` values from upstream `agents.ts` (for example
`.agents/skills/`, `.claude/skills/`, `.cortex/skills/`, or `skills/` for
OpenClaw). Do not derive project paths from global install locations because
some tools use different local and global directory layouts.

To see only skills not yet assigned to any router:
```bash
python <skill-path>/scripts/skill_router.py --list-skills --ungrouped
```

Handle the result:

- **None found** — tell the user no agent tool directories were found, and suggest running from the project root or using `--skills-dir`.
- **One found** — tell the user which agent was detected and show its available skills. Example: "Detected Claude Code at `.claude/skills/` with 12 skills: skill-a, skill-b, ..."
- **Multiple found** — list all detected agents and ask the user which one to use. Use `--list-agents --json` for structured output. Re-run with `--tool <tool-id>` to scope to that agent.

**Step 2 — Determine which skills to group.**

Two branches depending on what the user asked:

**Branch A — User already named the skills** (e.g. "group skill-a, skill-b, and skill-c"):

Proceed directly to Step 3 with those skills.

**Branch B — User wants suggestions** (e.g. "I have too many skills", "help me organise"):

**If the user has fewer than 4 ungrouped skills**, skip the analysis and ask directly: "Which skills would you like to group together?" There's no value in a router for 2–3 skills.

Run immediately without asking which strategy:

```bash
python <skill-path>/scripts/skill_router.py --list-skills-full --json
```

Analyse the full frontmatter of every skill using the **by-collection** strategy:

> Look at each skill's `name`, `description`, `tags`, `category`, `collection`, and `metadata`. Identify clusters that appear to come from the same install set, product suite, or thematic domain. Skills whose descriptions all mention the same keywords, or that share the same `category` tag, or whose `tags` overlap, likely belong together. Propose one router per identified cluster. Skills that fit no cluster remain ungrouped.

Then run `--list-strategies` to fetch saved strategies and present results + all options in one message:

```
Here's how I'd group your skills (by collection):

  • content-suite  → translate, summarise, rewrite, format-markdown
  • code-quality   → lint, test-runner, security-scan
  • (ungrouped)    → skill-router, find-skills

Shall I create these routers? Or try a different grouping strategy:

  1. By origin  — group by author / provenance / maintainer family
  2. Custom     — describe your own grouping logic (I'll save it for future use)
  [Only shown if saved strategies exist, e.g.]
  3. content-first — "Group all writing/publishing skills together, keep utility tools separate"
```

If the user picks an alternative strategy, apply it and loop back to show updated results:

- **By origin** — group by who made or maintains the skills. Use `--list-skills-full --json` and look at all available origin signals together: `author`, `source`, `homepage`, `repository`, `collection`, name patterns, and any consistent references in descriptions. Identify which skills clearly belong to the same maker, suite, or install source — whether that signal comes from a field or from the content itself. If all skills point to one origin, warn that this produces one large router and recommend by-collection instead.
- **Custom** — ask user to describe their logic, apply it to the `--list-skills-full --json` data, then offer to save: `--save-strategy <name> --strategy-description "..."`
- **Saved strategy** — apply its description as the grouping rationale against the same data.

Once the user confirms a set of groups, proceed to Step 3 for each group.

When you create routers using a saved or custom strategy, note the strategy name to the user so they know which strategy to re-apply after future skill installs.

**Step 3 — Read sub-skill descriptions and synthesize the router description.**

For each skill in the group, read its `description` field from its `SKILL.md` frontmatter. Then write the router description following "Generating the router description" below.

**Step 4 — Preview and confirm with the user.**

Run `--dry-run` first to generate the full SKILL.md preview without writing files:

```bash
python <skill-path>/scripts/skill_router.py \
  --name <name> \
  --skills <skill-1>,<skill-2>,<skill-3> \
  --description "<synthesised description>" \
  --dry-run
```

Show the user the generated SKILL.md output alongside the plan:

```
I'll create a router called "<name>" in <skills-dir>/ that routes to:
  - <skill-1>, <skill-2>, <skill-3>

Description: "<synthesised description>"

[Preview of generated SKILL.md shown above]

Proceed?
```

**Step 5 — Create the router.**

Re-run the same command without `--dry-run`:

```bash
python <skill-path>/scripts/skill_router.py \
  --name <name> \
  --skills <skill-1>,<skill-2>,<skill-3> \
  --description "<synthesised description>"
```

Repeat Steps 3–5 for each router group.

**Step 6 — Tell the user:**
- Each router is available as `/<router-name>`
- Sub-skills can still be invoked directly (`/<skill-name>`)
- Run `/skill-router` again to refresh a router after sub-skills are updated via `npx skills` or similar

## Refreshing a router

When the user asks to refresh an existing router, follow the same description-generation flow as creation — do not reuse the router's existing description:

1. Read the router's `_manifest.json` to find its sub-skills, or ask the user which router to refresh.
2. For each sub-skill, read its current `description` from its `SKILL.md` frontmatter.
3. Re-synthesize the router description from scratch following "Generating the router description" below.
4. Run `--dry-run` to preview, confirm with the user, then run without `--dry-run`:

```bash
python <skill-path>/scripts/skill_router.py \
  --refresh <name> \
  --description "<re-synthesised description>"
```

## Naming the router

The router name becomes a slash command (e.g. `/code-review`, `/content-pipeline`). A bad name makes it hard to remember and invoke.

**Rules:**

1. **Name the domain, not the list.** The name should express what the group collectively does or covers — not enumerate the skills inside it.
   - Good: `code-review`, `content-pipeline`, `data-tools`
   - Bad: `skill-a-skill-b-skill-c`, `skill-group-1`

2. **No vague catch-alls.** Words like `misc`, `other`, `general`, `utils`, `tools` (alone), `unknown`, `stuff` are not acceptable as the entire name. They carry no information.
   - Bad: `misc-skills`, `other-tools`, `general`
   - If skills truly don't share a domain, they shouldn't be in the same router.

3. **Suite prefix is acceptable — but add a domain suffix.** If skills clearly come from a named suite, the suite name can be a prefix, but it must be followed by what the suite does.
   - Good: `<suite>-content`, `<suite>-image-tools`
   - Acceptable: `<suite>-suite` (only when the suite itself is the identity and all skills are from it)
   - Bad: `<suite>` (too bare — says nothing about capability)

4. **Author alone is not a name.** Author usernames or company names are not router names. A router name must say something about what the skills do.

5. **When in doubt, ask "what would a user type to invoke this?"** If the name wouldn't help them recall when to use it, rename it.

**Quick reference:**

| Situation | Good name | Bad name |
|-----------|-----------|----------|
| Code analysis & review skills | `code-review` | `code`, `misc-tools` |
| Skills from a named suite | `<suite>-social`, `<suite>-images` | `<suite>`, `suite-stuff` |
| Quality-focused skills | `code-quality` or `design-quality` | `quality`, `misc-quality` |
| Skills from one author | `<author>-writing` | `<author>`, `author-tools` |
| No clear shared theme | (don't create a router) | `other-skills` |

## Generating the router description

The router description is the most important part — it's what the LLM uses to decide
whether to trigger this router. A weak description means wrong routing. Write it yourself
based on the sub-skills' actual content.

**Structure: WHAT + WHEN + NOT-WHEN** (total ≤ 1024 characters, no markdown)

### WHAT (1 sentence)

Summarise the problem domain this router covers — what class of user problem does it address?

Do NOT:
- Verbify skill names ("for linting code, scanning for issues, running tests...")
- Include origin or provenance ("from the X suite", "by <author>")
- Include implementation details ("uses OpenAI, Gemini, etc.")

Do:
- Write a domain statement that stands alone — someone unfamiliar with the skills should understand what this router is for
- Vary the sentence structure; avoid always defaulting to "A suite of X tools for Y"

Example:
```
Tools for reviewing and improving code quality, covering static analysis, test coverage, and security scanning.
```

### WHEN (1-2 sentences)

Answer: what does a user say or ask when they need this router?

**Critical rule: write user intent, not skill actions.**

For each sub-skill, ask "what problem is the user trying to solve?" — not "what does this skill do?" These are different questions. Use the sub-skill's trigger phrases as a starting point, then rephrase them in the user's voice.

| Skill-action framing (bad) | User-intent framing (good) |
|---------------------------|---------------------------|
| "run static analysis" | "find bugs in my code" / "check for issues before shipping" |
| "translate content" | "convert this to another language" / "make this multilingual" |
| "format or convert markdown" | "clean up my article" / "prepare this for publishing" |
| "normalize to design system" | "make this consistent with the rest of the app" |

- Do NOT name specific backends, APIs, or implementation choices unless the user would explicitly search for them by name
- Avoid vague phrases like "when the user needs help with X"

Example (good):
```
Use when the user wants to check their code for bugs, run tests, catch security issues, or get a thorough review before shipping.
```

Example (bad — skill-name verbing):
```
Use when the user wants to lint, test, scan, or analyse their code.
```

### NOT-WHEN (1 sentence)

Name adjacent skills or task types that should NOT be displaced:

```
Do NOT use for <adjacent task A>, <adjacent task B>, or <unrelated task type>.
```

Example:
```
Do NOT use for writing new code from scratch, managing deployments, or generating documentation.
```

### Constraints

- Total length ≤ 1024 characters
- No markdown (goes into YAML frontmatter `description: >`)
- Factually accurate — only claim what the sub-skills actually do
- If unsure about a sub-skill's purpose, re-read its full SKILL.md body

## Command reference

| Command | Usage |
|---------|-------|
| List skills | `skill_router.py --list-skills` |
| List ungrouped skills | `skill_router.py --list-skills --ungrouped` |
| List skills (full frontmatter) | `skill_router.py --list-skills-full --json` |
| List routers | `skill_router.py --list-routers` |
| List detected agents | `skill_router.py --list-agents` |
| Preview router (no write) | `skill_router.py --name <name> --skills <s1>,<s2> --description "..." --dry-run` |
| Create | `skill_router.py --name <name> --skills <s1>,<s2> --description "..."` |
| Create with description file | `skill_router.py --name <name> --skills <s1>,<s2> --description-file <path>` |
| Force overwrite | `skill_router.py --name <name> --skills <s1>,<s2> --force` |
| Refresh | `skill_router.py --refresh <name> --description "..."` |
| Add skill | `skill_router.py --add-skill <name> <skill>` |
| Remove skill | `skill_router.py --remove-skill <name> <skill>` |
| Delete | `skill_router.py --delete <name>` |
| Rename router | `skill_router.py --rename <old> <new>` |
| Save strategy | `skill_router.py --save-strategy <name> --strategy-description "..."` |
| List strategies | `skill_router.py --list-strategies` |

Common options: `--tool <tool-id>` (multi-agent), `--json`, `--skills-dir <path>`.

## Error handling

| Error | Cause | Fix |
|-------|-------|-----|
| Router already exists | `--name` matches existing dir | Use `--refresh` or `--delete` first |
| Invalid router name | Not kebab-case (e.g. "My Router!") | Use lowercase + hyphens only |
| Duplicate skill names | Same skill listed more than once in `--skills` | Remove duplicates before creating the router |
| Skill not found | Skill folder doesn't exist in skills dir | Check spelling; use `--list-skills` |
| No SKILL.md | Skill folder exists but has no SKILL.md | Reinstall the skill |
| No manifest | `--refresh`/`--delete` on a non-router dir | Only managed routers supported |
| No agent found | No tool dirs in current directory | Run from project root, or use `--skills-dir` |
| Skills directory not found | `--skills-dir` path doesn't exist | Check path spelling; must be an existing directory |
| Name conflict with existing skill | `--name` matches a non-router skill dir | Choose a different name; routers can't overwrite regular skills |
| Skill already in router | `--add-skill` targets a skill already in the router | No action needed; check with `--list-routers` |

## Reference

- `references/supported-agents.md` — upstream-aligned agent registry and local/global path matrix
- `references/best-practices.md` — Agent Skills Specification checklist
- `scripts/skill_router.py` — router create/refresh/add-skill/remove-skill/delete/list
- `scripts/scan_skills.py` — agent detection and skill scanning (used internally)
