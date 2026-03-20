# X Crawler Project

This is a standalone project for:

1. Stage 1: checking whether tweet IDs are still publicly available.
2. Stage 2: fetching tweets through `twitterapi.io` for the filtered IDs.
3. Test runs: randomly sampling IDs, then running stage 1 only or stage 1 plus stage 2.

It is self-contained and does not depend on the rest of `D:\MULTI`.

## Project Files

- `run_cli.py`: command-line entry
- `run_ui.py`: desktop UI entry
- `xcrawler_app/pipeline.py`: core stage logic
- `xcrawler_app/cli.py`: CLI wiring
- `xcrawler_app/ui.py`: Tkinter UI
- `requirements.txt`: dependencies
- `.env.example`: API key template

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Or just double-click:

- `setup.bat`

Optional environment variable:

```powershell
$env:TWITTERAPI_IO_KEY="YOUR_REAL_KEY"
```

## CLI Usage

Stage 1 only:

```powershell
python run_cli.py check --input "D:\path\to\tweet_ids.csv" --output-root ".\outputs"
```

Stage 2 only:

```powershell
python run_cli.py fetch --input "D:\path\to\available_ids.csv" --output-root ".\outputs" --api-key "YOUR_REAL_KEY"
```

Stage 1 + Stage 2:

```powershell
python run_cli.py pipeline --input "D:\path\to\tweet_ids.csv" --output-root ".\outputs" --api-key "YOUR_REAL_KEY"
```

Random sample test, stage 1 only:

```powershell
python run_cli.py test --input "D:\path\to\tweet_ids.csv" --mode check --sample-size 100 --seed 42 --output-root ".\outputs"
```

Random sample test, stage 1 + stage 2:

```powershell
python run_cli.py test --input "D:\path\to\tweet_ids.csv" --mode pipeline --sample-size 100 --seed 42 --output-root ".\outputs" --api-key "YOUR_REAL_KEY"
```

## UI Usage

Start the desktop app:

```powershell
python run_ui.py
```

Or just double-click:

- `start.ps1`
- `start.bat`

The UI lets you:

- input the `twitterapi.io` API key
- choose a local CSV or TXT file of tweet IDs
- choose the output root
- choose one of five run modes:
  - `check`
  - `fetch`
  - `pipeline`
  - `test-check`
  - `test-pipeline`
- set sample size and seed for test mode

## Output Layout

Given an output root like `.\outputs` and an input file named `roe_tweet_id.csv`, the project writes to:

- `.\outputs\roe_tweet_id\stage1_check\`
- `.\outputs\roe_tweet_id\stage2_fetch\`
- `.\outputs\roe_tweet_id\tests\`
- `.\outputs\roe_tweet_id\runs\`

## GitHub Notes

- Commit this folder only if you want a clean standalone repository.
- Do not commit real API keys.
- `.env.example` is safe to commit.
- `outputs/` is ignored by `.gitignore`.

## Upload To GitHub

If you want this folder to be its own repository, open a terminal in `XCrawlerProject` and run:

```powershell
git init
git add .
git commit -m "Initial X crawler project"
git branch -M main
git remote add origin https://github.com/<your-name>/<your-repo>.git
git push -u origin main
```

If the remote repository already exists and already has content, pull first:

```powershell
git pull origin main --allow-unrelated-histories
```
