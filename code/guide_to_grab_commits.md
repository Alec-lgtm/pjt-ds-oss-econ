

When using `grab_commits.py`, run the command in the terminal like so:

```bash
python grab_commits.py \
  --repo https://github.com/serde-rs/json.git \
  --since 2023-01-01 \
  --until 2024-12-01 \
  --out serde_json.csv
```

You can put any git repo into the `--repo` section. Whether local (`../data/curl`) or on cloud (`https://github.com/curl/curl.git`)

The `--since` and `--until` sections use `YYYY-MM-DD` format, for example: `2024-03-05`

The `--out` controls the name of the csv file and the directory. For instance saving it `--out ../data/serde.csv` saves the csv file to the data directory
