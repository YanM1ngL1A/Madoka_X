# Madoka_X

Madoka_X 是一个独立的 X（Twitter）推文复现抓取工具，面向那些因平台政策限制而只能公开发布 tweet ID、不能直接公开完整推文内容的数据集。

---

## 中文说明

### 项目介绍

很多公开的 X/Twitter 数据集不能直接再分发推文正文、媒体或完整元数据，只能公开 tweet ID。Madoka_X 就是针对这个场景设计的：它接收你本地的 CSV 或 TXT 格式 tweet ID 文件，先检查这些推文现在是否仍然公开可用，再通过 `twitterapi.io` 抓取仍可恢复的推文内容。

Madoka_X 支持两个可以分开执行的阶段：

1. 阶段一：检查 tweet ID 当前是否仍然公开可用，并生成筛查报告。
2. 阶段二：根据阶段一筛出的有效 ID 抓取推文内容。

它同时支持测试模式：

1. 从输入文件中随机抽样 100 条 ID。
2. 对样本只跑阶段一。
3. 或者对样本跑阶段一加阶段二的完整流程。

Madoka_X 提供以下使用方式：

1. CLI 命令行入口。
2. 桌面 UI 界面。
3. Windows 一键安装脚本。
4. Windows 启动脚本。
5. Windows 单文件 EXE 打包脚本。

运行时你只需要提供三类输入：

1. `twitterapi.io` 的 API Key。
2. 本地 `csv` 或 `txt` 格式的 tweet ID 文件。
3. 输出目录。

项目主要文件说明：

1. `run_cli.py`：CLI 命令行入口。
2. `run_ui.py`：桌面 UI 入口。
3. `xcrawler_app/pipeline.py`：核心流程逻辑。
4. `xcrawler_app/cli.py`：CLI 参数组织。
5. `xcrawler_app/ui_modern.py`：现代化桌面 UI。
6. `xcrawler_app/ui_text.py`：中英文 UI 文案。
7. `XCrawlerProject.spec`：PyInstaller 打包配置。
8. `build_exe.bat`：一键打包 EXE 的脚本。
9. `requirements.txt`：Python 依赖。
10. `.env.example`：API Key 模板文件。

### 使用说明

#### 1. 环境安装

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

也可以直接双击 `setup.bat`。

可选环境变量：

```powershell
$env:TWITTERAPI_IO_KEY="你的真实 API Key"
```

#### 2. CLI 使用方式

仅执行阶段一：

```powershell
python run_cli.py check --input "D:\你的路径\tweet_ids.csv" --output-root ".\outputs"
```

仅执行阶段二：

```powershell
python run_cli.py fetch --input "D:\你的路径\available_ids.csv" --output-root ".\outputs" --api-key "你的真实 API Key"
```

执行完整流程：

```powershell
python run_cli.py pipeline --input "D:\你的路径\tweet_ids.csv" --output-root ".\outputs" --api-key "你的真实 API Key"
```

抽样测试，只跑阶段一：

```powershell
python run_cli.py test --input "D:\你的路径\tweet_ids.csv" --mode check --sample-size 100 --seed 42 --output-root ".\outputs"
```

抽样测试，跑完整流程：

```powershell
python run_cli.py test --input "D:\你的路径\tweet_ids.csv" --mode pipeline --sample-size 100 --seed 42 --output-root ".\outputs" --api-key "你的真实 API Key"
```

#### 3. UI 使用方式

启动桌面 UI：

```powershell
python run_ui.py
```

也可以直接双击：

1. `start.bat`
2. `start.ps1`
3. 如果已经打包过 EXE，也可以双击 `Madoka_X.lnk`

UI 支持：

1. 输入 `twitterapi.io` API Key。
2. 选择本地 CSV 或 TXT 格式的 tweet ID 文件。
3. 选择输出目录。
4. 在中文和英文界面之间切换。
5. 选择五种运行模式之一。
6. 为测试模式设置抽样数量和随机种子。
7. 保存和加载 UI 配置。
8. 直接打开最新输出目录。
9. 在运行后直接打开最新报告。
10. 使用更大的默认窗口，并支持 Windows 高 DPI 缩放。

保存的 UI 配置会写入项目根目录下的 `ui_settings.json`。如果你把 API Key 一起保存进去，这个文件里会包含敏感信息，因此不要提交它。

#### 4. 打包 EXE

```powershell
.\build_exe.bat
```

打包脚本会做的事情：

1. 使用本地 `.venv`。
2. 安装或升级 `PyInstaller`。
3. 打包成无控制台窗口的单文件可执行程序。
4. 在项目根目录自动生成一个快捷方式，方便直接启动。

打包后的输出文件：

1. `.\dist\Madoka_X.exe`
2. `.\Madoka_X.lnk`

#### 5. 输出目录结构

如果输出根目录为 `.\outputs`，输入文件名为 `roe_tweet_id.csv`，则项目会写入：

1. `.\outputs\roe_tweet_id\stage1_check\`
2. `.\outputs\roe_tweet_id\stage2_fetch\`
3. `.\outputs\roe_tweet_id\tests\`
4. `.\outputs\roe_tweet_id\runs\`

#### 6. GitHub 提交说明

1. 不要提交真实 API Key。
2. `.env.example` 可以安全提交。
3. `outputs/`、`build/`、`dist/` 和 `*.lnk` 已由 `.gitignore` 忽略。
4. `ui_settings.json` 应只保留在本地。

#### 7. 上传到 GitHub

如果你希望这个文件夹单独作为一个仓库：

```powershell
git init
git add .
git commit -m "Initial Madoka_X project"
git branch -M main
git remote add origin https://github.com/<你的用户名>/<你的仓库名>.git
git push -u origin main
```

如果远程仓库里已经有内容，先拉取：

```powershell
git pull origin main --allow-unrelated-histories
```

---

## English Documentation

### Project Overview

Madoka_X is a standalone X (Twitter) rehydration toolkit for public datasets that, due to platform policy, can only release tweet IDs instead of full tweet content.

Many public X/Twitter datasets cannot directly redistribute tweet text, media, or full metadata. They can only publish tweet IDs. Madoka_X is built for that scenario: it takes a local CSV or TXT file of tweet IDs, checks which tweets are still publicly available, and then fetches the recoverable tweets through `twitterapi.io`.

Madoka_X supports two separable stages:

1. Stage 1: check whether tweet IDs are still publicly available and generate a report.
2. Stage 2: fetch tweets for the IDs that passed stage 1.

It also supports test runs:

1. Randomly sample 100 IDs from your input file.
2. Run stage 1 only on the sample.
3. Or run stage 1 plus stage 2 on the sample.

Madoka_X provides:

1. A CLI command-line interface.
2. A desktop UI.
3. A Windows setup script.
4. Windows start scripts.
5. A Windows single-file EXE build script.

You only need three kinds of inputs:

1. A `twitterapi.io` API key.
2. A local tweet ID file in `csv` or `txt` format.
3. An output directory.

Main project files:

1. `run_cli.py`: CLI entry.
2. `run_ui.py`: desktop UI entry.
3. `xcrawler_app/pipeline.py`: core pipeline logic.
4. `xcrawler_app/cli.py`: CLI argument wiring.
5. `xcrawler_app/ui_modern.py`: modern desktop UI.
6. `xcrawler_app/ui_text.py`: bilingual UI text.
7. `XCrawlerProject.spec`: PyInstaller spec.
8. `build_exe.bat`: one-click EXE build script.
9. `requirements.txt`: Python dependencies.
10. `.env.example`: API key template.

### Usage Guide

#### 1. Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Or just double-click `setup.bat`.

Optional environment variable:

```powershell
$env:TWITTERAPI_IO_KEY="YOUR_REAL_KEY"
```

#### 2. CLI Usage

Stage 1 only:

```powershell
python run_cli.py check --input "D:\path\to\tweet_ids.csv" --output-root ".\outputs"
```

Stage 2 only:

```powershell
python run_cli.py fetch --input "D:\path\to\available_ids.csv" --output-root ".\outputs" --api-key "YOUR_REAL_KEY"
```

Full pipeline:

```powershell
python run_cli.py pipeline --input "D:\path\to\tweet_ids.csv" --output-root ".\outputs" --api-key "YOUR_REAL_KEY"
```

Sample test, stage 1 only:

```powershell
python run_cli.py test --input "D:\path\to\tweet_ids.csv" --mode check --sample-size 100 --seed 42 --output-root ".\outputs"
```

Sample test, full pipeline:

```powershell
python run_cli.py test --input "D:\path\to\tweet_ids.csv" --mode pipeline --sample-size 100 --seed 42 --output-root ".\outputs" --api-key "YOUR_REAL_KEY"
```

#### 3. UI Usage

Start the desktop UI:

```powershell
python run_ui.py
```

Or double-click:

1. `start.bat`
2. `start.ps1`
3. If you have already built the EXE, `Madoka_X.lnk`

The UI lets you:

1. Input the `twitterapi.io` API key.
2. Choose a local CSV or TXT file of tweet IDs.
3. Choose the output root.
4. Switch UI language between Chinese and English.
5. Choose one of five run modes.
6. Set sample size and seed for test mode.
7. Save and load UI configuration.
8. Open the latest output directory directly.
9. Open the latest generated report directly after a run.
10. Use a larger default window with Windows high-DPI scaling.

Saved UI configuration is written to `ui_settings.json` in the project root. It may include your API key if you save it in the form, so do not commit that file.

#### 4. Build EXE

```powershell
.\build_exe.bat
```

The build script will:

1. Use the local `.venv`.
2. Install or upgrade `PyInstaller`.
3. Build a windowed single-file executable with no console window.
4. Create a shortcut in the project root for quick launch.

Build outputs:

1. `.\dist\Madoka_X.exe`
2. `.\Madoka_X.lnk`

#### 5. Output Layout

Given an output root like `.\outputs` and an input file named `roe_tweet_id.csv`, the project writes to:

1. `.\outputs\roe_tweet_id\stage1_check\`
2. `.\outputs\roe_tweet_id\stage2_fetch\`
3. `.\outputs\roe_tweet_id\tests\`
4. `.\outputs\roe_tweet_id\runs\`

#### 6. GitHub Notes

1. Do not commit real API keys.
2. `.env.example` is safe to commit.
3. `outputs/`, `build/`, `dist/`, and `*.lnk` are ignored by `.gitignore`.
4. `ui_settings.json` should stay local.

#### 7. Upload To GitHub

If you want this folder to be its own repository:

```powershell
git init
git add .
git commit -m "Initial Madoka_X project"
git branch -M main
git remote add origin https://github.com/<your-name>/<your-repo>.git
git push -u origin main
```

If the remote repository already has content, pull first:

```powershell
git pull origin main --allow-unrelated-histories
```
