#!/usr/bin/env python3
"""Create a compact snapshot of GitHub pull requests with gh CLI."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from typing import Any


LIST_FIELDS = [
    "number",
    "title",
    "url",
    "author",
    "headRefName",
    "baseRefName",
    "isDraft",
    "labels",
    "updatedAt",
]

VIEW_FIELDS = ["body", "files", "commits", "statusCheckRollup"]


def run_gh(args: list[str]) -> Any:
    command = ["gh", *args]
    result = subprocess.run(command, check=False, text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"command failed: {' '.join(command)}")
    return json.loads(result.stdout or "null")


def truncate(value: str | None, limit: int) -> str:
    if not value:
        return ""
    text = value.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def fetch_prs(state: str, limit: int, repo: str | None) -> list[dict[str, Any]]:
    args = ["pr", "list", "--state", state, "--limit", str(limit), "--json", ",".join(LIST_FIELDS)]
    if repo:
        args.extend(["--repo", repo])
    prs = run_gh(args)
    for pr in prs:
        view_args = ["pr", "view", str(pr["number"]), "--json", ",".join(VIEW_FIELDS)]
        if repo:
            view_args.extend(["--repo", repo])
        try:
            pr.update(run_gh(view_args))
        except RuntimeError as exc:
            pr["viewError"] = str(exc)
    return prs


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
                    "name": item.get("name") or item.get("workflowName"),
                    "status": item.get("status"),
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
    args = parser.parse_args()

    try:
        prs = normalize(fetch_prs(args.state, args.limit, args.repo), args.body_limit)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.format == "json":
        print(json.dumps(prs, indent=2, sort_keys=True))
    else:
        print_markdown(prs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
