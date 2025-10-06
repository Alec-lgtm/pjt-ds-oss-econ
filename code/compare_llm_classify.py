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
auth = github.Auth.Token("ghp_xxx")
g = github.Github(auth=auth)
repo = g.get_repo("serde-rs/json")
print(f"✓ Connected to repository: {repo.full_name}\n")

INPUT_COST_PER_MILLION_TOKENS = 0.25
OUTPUT_COST_PER_MILLION_TOKENS = 2.00

openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
deepseek_client = OpenAI(
    api_key=os.environ.get("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

CLASSIFIER_SYSTEM = """You are a precise PR classifier.
Return valid JSON only in the following format:

{
  "label": "feature|fix|refactor|docs|test|other",
  "confidence": float between 0 and 1,
  "rationale": "1–2 concise sentences explaining both label and magnitude."
}

Decision hierarchy:
1. fix → resolves a failure, error, crash, or CI breakage.
2. feature → adds new capability or user-visible functionality.
3. refactor → restructures or removes code/config without changing behavior.
4. docs → documentation, comments, or typos only.
5. test → adds/modifies tests.
6. other → everything else.

Always output valid JSON and ignore unrelated text or boilerplate.
"""

def classify_pr_openai(title, body):
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

    return {
        "classification": classification,
        "cost": total_cost,
        "api_call_id": resp.id
    }

def classify_pr_deepseek(title, body):
    user = f"""Classify this commit.

Commit message:
---
PR Title: {title}
PR Body: {body[:500] if body else 'No description'}
---
"""

    resp = deepseek_client.chat.completions.create(
        model="deepseek-chat",
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

    return {
        "classification": classification,
        "cost": total_cost,
        "api_call_id": resp.id
    }

def classify_pr(pr):
    """Classify a PR with both OpenAI and DeepSeek."""
    # Get both classifications
    openai_output = classify_pr_openai(pr.title, pr.body)
    deepseek_output = classify_pr_deepseek(pr.title, pr.body)

    openai_class = openai_output['classification']
    deepseek_class = deepseek_output['classification']

    agreement = (openai_class.get('label') == deepseek_class.get('label'))

    return {
        'openai': openai_output,
        'deepseek': deepseek_output,
        'agreement': agreement
    }

def main():
    # Date range
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=30)

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
        output = classify_pr(pr)

        openai_class = output['openai']['classification']
        deepseek_class = output['deepseek']['classification']

        classified_prs.append({
            'number': pr.number,
            'title': pr.title,
            'openai_category': openai_class.get('label'),
            'openai_confidence': openai_class.get('confidence'),
            'openai_rationale': openai_class.get('rationale'),
            'openai_magnitude': openai_class.get('magnitude'),
            'deepseek_category': deepseek_class.get('label'),
            'deepseek_confidence': deepseek_class.get('confidence'),
            'deepseek_rationale': deepseek_class.get('rationale'),
            'deepseek_magnitude': deepseek_class.get('magnitude'),
            'agreement': output['agreement'],
            'merged_at': pr.merged_at
        })

        total_api_cost += output['openai']['cost'] + output['deepseek']['cost']

        agree_symbol = '✓' if output['agreement'] else '✗'
        print(f"PR #{pr.number}: OpenAI={openai_class.get('label'):15} DeepSeek={deepseek_class.get('label'):15} {agree_symbol}")
        if not output['agreement']:
            print(f"    DISAGREEMENT - manual review needed")
        print(f"    cost: {output['openai']['cost'] + output['deepseek']['cost']:.5f}")

    print(f"\n{'='*80}")
    print("CLASSIFICATION SUMMARY")
    print(f"{'='*80}")

    openai_categories = Counter(p['openai_category'] for p in classified_prs)
    deepseek_categories = Counter(p['deepseek_category'] for p in classified_prs)

    print(f"\nTotal PRs classified: {len(classified_prs)}")

    print(f"\nOpenAI categories:")
    for cat, count in openai_categories.most_common():
        print(f"  {cat:20} {count:3}")

    print(f"\nDeepSeek categories:")
    for cat, count in deepseek_categories.most_common():
        print(f"  {cat:20} {count:3}")

    # API usage
    remaining, limit = g.rate_limiting
    print(f"\nGitHub API requests remaining: {remaining}/{limit}")
    print(f"Total API cost (this run): {total_api_cost:.5f}")

    # Disagreement analysis
    disagreements = [p for p in classified_prs if not p['agreement']]
    print(f"\nAgreement rate: {100*(1-len(disagreements)/len(classified_prs)):.1f}%")
    if disagreements:
        print(f"\nDisagreements ({len(disagreements)}):")
        for p in disagreements[:10]:  # Show first 10
            print(f"  PR #{p['number']}: OpenAI={p['openai_category']}, DeepSeek={p['deepseek_category']}")

    # Save to CSV
    csv_filename = f"pr_classifications_{repo.name}_llm_comparisons_{start_date.date()}_to_{end_date.date()}.csv"

    fieldnames = ['number', 'title',
              'openai_category', 'openai_confidence', 'openai_rationale', 'openai_magnitude',
              'deepseek_category', 'deepseek_confidence', 'deepseek_rationale', 'deepseek_magnitude',
              'agreement', 'merged_at']


    with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(classified_prs)

    print(f"\nResults saved to: {csv_filename}")

if __name__ == '__main__':
    main()

