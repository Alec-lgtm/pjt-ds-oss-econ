
import re, csv, argparse, sys
from datetime import datetime
from statistics import mean, median
from pydriller import Repository

def main():
    repo = Repository(
        path_to_repo='https://github.com/curl/curl.git',
        since=datetime(2024, 11, 1),
        to=datetime(2024, 12, 1),
    )

    for commit in repo.traverse_commits():
        print(f"{commit.hash[:8]} {commit.author.name} {commit.msg.splitlines()[0]}")


if __name__ == '__main__':
    main()
