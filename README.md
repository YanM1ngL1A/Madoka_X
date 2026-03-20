# X Crawler Project

## 中文说明

这是一个独立的 X（Twitter）推文爬取项目，支持两个可以分开执行的阶段：

1. 阶段一：检查 tweet ID 当前是否仍然公开可用，并输出筛查报告。
2. 阶段二：对阶段一筛出的可用 ID，使用 `twitterapi.io` API 抓取推文内容。

此外还支持测试模式：可以从你指定的 `csv` 或 `txt` tweet ID 文件中随机抽样 100 条，执行：

- 仅阶段一测试
- 阶段一加阶段二的完整流程测试

项目同时提供：

- CLI 命令行入口
- 桌面 UI 界面
- Windows 一键安装脚本
- Windows 一键启动脚本
- Windows GUI `exe` 打包脚本

运行时只需要你提供三类输入：

- `twitterapi.io` 的 API Key
- 本地 tweet ID 文件（`csv` 或 `txt`）
- 输出目录

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
- `xcrawler_app/ui_modern.py`: desktop UI implementation
- `xcrawler_app/ui_text.py`: bilingual UI text
- `XCrawlerProject.spec`: PyInstaller build spec
- `build_exe.bat`: one-click GUI exe build script
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
- switch UI language between Chinese and English
- choose one of five run modes:
  - `check`
  - `fetch`
  - `pipeline`
  - `test-check`
  - `test-pipeline`
- set sample size and seed for test mode
- save and load UI configuration with one click
- open the latest output directory directly
- open the latest generated report directly after a run
- use a larger default window with Windows high-DPI scaling

Saved UI configuration is written to `ui_settings.json` in the project root. It may include your API key if you save it in the form, so do not commit that file.

## Build EXE

Build a standalone Windows GUI executable:

```powershell
.\build_exe.bat
```

The build script will:

- use the local `.venv`
- install or upgrade `PyInstaller`
- build a windowed executable with no console window
- create a shortcut in the project root for quick launch

After a successful build, the UI executable will be at:

- `.\dist\Madoka_X.exe`
- `.\Madoka_X.lnk`

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
- `ui_settings.json` should stay local and should not be committed.

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
