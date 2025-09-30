#!/usr/bin/env python3
import re, csv, argparse, sys
from datetime import datetime
from pydriller import Repository, __version__ as pydriller_version

def parse_args():
    p = argparse.ArgumentParser(description="Get commit information and store as csv")
    p.add_argument("--repo", required=True, help="Local path or remote Git URL")
    p.add_argument("--since", default=None, help="YYYY-MM-DD")
    p.add_argument("--until", default=None, help="YYYY-MM-DD")
    p.add_argument("--branch", default=None, help="Branch")
    p.add_argument("--out", default="output.csv", help="Output CSV")
    return p.parse_args()

def to_dt(s):
    return datetime.strptime(s, "%Y-%m-%d") if s else None

def main():
    args = parse_args()
    since, until = to_dt(args.since), to_dt(args.until)

    print(f"[INFO] PyDriller version: {pydriller_version}")
    print(f"[INFO] Mining repo: {args.repo}")
    if since or until:
        print(f"[INFO] Date filter: since={args.since} until={args.until}")
    if args.branch:
        print(f"[INFO] Branch: {args.branch}")
    print(f"[INFO] Output CSV: {args.out}\n")

    commits_analyzed = 0
    rows = []

    repo = Repository(
        path_to_repo=args.repo,
        since=since,
        to=until,
        only_in_branch=args.branch
    )

    for commit in repo.traverse_commits():
        commits_analyzed += 1
        if commits_analyzed % 100 == 0:
            print(f"[DEBUG] Scanned {commits_analyzed} commits... last={commit.hash[:8]}")

        # Skip merges
        if getattr(commit, "merge", False):
            continue

        # Sum churn over modified files
        added = removed = 0

        rows.append({
            "commit_hash": commit.hash,
            "author_date": commit.author_date,
            "message": " ".join(commit.msg.split()),
            "files_changed": len(getattr(commit, "modified_files", [])),
            "lines_added": commit.insertions,
            "lines_removed": commit.deletions,
            "in_main_branch": commit.in_main_branch
        })

    # Write CSV
    fieldnames = ["commit_hash","author_date","message","files_changed","lines_added","lines_removed","in_main_branch"]
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    print(f"Commits scanned:       {commits_analyzed}")

if __name__ == "__main__":
    main()

