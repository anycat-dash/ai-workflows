#!/usr/bin/env python3
"""
Post a drafted PR review to GitHub.

Usage:
    post-pr-review.py <review-dir>

Reads:
    <review-dir>/pr-details.json
    <review-dir>/pr-comments/manifest.json
    <review-dir>/pr-comments/body.md
    <review-dir>/pr-comments/comment-*.md  (as listed in manifest)

Validates all inputs, then posts a single atomic review via the GitHub API.
Resolves any threads listed in manifest.resolve_thread_ids via GraphQL.
"""

import json
import subprocess
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# GitHub API helpers
# ---------------------------------------------------------------------------

def gh_api(endpoint, method="GET", data=None):
    cmd = ["gh", "api", endpoint, "-X", method, "--input", "-"]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        input=json.dumps(data or {}),
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    return json.loads(result.stdout) if result.stdout.strip() else {}


def gh_graphql(query, variables=None):
    cmd = ["gh", "api", "graphql", "--input", "-"]
    payload = {"query": query, "variables": variables or {}}
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        input=json.dumps(payload),
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    return json.loads(result.stdout)


RESOLVE_THREAD_MUTATION = """
mutation ResolveThread($threadId: ID!) {
  resolveReviewThread(input: {threadId: $threadId}) {
    thread {
      id
      isResolved
    }
  }
}
"""


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate(manifest, body, comments_dir, pr_details):
    errors = []

    valid_events = {"COMMENT", "REQUEST_CHANGES", "APPROVE"}
    if manifest.get("event") not in valid_events:
        errors.append(
            f"manifest.event must be one of {valid_events}; got {manifest.get('event')!r}"
        )

    if not body.strip():
        errors.append("body.md is empty — write a review summary before posting.")

    changed_files = set(pr_details.get("github", {}).get("changedFiles", []))

    for i, comment in enumerate(manifest.get("comments", []), start=1):
        prefix = f"comments[{i}]"

        if not comment.get("path"):
            errors.append(f"{prefix}: missing 'path'")
        elif changed_files and comment["path"] not in changed_files:
            errors.append(
                f"{prefix}: path '{comment['path']}' is not in the PR diff"
            )

        if not comment.get("line"):
            errors.append(f"{prefix}: missing 'line'")

        body_file_name = comment.get("body_file")
        if not body_file_name:
            errors.append(f"{prefix}: missing 'body_file'")
        else:
            bf = comments_dir / body_file_name
            if not bf.exists():
                errors.append(f"{prefix}: body_file '{body_file_name}' does not exist")
            elif not bf.read_text().strip():
                errors.append(f"{prefix}: body_file '{body_file_name}' is empty")

    return errors


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        sys.exit("Usage: post-pr-review.py <review-dir>")

    review_dir = Path(sys.argv[1]).expanduser().resolve()
    if not review_dir.exists():
        sys.exit(f"error: review directory not found: {review_dir}")

    pr_details_path = review_dir / "pr-details.json"
    comments_dir = review_dir / "pr-comments"
    manifest_path = comments_dir / "manifest.json"

    for p in (pr_details_path, manifest_path):
        if not p.exists():
            sys.exit(f"error: required file not found: {p}")

    pr_details = json.loads(pr_details_path.read_text())
    manifest = json.loads(manifest_path.read_text())

    body_path = comments_dir / manifest.get("body_file", "body.md")
    if not body_path.exists():
        sys.exit(f"error: body file not found: {body_path}")
    body = body_path.read_text()

    # Validate
    errors = validate(manifest, body, comments_dir, pr_details)
    if errors:
        print("Validation failed — fix these errors and re-run:", file=sys.stderr)
        for err in errors:
            print(f"  • {err}", file=sys.stderr)
        sys.exit(1)

    github = pr_details["github"]
    owner, repo_name = github["repo"].split("/", 1)
    pr_number = github["number"]
    head_sha = github["headRefOid"]

    # Build line-level comment list
    review_comments = []
    for c in manifest.get("comments", []):
        comment_body = (comments_dir / c["body_file"]).read_text()
        entry: dict = {
            "path": c["path"],
            "line": c["line"],
            "side": c.get("side", "RIGHT"),
            "body": comment_body,
        }
        if c.get("start_line"):
            entry["start_line"] = c["start_line"]
            entry["start_side"] = c.get("start_side", "RIGHT")
        review_comments.append(entry)

    payload = {
        "commit_id": head_sha,
        "body": body,
        "event": manifest["event"],
        "comments": review_comments,
    }

    n = len(review_comments)
    print(
        f"Posting {manifest['event']} review to {github['repo']}#{pr_number} "
        f"({n} line comment{'s' if n != 1 else ''}) ...",
        file=sys.stderr,
    )

    try:
        result = gh_api(
            f"/repos/{owner}/{repo_name}/pulls/{pr_number}/reviews",
            method="POST",
            data=payload,
        )
    except RuntimeError as e:
        sys.exit(f"error posting review: {e}")

    review_id = result.get("id", "?")
    html_url = result.get("html_url", "")
    print(f"  Posted review #{review_id}", file=sys.stderr)
    if html_url:
        print(f"  {html_url}", file=sys.stderr)

    # Resolve threads
    thread_ids = manifest.get("resolve_thread_ids", [])
    if thread_ids:
        print(f"Resolving {len(thread_ids)} thread(s) ...", file=sys.stderr)
        for tid in thread_ids:
            try:
                gh_graphql(RESOLVE_THREAD_MUTATION, {"threadId": tid})
                print(f"  resolved {tid}", file=sys.stderr)
            except RuntimeError as e:
                print(f"  warning: could not resolve {tid}: {e}", file=sys.stderr)

    print("Done.", file=sys.stderr)


if __name__ == "__main__":
    main()
