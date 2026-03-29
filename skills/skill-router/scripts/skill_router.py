#!/usr/bin/env python3
from __future__ import annotations

"""Create and manage skill routers — single-entry-point skills that route to sub-skills.

A skill router lives in the agent's skills directory alongside the skills it covers.
It does NOT move or modify the original skills.

Usage:
    # Create a router (auto-detects agent in current directory)
    python skill_router.py --name design-suite --skills audit,critique,adapt,harden

    # Specify tool when multiple agents are detected
    python skill_router.py --name design-suite --skills audit,critique --tool claude-code

    # Dry-run to preview
    python skill_router.py --name design-suite --skills audit,critique --dry-run

    # Refresh router after sub-skills are updated
    python skill_router.py --refresh design-suite

    # Add or remove a skill from an existing router
    python skill_router.py --add-skill design-suite adapt
    python skill_router.py --remove-skill design-suite adapt

    # List all available skills (and existing routers)
    python skill_router.py --list-skills

    # List all routers in the skills directory
    python skill_router.py --list-routers

    # Delete a router
    python skill_router.py --delete design-suite
"""

import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))
from scan_skills import expand_path, find_skill_md, parse_frontmatter


# ---------------------------------------------------------------------------
# Name validation
# ---------------------------------------------------------------------------

_ROUTER_NAME_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")


def _validate_router_name(name: str) -> str | None:
    """Return an error message if name is invalid, else None."""
    if not name:
        return "Router name cannot be empty"
    if len(name) > 64:
        return f"Router name '{name}' exceeds 64 characters"
    if not _ROUTER_NAME_RE.match(name):
        return (
            f"Invalid router name '{name}'. "
            "Must be lowercase alphanumeric with hyphens (e.g. design-quality). "
            "No leading/trailing hyphens, no consecutive hyphens."
        )
    return None


# ---------------------------------------------------------------------------
# Agent detection
# ---------------------------------------------------------------------------

_PROJECT_AGENT_RULES = [
    {"tool": "amp", "display_name": "Amp", "skills_dir": ".agents/skills"},
    {"tool": "antigravity", "display_name": "Antigravity", "skills_dir": ".agents/skills"},
    {"tool": "augment", "display_name": "Augment", "skills_dir": ".augment/skills"},
    {"tool": "claude-code", "display_name": "Claude Code", "skills_dir": ".claude/skills"},
    {"tool": "openclaw", "display_name": "OpenClaw", "skills_dir": "skills", "required_marker": ".openclaw"},
    {"tool": "cline", "display_name": "Cline", "skills_dir": ".agents/skills"},
    {"tool": "codebuddy", "display_name": "CodeBuddy", "skills_dir": ".codebuddy/skills"},
    {"tool": "codex", "display_name": "Codex", "skills_dir": ".agents/skills"},
    {"tool": "command-code", "display_name": "Command Code", "skills_dir": ".commandcode/skills"},
    {"tool": "continue", "display_name": "Continue", "skills_dir": ".continue/skills"},
    {"tool": "cortex", "display_name": "Cortex Code", "skills_dir": ".cortex/skills"},
    {"tool": "crush", "display_name": "Crush", "skills_dir": ".crush/skills"},
    {"tool": "cursor", "display_name": "Cursor", "skills_dir": ".agents/skills"},
    {"tool": "deepagents", "display_name": "Deep Agents", "skills_dir": ".agents/skills"},
    {"tool": "droid", "display_name": "Droid", "skills_dir": ".factory/skills"},
    {"tool": "gemini-cli", "display_name": "Gemini CLI", "skills_dir": ".agents/skills"},
    {"tool": "github-copilot", "display_name": "GitHub Copilot", "skills_dir": ".agents/skills"},
    {"tool": "goose", "display_name": "Goose", "skills_dir": ".goose/skills"},
    {"tool": "junie", "display_name": "Junie", "skills_dir": ".junie/skills"},
    {"tool": "iflow-cli", "display_name": "iFlow CLI", "skills_dir": ".iflow/skills"},
    {"tool": "kilo", "display_name": "Kilo Code", "skills_dir": ".kilocode/skills"},
    {"tool": "kimi-cli", "display_name": "Kimi Code CLI", "skills_dir": ".agents/skills"},
    {"tool": "kiro-cli", "display_name": "Kiro CLI", "skills_dir": ".kiro/skills"},
    {"tool": "kode", "display_name": "Kode", "skills_dir": ".kode/skills"},
    {"tool": "mcpjam", "display_name": "MCPJam", "skills_dir": ".mcpjam/skills"},
    {"tool": "mistral-vibe", "display_name": "Mistral Vibe", "skills_dir": ".vibe/skills"},
    {"tool": "mux", "display_name": "Mux", "skills_dir": ".mux/skills"},
    {"tool": "opencode", "display_name": "OpenCode", "skills_dir": ".agents/skills"},
    {"tool": "openhands", "display_name": "OpenHands", "skills_dir": ".openhands/skills"},
    {"tool": "pi", "display_name": "Pi", "skills_dir": ".pi/skills"},
    {"tool": "qoder", "display_name": "Qoder", "skills_dir": ".qoder/skills"},
    {"tool": "qwen-code", "display_name": "Qwen Code", "skills_dir": ".qwen/skills"},
    {
        "tool": "replit",
        "display_name": "Replit",
        "skills_dir": ".agents/skills",
        "show_in_universal_list": False,
    },
    {"tool": "roo", "display_name": "Roo Code", "skills_dir": ".roo/skills"},
    {"tool": "trae", "display_name": "Trae", "skills_dir": ".trae/skills"},
    {"tool": "trae-cn", "display_name": "Trae CN", "skills_dir": ".trae/skills"},
    {"tool": "warp", "display_name": "Warp", "skills_dir": ".agents/skills"},
    {"tool": "windsurf", "display_name": "Windsurf", "skills_dir": ".windsurf/skills"},
    {"tool": "zencoder", "display_name": "Zencoder", "skills_dir": ".zencoder/skills"},
    {"tool": "neovate", "display_name": "Neovate", "skills_dir": ".neovate/skills"},
    {"tool": "pochi", "display_name": "Pochi", "skills_dir": ".pochi/skills"},
    {"tool": "adal", "display_name": "AdaL", "skills_dir": ".adal/skills"},
    {
        "tool": "universal",
        "display_name": "Universal",
        "skills_dir": ".agents/skills",
        "show_in_universal_list": False,
    },
]


def _present_project_agent_rules(cwd: Path) -> list[dict]:
    """Return upstream-aligned agent rules whose project-local skills dir exists."""
    present: list[dict] = []
    for rule in _PROJECT_AGENT_RULES:
        project_path = cwd / rule["skills_dir"]
        if not project_path.is_dir():
            continue
        marker = rule.get("required_marker")
        if marker and not (cwd / marker).exists():
            continue
        present.append({**rule, "project_path": project_path})
    return present


def _group_present_agent_rules(present_rules: list[dict]) -> list[dict]:
    """Group present agent rules by their project-local skills directory."""
    groups: dict[str, dict] = {}
    for rule in present_rules:
        key = str(rule["project_path"].resolve())
        group = groups.setdefault(key, {
            "skills_dir": rule["project_path"],
            "relative_path": rule["skills_dir"],
            "rules": [],
        })
        group["rules"].append(rule)
    return list(groups.values())


def detect_project_agents(cwd: Path) -> list[dict]:
    """Detect agent tool directories present in the given project directory.

    Local project skill directories do not always mirror global install paths,
    so this uses explicit project-local rules instead of deriving from the
    global scan registry.
    """
    agents: list[dict] = []
    present_rules = _present_project_agent_rules(cwd)

    for group in _group_present_agent_rules(present_rules):
        visible_rules = [
            rule for rule in group["rules"]
            if rule.get("show_in_universal_list", True)
        ]
        if not visible_rules:
            continue
        if len(visible_rules) == 1:
            rule = visible_rules[0]
            agents.append({
                "tool": rule["tool"],
                "display_name": rule["display_name"],
                "skills_dir": group["skills_dir"],
            })
            continue
        display_name = (
            "Shared Agents"
            if group["relative_path"] == ".agents/skills"
            else " / ".join(rule["display_name"] for rule in visible_rules)
        )
        agents.append({
            "tool": "agents-shared" if group["relative_path"] == ".agents/skills" else visible_rules[0]["tool"],
            "display_name": display_name,
            "skills_dir": group["skills_dir"],
            "tool_aliases": [rule["tool"] for rule in visible_rules],
        })

    return agents


# ---------------------------------------------------------------------------
# Skill reading helpers
# ---------------------------------------------------------------------------

def _read_skill_field(skill_path: Path, field: str, default: str) -> str:
    skill_md = find_skill_md(skill_path)
    if skill_md is None:
        return default
    try:
        fm = parse_frontmatter(skill_md.read_text(encoding="utf-8"))
        return fm.get(field, default)
    except (OSError, UnicodeDecodeError) as e:
        print(f"Warning: cannot read {skill_md}: {e}", file=sys.stderr)
        return default


def _read_skill_name_and_description(skill_path: Path) -> tuple[str, str]:
    """Read name and description from a skill's SKILL.md in one pass."""
    skill_md = find_skill_md(skill_path)
    if skill_md is None:
        return skill_path.name, ""
    try:
        fm = parse_frontmatter(skill_md.read_text(encoding="utf-8"))
        return fm.get("name", skill_path.name), fm.get("description", "")
    except (OSError, UnicodeDecodeError) as e:
        print(f"Warning: cannot read {skill_md}: {e}", file=sys.stderr)
        return skill_path.name, ""


def read_skill_description(skill_path: Path) -> str:
    """Read the description field from a skill's SKILL.md."""
    return _read_skill_field(skill_path, "description", "")


def read_skill_name(skill_path: Path) -> str:
    """Read the name field from a skill's SKILL.md."""
    return _read_skill_field(skill_path, "name", skill_path.name)


# ---------------------------------------------------------------------------
# Router SKILL.md generation
# ---------------------------------------------------------------------------

def _wrap_yaml_description(text: str, indent: int = 2, width: int = 90) -> list[str]:
    """Wrap a YAML folded-string (>) value into consistently indented lines."""
    prefix = " " * indent
    paragraphs = re.split(r'\n\s*\n', text.strip())
    all_lines: list[str] = []
    for para_idx, para in enumerate(paragraphs):
        words = para.split()
        if not words:
            continue
        if para_idx > 0:
            all_lines.append(prefix)  # blank indented line between paragraphs
        current = prefix + words[0]
        for word in words[1:]:
            if len(current) + 1 + len(word) > width:
                all_lines.append(current)
                current = prefix + word
            else:
                current += " " + word
        all_lines.append(current)
    return all_lines if all_lines else [prefix]


def _build_fallback_description(router_name: str, skills: list[dict]) -> str:
    """Minimal description used when --description is not provided.

    For a high-quality description, let the LLM synthesize one by following the
    'Generating the router description' section in SKILL.md, then pass it via
    --description.
    """
    domain = router_name.replace("-suite", "").replace("-router", "").replace("-", " ")
    what = f"A suite of {domain} tools."
    when = f" Use when the request involves {', '.join(s['name'] for s in skills)}."
    not_when = f" Do NOT use for requests outside these {domain} capabilities."
    return (what + when + not_when)[:1024]


def _find_duplicate_names(names: list[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for name in names:
        if name in seen:
            duplicates.add(name)
        seen.add(name)
    return sorted(duplicates)


def generate_router_skill_md(
    router_name: str,
    skills: list[dict],
    skills_dir: Path,
    description: str = "",
) -> str:
    """Generate a spec-compliant SKILL.md for a skill router."""
    desc = description[:1024] if description else _build_fallback_description(router_name, skills)

    lines: list[str] = []

    lines += [
        "---",
        f"name: {router_name}",
        "description: >",
    ]
    lines.extend(_wrap_yaml_description(desc))
    lines += [
        "user-invokable: true",
        "args:",
        "  - name: skill",
        "    description: >",
    ]
    skill_names_str = ", ".join(f'"{s["name"]}"' for s in skills)
    lines.append(f'      Name of a specific sub-skill to invoke directly. Available: {skill_names_str}.')
    lines += [
        "    required: false",
        "metadata:",
        '  category: "router"',
        f'  merged_count: "{len(skills)}"',
        "---",
        "",
    ]

    title = router_name.replace("-", " ").title()
    lines += [
        f"# {title}",
        "",
        f"Routes requests to one of {len(skills)} sub-skills. "
        "Read the relevant sub-skill's full instructions before acting.",
        "",
    ]

    lines += [
        "## Dispatch",
        "",
        f"When the user specifies a sub-skill (e.g. `/{router_name} <skill>`), "
        "load that skill's instructions directly.",
        "",
    ]
    for s in skills:
        ref = f"../{s['folder_name']}/SKILL.md"
        lines.append(f"- **`{s['name']}`** → read `{ref}`")
    lines += [
        "",
        "If the name doesn't match, suggest the closest match.",
        "",
    ]

    lines += [
        "## Matching",
        "",
        "When no sub-skill is specified, pick based on the user's request:",
        "",
        "1. **Single clear match** — load that sub-skill's instructions directly.",
        "2. **Multiple possible matches** — list candidates and ask the user to choose.",
        "3. **No match** — show the capabilities below and ask what they need.",
        "",
    ]

    lines += ["## Capabilities", ""]
    for s in skills:
        ref = f"../{s['folder_name']}/SKILL.md"
        lines += [
            f"### {s['name']}",
            "",
            s.get("description", ""),
            "",
            f"Full instructions: `{ref}`",
            "",
        ]

    lines += [
        "## Examples",
        "",
        "```",
        f"/{router_name}",
        "```",
        "",
        "```",
    ]
    if skills:
        lines.append(f"/{router_name} {skills[0]['name']}")
    lines += ["```", ""]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------

def create_manifest(
    router_name: str,
    skills: list[dict],
    skills_dir: Path,
    description: str = "",
) -> dict:
    now = datetime.now(tz=timezone.utc).isoformat()
    manifest = {
        "router_name": router_name,
        "skills_dir": str(skills_dir),
        "created": now,
        "last_refreshed": now,
        "skills": [
            {
                "name": s["name"],
                "folder_name": s["folder_name"],
                "description_at_merge": s.get("description", ""),
            }
            for s in skills
        ],
    }
    if description:
        manifest["router_description"] = description[:1024]
        manifest["description_source"] = "custom"
    return manifest


def load_manifest(router_path: Path) -> dict | None:
    manifest_path = router_path / "_manifest.json"
    if not manifest_path.exists():
        return None
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"Warning: cannot read manifest {manifest_path}: {e}", file=sys.stderr)
        return None


def _load_skill_entries_from_manifest(
    manifest: dict,
    skills_dir: Path,
    not_found: list[str] | None = None,
) -> list[dict]:
    """Load current skill data for all skills listed in a manifest."""
    entries = []
    for skill_info in manifest["skills"]:
        original = skills_dir / skill_info["folder_name"]
        if not original.exists():
            if not_found is not None:
                not_found.append(skill_info["folder_name"])
            continue
        entries.append({
            "name": skill_info["name"],
            "folder_name": skill_info["folder_name"],
            "description": (
                read_skill_description(original)
                or skill_info.get("description_at_merge", "")
            ),
        })
    return entries


def _save_router(
    router_path: Path,
    router_name: str,
    skill_entries: list[dict],
    manifest: dict,
    skills_dir: Path,
    description: str = "",
) -> None:
    """Write SKILL.md and _manifest.json for a router."""
    effective_description = description[:1024] if description else ""
    if effective_description:
        manifest["router_description"] = effective_description
        manifest["description_source"] = "custom"
    elif manifest.get("description_source") == "custom" and manifest.get("router_description"):
        effective_description = str(manifest["router_description"])[:1024]
    else:
        manifest.pop("router_description", None)
        manifest.pop("description_source", None)

    manifest["last_refreshed"] = datetime.now(tz=timezone.utc).isoformat()
    manifest["skills"] = [
        {
            "name": s["name"],
            "folder_name": s["folder_name"],
            "description_at_merge": s.get("description", ""),
        }
        for s in skill_entries
    ]
    skill_md = generate_router_skill_md(
        router_name, skill_entries, skills_dir, effective_description,
    )
    (router_path / "SKILL.md").write_text(skill_md, encoding="utf-8")
    (router_path / "_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _effective_router_description(manifest: dict, description: str = "") -> str:
    """Return the description that should be used for a generated router preview."""
    if description:
        return description[:1024]
    if manifest.get("description_source") == "custom" and manifest.get("router_description"):
        return str(manifest["router_description"])[:1024]
    return ""

def _resolve_source_skills_dir(manifest: dict, skills_dir: Path, router_path: Path) -> Path:
    """Resolve source skills dir from manifest, falling back to the router's parent."""
    source = Path(manifest.get("skills_dir", str(skills_dir)))
    return source if source.is_dir() else router_path.parent


def _filter_ungrouped_skills(skills: list[dict]) -> list[dict]:
    """Return only skills that are not grouped under any router."""
    in_router: set[str] = set()
    for s in skills:
        if s["is_router"]:
            in_router.update(s["router_skills"])
    return [s for s in skills if not s["is_router"] and s["name"] not in in_router]


# ---------------------------------------------------------------------------
# Sub-skill invocation control
# ---------------------------------------------------------------------------

def _set_disable_model_invocation_in_text(content: str, enable: bool) -> tuple[str, bool]:
    """Add or remove ``disable-model-invocation: true`` in a SKILL.md frontmatter.

    Returns ``(new_content, was_changed)``.  Only the first frontmatter block is
    modified.  When *enable* is True the field is inserted just before the closing
    ``---``; when False the field line is removed entirely.
    """
    lines = content.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return content, False

    close_idx: int | None = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            close_idx = i
            break
    if close_idx is None:
        return content, False

    field_idx: int | None = None
    for i in range(1, close_idx):
        if lines[i].startswith("disable-model-invocation:"):
            field_idx = i
            break

    if enable:
        if field_idx is not None:
            current_val = lines[field_idx].split(":", 1)[1].strip().lower()
            if current_val == "true":
                return content, False  # already enabled — no change needed
            lines[field_idx] = "disable-model-invocation: true\n"
        else:
            lines.insert(close_idx, "disable-model-invocation: true\n")
    else:
        if field_idx is None:
            return content, False  # field absent — nothing to remove
        lines.pop(field_idx)

    return "".join(lines), True


def set_skill_disable_model_invocation(skill_path: Path, enable: bool) -> bool:
    """Write ``disable-model-invocation: true/false`` to a skill's SKILL.md.

    Returns True if the file was actually modified.
    """
    skill_md = find_skill_md(skill_path)
    if skill_md is None:
        return False
    try:
        content = skill_md.read_text(encoding="utf-8")
        new_content, changed = _set_disable_model_invocation_in_text(content, enable)
        if changed:
            skill_md.write_text(new_content, encoding="utf-8")
        return changed
    except (OSError, UnicodeDecodeError):
        return False


def _get_skill_disable_model_invocation(skill_path: Path) -> bool | None:
    """Return True/False if the field is explicitly set, None if absent."""
    skill_md = find_skill_md(skill_path)
    if skill_md is None:
        return None
    try:
        fm = parse_frontmatter(skill_md.read_text(encoding="utf-8"))
        if "disable-model-invocation" not in fm:
            return None
        val = fm["disable-model-invocation"]
        if isinstance(val, bool):
            return val
        return str(val).lower() == "true"
    except (OSError, UnicodeDecodeError):
        return None


def _suppress_subskill_invocations(
    skills_dir: Path,
    skill_folder_names: list[str],
    manifest: dict,
) -> list[str]:
    """Set ``disable-model-invocation: true`` on sub-skills that don't already
    have the field set (in either direction).

    Only skills whose frontmatter has *no* ``disable-model-invocation`` field
    are modified.  Skills that already carry the field (true or false) are left
    untouched so we don't override an explicit author choice.

    Returns the list of folder names that were actually modified.
    """
    already_tracked: set[str] = set(manifest.get("invocation_disabled_by_router", []))
    newly_disabled: list[str] = []
    for folder_name in skill_folder_names:
        if folder_name in already_tracked:
            continue
        skill_path = skills_dir / folder_name
        if not skill_path.is_dir():
            continue
        if _get_skill_disable_model_invocation(skill_path) is not None:
            continue  # field already set explicitly — don't touch it
        if set_skill_disable_model_invocation(skill_path, True):
            newly_disabled.append(folder_name)
    return newly_disabled


def _restore_subskill_invocations(skills_dir: Path, manifest: dict) -> list[str]:
    """Remove ``disable-model-invocation: true`` from skills we previously suppressed.

    Only removes the field from skills listed in ``manifest["invocation_disabled_by_router"]``.
    Returns the list of folder names that were actually restored.
    """
    to_restore: list[str] = manifest.get("invocation_disabled_by_router", [])
    restored: list[str] = []
    for folder_name in to_restore:
        skill_path = skills_dir / folder_name
        if not skill_path.is_dir():
            continue
        if set_skill_disable_model_invocation(skill_path, False):
            restored.append(folder_name)
    return restored


# ---------------------------------------------------------------------------
# Core operations
# ---------------------------------------------------------------------------

def create_router(
    router_name: str,
    skill_names: list[str],
    skills_dir: Path,
    description: str = "",
    dry_run: bool = False,
    force: bool = False,
) -> dict:
    """Create a skill router in skills_dir."""
    result: dict = {
        "router_name": router_name,
        "skills_dir": str(skills_dir),
        "dry_run": dry_run,
        "skills": [],
        "errors": [],
    }

    name_err = _validate_router_name(router_name)
    if name_err:
        result["errors"].append(name_err)
        return result

    duplicates = _find_duplicate_names(skill_names)
    if duplicates:
        result["errors"].append(
            f"Duplicate skills specified: {', '.join(duplicates)}"
        )
        return result

    router_path = skills_dir / router_name
    if router_path.exists():
        if force and (router_path / "_manifest.json").exists():
            shutil.rmtree(str(router_path))
        elif (router_path / "_manifest.json").exists():
            result["errors"].append(
                f"Router '{router_name}' already exists at {router_path}. "
                "Use --refresh to update it or --delete to remove it first."
            )
            return result
        else:
            result["errors"].append(
                f"A skill named '{router_name}' already exists at {router_path}. "
                "Choose a different name for the router."
            )
            return result

    skill_entries: list[dict] = []
    for name in skill_names:
        skill_path = skills_dir / name
        if not skill_path.exists():
            result["errors"].append(f"Skill '{name}' not found in {skills_dir}")
            continue
        resolved = skill_path.resolve() if skill_path.is_symlink() else skill_path
        if find_skill_md(resolved) is None:
            result["errors"].append(f"Skill '{name}' has no SKILL.md")
            continue
        skill_name_val, skill_desc = _read_skill_name_and_description(resolved)
        skill_entries.append({
            "name": skill_name_val,
            "folder_name": name,
            "description": skill_desc,
        })

    if result["errors"]:
        return result

    if not skill_entries:
        result["errors"].append("No valid skills to route")
        return result

    result["skills"] = [
        {"name": e["name"], "folder_name": e["folder_name"]}
        for e in skill_entries
    ]
    result["router_path"] = str(router_path)

    if dry_run:
        result["preview"] = generate_router_skill_md(
            router_name,
            skill_entries,
            skills_dir,
            description,
        )
        return result

    router_path.mkdir(parents=True, exist_ok=True)
    manifest = create_manifest(router_name, skill_entries, skills_dir, description)

    # Pre-compute which sub-skills need invocation suppressed so the manifest
    # is written with the correct tracking list in a single _save_router call.
    skills_to_disable = [
        e["folder_name"] for e in skill_entries
        if _get_skill_disable_model_invocation(skills_dir / e["folder_name"]) is None
    ]
    if skills_to_disable:
        manifest["invocation_disabled_by_router"] = skills_to_disable

    _save_router(router_path, router_name, skill_entries, manifest, skills_dir, description)

    # Apply the flag to sub-skill files after the router itself is written.
    for folder_name in skills_to_disable:
        set_skill_disable_model_invocation(skills_dir / folder_name, True)

    result["created"] = str(router_path)
    result["invocation_disabled"] = skills_to_disable
    return result


def refresh_router(
    router_name: str,
    skills_dir: Path,
    description: str = "",
    dry_run: bool = False,
) -> dict:
    """Regenerate router SKILL.md from current sub-skill descriptions.

    Args:
        description: Optional new description. If omitted, preserve a previously
                     saved custom description; otherwise regenerate the fallback.
                     Pass the LLM-synthesized description for best quality.
    """
    result: dict = {
        "router_name": router_name,
        "dry_run": dry_run,
        "refreshed": [],
        "not_found": [],
        "errors": [],
    }

    router_path = skills_dir / router_name
    manifest = load_manifest(router_path)
    if not manifest:
        result["errors"].append(f"No manifest found at {router_path}/_manifest.json")
        return result

    source_skills_dir = _resolve_source_skills_dir(manifest, skills_dir, router_path)
    skill_entries = _load_skill_entries_from_manifest(
        manifest, source_skills_dir, not_found=result["not_found"]
    )
    result["refreshed"] = [s["folder_name"] for s in skill_entries]

    if dry_run and skill_entries:
        result["preview"] = generate_router_skill_md(
            router_name,
            skill_entries,
            source_skills_dir,
            _effective_router_description(manifest, description),
        )
        return result

    if not skill_entries:
        return result

    _save_router(router_path, router_name, skill_entries, manifest, source_skills_dir, description)
    result["updated"] = str(router_path / "SKILL.md")
    return result


def delete_router(router_name: str, skills_dir: Path, dry_run: bool = False) -> dict:
    """Remove a skill router. Sub-skills are NOT touched."""
    result: dict = {
        "router_name": router_name,
        "dry_run": dry_run,
        "errors": [],
    }

    router_path = skills_dir / router_name
    if not router_path.exists():
        result["errors"].append(f"Router '{router_name}' not found at {router_path}")
        return result

    if not (router_path / "_manifest.json").exists():
        result["errors"].append(
            f"'{router_name}' has no _manifest.json — not a managed router"
        )
        return result

    result["router_path"] = str(router_path)

    if dry_run:
        return result

    # Restore sub-skill invocation control before the router directory is removed.
    manifest = load_manifest(router_path)
    if manifest:
        source_skills_dir = _resolve_source_skills_dir(manifest, skills_dir, router_path)
        result["invocation_restored"] = _restore_subskill_invocations(source_skills_dir, manifest)

    # Warn about unexpected files beyond known router files
    known_files = {"SKILL.md", "_manifest.json"}
    extra = [f.name for f in router_path.iterdir() if f.is_file() and f.name not in known_files]
    if extra:
        print(f"Warning: removing router '{router_name}' also deletes: {', '.join(extra)}", file=sys.stderr)

    try:
        shutil.rmtree(str(router_path))
        result["removed"] = True
    except OSError as e:
        result["errors"].append(f"Failed to remove router: {e}")

    return result


def add_skill(
    router_name: str,
    skill_name: str,
    skills_dir: Path,
    dry_run: bool = False,
) -> dict:
    """Add a skill to an existing router."""
    result: dict = {
        "router_name": router_name,
        "skill_name": skill_name,
        "dry_run": dry_run,
        "errors": [],
    }

    router_path = skills_dir / router_name
    manifest = load_manifest(router_path)
    if not manifest:
        result["errors"].append(f"No manifest found at {router_path}/_manifest.json")
        return result

    existing = [s["folder_name"] for s in manifest["skills"]]
    if skill_name in existing:
        result["errors"].append(f"'{skill_name}' is already in router '{router_name}'")
        return result

    skill_path = skills_dir / skill_name
    if not skill_path.exists():
        result["errors"].append(f"Skill '{skill_name}' not found in {skills_dir}")
        return result
    resolved = skill_path.resolve() if skill_path.is_symlink() else skill_path
    if find_skill_md(resolved) is None:
        result["errors"].append(f"Skill '{skill_name}' has no SKILL.md")
        return result

    if dry_run:
        result["total_skills"] = len(manifest["skills"]) + 1
        return result

    # Add to manifest and regenerate
    skill_name_val, skill_desc = _read_skill_name_and_description(resolved)
    source_skills_dir = _resolve_source_skills_dir(manifest, skills_dir, router_path)

    # Pre-compute invocation control so the manifest is correct in one write.
    should_disable = _get_skill_disable_model_invocation(source_skills_dir / skill_name) is None
    if should_disable:
        disabled = list(manifest.get("invocation_disabled_by_router", []))
        disabled.append(skill_name)
        manifest["invocation_disabled_by_router"] = disabled

    manifest["skills"].append({
        "name": skill_name_val,
        "folder_name": skill_name,
        "description_at_merge": skill_desc,
    })
    skill_entries = _load_skill_entries_from_manifest(manifest, source_skills_dir)
    _save_router(router_path, router_name, skill_entries, manifest, source_skills_dir)

    if should_disable:
        set_skill_disable_model_invocation(source_skills_dir / skill_name, True)
        result["invocation_disabled"] = [skill_name]

    result["total_skills"] = len(skill_entries)
    return result


def remove_skill(
    router_name: str,
    skill_name: str,
    skills_dir: Path,
    dry_run: bool = False,
) -> dict:
    """Remove a skill from an existing router."""
    result: dict = {
        "router_name": router_name,
        "skill_name": skill_name,
        "dry_run": dry_run,
        "errors": [],
    }

    router_path = skills_dir / router_name
    manifest = load_manifest(router_path)
    if not manifest:
        result["errors"].append(f"No manifest found at {router_path}/_manifest.json")
        return result

    existing = [s["folder_name"] for s in manifest["skills"]]
    if skill_name not in existing:
        result["errors"].append(f"'{skill_name}' is not in router '{router_name}'")
        return result

    if len(manifest["skills"]) <= 1:
        result["errors"].append(
            "Cannot remove the last skill from a router. "
            "Use --delete to remove the router entirely."
        )
        return result

    if dry_run:
        result["total_skills"] = len(manifest["skills"]) - 1
        return result

    source_skills_dir = _resolve_source_skills_dir(manifest, skills_dir, router_path)

    # Pre-compute invocation restore so the manifest is correct in one write.
    disabled = list(manifest.get("invocation_disabled_by_router", []))
    should_restore = skill_name in disabled
    if should_restore:
        disabled.remove(skill_name)
        manifest["invocation_disabled_by_router"] = disabled

    manifest["skills"] = [s for s in manifest["skills"] if s["folder_name"] != skill_name]
    skill_entries = _load_skill_entries_from_manifest(manifest, source_skills_dir)
    _save_router(router_path, router_name, skill_entries, manifest, source_skills_dir)

    if should_restore:
        set_skill_disable_model_invocation(source_skills_dir / skill_name, False)
        result["invocation_restored"] = [skill_name]

    result["total_skills"] = len(skill_entries)
    return result


def rename_router(
    old_name: str,
    new_name: str,
    skills_dir: Path,
    dry_run: bool = False,
) -> dict:
    """Rename an existing router."""
    result: dict = {
        "old_name": old_name,
        "new_name": new_name,
        "dry_run": dry_run,
        "errors": [],
    }

    name_err = _validate_router_name(new_name)
    if name_err:
        result["errors"].append(name_err)
        return result

    old_path = skills_dir / old_name
    new_path = skills_dir / new_name

    manifest = load_manifest(old_path)
    if not manifest:
        result["errors"].append(f"No manifest found at {old_path}/_manifest.json")
        return result

    if new_path.exists():
        result["errors"].append(f"'{new_name}' already exists at {new_path}")
        return result

    result["old_path"] = str(old_path)
    result["new_path"] = str(new_path)

    if dry_run:
        return result

    # Update manifest
    manifest["router_name"] = new_name

    # Move directory
    old_path.rename(new_path)

    # Regenerate SKILL.md with new name (_save_router preserves custom description automatically)
    source_skills_dir = _resolve_source_skills_dir(manifest, skills_dir, new_path)
    skill_entries = _load_skill_entries_from_manifest(manifest, source_skills_dir)
    _save_router(new_path, new_name, skill_entries, manifest, source_skills_dir)

    return result


def list_routers(skills_dir: Path) -> list[dict]:
    """List all managed routers in skills_dir."""
    routers = []
    if not skills_dir.is_dir():
        return routers
    for entry in sorted(skills_dir.iterdir()):
        if entry.is_dir():
            manifest = load_manifest(entry)
            if manifest:
                routers.append({
                    "name": manifest["router_name"],
                    "skills": [s["folder_name"] for s in manifest["skills"]],
                    "created": manifest.get("created", ""),
                    "last_refreshed": manifest.get("last_refreshed", ""),
                })
    return routers


def read_skill_frontmatter(skill_path: Path) -> dict:
    """Read the full frontmatter from a skill's SKILL.md."""
    skill_md = find_skill_md(skill_path)
    if skill_md is None:
        return {}
    try:
        content = skill_md.read_text(encoding="utf-8")
        return parse_frontmatter(content)
    except (OSError, UnicodeDecodeError):
        return {}


def list_skills(skills_dir: Path, include_frontmatter: bool = False) -> list[dict]:
    """List all skills in skills_dir, marking routers separately.

    Args:
        include_frontmatter: If True, include full frontmatter for each skill.
                             Used by LLM for by-collection grouping analysis.
    """
    skills = []
    routers = []
    if not skills_dir.is_dir():
        return []
    for entry in sorted(skills_dir.iterdir()):
        if entry.name.startswith("."):
            continue
        if not entry.is_dir():
            continue
        manifest = load_manifest(entry)
        if manifest:
            routers.append({
                "name": entry.name,
                "is_router": True,
                "router_skills": [s["folder_name"] for s in manifest["skills"]],
                "description": "",
            })
        else:
            resolved = entry.resolve() if entry.is_symlink() else entry
            if find_skill_md(resolved) is None:
                continue
            if include_frontmatter:
                fm = read_skill_frontmatter(resolved)
                item: dict = {
                    "name": entry.name,
                    "is_router": False,
                    "description": fm.get("description", ""),
                    "frontmatter": fm,
                }
            else:
                item = {
                    "name": entry.name,
                    "is_router": False,
                    "description": read_skill_description(resolved),
                }
            skills.append(item)
    return skills + routers


# ---------------------------------------------------------------------------
# Strategy persistence  (~/.config/skill-router/config.json)
# ---------------------------------------------------------------------------

_XDG_CONFIG_HOME = (os.environ.get("XDG_CONFIG_HOME") or "").strip() or str(Path.home() / ".config")
_CONFIG_PATH = Path(_XDG_CONFIG_HOME) / "skill-router" / "config.json"


def _load_config() -> dict:
    if not _CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save_config(config: dict) -> None:
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")


def save_strategy(name: str, description: str) -> dict:
    """Save a user-defined grouping strategy to the config file."""
    config = _load_config()
    config.setdefault("strategies", {})[name] = {"description": description}
    _save_config(config)
    return {"saved": name, "description": description, "errors": []}


def list_strategies() -> dict:
    """Return all user-defined strategies from the config file."""
    config = _load_config()
    return config.get("strategies", {})


# ---------------------------------------------------------------------------
# CLI output formatting
# ---------------------------------------------------------------------------

def _print_errors(errors: list[str]) -> None:
    for e in errors:
        print(f"Error: {e}", file=sys.stderr)


def _print_create(result: dict) -> None:
    if result["errors"]:
        _print_errors(result["errors"])
        return
    skill_names = ", ".join(s["name"] for s in result["skills"])
    prefix = "[dry-run] Would create" if result["dry_run"] else "Created"
    print(f"{prefix} router '{result['router_name']}'")
    print(f"  Location: {result['router_path']}")
    print(f"  Skills: {skill_names}")
    if result["dry_run"] and result.get("preview"):
        print()
        print(result["preview"])


def _print_refresh(result: dict) -> None:
    if result["errors"]:
        _print_errors(result["errors"])
        return
    updated = result["refreshed"]
    not_found = result["not_found"]
    prefix = "[dry-run] Would refresh" if result["dry_run"] else "Refreshed"
    suffix = f" ({len(not_found)} missing: {', '.join(not_found)})" if not_found else ""
    print(f"{prefix} router '{result['router_name']}'{suffix}")
    print(f"  Skills: {', '.join(updated)}")
    if result["dry_run"] and result.get("preview"):
        print()
        print(result["preview"])


def _print_delete(result: dict) -> None:
    if result["errors"]:
        _print_errors(result["errors"])
        return
    prefix = "[dry-run] Would delete" if result["dry_run"] else "Deleted"
    print(f"{prefix} router '{result['router_name']}'")
    if not result["dry_run"]:
        print(f"  Removed: {result['router_path']}")


def _print_add_skill(result: dict) -> None:
    if result["errors"]:
        _print_errors(result["errors"])
        return
    prefix = "[dry-run] Would add" if result["dry_run"] else "Added"
    print(f"{prefix} '{result['skill_name']}' to router '{result['router_name']}' "
          f"(now {result['total_skills']} skills)")


def _print_remove_skill(result: dict) -> None:
    if result["errors"]:
        _print_errors(result["errors"])
        return
    prefix = "[dry-run] Would remove" if result["dry_run"] else "Removed"
    print(f"{prefix} '{result['skill_name']}' from router '{result['router_name']}' "
          f"(now {result['total_skills']} skills)")


def _print_rename(result: dict) -> None:
    if result["errors"]:
        _print_errors(result["errors"])
        return
    prefix = "[dry-run] Would rename" if result["dry_run"] else "Renamed"
    print(f"{prefix} router '{result['old_name']}' → '{result['new_name']}'")
    if not result["dry_run"]:
        print(f"  New location: {result['new_path']}")


def _print_list_routers(routers: list[dict], skills_dir: Path) -> None:
    if not routers:
        print(f"No routers found in {skills_dir}")
        return
    print(f"Routers in {skills_dir}:")
    for r in routers:
        skills_str = ", ".join(r["skills"])
        print(f"  {r['name']:<30} {len(r['skills'])} skills — {skills_str}")


def _print_list_skills(skills: list[dict], skills_dir: Path) -> None:
    if not skills:
        print(f"No skills found in {skills_dir}")
        return
    print(f"Skills in {skills_dir}:")
    for s in skills:
        if s["is_router"]:
            sub = ", ".join(s["router_skills"])
            print(f"  {s['name']:<30} [router → {sub}]")
        else:
            desc_preview = s["description"][:60].rstrip() + "..." if len(s["description"]) > 60 else s["description"]
            print(f"  {s['name']:<30} {desc_preview}")


def _print_list_strategies(strategies: dict) -> None:
    if not strategies:
        print(f"No saved strategies. ({_CONFIG_PATH})")
        return
    print(f"Saved strategies ({_CONFIG_PATH}):")
    for name, s in strategies.items():
        print(f"  {name:<30} {s.get('description', '')}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _resolve_skills_dir(args_tool: str | None, cwd: Path) -> tuple[Path | None, str]:
    present_rules = _present_project_agent_rules(cwd)
    agent_groups = _group_present_agent_rules(present_rules)
    agents = detect_project_agents(cwd)

    if not present_rules:
        return None, (
            f"No agent tool directories found in {cwd}.\n"
            "Expected directories like .agents/skills/, .claude/skills/, "
            ".cortex/skills/, or skills/."
        )

    if args_tool:
        lower_tool = args_tool.lower()
        match = next((
            rule for rule in present_rules
            if rule["tool"] == args_tool or rule["display_name"].lower() == lower_tool
        ), None)
        if match is None and args_tool == "agents-shared":
            match = next((
                rule for rule in present_rules
                if rule["skills_dir"] == ".agents/skills"
            ), None)
        if not match:
            found = sorted({
                rule["tool"] for rule in present_rules
            } | ({
                "agents-shared"
            } if any(rule["skills_dir"] == ".agents/skills" for rule in present_rules) else set()))
            found_str = ", ".join(found)
            return None, f"Tool '{args_tool}' not found. Detected: {found_str}"
        if args_tool == "agents-shared":
            return match["project_path"], "Shared Agents"
        return match["project_path"], match["display_name"]

    if len(agent_groups) == 1:
        a = agents[0]
        tool_aliases = a.get("tool_aliases", [])
        if tool_aliases:
            aliases = ", ".join(tool_aliases)
            print(
                f"Detected agent group: {a['display_name']} ({a['skills_dir']}) "
                f"[tools: {aliases}]",
                file=sys.stderr,
            )
        else:
            print(f"Detected agent: {a['display_name']} ({a['skills_dir']})", file=sys.stderr)
        return a["skills_dir"], a["display_name"]

    lines = ["Multiple agent tool directories found. Use --tool to specify one:"]
    for group in sorted(agent_groups, key=lambda item: item["relative_path"]):
        visible_rules = [
            rule for rule in group["rules"]
            if rule.get("show_in_universal_list", True)
        ]
        if not visible_rules:
            visible_rules = group["rules"]
        if group["relative_path"] == ".agents/skills":
            display_name = "Shared Agents"
        elif len(visible_rules) == 1:
            display_name = visible_rules[0]["display_name"]
        else:
            display_name = " / ".join(rule["display_name"] for rule in visible_rules)
        tool_values = ", ".join(rule["tool"] for rule in visible_rules)
        lines.append(
            f"  {group['relative_path']:<18} {display_name} "
            f"(--tool {tool_values})"
        )
    return None, "\n".join(lines)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Create and manage skill routers for AI coding agents"
    )
    parser.add_argument("--name", help="Router name (kebab-case)")
    parser.add_argument("--skills", help="Comma-separated skill folder names to include")
    parser.add_argument("--description", help="Custom description for the router")
    parser.add_argument("--description-file", metavar="FILE", help="Read router description from a file")
    parser.add_argument(
        "--tool",
        help="Agent tool to use (e.g. claude-code, cursor). "
             "Required when multiple agents are detected.",
    )
    parser.add_argument("--skills-dir", help="Skills directory override (advanced)")
    parser.add_argument("--refresh", metavar="ROUTER", help="Regenerate router SKILL.md")
    parser.add_argument(
        "--add-skill", nargs=2, metavar=("ROUTER", "SKILL"),
        help="Add a skill to an existing router",
    )
    parser.add_argument(
        "--remove-skill", nargs=2, metavar=("ROUTER", "SKILL"),
        help="Remove a skill from an existing router",
    )
    parser.add_argument(
        "--rename", nargs=2, metavar=("OLD", "NEW"),
        help="Rename a router",
    )
    parser.add_argument("--list-skills", action="store_true", help="List all available skills (and existing routers)")
    parser.add_argument("--list-skills-full", action="store_true", help="List skills with full frontmatter (for collection grouping)")
    parser.add_argument("--list-routers", action="store_true", help="List all routers")
    parser.add_argument("--list-agents", action="store_true", help="List detected agent directories")
    parser.add_argument("--ungrouped", action="store_true", help="Only show skills not in any router")
    parser.add_argument("--save-strategy", metavar="NAME", help="Save a custom grouping strategy")
    parser.add_argument("--strategy-description", metavar="DESC", help="Description for the strategy being saved")
    parser.add_argument("--list-strategies", action="store_true", help="List saved custom strategies")
    parser.add_argument("--delete", metavar="ROUTER", help="Delete a router")
    parser.add_argument("--force", action="store_true", help="Overwrite existing router")
    parser.add_argument("--dry-run", action="store_true", help="Preview without changes")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")

    args = parser.parse_args()

    # Handle --list-agents before resolving skills dir
    if args.list_agents:
        agents = detect_project_agents(Path.cwd())
        if args.json:
            json.dump({"agents": [{"tool": a["tool"], "display_name": a["display_name"], "skills_dir": str(a["skills_dir"])} for a in agents]}, sys.stdout, indent=2)
            print()
        else:
            if not agents:
                print("No agent directories found")
            else:
                for a in agents:
                    print(f"  {a['tool']:<20} {a['display_name']:<20} {a['skills_dir']}")
        return

    # Resolve skills directory
    if args.skills_dir:
        skills_dir: Path | None = expand_path(args.skills_dir)
        if not skills_dir.is_dir():
            print(f"Error: skills directory does not exist: {skills_dir}", file=sys.stderr)
            sys.exit(1)
    else:
        skills_dir, msg = _resolve_skills_dir(args.tool, Path.cwd())
        if skills_dir is None:
            print(f"Error: {msg}", file=sys.stderr)
            sys.exit(2)

    # Resolve description text (--description-file takes precedence over --description)
    description_text = args.description or ""
    if args.description_file:
        try:
            description_text = Path(args.description_file).read_text(encoding="utf-8").strip()
        except OSError as e:
            print(f"Error: cannot read description file: {e}", file=sys.stderr)
            sys.exit(1)

    def emit(result: dict, print_fn) -> None:
        if args.json:
            json.dump(result, sys.stdout, indent=2)
            print()
        else:
            print_fn(result)
        if result.get("errors"):
            sys.exit(1)

    if args.list_strategies:
        strategies = list_strategies()
        if args.json:
            json.dump(strategies, sys.stdout, indent=2)
            print()
        else:
            _print_list_strategies(strategies)
        return

    if args.save_strategy:
        if not args.strategy_description:
            print("Error: --strategy-description is required with --save-strategy", file=sys.stderr)
            sys.exit(1)
        result = save_strategy(args.save_strategy, args.strategy_description)
        if args.json:
            json.dump(result, sys.stdout, indent=2)
            print()
        else:
            print(f"Saved strategy '{result['saved']}': {result['description']}")
        return

    if args.list_skills_full or args.list_skills:
        skills = list_skills(skills_dir, include_frontmatter=args.list_skills_full)
        if args.ungrouped:
            skills = _filter_ungrouped_skills(skills)
        if args.json:
            json.dump(skills, sys.stdout, indent=2)
            print()
        else:
            _print_list_skills(skills, skills_dir)
        return

    if args.list_routers:
        routers = list_routers(skills_dir)
        if args.json:
            json.dump(routers, sys.stdout, indent=2)
            print()
        else:
            _print_list_routers(routers, skills_dir)
        return

    if args.refresh:
        result = refresh_router(args.refresh, skills_dir, description=description_text, dry_run=args.dry_run)
        emit(result, _print_refresh)
        return

    if args.add_skill:
        router_name, skill_name = args.add_skill
        result = add_skill(router_name, skill_name, skills_dir, dry_run=args.dry_run)
        emit(result, _print_add_skill)
        return

    if args.remove_skill:
        router_name, skill_name = args.remove_skill
        result = remove_skill(router_name, skill_name, skills_dir, dry_run=args.dry_run)
        emit(result, _print_remove_skill)
        return

    if args.rename:
        old_name, new_name = args.rename
        result = rename_router(old_name, new_name, skills_dir, dry_run=args.dry_run)
        emit(result, _print_rename)
        return

    if args.delete:
        result = delete_router(args.delete, skills_dir, dry_run=args.dry_run)
        emit(result, _print_delete)
        return

    if args.name and args.skills:
        skill_names = [s.strip() for s in args.skills.split(",") if s.strip()]
        result = create_router(
            router_name=args.name,
            skill_names=skill_names,
            skills_dir=skills_dir,
            description=description_text,
            dry_run=args.dry_run,
            force=args.force,
        )
        emit(result, _print_create)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
