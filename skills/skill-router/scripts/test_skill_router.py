from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from scan_skills import parse_frontmatter  # noqa: E402
from skill_router import (  # noqa: E402
    _build_fallback_description,
    _filter_ungrouped_skills,
    _validate_router_name,
    _wrap_yaml_description,
    add_skill,
    create_router,
    delete_router,
    detect_project_agents,
    list_routers,
    list_skills,
    list_strategies,
    refresh_router,
    remove_skill,
    rename_router,
    save_strategy,
)


def write_skill(skills_dir: Path, name: str, description: str) -> None:
    skill_dir = skills_dir / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        "\n".join([
            "---",
            f"name: {name}",
            "description: >",
            f"  {description}",
            "---",
            "",
            f"# {name}",
            "",
        ]),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Original tests (preserved)
# ---------------------------------------------------------------------------

class SkillRouterTests(unittest.TestCase):
    def test_parse_frontmatter_preserves_nested_structures(self) -> None:
        content = "\n".join([
            "---",
            "name: animate",
            "description: >",
            "  Improve motion for a feature.",
            "user-invokable: true",
            "args:",
            "  - name: target",
            "    description: The feature to animate",
            "    required: false",
            "metadata:",
            "  author: vercel",
            '  version: "1.0.0"',
            "---",
            "",
            "# Animate",
        ])

        frontmatter = parse_frontmatter(content)

        self.assertEqual(frontmatter["name"], "animate")
        self.assertTrue(frontmatter["user-invokable"])
        self.assertEqual(frontmatter["metadata"]["author"], "vercel")
        self.assertEqual(frontmatter["metadata"]["version"], "1.0.0")
        self.assertEqual(frontmatter["args"][0]["name"], "target")
        self.assertEqual(frontmatter["args"][0]["description"], "The feature to animate")
        self.assertFalse(frontmatter["args"][0]["required"])

    def test_create_router_rejects_duplicate_skill_names(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-router-test-") as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            write_skill(skills_dir, "audit", "Audit interfaces.")

            result = create_router("design-quality", ["audit", "audit"], skills_dir, dry_run=True)

            self.assertEqual(
                result["errors"],
                ["Duplicate skills specified: audit"],
            )

    def test_refresh_and_add_skill_preserve_custom_router_description(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-router-test-") as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            write_skill(skills_dir, "audit", "Audit interfaces.")
            write_skill(skills_dir, "harden", "Harden interfaces.")
            write_skill(skills_dir, "optimize", "Optimize interfaces.")

            custom_description = "Custom merged description."
            create_result = create_router(
                "design-quality",
                ["audit", "harden"],
                skills_dir,
                description=custom_description,
            )
            self.assertFalse(create_result["errors"])

            refresh_result = refresh_router("design-quality", skills_dir)
            self.assertFalse(refresh_result["errors"])

            add_result = add_skill("design-quality", "optimize", skills_dir)
            self.assertFalse(add_result["errors"])

            router_skill_md = (skills_dir / "design-quality" / "SKILL.md").read_text(encoding="utf-8")
            frontmatter = parse_frontmatter(router_skill_md)
            self.assertEqual(frontmatter["description"], custom_description)

    def test_list_skills_skips_hidden_and_non_skill_directories(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-router-test-") as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            write_skill(skills_dir, "audit", "Audit interfaces.")
            (skills_dir / ".system").mkdir()
            (skills_dir / "references").mkdir()

            skills = list_skills(skills_dir, include_frontmatter=True)

            self.assertEqual([skill["name"] for skill in skills], ["audit"])
            self.assertEqual(skills[0]["frontmatter"]["name"], "audit")


# ---------------------------------------------------------------------------
# remove_skill
# ---------------------------------------------------------------------------

class RemoveSkillTests(unittest.TestCase):
    def test_remove_skill_succeeds(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-router-test-") as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            write_skill(skills_dir, "audit", "Audit interfaces.")
            write_skill(skills_dir, "harden", "Harden interfaces.")
            write_skill(skills_dir, "optimize", "Optimize interfaces.")
            create_router("design-quality", ["audit", "harden", "optimize"], skills_dir)

            result = remove_skill("design-quality", "optimize", skills_dir)

            self.assertFalse(result["errors"])
            self.assertEqual(result["total_skills"], 2)
            # Verify the manifest no longer contains the removed skill
            manifest_path = skills_dir / "design-quality" / "_manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            skill_names = [s["folder_name"] for s in manifest["skills"]]
            self.assertNotIn("optimize", skill_names)
            self.assertIn("audit", skill_names)
            self.assertIn("harden", skill_names)

    def test_remove_last_skill_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-router-test-") as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            write_skill(skills_dir, "audit", "Audit interfaces.")
            write_skill(skills_dir, "harden", "Harden interfaces.")
            create_router("design-quality", ["audit", "harden"], skills_dir)
            remove_skill("design-quality", "harden", skills_dir)

            result = remove_skill("design-quality", "audit", skills_dir)

            self.assertTrue(result["errors"])
            self.assertIn("last skill", result["errors"][0])

    def test_remove_nonexistent_skill_errors(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-router-test-") as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            write_skill(skills_dir, "audit", "Audit interfaces.")
            write_skill(skills_dir, "harden", "Harden interfaces.")
            create_router("design-quality", ["audit", "harden"], skills_dir)

            result = remove_skill("design-quality", "nonexistent", skills_dir)

            self.assertTrue(result["errors"])
            self.assertIn("nonexistent", result["errors"][0])


# ---------------------------------------------------------------------------
# delete_router
# ---------------------------------------------------------------------------

class DeleteRouterTests(unittest.TestCase):
    def test_delete_managed_router_succeeds(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-router-test-") as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            write_skill(skills_dir, "audit", "Audit interfaces.")
            write_skill(skills_dir, "harden", "Harden interfaces.")
            create_router("design-quality", ["audit", "harden"], skills_dir)

            result = delete_router("design-quality", skills_dir)

            self.assertFalse(result["errors"])
            self.assertTrue(result.get("removed"))
            self.assertFalse((skills_dir / "design-quality").exists())
            # Sub-skills must remain untouched
            self.assertTrue((skills_dir / "audit").exists())
            self.assertTrue((skills_dir / "harden").exists())

    def test_delete_non_router_dir_fails(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-router-test-") as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            write_skill(skills_dir, "audit", "Audit interfaces.")

            result = delete_router("audit", skills_dir)

            self.assertTrue(result["errors"])
            self.assertIn("_manifest.json", result["errors"][0])

    def test_delete_router_dry_run_does_not_remove_directory(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-router-test-") as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            write_skill(skills_dir, "audit", "Audit interfaces.")
            write_skill(skills_dir, "harden", "Harden interfaces.")
            create_router("design-quality", ["audit", "harden"], skills_dir)

            result = delete_router("design-quality", skills_dir, dry_run=True)

            self.assertFalse(result["errors"])
            self.assertTrue(result["dry_run"])
            # Directory must still exist in dry-run mode
            self.assertTrue((skills_dir / "design-quality").exists())


# ---------------------------------------------------------------------------
# rename_router
# ---------------------------------------------------------------------------

class RenameRouterTests(unittest.TestCase):
    def test_rename_succeeds(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-router-test-") as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            write_skill(skills_dir, "audit", "Audit interfaces.")
            write_skill(skills_dir, "harden", "Harden interfaces.")
            create_router("design-quality", ["audit", "harden"], skills_dir)

            result = rename_router("design-quality", "design-suite", skills_dir)

            self.assertFalse(result["errors"])
            # Old directory gone, new directory present
            self.assertFalse((skills_dir / "design-quality").exists())
            self.assertTrue((skills_dir / "design-suite").exists())
            # Manifest router_name updated
            manifest = json.loads(
                (skills_dir / "design-suite" / "_manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["router_name"], "design-suite")
            # SKILL.md name field updated
            skill_md = (skills_dir / "design-suite" / "SKILL.md").read_text(encoding="utf-8")
            fm = parse_frontmatter(skill_md)
            self.assertEqual(fm["name"], "design-suite")

    def test_rename_to_existing_name_fails(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-router-test-") as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            write_skill(skills_dir, "audit", "Audit interfaces.")
            write_skill(skills_dir, "harden", "Harden interfaces.")
            write_skill(skills_dir, "optimize", "Optimize interfaces.")
            create_router("design-quality", ["audit", "harden"], skills_dir)
            create_router("design-suite", ["optimize"], skills_dir)

            result = rename_router("design-quality", "design-suite", skills_dir)

            self.assertTrue(result["errors"])
            self.assertIn("already exists", result["errors"][0])

    def test_rename_non_router_fails(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-router-test-") as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            write_skill(skills_dir, "audit", "Audit interfaces.")

            result = rename_router("audit", "audit-v2", skills_dir)

            self.assertTrue(result["errors"])
            self.assertIn("_manifest.json", result["errors"][0])

    def test_rename_to_invalid_name_fails(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-router-test-") as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            write_skill(skills_dir, "audit", "Audit interfaces.")
            write_skill(skills_dir, "harden", "Harden interfaces.")
            create_router("design-quality", ["audit", "harden"], skills_dir)

            result = rename_router("design-quality", "Design_Quality", skills_dir)

            self.assertTrue(result["errors"])


# ---------------------------------------------------------------------------
# detect_project_agents
# ---------------------------------------------------------------------------

class DetectProjectAgentsTests(unittest.TestCase):
    def test_single_agent_dir_detected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-router-test-") as tmp:
            cwd = Path(tmp)
            (cwd / ".claude" / "skills").mkdir(parents=True)

            agents = detect_project_agents(cwd)

            self.assertEqual(len(agents), 1)
            self.assertEqual(agents[0]["tool"], "claude-code")

    def test_multiple_distinct_dirs_map_to_different_groups(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-router-test-") as tmp:
            cwd = Path(tmp)
            (cwd / ".claude" / "skills").mkdir(parents=True)
            (cwd / ".windsurf" / "skills").mkdir(parents=True)

            agents = detect_project_agents(cwd)

            tools = {a["tool"] for a in agents}
            self.assertIn("claude-code", tools)
            self.assertIn("windsurf", tools)
            self.assertEqual(len(agents), 2)

    def test_agents_skills_shared_dir_groups_together(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-router-test-") as tmp:
            cwd = Path(tmp)
            # .agents/skills is shared by amp, cursor, codex, cline, etc.
            (cwd / ".agents" / "skills").mkdir(parents=True)

            agents = detect_project_agents(cwd)

            self.assertEqual(len(agents), 1)
            self.assertEqual(agents[0]["tool"], "agents-shared")
            self.assertIn("tool_aliases", agents[0])
            self.assertGreater(len(agents[0]["tool_aliases"]), 1)


# ---------------------------------------------------------------------------
# Name validation
# ---------------------------------------------------------------------------

class NameValidationTests(unittest.TestCase):
    def test_valid_names_pass(self) -> None:
        for name in ["audit", "design-quality", "a1b2", "x"]:
            with self.subTest(name=name):
                self.assertIsNone(_validate_router_name(name))

    def test_leading_hyphen_fails(self) -> None:
        result = _validate_router_name("-audit")
        self.assertIsNotNone(result)

    def test_trailing_hyphen_fails(self) -> None:
        result = _validate_router_name("audit-")
        self.assertIsNotNone(result)

    def test_double_hyphen_fails(self) -> None:
        result = _validate_router_name("design--quality")
        self.assertIsNotNone(result)

    def test_uppercase_fails(self) -> None:
        result = _validate_router_name("Design")
        self.assertIsNotNone(result)

    def test_exceeding_64_chars_fails(self) -> None:
        long_name = "a" * 65
        result = _validate_router_name(long_name)
        self.assertIsNotNone(result)
        self.assertIn("64", result)

    def test_empty_name_fails(self) -> None:
        result = _validate_router_name("")
        self.assertIsNotNone(result)
        self.assertIn("empty", result.lower())


# ---------------------------------------------------------------------------
# Strategy persistence
# ---------------------------------------------------------------------------

class StrategyPersistenceTests(unittest.TestCase):
    def test_save_strategy_writes_to_config(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-router-test-") as tmp:
            config_path = Path(tmp) / "config.json"
            with patch("skill_router._CONFIG_PATH", config_path):
                result = save_strategy("by-domain", "Group skills by product domain.")

            self.assertFalse(result["errors"])
            self.assertEqual(result["saved"], "by-domain")
            config = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertIn("by-domain", config["strategies"])

    def test_list_strategies_reads_back_saved_strategies(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-router-test-") as tmp:
            config_path = Path(tmp) / "config.json"
            with patch("skill_router._CONFIG_PATH", config_path):
                save_strategy("by-domain", "Group skills by product domain.")
                strategies = list_strategies()

            self.assertIn("by-domain", strategies)
            self.assertEqual(strategies["by-domain"]["description"], "Group skills by product domain.")

    def test_overwriting_strategy_updates_description(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-router-test-") as tmp:
            config_path = Path(tmp) / "config.json"
            with patch("skill_router._CONFIG_PATH", config_path):
                save_strategy("by-domain", "Original description.")
                save_strategy("by-domain", "Updated description.")
                strategies = list_strategies()

            self.assertEqual(strategies["by-domain"]["description"], "Updated description.")


# ---------------------------------------------------------------------------
# --ungrouped filter (via list_skills)
# ---------------------------------------------------------------------------

class UngroupedFilterTests(unittest.TestCase):
    def test_ungrouped_filter_returns_only_skills_not_in_any_router(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-router-test-") as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            write_skill(skills_dir, "skill-a", "Skill A.")
            write_skill(skills_dir, "skill-b", "Skill B.")
            write_skill(skills_dir, "skill-c", "Skill C.")
            create_router("my-router", ["skill-a", "skill-b"], skills_dir)

            all_skills = list_skills(skills_dir)
            # Apply the same ungrouped filter the CLI uses
            all_router_skills: set[str] = set()
            for s in all_skills:
                if s["is_router"]:
                    all_router_skills.update(s["router_skills"])
            ungrouped = [s for s in all_skills if not s["is_router"] and s["name"] not in all_router_skills]

            self.assertEqual([s["name"] for s in ungrouped], ["skill-c"])


# ---------------------------------------------------------------------------
# create_router with force=True
# ---------------------------------------------------------------------------

class CreateRouterForceTests(unittest.TestCase):
    def test_create_router_with_force_overwrites_existing_router(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-router-test-") as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            write_skill(skills_dir, "audit", "Audit interfaces.")
            write_skill(skills_dir, "harden", "Harden interfaces.")
            write_skill(skills_dir, "optimize", "Optimize interfaces.")

            create_router("design-quality", ["audit", "harden"], skills_dir)
            # Capture creation time from first manifest
            first_manifest = json.loads(
                (skills_dir / "design-quality" / "_manifest.json").read_text(encoding="utf-8")
            )

            result = create_router("design-quality", ["audit", "optimize"], skills_dir, force=True)

            self.assertFalse(result["errors"])
            new_manifest = json.loads(
                (skills_dir / "design-quality" / "_manifest.json").read_text(encoding="utf-8")
            )
            new_skill_names = [s["folder_name"] for s in new_manifest["skills"]]
            self.assertIn("optimize", new_skill_names)
            self.assertNotIn("harden", new_skill_names)
            # Router was regenerated (created timestamp differs or skills list differs)
            self.assertNotEqual(first_manifest["skills"], new_manifest["skills"])


# ---------------------------------------------------------------------------
# create_router name conflict with plain skill
# ---------------------------------------------------------------------------

class CreateRouterNameConflictTests(unittest.TestCase):
    def test_create_router_name_conflict_with_plain_skill_mentions_skill(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-router-test-") as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            # Create a plain skill dir (no _manifest.json) named "audit"
            write_skill(skills_dir, "audit", "Audit interfaces.")
            write_skill(skills_dir, "harden", "Harden interfaces.")

            result = create_router("audit", ["harden"], skills_dir)

            self.assertTrue(result["errors"])
            error_msg = result["errors"][0].lower()
            # Error must mention "skill" (not "router already exists")
            self.assertIn("skill", error_msg)
            # The phrase "router '…' already exists" (existing-router path) must not appear
            self.assertNotIn("router 'audit' already exists", error_msg)


# ---------------------------------------------------------------------------
# refresh_router — new workflow: always re-synthesize description from sub-skills
# ---------------------------------------------------------------------------

class RefreshRouterTests(unittest.TestCase):
    def test_refresh_with_new_description_replaces_old_description(self) -> None:
        """Passing a new description to refresh must overwrite the original one."""
        with tempfile.TemporaryDirectory(prefix="skill-router-test-") as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            write_skill(skills_dir, "skill-a", "Skill A.")
            write_skill(skills_dir, "skill-b", "Skill B.")
            create_router("my-router", ["skill-a", "skill-b"], skills_dir,
                          description="Original description.")

            result = refresh_router("my-router", skills_dir,
                                    description="Re-synthesised description.")

            self.assertFalse(result["errors"])
            skill_md = (skills_dir / "my-router" / "SKILL.md").read_text(encoding="utf-8")
            fm = parse_frontmatter(skill_md)
            self.assertEqual(fm["description"], "Re-synthesised description.")
            # Manifest must also reflect the new description
            manifest = json.loads(
                (skills_dir / "my-router" / "_manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["router_description"], "Re-synthesised description.")

    def test_refresh_updates_capabilities_when_sub_skill_description_changes(self) -> None:
        """After a sub-skill's SKILL.md is updated, refresh must reflect the new
        description in the router's Capabilities section."""
        with tempfile.TemporaryDirectory(prefix="skill-router-test-") as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            write_skill(skills_dir, "skill-a", "Original skill-a description.")
            write_skill(skills_dir, "skill-b", "Skill B.")
            create_router("my-router", ["skill-a", "skill-b"], skills_dir,
                          description="Router description.")

            # Simulate the user updating the sub-skill via npx skills or similar
            write_skill(skills_dir, "skill-a", "Updated skill-a description.")

            refresh_router("my-router", skills_dir, description="Router description.")

            skill_md = (skills_dir / "my-router" / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn("Updated skill-a description.", skill_md)
            self.assertNotIn("Original skill-a description.", skill_md)

    def test_refresh_reads_sub_skills_from_manifest_not_from_skills_dir(self) -> None:
        """Refresh must only include the skills recorded in the manifest.
        Skills added to the directory after router creation must not appear."""
        with tempfile.TemporaryDirectory(prefix="skill-router-test-") as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            write_skill(skills_dir, "skill-a", "Skill A.")
            write_skill(skills_dir, "skill-b", "Skill B.")
            create_router("my-router", ["skill-a", "skill-b"], skills_dir)

            # New skill appears in the directory but was never added to the router
            write_skill(skills_dir, "skill-c", "Skill C.")

            refresh_router("my-router", skills_dir, description="Router description.")

            skill_md = (skills_dir / "my-router" / "SKILL.md").read_text(encoding="utf-8")
            self.assertNotIn("skill-c", skill_md)
            manifest = json.loads(
                (skills_dir / "my-router" / "_manifest.json").read_text(encoding="utf-8")
            )
            skill_names = [s["folder_name"] for s in manifest["skills"]]
            self.assertNotIn("skill-c", skill_names)

    def test_refresh_dry_run_does_not_modify_skill_md(self) -> None:
        """dry_run=True must leave the router SKILL.md unchanged."""
        with tempfile.TemporaryDirectory(prefix="skill-router-test-") as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            write_skill(skills_dir, "skill-a", "Skill A.")
            write_skill(skills_dir, "skill-b", "Skill B.")
            create_router("my-router", ["skill-a", "skill-b"], skills_dir,
                          description="Original description.")
            original_md = (skills_dir / "my-router" / "SKILL.md").read_text(encoding="utf-8")

            write_skill(skills_dir, "skill-a", "Updated skill-a description.")
            result = refresh_router("my-router", skills_dir,
                                    description="New description.", dry_run=True)

            self.assertFalse(result["errors"])
            self.assertTrue(result["dry_run"])
            current_md = (skills_dir / "my-router" / "SKILL.md").read_text(encoding="utf-8")
            self.assertEqual(current_md, original_md)

    def test_refresh_dry_run_returns_preview_with_updated_content(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-router-test-") as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            write_skill(skills_dir, "skill-a", "Skill A.")
            write_skill(skills_dir, "skill-b", "Skill B.")
            create_router("my-router", ["skill-a", "skill-b"], skills_dir,
                          description="Original description.")

            write_skill(skills_dir, "skill-a", "Updated skill-a description.")
            result = refresh_router("my-router", skills_dir,
                                    description="New description.", dry_run=True)

            self.assertFalse(result["errors"])
            self.assertTrue(result["dry_run"])
            self.assertIn("preview", result)
            self.assertIn("New description.", result["preview"])
            self.assertIn("Updated skill-a description.", result["preview"])


# ---------------------------------------------------------------------------
# refresh_router with missing sub-skill
# ---------------------------------------------------------------------------

class RefreshRouterMissingSkillTests(unittest.TestCase):
    def test_refresh_with_missing_sub_skill_reports_not_found(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-router-test-") as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            write_skill(skills_dir, "skill-a", "Skill A.")
            write_skill(skills_dir, "skill-b", "Skill B.")
            create_router("my-router", ["skill-a", "skill-b"], skills_dir)

            # Delete skill-b's directory to simulate a missing sub-skill
            import shutil
            shutil.rmtree(str(skills_dir / "skill-b"))

            result = refresh_router("my-router", skills_dir)

            self.assertFalse(result["errors"])
            self.assertIn("skill-b", result["not_found"])
            self.assertIn("skill-a", result["refreshed"])


# ---------------------------------------------------------------------------
# _wrap_yaml_description paragraphs
# ---------------------------------------------------------------------------

class WrapYamlDescriptionTests(unittest.TestCase):
    def test_single_paragraph_produces_no_blank_line(self) -> None:
        lines = _wrap_yaml_description("Hello world.")
        # No blank indented line should appear for a single paragraph
        blank_lines = [ln for ln in lines if ln.strip() == ""]
        self.assertEqual(blank_lines, [])

    def test_two_paragraphs_produce_blank_indented_separator(self) -> None:
        text = "First paragraph text.\n\nSecond paragraph text."
        lines = _wrap_yaml_description(text)
        # There must be exactly one blank-indented separator line between paragraphs
        blank_lines = [ln for ln in lines if ln.strip() == ""]
        self.assertEqual(len(blank_lines), 1)
        # The separator must consist only of the indent prefix (spaces), not be truly empty
        separator = blank_lines[0]
        self.assertTrue(separator.startswith(" "))
        # Content lines from both paragraphs must be present
        all_text = " ".join(lines)
        self.assertIn("First paragraph", all_text)
        self.assertIn("Second paragraph", all_text)

    def test_three_paragraphs_produce_two_separators(self) -> None:
        text = "Para one.\n\nPara two.\n\nPara three."
        lines = _wrap_yaml_description(text)
        blank_lines = [ln for ln in lines if ln.strip() == ""]
        self.assertEqual(len(blank_lines), 2)

    def test_long_line_is_wrapped_at_90_chars(self) -> None:
        # Build a single paragraph whose words, joined, exceed 90 chars per line
        words = ["word"] * 30  # "word word word ..." — forces multiple lines
        text = " ".join(words)
        lines = _wrap_yaml_description(text)
        for line in lines:
            self.assertLessEqual(len(line), 92)  # indent(2) + 90-char limit


# ---------------------------------------------------------------------------
# add_skill
# ---------------------------------------------------------------------------

class AddSkillTests(unittest.TestCase):
    def test_add_skill_updates_dispatch_and_capabilities(self) -> None:
        """Adding a skill must appear in both the Dispatch and Capabilities sections."""
        with tempfile.TemporaryDirectory(prefix="skill-router-test-") as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            write_skill(skills_dir, "skill-a", "Skill A description.")
            write_skill(skills_dir, "skill-b", "Skill B description.")
            write_skill(skills_dir, "skill-c", "Skill C description.")
            create_router("my-router", ["skill-a", "skill-b"], skills_dir)

            result = add_skill("my-router", "skill-c", skills_dir)

            self.assertFalse(result["errors"])
            self.assertEqual(result["total_skills"], 3)
            skill_md = (skills_dir / "my-router" / "SKILL.md").read_text(encoding="utf-8")
            # Dispatch section
            self.assertIn("../skill-c/SKILL.md", skill_md)
            # Capabilities section
            self.assertIn("Skill C description.", skill_md)

    def test_add_skill_dry_run_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-router-test-") as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            write_skill(skills_dir, "skill-a", "Skill A.")
            write_skill(skills_dir, "skill-b", "Skill B.")
            write_skill(skills_dir, "skill-c", "Skill C.")
            create_router("my-router", ["skill-a", "skill-b"], skills_dir)
            original_md = (skills_dir / "my-router" / "SKILL.md").read_text(encoding="utf-8")

            result = add_skill("my-router", "skill-c", skills_dir, dry_run=True)

            self.assertFalse(result["errors"])
            self.assertTrue(result["dry_run"])
            self.assertEqual(result["total_skills"], 3)
            self.assertEqual(
                (skills_dir / "my-router" / "SKILL.md").read_text(encoding="utf-8"),
                original_md,
            )

    def test_add_skill_duplicate_reports_error(self) -> None:
        """Adding a skill that is already in the router must return an error."""
        with tempfile.TemporaryDirectory(prefix="skill-router-test-") as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            write_skill(skills_dir, "skill-a", "Skill A.")
            write_skill(skills_dir, "skill-b", "Skill B.")
            create_router("my-router", ["skill-a", "skill-b"], skills_dir)

            result = add_skill("my-router", "skill-a", skills_dir)

            self.assertTrue(result["errors"])
            self.assertIn("skill-a", result["errors"][0])

    def test_add_skill_on_non_router_fails(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-router-test-") as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            write_skill(skills_dir, "skill-a", "Skill A.")
            write_skill(skills_dir, "skill-b", "Skill B.")

            result = add_skill("skill-a", "skill-b", skills_dir)

            self.assertTrue(result["errors"])
            self.assertIn("_manifest.json", result["errors"][0])


# ---------------------------------------------------------------------------
# create_router — dry_run and generated content
# ---------------------------------------------------------------------------

class CreateRouterContentTests(unittest.TestCase):
    def test_create_router_dry_run_does_not_create_directory(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-router-test-") as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            write_skill(skills_dir, "skill-a", "Skill A.")
            write_skill(skills_dir, "skill-b", "Skill B.")

            result = create_router("my-router", ["skill-a", "skill-b"], skills_dir, dry_run=True)

            self.assertFalse(result["errors"])
            self.assertTrue(result["dry_run"])
            self.assertFalse((skills_dir / "my-router").exists())

    def test_create_router_dry_run_returns_preview(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-router-test-") as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            write_skill(skills_dir, "skill-a", "Skill A.")
            write_skill(skills_dir, "skill-b", "Skill B.")

            result = create_router(
                "my-router",
                ["skill-a", "skill-b"],
                skills_dir,
                description="Custom router description.",
                dry_run=True,
            )

            self.assertFalse(result["errors"])
            self.assertTrue(result["dry_run"])
            self.assertIn("preview", result)
            self.assertIn("name: my-router", result["preview"])
            self.assertIn("Custom router description.", result["preview"])
            self.assertIn("../skill-a/SKILL.md", result["preview"])

    def test_create_router_dispatch_section_has_correct_refs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-router-test-") as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            write_skill(skills_dir, "skill-a", "Skill A.")
            write_skill(skills_dir, "skill-b", "Skill B.")

            create_router("my-router", ["skill-a", "skill-b"], skills_dir)

            skill_md = (skills_dir / "my-router" / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn("../skill-a/SKILL.md", skill_md)
            self.assertIn("../skill-b/SKILL.md", skill_md)

    def test_create_router_capabilities_section_has_sub_skill_descriptions(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-router-test-") as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            write_skill(skills_dir, "skill-a", "Skill A does something useful.")
            write_skill(skills_dir, "skill-b", "Skill B does something else.")

            create_router("my-router", ["skill-a", "skill-b"], skills_dir)

            skill_md = (skills_dir / "my-router" / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn("Skill A does something useful.", skill_md)
            self.assertIn("Skill B does something else.", skill_md)

    def test_create_router_description_written_to_frontmatter(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-router-test-") as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            write_skill(skills_dir, "skill-a", "Skill A.")
            write_skill(skills_dir, "skill-b", "Skill B.")

            create_router("my-router", ["skill-a", "skill-b"], skills_dir,
                          description="Custom router description.")

            skill_md = (skills_dir / "my-router" / "SKILL.md").read_text(encoding="utf-8")
            fm = parse_frontmatter(skill_md)
            self.assertEqual(fm["description"], "Custom router description.")

    def test_create_router_fallback_description_when_none_provided(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-router-test-") as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            write_skill(skills_dir, "skill-a", "Skill A.")
            write_skill(skills_dir, "skill-b", "Skill B.")

            create_router("my-router", ["skill-a", "skill-b"], skills_dir)

            skill_md = (skills_dir / "my-router" / "SKILL.md").read_text(encoding="utf-8")
            fm = parse_frontmatter(skill_md)
            self.assertIsNotNone(fm.get("description"))
            self.assertLessEqual(len(fm["description"]), 1024)

    def test_build_fallback_description_within_1024_chars(self) -> None:
        skills = [{"name": f"skill-{i}"} for i in range(20)]
        desc = _build_fallback_description("my-router", skills)
        self.assertLessEqual(len(desc), 1024)


# ---------------------------------------------------------------------------
# list_routers
# ---------------------------------------------------------------------------

class ListRoutersTests(unittest.TestCase):
    def test_list_routers_returns_only_routers_not_plain_skills(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-router-test-") as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            write_skill(skills_dir, "skill-a", "Skill A.")
            write_skill(skills_dir, "skill-b", "Skill B.")
            write_skill(skills_dir, "skill-c", "Skill C.")
            create_router("my-router", ["skill-a", "skill-b"], skills_dir)

            routers = list_routers(skills_dir)

            names = [r["name"] for r in routers]
            self.assertIn("my-router", names)
            self.assertNotIn("skill-a", names)
            self.assertNotIn("skill-b", names)
            self.assertNotIn("skill-c", names)

    def test_list_routers_includes_correct_skills_list(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-router-test-") as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            write_skill(skills_dir, "skill-a", "Skill A.")
            write_skill(skills_dir, "skill-b", "Skill B.")
            write_skill(skills_dir, "skill-c", "Skill C.")
            create_router("my-router", ["skill-a", "skill-b", "skill-c"], skills_dir)

            routers = list_routers(skills_dir)

            self.assertEqual(len(routers), 1)
            self.assertEqual(sorted(routers[0]["skills"]), ["skill-a", "skill-b", "skill-c"])


# ---------------------------------------------------------------------------
# remove_skill — dry_run
# ---------------------------------------------------------------------------

class RemoveSkillDryRunTests(unittest.TestCase):
    def test_remove_skill_dry_run_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-router-test-") as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            write_skill(skills_dir, "skill-a", "Skill A.")
            write_skill(skills_dir, "skill-b", "Skill B.")
            create_router("my-router", ["skill-a", "skill-b"], skills_dir)
            original_md = (skills_dir / "my-router" / "SKILL.md").read_text(encoding="utf-8")

            result = remove_skill("my-router", "skill-b", skills_dir, dry_run=True)

            self.assertFalse(result["errors"])
            self.assertTrue(result["dry_run"])
            self.assertEqual(result["total_skills"], 1)
            self.assertEqual(
                (skills_dir / "my-router" / "SKILL.md").read_text(encoding="utf-8"),
                original_md,
            )


# ---------------------------------------------------------------------------
# list_skills — router entries
# ---------------------------------------------------------------------------

class ListSkillsRouterTests(unittest.TestCase):
    def test_list_skills_marks_routers_correctly(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-router-test-") as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            write_skill(skills_dir, "skill-a", "Skill A.")
            write_skill(skills_dir, "skill-b", "Skill B.")
            create_router("my-router", ["skill-a", "skill-b"], skills_dir)

            skills = list_skills(skills_dir)

            router_entries = [s for s in skills if s["name"] == "my-router"]
            self.assertEqual(len(router_entries), 1)
            self.assertTrue(router_entries[0]["is_router"])
            self.assertEqual(sorted(router_entries[0]["router_skills"]), ["skill-a", "skill-b"])

    def test_list_skills_plain_skills_have_is_router_false(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-router-test-") as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            write_skill(skills_dir, "skill-a", "Skill A.")
            write_skill(skills_dir, "skill-b", "Skill B.")
            create_router("my-router", ["skill-a", "skill-b"], skills_dir)

            skills = list_skills(skills_dir)

            plain = [s for s in skills if not s["is_router"]]
            self.assertEqual(sorted(s["name"] for s in plain), ["skill-a", "skill-b"])
            for s in plain:
                self.assertFalse(s["is_router"])


# ---------------------------------------------------------------------------
# _filter_ungrouped_skills
# ---------------------------------------------------------------------------

class FilterUngroupedSkillsTests(unittest.TestCase):
    def test_filter_excludes_skills_in_router(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-router-test-") as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            write_skill(skills_dir, "skill-a", "Skill A.")
            write_skill(skills_dir, "skill-b", "Skill B.")
            write_skill(skills_dir, "skill-c", "Skill C.")
            create_router("my-router", ["skill-a", "skill-b"], skills_dir)

            all_skills = list_skills(skills_dir)
            ungrouped = _filter_ungrouped_skills(all_skills)

            names = [s["name"] for s in ungrouped]
            self.assertIn("skill-c", names)
            self.assertNotIn("skill-a", names)
            self.assertNotIn("skill-b", names)

    def test_filter_excludes_router_entries_themselves(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-router-test-") as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            write_skill(skills_dir, "skill-a", "Skill A.")
            write_skill(skills_dir, "skill-b", "Skill B.")
            create_router("my-router", ["skill-a", "skill-b"], skills_dir)

            all_skills = list_skills(skills_dir)
            ungrouped = _filter_ungrouped_skills(all_skills)

            names = [s["name"] for s in ungrouped]
            self.assertNotIn("my-router", names)


# ---------------------------------------------------------------------------
# rename_router — dry_run
# ---------------------------------------------------------------------------

class RenameRouterDryRunTests(unittest.TestCase):
    def test_rename_router_dry_run_does_not_move_directory(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-router-test-") as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            write_skill(skills_dir, "skill-a", "Skill A.")
            write_skill(skills_dir, "skill-b", "Skill B.")
            create_router("my-router", ["skill-a", "skill-b"], skills_dir)

            result = rename_router("my-router", "new-router", skills_dir, dry_run=True)

            self.assertFalse(result["errors"])
            self.assertTrue(result["dry_run"])
            self.assertTrue((skills_dir / "my-router").exists())
            self.assertFalse((skills_dir / "new-router").exists())


if __name__ == "__main__":
    unittest.main()
