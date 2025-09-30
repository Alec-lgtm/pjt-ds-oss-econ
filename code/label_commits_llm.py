#!/usr/bin/env python3
import re, csv, argparse, sys
from datetime import datetime
from pydriller import Repository, __version__ as pydriller_version
import json
from openai import OpenAI
import os

client = OpenAI()

CLASSIFIER_SYSTEM = """You are a precise commit classifier.
Return strict JSON with keys:
- label: one of ["feature","fix","refactor","docs","test","other"]
- confidence: float in [0,1]
- rationale: 1-2 sentences max (no code blocks).
Heuristics:
- fix: bug fix, patch, regression, crash, error handling
- feature: new functionality, new API, added support
- refactor: restructure without changing behavior, cleanup, rename
- docs: documentation updates, comments, README
- test: adds or modifies tests
- other: anything else
"""

def classify_commit_llm(message: str, diff_hint: str = "") -> dict:
    user = f"""Classify this commit.

Commit message:
---
{message.strip()}
---
"""

    resp = client.chat.completions.create(
        model="gpt-5-mini",
        # temperature=0,
        response_format={"type":"json_object"},
        messages=[
            {"role": "system", "content": CLASSIFIER_SYSTEM},
            {"role": "user", "content": user},
        ],
        #reasoning={"effort": "low"}
        #max_completion_tokens=200
    )

    print(resp)
    print(resp.choices[0].message.content)

    return json.loads(resp.choices[0].message.content)

def parse_args():
    p = argparse.ArgumentParser(description="Get commit information and store as csv")
    p.add_argument("--repo", required=True, help="Local path or remote Git URL")
    p.add_argument("--since", default=None, help="YYYY-MM-DD")
    p.add_argument("--until", default=None, help="YYYY-MM-DD")
    p.add_argument("--branch", default=None, help="Branch")
    p.add_argument("--saveas", default="name", help="Output CSV")
    p.add_argument("--label", action="store_true",
                   help="If set, call LLM to classify each commit")
    p.add_argument("--label-limit", type=int, default=None,
                   help="Max number of commits to label (for testing/cost control)")
    p.add_argument("--label-cache", default="../data/label_cache.jsonl",
                   help="Path to JSONL cache to avoid re-labeling")
    return p.parse_args()

def to_dt(s):
    return datetime.strptime(s, "%Y-%m-%d") if s else None

def load_cache(path):
    cache = {}
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    obj = json.loads(line)
                    cache[obj["hash"]] = obj
                except Exception:
                    pass
    return cache

def append_cache(path, record):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

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

    cache = load_cache(args.label_cache) if args.label else {}

    repo = Repository(
        path_to_repo=args.repo,
        since=since,
        to=until,
        only_in_branch=args.branch
    )
    labeled_count = 0


    for commit in repo.traverse_commits():
        msg_one_line = " ".join(commit.msg.split())
        commits_analyzed += 1
        if commits_analyzed % 100 == 0:
            print(f"[DEBUG] Scanned {commits_analyzed} commits... last={commit.hash[:8]}")

        # Skip merges
        if getattr(commit, "merge", False):
            continue

        label, confidence, rationale = None, None, None
        if args.label and (args.label_limit is None or labeled_count < args.label_limit):
            if commit.hash in cache:
                label = cache[commit.hash]["label"]
                confidence = cache[commit.hash]["confidence"]
                rationale = cache[commit.hash].get("rationale")
            else:
                try:
                    out = classify_commit_llm(msg_one_line)
                    label = out.get("label")
                    confidence = out.get("confidence")
                    rationale = out.get("rationale")
                    append_cache(args.label_cache, {
                        "hash": commit.hash,
                        "label": label,
                        "confidence": confidence,
                        "rationale": rationale,
                        "msg": msg_one_line
                    })
                except Exception as e:
                    print(f"[WARN] LLM classify failed for {commit.hash[:8]}: {e}")
            if label is not None:
                labeled_count += 1

        commit_info.append({
            "hash": commit.hash,
            "date": commit.author_date,
            "author": commit.author,
            "message": msg_one_line,
            # "branches": commit.branches,
            "lines_added": commit.insertions,
            "lines_removed": commit.deletions,
            "in_main_branch": commit.in_main_branch,
            "llm_label": label,
            "llm_confidence": confidence,
            "llm_rationale": rationale
        })

    # Write CSV
    fieldnames = ["hash", "date", "author", "message", "lines_added", "lines_removed", "in_main_branch", "llm_label", "llm_confidence", "llm_rationale"]
    with open(commit_saveas, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in commit_info:
            w.writerow(r)

    print(f"Commits scanned:       {commits_analyzed}")

if __name__ == "__main__":
    main()

