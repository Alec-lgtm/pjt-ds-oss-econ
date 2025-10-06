import github
from datetime import datetime, timedelta, timezone
import re
import os
import json
import csv
from openai import OpenAI
from collections import Counter


# Setup
print("🔧 Setting up GitHub connection...")
auth = github.Auth.Token("ghp_xxx") # replace with your own token
g = github.Github(auth=auth)
repo = g.get_repo("serde-rs/json")
print(f"✓ Connected to repository: {repo.full_name}\n")

INPUT_COST_PER_MILLION_TOKENS = 0.25
OUTPUT_COST_PER_MILLION_TOKENS = 2.00


openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

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

def classify_pr_llm(title, body):
    user = f"""Classify this commit.

Commit message:
---
PR Title: {title}
PR Body: {body[:500] if body else 'No description'}
---
"""

    resp = openai_client.chat.completions.create(
        model="gpt-4.1-mini",
        # temperature=0,
        response_format={"type":"json_object"},
        messages=[
            {"role": "system", "content": CLASSIFIER_SYSTEM},
            {"role": "user", "content": user},
        ],
        #reasoning={"effort": "low"}
        #max_completion_tokens=200
    )

    if resp.usage:
        input_cost = (resp.usage.prompt_tokens / 1_000_000) * INPUT_COST_PER_MILLION_TOKENS
        output_cost = (resp.usage.completion_tokens / 1_000_000) * OUTPUT_COST_PER_MILLION_TOKENS
        total_cost = input_cost + output_cost
    else:
        total_cost = 0.0

    # Return a dictionary with classification and cost
    classification = json.loads(resp.choices[0].message.content)

    # print(f"classification: {classification.get('label')}\nrationale: {classification.get('rationale')}\nconfidence:{classification.get('confidence')}\n")

    return {
        "classification": classification,
        "cost": total_cost,
        "api_call_id": resp.id
    }

def classify_pr_regex(title, body):
    """Try to classify PR using regex patterns. Returns None if uncertain."""
    title_lower = title.lower()
    body_lower = (body or "").lower()
    text = title_lower + " " + body_lower

    # Dependency updates
    if any(word in title_lower for word in ['dependabot', 'bump', 'update dependencies']):
        return 'dependency_update'

    # Documentation
    if any(word in title_lower for word in ['docs', 'documentation', 'readme', 'comment']):
        if 'fix' not in title_lower:  # "fix docs" is different from "add docs"
            return 'documentation'

    # Bug fixes - be conservative, look for clear signals
    bug_patterns = [
        r'\bfix(es|ed)?\s+(bug|issue|#\d+)',
        r'\b(bug|issue)\s*fix',
        r'^fix:',
        r'\bsegfault\b',
        r'\bcrash\b',
        r'\bmemory leak\b'
    ]
    if any(re.search(pattern, title_lower) for pattern in bug_patterns):
        return 'bug_fix'

    # Refactoring
    if any(word in title_lower for word in ['refactor', 'clean up', 'simplify', 'reorganize']):
        return 'refactor'

    # CI/Build
    if any(word in title_lower for word in ['ci ', 'github actions', 'build', 'test']):
        return 'ci_build'

    # If we're unsure, return None to trigger LLM
    return None

def classify_pr(pr):
    """Classify a PR, trying regex first, then LLM."""
    # Try regex first
    category = classify_pr_regex(pr.title, pr.body)

    if category:
        return category, 'regex'

    # Fall back to LLM
    output = classify_pr_llm(pr.title, pr.body)
    return output, 'llm'

def main():
    # Date range
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=180)

    print(f"📊 Fetching PRs from {start_date.date()} to {end_date.date()}...\n")

    # Get PRs
    prs = repo.get_pulls(state='closed', sort='updated', direction='desc')

    classified_prs = []
    count = 0
    total_api_cost = 0.0

    for pr in prs:
        if pr.updated_at < start_date:
            print(f"\nStopped - reached PRs older than {start_date.date()}")
            break

        count += 1
        if count > 50:  # Limit for testing
            print("\nStopped at 50 PRs")
            break

        # Only process merged PRs
        if not pr.merged_at or pr.merged_at < start_date or pr.merged_at > end_date:
            continue

        # Classify
        output, method = classify_pr(pr)

        classification = output['classification']

        classified_prs.append({
            'number': pr.number,
            'title': pr.title,
            'category': classification.get('label'),
            'method': method,
            'merged_at': pr.merged_at,
            'confidence': classification.get("confidence"),
            'rationale': classification.get("rationale")
        })

        total_api_cost += output['cost']

        print(f"PR #{pr.number}: {classification.get('label'):20} [{method}] - {pr.title[:60]}")
        print(f"    confidence: {classification.get('confidence')}\n    rationale: {classification.get('rationale')[:60]}")
        print(f"    cost: {output['cost']:.5f}")

    # Summary
    print(f"\n{'='*80}")
    print("CLASSIFICATION SUMMARY")
    print(f"{'='*80}")

    categories = Counter(p['category'] for p in classified_prs)
    methods = Counter(p['method'] for p in classified_prs)

    print(f"\nTotal PRs classified: {len(classified_prs)}")
    print(f"\nBy category:")
    for cat, count in categories.most_common():
        print(f"  {cat:20} {count:3}")

    print(f"\nClassification method:")
    for method, count in methods.items():
        print(f"  {method:10} {count:3} ({100*count/len(classified_prs):.1f}%)")

    # API usage
    remaining, limit = g.rate_limiting
    print(f"\nGitHub API requests remaining: {remaining}/{limit}")
    print(f"Total API cost (this run): {total_api_cost:.5f}")

    # Save to CSV
    csv_filename = f"pr_classifications_{repo.name}_{start_date.date()}_to_{end_date.date()}.csv"

    fieldnames=['number', 'title', 'category', 'method', 'merged_at','confidence','rationale']

    with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(classified_prs)

    print(f"\nResults saved to: {csv_filename}")

if __name__ == '__main__':
    main()

