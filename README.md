# Madoka_X

Madoka_X is a standalone X (Twitter) rehydration toolkit for public datasets that, due to platform policy, can only release tweet IDs instead of full tweet content.

Madoka_X 是一个独立的 X（Twitter）推文复现抓取工具，面向那些因平台政策限制而只能公开发布 tweet ID、不能直接公开完整推文内容的数据集。

---

## Part I. Project Introduction | 第一部分：项目介绍

### 1. What This Project Is For | 1. 这个项目是做什么的

Many public X/Twitter datasets cannot directly redistribute tweet text, media, or full metadata. They can only publish tweet IDs. Madoka_X is built for that scenario: it helps you take a local CSV or TXT file of tweet IDs, check which tweets are still publicly available, and then fetch the recoverable tweets through `twitterapi.io`.

很多公开的 X/Twitter 数据集不能直接再分发推文正文、媒体或完整元数据，只能公开 tweet ID。Madoka_X 就是针对这个场景设计的：它接收你本地的 CSV 或 TXT 格式 tweet ID 文件，先检查这些推文现在是否仍然公开可用，再通过 `twitterapi.io` 抓取仍可恢复的推文内容。

### 2. Core Workflow | 2. 核心流程

Madoka_X supports two separable stages:

Madoka_X 支持两个可以分开执行的阶段：

1. Stage 1: check whether tweet IDs are still publicly available and generate a report.
2. Stage 2: fetch tweets for the IDs that passed stage 1.

1. 阶段一：检查 tweet ID 当前是否仍然公开可用，并生成筛查报告。
2. 阶段二：根据阶段一筛出的有效 ID 抓取推文内容。

It also supports test runs:

它同时支持测试模式：

- randomly sample 100 IDs from your input file
- run stage 1 only, or run stage 1 plus stage 2 on the sample

- 从输入文件中随机抽样 100 条 ID
- 对样本只跑阶段一，或者跑阶段一加阶段二的完整流程

### 3. Interfaces Provided | 3. 提供的使用方式

Madoka_X provides:

Madoka_X 提供以下使用方式：

- CLI command-line interface
- desktop UI
- Windows setup script
- Windows start scripts
- Windows single-file EXE build script

- CLI 命令行入口
- 桌面 UI 界面
- Windows 一键安装脚本
- Windows 启动脚本
- Windows 单文件 EXE 打包脚本

### 4. Required Inputs | 4. 运行所需输入

You only need three kinds of inputs:

运行时你只需要提供三类输入：

- `twitterapi.io` API key
- a local tweet ID file in `csv` or `txt` format
- an output directory

- `twitterapi.io` 的 API Key
- 本地 `csv` 或 `txt` 格式的 tweet ID 文件
- 输出目录

### 5. Project Files | 5. 项目文件说明

- `run_cli.py`: CLI entry
  - `run_cli.py`：CLI 命令行入口
- `run_ui.py`: desktop UI entry
  - `run_ui.py`：桌面 UI 入口
- `xcrawler_app/pipeline.py`: core pipeline logic
  - `xcrawler_app/pipeline.py`：核心流程逻辑
- `xcrawler_app/cli.py`: CLI argument wiring
  - `xcrawler_app/cli.py`：CLI 参数组织
- `xcrawler_app/ui_modern.py`: modern desktop UI
  - `xcrawler_app/ui_modern.py`：现代化桌面 UI
- `xcrawler_app/ui_text.py`: bilingual UI text
  - `xcrawler_app/ui_text.py`：中英文 UI 文案
- `XCrawlerProject.spec`: PyInstaller spec
  - `XCrawlerProject.spec`：PyInstaller 打包配置
- `build_exe.bat`: one-click EXE build script
  - `build_exe.bat`：一键打包 EXE 的脚本
- `requirements.txt`: Python dependencies
  - `requirements.txt`：Python 依赖
- `.env.example`: API key template
  - `.env.example`：API Key 模板文件

---

## Part II. Usage Guide | 第二部分：使用说明

### 1. Setup | 1. 环境安装

English:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

中文：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Or double-click `setup.bat`.

也可以直接双击 `setup.bat`。

Optional environment variable:

可选环境变量：

```powershell
$env:TWITTERAPI_IO_KEY="YOUR_REAL_KEY"
```

```powershell
$env:TWITTERAPI_IO_KEY="你的真实 API Key"
```

### 2. CLI Usage | 2. CLI 使用方式

#### Stage 1 only | 仅执行阶段一

English:

```powershell
python run_cli.py check --input "D:\path\to\tweet_ids.csv" --output-root ".\outputs"
```

中文：

```powershell
python run_cli.py check --input "D:\你的路径\tweet_ids.csv" --output-root ".\outputs"
```

#### Stage 2 only | 仅执行阶段二

English:

```powershell
python run_cli.py fetch --input "D:\path\to\available_ids.csv" --output-root ".\outputs" --api-key "YOUR_REAL_KEY"
```

中文：

```powershell
python run_cli.py fetch --input "D:\你的路径\available_ids.csv" --output-root ".\outputs" --api-key "你的真实 API Key"
```

#### Full pipeline | 执行完整流程

English:

```powershell
python run_cli.py pipeline --input "D:\path\to\tweet_ids.csv" --output-root ".\outputs" --api-key "YOUR_REAL_KEY"
```

中文：

```powershell
python run_cli.py pipeline --input "D:\你的路径\tweet_ids.csv" --output-root ".\outputs" --api-key "你的真实 API Key"
```

#### Sample test: stage 1 only | 抽样测试：只跑阶段一

English:

```powershell
python run_cli.py test --input "D:\path\to\tweet_ids.csv" --mode check --sample-size 100 --seed 42 --output-root ".\outputs"
```

中文：

```powershell
python run_cli.py test --input "D:\你的路径\tweet_ids.csv" --mode check --sample-size 100 --seed 42 --output-root ".\outputs"
```

#### Sample test: full pipeline | 抽样测试：跑完整流程

English:

```powershell
python run_cli.py test --input "D:\path\to\tweet_ids.csv" --mode pipeline --sample-size 100 --seed 42 --output-root ".\outputs" --api-key "YOUR_REAL_KEY"
```

中文：

```powershell
python run_cli.py test --input "D:\你的路径\tweet_ids.csv" --mode pipeline --sample-size 100 --seed 42 --output-root ".\outputs" --api-key "你的真实 API Key"
```

### 3. UI Usage | 3. UI 使用方式

Start the desktop UI:

启动桌面 UI：

English:

```powershell
python run_ui.py
```

中文：

```powershell
python run_ui.py
```

Or double-click:

也可以直接双击：

- `start.bat`
- `start.ps1`
- `Madoka_X.lnk` if you have already built the EXE
- 如果你已经打包过 EXE，也可以双击 `Madoka_X.lnk`

What the UI can do:

UI 可以做的事情：

- input the `twitterapi.io` API key
  - 输入 `twitterapi.io` API Key
- choose a local CSV or TXT file of tweet IDs
  - 选择本地 CSV 或 TXT 格式的 tweet ID 文件
- choose the output root
  - 选择输出目录
- switch UI language between Chinese and English
  - 在中文和英文界面之间切换
- choose one of five run modes
  - 选择五种运行模式之一
- set sample size and seed for test mode
  - 为测试模式设置抽样数量和随机种子
- save and load UI configuration
  - 保存和加载 UI 配置
- open the latest output directory directly
  - 直接打开最新输出目录
- open the latest report directly after a run
  - 在运行后直接打开最新报告
- use a larger default window with Windows high-DPI scaling
  - 使用更大的默认窗口，并支持 Windows 高 DPI 缩放

Saved UI configuration is written to `ui_settings.json` in the project root. It may include your API key if you save it in the form, so do not commit that file.

保存的 UI 配置会写入项目根目录下的 `ui_settings.json`。如果你把 API Key 一起保存进去，这个文件里会包含敏感信息，因此不要提交它。

### 4. Build EXE | 4. 打包 EXE

English:

```powershell
.\build_exe.bat
```

中文：

```powershell
.\build_exe.bat
```

What the build script does:

打包脚本会做的事情：

- use the local `.venv`
  - 使用本地 `.venv`
- install or upgrade `PyInstaller`
  - 安装或升级 `PyInstaller`
- build a windowed single-file executable with no console window
  - 打包成无控制台窗口的单文件可执行程序
- create a shortcut in the project root for quick launch
  - 在项目根目录自动生成一个快捷方式，方便直接启动

Output files after build:

打包后的输出文件：

- `.\dist\Madoka_X.exe`
- `.\Madoka_X.lnk`

### 5. Output Layout | 5. 输出目录结构

Given an output root like `.\outputs` and an input file named `roe_tweet_id.csv`, the project writes to:

如果输出根目录为 `.\outputs`，输入文件名为 `roe_tweet_id.csv`，则项目会写入：

- `.\outputs\roe_tweet_id\stage1_check\`
- `.\outputs\roe_tweet_id\stage2_fetch\`
- `.\outputs\roe_tweet_id\tests\`
- `.\outputs\roe_tweet_id\runs\`

### 6. GitHub Notes | 6. GitHub 提交说明

- Do not commit real API keys.
  - 不要提交真实 API Key。
- `.env.example` is safe to commit.
  - `.env.example` 可以安全提交。
- `outputs/`, `build/`, `dist/`, and `*.lnk` are ignored by `.gitignore`.
  - `outputs/`、`build/`、`dist/` 和 `*.lnk` 已由 `.gitignore` 忽略。
- `ui_settings.json` should stay local.
  - `ui_settings.json` 应只保留在本地。

### 7. Upload To GitHub | 7. 上传到 GitHub

If you want this folder to be its own repository:

如果你希望这个文件夹单独作为一个仓库：

English:

```powershell
git init
git add .
git commit -m "Initial Madoka_X project"
git branch -M main
git remote add origin https://github.com/<your-name>/<your-repo>.git
git push -u origin main
```

中文：

```powershell
git init
git add .
git commit -m "Initial Madoka_X project"
git branch -M main
git remote add origin https://github.com/<你的用户名>/<你的仓库名>.git
git push -u origin main
```

If the remote repository already has content, pull first:

如果远程仓库里已经有内容，先拉取：

English:

```powershell
git pull origin main --allow-unrelated-histories
```

中文：

```powershell
git pull origin main --allow-unrelated-histories
```
