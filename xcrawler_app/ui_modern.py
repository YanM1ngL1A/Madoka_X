import json
import os
import queue
import threading
import tkinter as tk
import ctypes
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from xcrawler_app.pipeline import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_FETCH_TIMEOUT,
    DEFAULT_SAMPLE_SEED,
    DEFAULT_SAMPLE_SIZE,
    DEFAULT_SLEEP_SEC,
    DEFAULT_TIMEOUT,
    DEFAULT_WORKERS,
    CheckConfig,
    FetchConfig,
    get_api_key,
    run_check,
    run_fetch,
    run_pipeline,
    run_test,
)
from xcrawler_app.ui_text import MODE_TEXT, TEXT


CONFIG_PATH = Path(__file__).resolve().parents[1] / "ui_settings.json"


def configure_high_dpi(root: tk.Tk) -> None:
    if os.name != "nt":
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            return

    try:
        dpi = ctypes.windll.user32.GetDpiForSystem()
    except Exception:
        dpi = 96
    scale = max(1.0, dpi / 96.0)
    try:
        root.tk.call("tk", "scaling", scale)
    except Exception:
        pass


class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.lang = "en"
        self.stage_code = "check"
        self.log_queue: queue.Queue[str] = queue.Queue()
        self.worker_thread: threading.Thread | None = None
        self.latest_output_path: Path | None = None
        self.latest_report_path: Path | None = None
        self._init_vars()
        self._style()
        self._build()
        self._apply_text()
        self._refresh_fields()
        self.root.after(100, self._drain_log_queue)

    def _init_vars(self) -> None:
        base = Path(__file__).resolve().parents[1] / "outputs"
        self.mode_var = tk.StringVar()
        self.input_var = tk.StringVar()
        self.output_var = tk.StringVar(value=str(base))
        self.api_var = tk.StringVar()
        self.top_n_var = tk.StringVar(value="0")
        self.sample_size_var = tk.StringVar(value=str(DEFAULT_SAMPLE_SIZE))
        self.seed_var = tk.StringVar(value=str(DEFAULT_SAMPLE_SEED))
        self.workers_var = tk.StringVar(value=str(DEFAULT_WORKERS))
        self.check_timeout_var = tk.StringVar(value=str(DEFAULT_TIMEOUT))
        self.check_retries_var = tk.StringVar(value="2")
        self.batch_var = tk.StringVar(value=str(DEFAULT_BATCH_SIZE))
        self.sleep_var = tk.StringVar(value=str(DEFAULT_SLEEP_SEC))
        self.fetch_timeout_var = tk.StringVar(value=str(DEFAULT_FETCH_TIMEOUT))
        self.fetch_retries_var = tk.StringVar(value="3")
        self.status_var = tk.StringVar()

    def _style(self) -> None:
        self.root.title("X Crawler")
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        width = min(1440, max(1180, int(screen_width * 0.82)))
        height = min(980, max(820, int(screen_height * 0.84)))
        self.root.geometry(f"{width}x{height}")
        self.root.minsize(1180, 820)
        self.root.configure(bg="#f3efe7")

        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("Bg.TFrame", background="#f3efe7")
        style.configure("Card.TFrame", background="#fffdf8")
        style.configure("Card.TLabelframe", background="#fffdf8", borderwidth=1, relief="solid")
        style.configure(
            "Card.TLabelframe.Label",
            background="#fffdf8",
            foreground="#22313f",
            font=("Segoe UI", 10, "bold"),
        )
        style.configure("Title.TLabel", background="#f3efe7", foreground="#1b2733", font=("Segoe UI", 24, "bold"))
        style.configure("Sub.TLabel", background="#f3efe7", foreground="#667380", font=("Segoe UI", 10))
        style.configure("Field.TLabel", background="#fffdf8", foreground="#22313f", font=("Segoe UI", 10, "bold"))
        style.configure("Hint.TLabel", background="#fffdf8", foreground="#74808a", font=("Segoe UI", 9))
        style.configure("Accent.TButton", background="#176b87", foreground="#ffffff", borderwidth=0, padding=(14, 10))
        style.map("Accent.TButton", background=[("active", "#0f5a72")])
        style.configure("Soft.TButton", background="#e5eee7", foreground="#22313f", borderwidth=0, padding=(12, 10))
        style.map("Soft.TButton", background=[("active", "#d7e6dc")])
        style.configure("RunSecondary.TButton", background="#e7edf6", foreground="#24496e", borderwidth=0, padding=(12, 10))
        style.map("RunSecondary.TButton", background=[("active", "#d9e3f2")])
        style.configure("Lang.TButton", background="#eee0cb", foreground="#5d4521", borderwidth=0, padding=(12, 8))
        style.map("Lang.TButton", background=[("active", "#e4d2b4")])
        style.configure("Modern.TEntry", fieldbackground="#fffdf8", foreground="#1b2733", borderwidth=1)
        style.configure("Modern.TCombobox", fieldbackground="#fffdf8", foreground="#1b2733", arrowsize=16)

    def _build(self) -> None:
        outer = ttk.Frame(self.root, style="Bg.TFrame", padding=18)
        outer.pack(fill=tk.BOTH, expand=True)
        outer.columnconfigure(0, weight=3)
        outer.columnconfigure(1, weight=2)
        outer.rowconfigure(1, weight=1)

        header = ttk.Frame(outer, style="Bg.TFrame")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 14))
        header.columnconfigure(0, weight=1)
        self.title_label = ttk.Label(header, style="Title.TLabel")
        self.title_label.grid(row=0, column=0, sticky="w")
        self.subtitle_label = ttk.Label(header, style="Sub.TLabel")
        self.subtitle_label.grid(row=1, column=0, sticky="w", pady=(4, 0))
        self.lang_button = ttk.Button(header, style="Lang.TButton", command=self._toggle_language)
        self.lang_button.grid(row=0, column=1, sticky="e")
        self.status_badge = tk.Label(
            header,
            textvariable=self.status_var,
            bg="#e7efe4",
            fg="#2f5832",
            padx=12,
            pady=6,
            font=("Segoe UI", 10, "bold"),
        )
        self.status_badge.grid(row=1, column=1, sticky="e")

        left = ttk.Frame(outer, style="Card.TFrame", padding=18)
        left.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        left.columnconfigure(1, weight=1)
        self._build_left(left)

        right = ttk.Frame(outer, style="Card.TFrame", padding=18)
        right.grid(row=1, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(3, weight=1)
        self._build_right(right)

    def _build_left(self, parent: ttk.Frame) -> None:
        self.mode_label = ttk.Label(parent, style="Field.TLabel")
        self.mode_label.grid(row=0, column=0, sticky="w", pady=6)
        self.mode_box = ttk.Combobox(parent, textvariable=self.mode_var, state="readonly", style="Modern.TCombobox")
        self.mode_box.grid(row=0, column=1, columnspan=2, sticky="ew", pady=6)
        self.mode_box.bind("<<ComboboxSelected>>", self._on_mode_change)

        self.input_label = ttk.Label(parent, style="Field.TLabel")
        self.input_label.grid(row=1, column=0, sticky="w", pady=6)
        ttk.Entry(parent, textvariable=self.input_var, style="Modern.TEntry").grid(row=1, column=1, sticky="ew", pady=6)
        self.input_button = ttk.Button(parent, style="Soft.TButton", command=self._choose_input)
        self.input_button.grid(row=1, column=2, sticky="ew", padx=(10, 0), pady=6)

        self.output_label = ttk.Label(parent, style="Field.TLabel")
        self.output_label.grid(row=2, column=0, sticky="w", pady=6)
        ttk.Entry(parent, textvariable=self.output_var, style="Modern.TEntry").grid(row=2, column=1, sticky="ew", pady=6)
        self.output_button = ttk.Button(parent, style="Soft.TButton", command=self._choose_output)
        self.output_button.grid(row=2, column=2, sticky="ew", padx=(10, 0), pady=6)

        self.api_label = ttk.Label(parent, style="Field.TLabel")
        self.api_label.grid(row=3, column=0, sticky="w", pady=6)
        self.api_entry = ttk.Entry(parent, textvariable=self.api_var, show="*", style="Modern.TEntry")
        self.api_entry.grid(row=3, column=1, sticky="ew", pady=6)
        self.api_hint = ttk.Label(parent, style="Hint.TLabel")
        self.api_hint.grid(row=3, column=2, sticky="w", padx=(10, 0), pady=6)

        self.top_n_label = ttk.Label(parent, style="Field.TLabel")
        self.top_n_label.grid(row=4, column=0, sticky="w", pady=6)
        ttk.Entry(parent, textvariable=self.top_n_var, style="Modern.TEntry").grid(row=4, column=1, columnspan=2, sticky="ew", pady=6)

        self.sample_size_label = ttk.Label(parent, style="Field.TLabel")
        self.sample_size_label.grid(row=5, column=0, sticky="w", pady=6)
        self.sample_size_entry = ttk.Entry(parent, textvariable=self.sample_size_var, style="Modern.TEntry")
        self.sample_size_entry.grid(row=5, column=1, sticky="ew", pady=6)
        self.sample_hint = ttk.Label(parent, style="Hint.TLabel")
        self.sample_hint.grid(row=5, column=2, sticky="w", padx=(10, 0), pady=6)

        self.seed_label = ttk.Label(parent, style="Field.TLabel")
        self.seed_label.grid(row=6, column=0, sticky="w", pady=6)
        self.seed_entry = ttk.Entry(parent, textvariable=self.seed_var, style="Modern.TEntry")
        self.seed_entry.grid(row=6, column=1, columnspan=2, sticky="ew", pady=6)

        btns = ttk.Frame(parent, style="Card.TFrame")
        btns.grid(row=7, column=0, columnspan=3, sticky="ew", pady=(16, 0))
        self.run_button = ttk.Button(btns, style="Accent.TButton", command=self._run)
        self.run_button.pack(side=tk.LEFT)
        self.clear_button = ttk.Button(btns, style="Soft.TButton", command=self._clear_log)
        self.clear_button.pack(side=tk.LEFT, padx=(10, 0))

        btns2 = ttk.Frame(parent, style="Card.TFrame")
        btns2.grid(row=8, column=0, columnspan=3, sticky="ew", pady=(10, 0))
        self.save_button = ttk.Button(btns2, style="RunSecondary.TButton", command=self._save_config)
        self.save_button.pack(side=tk.LEFT)
        self.load_button = ttk.Button(btns2, style="RunSecondary.TButton", command=self._load_config)
        self.load_button.pack(side=tk.LEFT, padx=(10, 0))
        self.open_output_button = ttk.Button(btns2, style="Soft.TButton", command=self._open_output_dir)
        self.open_output_button.pack(side=tk.LEFT, padx=(10, 0))
        self.open_report_button = ttk.Button(btns2, style="Soft.TButton", command=self._open_latest_report)
        self.open_report_button.pack(side=tk.LEFT, padx=(10, 0))

    def _build_right(self, parent: ttk.Frame) -> None:
        self.check_card = ttk.LabelFrame(parent, style="Card.TLabelframe", padding=14)
        self.check_card.grid(row=0, column=0, sticky="ew")
        self.check_card.columnconfigure(1, weight=1)
        self.workers_label = ttk.Label(self.check_card, style="Field.TLabel")
        self.workers_label.grid(row=0, column=0, sticky="w", pady=6)
        ttk.Entry(self.check_card, textvariable=self.workers_var, style="Modern.TEntry").grid(row=0, column=1, sticky="ew", pady=6)
        self.check_timeout_label = ttk.Label(self.check_card, style="Field.TLabel")
        self.check_timeout_label.grid(row=1, column=0, sticky="w", pady=6)
        ttk.Entry(self.check_card, textvariable=self.check_timeout_var, style="Modern.TEntry").grid(row=1, column=1, sticky="ew", pady=6)
        self.check_retries_label = ttk.Label(self.check_card, style="Field.TLabel")
        self.check_retries_label.grid(row=2, column=0, sticky="w", pady=6)
        ttk.Entry(self.check_card, textvariable=self.check_retries_var, style="Modern.TEntry").grid(row=2, column=1, sticky="ew", pady=6)

        self.fetch_card = ttk.LabelFrame(parent, style="Card.TLabelframe", padding=14)
        self.fetch_card.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        self.fetch_card.columnconfigure(1, weight=1)
        self.batch_label = ttk.Label(self.fetch_card, style="Field.TLabel")
        self.batch_label.grid(row=0, column=0, sticky="w", pady=6)
        self.batch_entry = ttk.Entry(self.fetch_card, textvariable=self.batch_var, style="Modern.TEntry")
        self.batch_entry.grid(row=0, column=1, sticky="ew", pady=6)
        self.sleep_label = ttk.Label(self.fetch_card, style="Field.TLabel")
        self.sleep_label.grid(row=1, column=0, sticky="w", pady=6)
        self.sleep_entry = ttk.Entry(self.fetch_card, textvariable=self.sleep_var, style="Modern.TEntry")
        self.sleep_entry.grid(row=1, column=1, sticky="ew", pady=6)
        self.fetch_timeout_label = ttk.Label(self.fetch_card, style="Field.TLabel")
        self.fetch_timeout_label.grid(row=2, column=0, sticky="w", pady=6)
        self.fetch_timeout_entry = ttk.Entry(self.fetch_card, textvariable=self.fetch_timeout_var, style="Modern.TEntry")
        self.fetch_timeout_entry.grid(row=2, column=1, sticky="ew", pady=6)
        self.fetch_retries_label = ttk.Label(self.fetch_card, style="Field.TLabel")
        self.fetch_retries_label.grid(row=3, column=0, sticky="w", pady=6)
        self.fetch_retries_entry = ttk.Entry(self.fetch_card, textvariable=self.fetch_retries_var, style="Modern.TEntry")
        self.fetch_retries_entry.grid(row=3, column=1, sticky="ew", pady=6)

        self.log_label = ttk.Label(parent, style="Field.TLabel")
        self.log_label.grid(row=2, column=0, sticky="w", pady=(14, 6))
        self.log_text = tk.Text(
            parent,
            bg="#0f1720",
            fg="#d7e2ea",
            insertbackground="#d7e2ea",
            relief="flat",
            font=("Consolas", 10),
            padx=12,
            pady=12,
            wrap="word",
        )
        self.log_text.grid(row=3, column=0, sticky="nsew")

    def tr(self, key: str) -> str:
        return TEXT[self.lang][key]

    def _apply_text(self) -> None:
        self.root.title(self.tr("title"))
        self.title_label.configure(text=self.tr("title"))
        self.subtitle_label.configure(text=self.tr("subtitle"))
        self.lang_button.configure(text=self.tr("toggle"))
        self.mode_label.configure(text=self.tr("mode"))
        self.input_label.configure(text=self.tr("input"))
        self.output_label.configure(text=self.tr("output"))
        self.api_label.configure(text=self.tr("api"))
        self.api_hint.configure(text=self.tr("api_hint"))
        self.top_n_label.configure(text=self.tr("top_n"))
        self.sample_size_label.configure(text=self.tr("sample_size"))
        self.sample_hint.configure(text=self.tr("sample_hint"))
        self.seed_label.configure(text=self.tr("seed"))
        self.check_card.configure(text=self.tr("check_card"))
        self.fetch_card.configure(text=self.tr("fetch_card"))
        self.workers_label.configure(text=self.tr("workers"))
        self.check_timeout_label.configure(text=self.tr("timeout"))
        self.check_retries_label.configure(text=self.tr("retries"))
        self.batch_label.configure(text=self.tr("batch"))
        self.sleep_label.configure(text=self.tr("sleep"))
        self.fetch_timeout_label.configure(text=self.tr("timeout"))
        self.fetch_retries_label.configure(text=self.tr("retries"))
        self.input_button.configure(text=self.tr("browse"))
        self.output_button.configure(text=self.tr("browse"))
        self.run_button.configure(text=self.tr("run"))
        self.clear_button.configure(text=self.tr("clear"))
        self.save_button.configure(text=self.tr("save_config"))
        self.load_button.configure(text=self.tr("load_config"))
        self.open_output_button.configure(text=self.tr("open_output"))
        self.open_report_button.configure(text=self.tr("open_report"))
        self.log_label.configure(text=self.tr("log"))
        self._refresh_modes()
        self._set_status("idle")

    def _refresh_modes(self) -> None:
        order = ("check", "fetch", "pipeline", "test-check", "test-pipeline")
        values = [MODE_TEXT[self.lang][code] for code in order]
        self.mode_box.configure(values=values)
        self.mode_var.set(MODE_TEXT[self.lang][self.stage_code])

    def _toggle_language(self) -> None:
        self.lang = "zh" if self.lang == "en" else "en"
        self._apply_text()
        self._refresh_fields()

    def _stage_from_label(self, label: str) -> str:
        for code, text in MODE_TEXT[self.lang].items():
            if text == label:
                return code
        return "check"

    def _set_status(self, state: str) -> None:
        self.status_var.set(self.tr(state))
        palette = {
            "idle": ("#e7efe4", "#2f5832"),
            "running": ("#e9f0fb", "#1f477d"),
            "done": ("#e7efe4", "#2f5832"),
            "error": ("#f9e6e4", "#8c3129"),
        }
        bg, fg = palette[state]
        self.status_badge.configure(bg=bg, fg=fg)

    def _set_status_async(self, state: str) -> None:
        self.root.after(0, lambda: self._set_status(state))

    def _on_mode_change(self, _event=None) -> None:
        self.stage_code = self._stage_from_label(self.mode_var.get())
        self._refresh_fields()

    def _refresh_fields(self) -> None:
        is_test = self.stage_code.startswith("test")
        needs_fetch = self.stage_code in {"fetch", "pipeline", "test-pipeline"}
        sample_state = "normal" if is_test else "disabled"
        fetch_state = "normal" if needs_fetch else "disabled"

        self.sample_size_entry.configure(state=sample_state)
        self.seed_entry.configure(state=sample_state)
        self.api_entry.configure(state=fetch_state)
        self.batch_entry.configure(state=fetch_state)
        self.sleep_entry.configure(state=fetch_state)
        self.fetch_timeout_entry.configure(state=fetch_state)
        self.fetch_retries_entry.configure(state=fetch_state)

    def _choose_input(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("ID files", "*.csv *.txt"), ("All files", "*.*")])
        if path:
            self.input_var.set(path)

    def _choose_output(self) -> None:
        path = filedialog.askdirectory()
        if path:
            self.output_var.set(path)

    def _clear_log(self) -> None:
        self.log_text.delete("1.0", tk.END)

    def _collect_config(self) -> dict:
        return {
            "lang": self.lang,
            "stage_code": self.stage_code,
            "input": self.input_var.get(),
            "output": self.output_var.get(),
            "api": self.api_var.get(),
            "top_n": self.top_n_var.get(),
            "sample_size": self.sample_size_var.get(),
            "seed": self.seed_var.get(),
            "workers": self.workers_var.get(),
            "check_timeout": self.check_timeout_var.get(),
            "check_retries": self.check_retries_var.get(),
            "batch": self.batch_var.get(),
            "sleep": self.sleep_var.get(),
            "fetch_timeout": self.fetch_timeout_var.get(),
            "fetch_retries": self.fetch_retries_var.get(),
        }

    def _apply_config(self, data: dict) -> None:
        self.lang = data.get("lang", self.lang)
        self.stage_code = data.get("stage_code", self.stage_code)
        self.input_var.set(data.get("input", self.input_var.get()))
        self.output_var.set(data.get("output", self.output_var.get()))
        self.api_var.set(data.get("api", self.api_var.get()))
        self.top_n_var.set(data.get("top_n", self.top_n_var.get()))
        self.sample_size_var.set(data.get("sample_size", self.sample_size_var.get()))
        self.seed_var.set(data.get("seed", self.seed_var.get()))
        self.workers_var.set(data.get("workers", self.workers_var.get()))
        self.check_timeout_var.set(data.get("check_timeout", self.check_timeout_var.get()))
        self.check_retries_var.set(data.get("check_retries", self.check_retries_var.get()))
        self.batch_var.set(data.get("batch", self.batch_var.get()))
        self.sleep_var.set(data.get("sleep", self.sleep_var.get()))
        self.fetch_timeout_var.set(data.get("fetch_timeout", self.fetch_timeout_var.get()))
        self.fetch_retries_var.set(data.get("fetch_retries", self.fetch_retries_var.get()))
        self._apply_text()
        self._refresh_fields()

    def _save_config(self) -> None:
        CONFIG_PATH.write_text(json.dumps(self._collect_config(), ensure_ascii=False, indent=2), encoding="utf-8")
        self._log(self.tr("msg_save_done"))

    def _load_config(self) -> None:
        if not CONFIG_PATH.exists():
            messagebox.showinfo(self.tr("msg_open_title"), self.tr("msg_no_config"))
            return
        self._apply_config(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
        self._log(self.tr("msg_load_done"))

    def _open_path(self, path: Path | None) -> None:
        if path is None or not path.exists():
            messagebox.showinfo(self.tr("msg_open_title"), self.tr("msg_open_missing"))
            return
        try:
            os.startfile(str(path))
        except Exception as exc:
            messagebox.showerror(self.tr("msg_open_title"), str(exc))

    def _open_output_dir(self) -> None:
        target = self.latest_output_path or Path(self.output_var.get().strip())
        self._open_path(target)

    def _open_latest_report(self) -> None:
        self._open_path(self.latest_report_path)

    def _log(self, message: str) -> None:
        self.log_queue.put(message)

    def _drain_log_queue(self) -> None:
        while not self.log_queue.empty():
            self.log_text.insert(tk.END, self.log_queue.get() + "\n")
            self.log_text.see(tk.END)
        self.root.after(100, self._drain_log_queue)

    def _parse_int(self, value: str, label: str) -> int:
        try:
            return int(value)
        except ValueError as exc:
            raise ValueError(f"{label} must be an integer.") from exc

    def _parse_float(self, value: str, label: str) -> float:
        try:
            return float(value)
        except ValueError as exc:
            raise ValueError(f"{label} must be a number.") from exc

    def _extract_report_path(self, result: dict) -> Path | None:
        if not isinstance(result, dict):
            return None
        for key in ("summary_path", "report_csv", "output_json", "available_csv"):
            value = result.get(key)
            if value:
                return Path(value)
        for key in ("check_summary", "fetch_summary", "result"):
            nested = result.get(key)
            nested_path = self._extract_report_path(nested)
            if nested_path is not None:
                return nested_path
        return None

    def _extract_output_dir(self, result: dict) -> Path | None:
        if not isinstance(result, dict):
            return None
        output_dir = result.get("output_dir")
        if output_dir:
            return Path(output_dir)
        for key in ("check_summary", "fetch_summary", "result"):
            nested = result.get(key)
            nested_path = self._extract_output_dir(nested)
            if nested_path is not None:
                return nested_path
        return None

    def _update_latest_paths(self, result: dict, output_root: Path) -> None:
        self.latest_output_path = self._extract_output_dir(result) or output_root
        self.latest_report_path = self._extract_report_path(result)

    def _finish_run(self, result: dict, output_root: Path) -> None:
        self._update_latest_paths(result, output_root)
        self._log(self.tr("msg_finished"))
        self._set_status("done")

    def _fail_run(self, exc: Exception) -> None:
        self._log(f"ERROR: {exc}")
        self._set_status("error")

    def _run(self) -> None:
        if self.worker_thread and self.worker_thread.is_alive():
            messagebox.showinfo(self.tr("msg_running_title"), self.tr("msg_running"))
            return

        try:
            input_path = Path(self.input_var.get().strip())
            output_root = Path(self.output_var.get().strip())
            top_n = self._parse_int(self.top_n_var.get().strip(), self.tr("top_n"))
            workers = self._parse_int(self.workers_var.get().strip(), self.tr("workers"))
            check_timeout = self._parse_int(self.check_timeout_var.get().strip(), self.tr("timeout"))
            check_retries = self._parse_int(self.check_retries_var.get().strip(), self.tr("retries"))
            batch_size = self._parse_int(self.batch_var.get().strip(), self.tr("batch"))
            sleep_sec = self._parse_float(self.sleep_var.get().strip(), self.tr("sleep"))
            fetch_timeout = self._parse_int(self.fetch_timeout_var.get().strip(), self.tr("timeout"))
            fetch_retries = self._parse_int(self.fetch_retries_var.get().strip(), self.tr("retries"))
            sample_size = self._parse_int(self.sample_size_var.get().strip(), self.tr("sample_size"))
            seed = self._parse_int(self.seed_var.get().strip(), self.tr("seed"))
            api_key = self.api_var.get().strip()

            if not input_path.exists():
                raise ValueError(self.tr("msg_input_missing").format(path=input_path))
            output_root.mkdir(parents=True, exist_ok=True)
            if self.stage_code in {"fetch", "pipeline", "test-pipeline"}:
                get_api_key(api_key)
        except Exception as exc:
            self._set_status("error")
            messagebox.showerror(self.tr("msg_invalid_title"), str(exc))
            return

        def worker() -> None:
            try:
                self._set_status_async("running")
                self._log(self.tr("msg_starting").format(mode=MODE_TEXT[self.lang][self.stage_code]))
                if self.stage_code == "check":
                    result = run_check(
                        CheckConfig(input_path, output_root, top_n, workers, check_timeout, check_retries),
                        log=self._log,
                    )
                elif self.stage_code == "fetch":
                    result = run_fetch(
                        FetchConfig(
                            input_path,
                            output_root,
                            api_key,
                            top_n,
                            batch_size,
                            sleep_sec,
                            fetch_timeout,
                            fetch_retries,
                        ),
                        log=self._log,
                    )
                elif self.stage_code == "pipeline":
                    result = run_pipeline(
                        input_path,
                        output_root,
                        api_key,
                        top_n,
                        workers,
                        check_timeout,
                        check_retries,
                        batch_size,
                        sleep_sec,
                        fetch_timeout,
                        fetch_retries,
                        log=self._log,
                    )
                elif self.stage_code == "test-check":
                    result = run_test(
                        input_path,
                        output_root,
                        None,
                        "check",
                        sample_size,
                        seed,
                        top_n,
                        workers,
                        check_timeout,
                        check_retries,
                        batch_size,
                        sleep_sec,
                        fetch_timeout,
                        fetch_retries,
                        log=self._log,
                    )
                elif self.stage_code == "test-pipeline":
                    result = run_test(
                        input_path,
                        output_root,
                        api_key,
                        "pipeline",
                        sample_size,
                        seed,
                        top_n,
                        workers,
                        check_timeout,
                        check_retries,
                        batch_size,
                        sleep_sec,
                        fetch_timeout,
                        fetch_retries,
                        log=self._log,
                    )
                else:
                    raise RuntimeError(f"Unsupported mode: {self.stage_code}")
                self.root.after(0, lambda: self._finish_run(result, output_root))
            except Exception as exc:
                self.root.after(0, lambda: self._fail_run(exc))

        self.worker_thread = threading.Thread(target=worker, daemon=True)
        self.worker_thread.start()


def main() -> int:
    root = tk.Tk()
    configure_high_dpi(root)
    App(root)
    root.mainloop()
    return 0
