

### General Usage

When using `grab_commits.py`, run the command in the terminal like so:

```bash
python grab_commits.py \
  --repo https://github.com/serde-rs/json.git \
  --since 2023-01-01 \
  --until 2024-12-01 \
  --saveas serde_json
```

You can put any git repo into the `--repo` section. Whether local (`../data/curl`) or on cloud (`https://github.com/curl/curl.git`)

The `--since` and `--until` sections use `YYYY-MM-DD` format, for example: `2024-03-05`

The `--saveas` is the name you want your csv file to be saved as. There will be two csv files, one for commits and one for files modified. For example the above command outputs: `serde_json_commit_info.csv` and `serde_json_modified_file_info.csv`

**Csv files will be saved in the data/ directory**

---

### Data Dictionary

**For the commit_info csv:**

- **`hash`** - Unique SHA-1 identifier of the commit
- **`date`** - Author date timestamp of when the commit was created
- **`author`** - Name/email of the person who authored the commit
- **`message`** - Commit message text (whitespace normalized)
- **`lines_added`** - Count of lines inserted in this commit
- **`lines_removed`** - Count of lines deleted in this commit

**For the modified_file csv:

- **`commit_hash`** - Parent commit identifier
- **`commit_message`** - Normalized commit message
- **`filename`** - Name of the modified file
- **`change_type`** - Type of change (ADD, MODIFY, DELETE, etc.)
- **`changed_methods`** - Comma-separated list of method names affected by commit
- **`nloc`** - Number of lines of code in the file
- **`complexity`** - Cyclomatic complexity score
- **`token_count`** - Total number of code tokens
- **`added_line_placement`** - Comma-separated line numbers where content was added
- **`added_content`** - Pipe-separated actual content of added lines
- **`added_lines_count`** - Total count of added lines
- **`deleted_line_placement`** - Comma-separated line numbers where content was removed
- **`deleted_content`** - Pipe-separated actual content of deleted lines (pipe is this symbol |)
- **`deleted_lines_count`** - Total count of deleted lines
- **`diff_parsed`** - diff parsed is a json object that contains the added and deleted lines. (for easier data analysis compared to the `added_content` and `added_line_placement` variables)

**Diagram**

For illustration:

```
┌─────────────────┐
│   Commit Data   │
└─────────────────┘
        │
        ▼
┌─────────────────┐    ┌────────────────────┐
│ Modified Files  │───▶│ Per-File Analysis  │
└─────────────────┘    └────────────────────┘
       │
       ▼
├─ File Metadata    ──┐
├─ Line Changes      │
├─ Method Changes    │───▶ Structured Record
├─ Complexity Metrics │
└─ Content Details   ──┘
```
