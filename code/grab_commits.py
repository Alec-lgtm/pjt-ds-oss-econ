#!/usr/bin/env python3
import re, csv, argparse, sys
from datetime import datetime
from pydriller import Repository, __version__ as pydriller_version
import json

def parse_args():
    p = argparse.ArgumentParser(description="Get commit information and store as csv")
    p.add_argument("--repo", required=True, help="Local path or remote Git URL")
    p.add_argument("--since", default=None, help="YYYY-MM-DD")
    p.add_argument("--until", default=None, help="YYYY-MM-DD")
    p.add_argument("--branch", default=None, help="Branch")
    p.add_argument("--saveas", default="name", help="Output CSV")
    return p.parse_args()

def to_dt(s):
    return datetime.strptime(s, "%Y-%m-%d") if s else None

def main():
    args = parse_args()
    since, until = to_dt(args.since), to_dt(args.until)

    name = args.saveas
    commit_saveas = f'../data/{name}_commit_info.csv'
    modified_file_saveas = f'../data/{name}_modified_file_info.csv'

    print(f"[INFO] PyDriller version: {pydriller_version}")
    print(f"[INFO] Mining repo: {args.repo}")
    if since or until:
        print(f"[INFO] Date filter: since={args.since} until={args.until}")
    if args.branch:
        print(f"[INFO] Branch: {args.branch}")
    print(f"[INFO] Commit Info Output CSV: {commit_saveas}")
    print(f"[INFO] Modified Files Output CSV: {modified_file_saveas}\n")

    commits_analyzed = 0
    commit_info = []
    modified_files_info = []

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

        commit_info.append({
            "hash": commit.hash,
            "date": commit.author_date,
            "author": commit.author,
            "message": " ".join(commit.msg.split()),
            # "branches": commit.branches,
            "lines_added": commit.insertions,
            "lines_removed": commit.deletions,
            "in_main_branch": commit.in_main_branch
        })


        for mf in commit.modified_files:
            method_names = [method.name for method in mf.changed_methods]

            added_lines = [str(line_num) for line_num, content in mf.diff_parsed['added']]
            added_content = [content for line_num, content in mf.diff_parsed['added']]

            deleted_lines = [str(line_num) for line_num, content in mf.diff_parsed['deleted']]
            deleted_content = [content for line_num, content in mf.diff_parsed['deleted']]

            modified_files_info.append({
                "commit_hash": commit.hash,
                "commit_message": " ".join(commit.msg.split()),
                "filename": mf.filename,
                "change_type": mf.change_type,
                "diff_parsed": json.dumps(mf.diff_parsed), # convert to actual csv
                "changed_methods": ", ".join(method_names),
                "nloc": mf.nloc,
                "complexity": mf.complexity,
                "added_line_placement":",".join(added_lines),
                "added_content": "|".join(added_content),

                "deleted_line_placement":",".join(deleted_lines),
                "deleted_content": "|".join(deleted_content),

                "added_lines_count": mf.added_lines,
                "deleted_lines_count": mf.deleted_lines,
                "token_count": mf.token_count
            })

        # print(dir(mf.changed_methods))
        # print(type(mf.changed_methods))
        # print(mf.diff_parsed.keys())
        # print(mf.diff_parsed['added'])
        # return

    # print(commit.branches)
    # print(" ".join(commit.branches.split()))

    # Write CSV
    fieldnames = ["hash", "date", "author", "message", "branches", "lines_added", "lines_removed", "in_main_branch"]
    with open(commit_saveas, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in commit_info:
            w.writerow(r)

    fieldnames = ["commit_hash", "commit_message", "filename", "change_type", "diff_parsed", "changed_methods", "nloc", "complexity", "added_line_placement", "added_content", "deleted_line_placement", "deleted_content", "added_lines_count", "deleted_lines_count", "token_count"]
    with open(modified_file_saveas, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in modified_files_info:
            w.writerow(r)

    print(f"Commits scanned:       {commits_analyzed}")

if __name__ == "__main__":
    main()

