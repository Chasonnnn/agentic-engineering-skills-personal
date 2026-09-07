#!/usr/bin/env python3
"""Create a compact snapshot of GitHub pull requests with gh CLI."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from typing import Any
from github_cli import CliError, add_auth_options, gh_json


LIST_FIELDS = [
    "number",
    "title",
    "url",
    "author",
    "headRefName",
    "baseRefName",
    "baseRefOid",
    "headRefOid",
    "isDraft",
    "labels",
    "updatedAt",
]

VIEW_FIELDS = ["body", "files", "changedFiles", "commits", "statusCheckRollup"]


def truncate(value: str | None, limit: int) -> str:
    if not value:
        return ""
    text = value.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def fetch_prs(state: str, limit: int, repo: str | None, options) -> tuple[list[dict[str, Any]], bool]:
    args = ["pr", "list", "--state", state, "--limit", str(limit + 1), "--json", ",".join(LIST_FIELDS)]
    if repo:
        args.extend(["--repo", repo])
    all_prs = gh_json(args, options)
    truncated = len(all_prs) > limit
    prs = all_prs[:limit]
    for pr in prs:
        view_args = ["pr", "view", str(pr["number"]), "--json", ",".join(VIEW_FIELDS)]
        if repo:
            view_args.extend(["--repo", repo])
        try:
            pr.update(gh_json(view_args, options))
        except (RuntimeError, ValueError, OSError, subprocess.SubprocessError) as exc:
            if isinstance(exc, CliError) and exc.returncode == 10:
                raise
            pr["viewError"] = str(exc)
    return prs, truncated


def normalize(prs: list[dict[str, Any]], body_limit: int) -> list[dict[str, Any]]:
    normalized = []
    for pr in prs:
        files = [item.get("path", "") for item in pr.get("files", [])]
        commits = [
            {
                "oid": item.get("oid"),
                "headline": item.get("messageHeadline"),
            }
            for item in pr.get("commits", [])
        ]
        checks = []
        for item in pr.get("statusCheckRollup", []) or []:
            checks.append(
                {
                    "name": item.get("name") or item.get("context") or item.get("workflowName"),
                    "status": item.get("status") or item.get("state"),
                    "conclusion": item.get("conclusion"),
                }
            )
        normalized.append(
            {
                "number": pr.get("number"),
                "title": pr.get("title"),
                "url": pr.get("url"),
                "author": (pr.get("author") or {}).get("login"),
                "base": pr.get("baseRefName"),
                "head": pr.get("headRefName"),
                "headSha": pr.get("headRefOid"),
                "baseSha": pr.get("baseRefOid"),
                "filesIncomplete": len(files) < pr.get("changedFiles", len(files)),
                "draft": pr.get("isDraft"),
                "updatedAt": pr.get("updatedAt"),
                "labels": [item.get("name") for item in pr.get("labels", [])],
                "body": truncate(pr.get("body"), body_limit),
                "files": files,
                "commits": commits,
                "checks": checks,
                "viewError": pr.get("viewError"),
            }
        )
    return normalized


def print_markdown(prs: list[dict[str, Any]]) -> None:
    for pr in prs:
        print(f"## #{pr['number']} {pr['title']}")
        print(f"- URL: {pr['url']}")
        print(f"- Base/head: {pr['base']} <- {pr['head']}")
        print(f"- Base/head SHA: {pr['baseSha']} <- {pr['headSha']}")
        print(f"- Files incomplete: {pr['filesIncomplete']}")
        print(f"- Author: {pr['author']}")
        if pr["labels"]:
            print(f"- Labels: {', '.join(pr['labels'])}")
        if pr["files"]:
            print(f"- Files: {', '.join(pr['files'])}")
        if pr["commits"]:
            headlines = [item["headline"] or item["oid"] for item in pr["commits"]]
            print(f"- Commits: {'; '.join(headlines)}")
        if pr["checks"]:
            rendered = [
                f"{item['name']}={item['conclusion'] or item['status']}"
                for item in pr["checks"]
                if item["name"]
            ]
            if rendered:
                print(f"- Checks: {', '.join(rendered)}")
        if pr.get("viewError"):
            print(f"- View error: {pr['viewError']}")
        if pr["body"]:
            print()
            print(truncate(pr["body"], 1200))
        print()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", help="GitHub repository in owner/name form.")
    parser.add_argument("--state", default="open", choices=["open", "closed", "merged", "all"])
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--body-limit", type=int, default=2000)
    parser.add_argument("--format", choices=["json", "markdown"], default="markdown")
    add_auth_options(parser)
    args = parser.parse_args()
    if args.limit <= 0 or args.body_limit < 4:
        parser.error("--limit must be positive and --body-limit at least 4")

    try:
        raw, truncated = fetch_prs(args.state, args.limit, args.repo, args)
        prs = normalize(raw, args.body_limit)
    except (RuntimeError, ValueError, OSError, subprocess.SubprocessError) as exc:
        print(str(exc), file=sys.stderr)
        if isinstance(exc, CliError) and exc.returncode == 10:
            print("Stopped leaf argv: " + json.dumps(exc.command), file=sys.stderr)
            return 10
        return 1

    incomplete = truncated or any(pr["viewError"] or pr["filesIncomplete"] for pr in prs)
    coverage = {"queue_truncated": truncated, "detail_errors": sum(bool(pr["viewError"]) for pr in prs),
                "files_incomplete": any(pr["filesIncomplete"] for pr in prs),
                "count": len(prs), "scope": "summary; bodies and commit/check details may be abbreviated"}
    if args.format == "json":
        print(json.dumps({"coverage": coverage, "pull_requests": prs}, indent=2, sort_keys=True))
    else:
        print("Coverage: " + json.dumps(coverage))
        print_markdown(prs)
    return 2 if incomplete else 0


if __name__ == "__main__":
    raise SystemExit(main())
