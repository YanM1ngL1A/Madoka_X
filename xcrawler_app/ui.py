import queue
import threading
import tkinter as tk
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


class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("X Crawler Project")
        self.root.geometry("980x760")
        self.log_queue: queue.Queue[str] = queue.Queue()
        self.worker_thread: threading.Thread | None = None
        self._build()
        self.root.after(100, self._drain_log_queue)

    def _build(self) -> None:
        frame = ttk.Frame(self.root, padding=16)
        frame.pack(fill=tk.BOTH, expand=True)
        frame.columnconfigure(1, weight=1)

        self.stage_var = tk.StringVar(value="check")
        self.input_var = tk.StringVar()
        self.output_var = tk.StringVar(value=str(Path(__file__).resolve().parents[1] / "outputs"))
        self.api_key_var = tk.StringVar()
        self.top_n_var = tk.StringVar(value="0")
        self.sample_size_var = tk.StringVar(value=str(DEFAULT_SAMPLE_SIZE))
        self.seed_var = tk.StringVar(value=str(DEFAULT_SAMPLE_SEED))
        self.workers_var = tk.StringVar(value=str(DEFAULT_WORKERS))
        self.check_timeout_var = tk.StringVar(value=str(DEFAULT_TIMEOUT))
        self.check_retries_var = tk.StringVar(value="2")
        self.batch_size_var = tk.StringVar(value=str(DEFAULT_BATCH_SIZE))
        self.sleep_sec_var = tk.StringVar(value=str(DEFAULT_SLEEP_SEC))
        self.fetch_timeout_var = tk.StringVar(value=str(DEFAULT_FETCH_TIMEOUT))
        self.fetch_retries_var = tk.StringVar(value="3")

        row = 0
        ttk.Label(frame, text="Run Mode").grid(row=row, column=0, sticky="w", pady=4)
        stage_box = ttk.Combobox(
            frame,
            textvariable=self.stage_var,
            state="readonly",
            values=["check", "fetch", "pipeline", "test-check", "test-pipeline"],
        )
        stage_box.grid(row=row, column=1, sticky="ew", pady=4)
        stage_box.bind("<<ComboboxSelected>>", lambda _event: self._refresh_fields())

        row += 1
        ttk.Label(frame, text="Tweet IDs File").grid(row=row, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=self.input_var).grid(row=row, column=1, sticky="ew", pady=4)
        ttk.Button(frame, text="Browse", command=self._choose_input).grid(row=row, column=2, sticky="ew", padx=(8, 0))

        row += 1
        ttk.Label(frame, text="Output Root").grid(row=row, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=self.output_var).grid(row=row, column=1, sticky="ew", pady=4)
        ttk.Button(frame, text="Browse", command=self._choose_output).grid(row=row, column=2, sticky="ew", padx=(8, 0))

        row += 1
        ttk.Label(frame, text="twitterapi.io API Key").grid(row=row, column=0, sticky="w", pady=4)
        self.api_key_entry = ttk.Entry(frame, textvariable=self.api_key_var, show="*")
        self.api_key_entry.grid(row=row, column=1, sticky="ew", pady=4)
        ttk.Label(frame, text="Only needed for fetch / pipeline modes").grid(row=row, column=2, sticky="w", padx=(8, 0))

        row += 1
        ttk.Label(frame, text="Top N (0 = all)").grid(row=row, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=self.top_n_var).grid(row=row, column=1, sticky="ew", pady=4)

        row += 1
        ttk.Label(frame, text="Sample Size").grid(row=row, column=0, sticky="w", pady=4)
        self.sample_size_entry = ttk.Entry(frame, textvariable=self.sample_size_var)
        self.sample_size_entry.grid(row=row, column=1, sticky="ew", pady=4)
        ttk.Label(frame, text="Used by test modes").grid(row=row, column=2, sticky="w", padx=(8, 0))

        row += 1
        ttk.Label(frame, text="Sample Seed").grid(row=row, column=0, sticky="w", pady=4)
        self.seed_entry = ttk.Entry(frame, textvariable=self.seed_var)
        self.seed_entry.grid(row=row, column=1, sticky="ew", pady=4)

        row += 1
        ttk.Separator(frame, orient=tk.HORIZONTAL).grid(row=row, column=0, columnspan=3, sticky="ew", pady=10)

        row += 1
        ttk.Label(frame, text="Stage 1 Workers").grid(row=row, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=self.workers_var).grid(row=row, column=1, sticky="ew", pady=4)

        row += 1
        ttk.Label(frame, text="Stage 1 Timeout").grid(row=row, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=self.check_timeout_var).grid(row=row, column=1, sticky="ew", pady=4)

        row += 1
        ttk.Label(frame, text="Stage 1 Retries").grid(row=row, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=self.check_retries_var).grid(row=row, column=1, sticky="ew", pady=4)

        row += 1
        ttk.Label(frame, text="Stage 2 Batch Size").grid(row=row, column=0, sticky="w", pady=4)
        self.batch_size_entry = ttk.Entry(frame, textvariable=self.batch_size_var)
        self.batch_size_entry.grid(row=row, column=1, sticky="ew", pady=4)

        row += 1
        ttk.Label(frame, text="Stage 2 Sleep Sec").grid(row=row, column=0, sticky="w", pady=4)
        self.sleep_sec_entry = ttk.Entry(frame, textvariable=self.sleep_sec_var)
        self.sleep_sec_entry.grid(row=row, column=1, sticky="ew", pady=4)

        row += 1
        ttk.Label(frame, text="Stage 2 Timeout").grid(row=row, column=0, sticky="w", pady=4)
        self.fetch_timeout_entry = ttk.Entry(frame, textvariable=self.fetch_timeout_var)
        self.fetch_timeout_entry.grid(row=row, column=1, sticky="ew", pady=4)

        row += 1
        ttk.Label(frame, text="Stage 2 Retries").grid(row=row, column=0, sticky="w", pady=4)
        self.fetch_retries_entry = ttk.Entry(frame, textvariable=self.fetch_retries_var)
        self.fetch_retries_entry.grid(row=row, column=1, sticky="ew", pady=4)

        row += 1
        buttons = ttk.Frame(frame)
        buttons.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(12, 8))
        ttk.Button(buttons, text="Run", command=self._run).pack(side=tk.LEFT)
        ttk.Button(buttons, text="Clear Log", command=self._clear_log).pack(side=tk.LEFT, padx=(8, 0))

        row += 1
        ttk.Label(frame, text="Log").grid(row=row, column=0, sticky="w", pady=(6, 4))

        row += 1
        self.log_text = tk.Text(frame, height=20, wrap="word")
        self.log_text.grid(row=row, column=0, columnspan=3, sticky="nsew")
        frame.rowconfigure(row, weight=1)
        self._refresh_fields()

    def _refresh_fields(self) -> None:
        stage = self.stage_var.get()
        is_test = stage.startswith("test")
        needs_fetch = stage in {"fetch", "pipeline", "test-pipeline"}

        sample_state = "normal" if is_test else "disabled"
        fetch_state = "normal" if needs_fetch else "disabled"

        self.sample_size_entry.configure(state=sample_state)
        self.seed_entry.configure(state=sample_state)
        self.api_key_entry.configure(state=fetch_state)
        self.batch_size_entry.configure(state=fetch_state)
        self.sleep_sec_entry.configure(state=fetch_state)
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

    def _log(self, message: str) -> None:
        self.log_queue.put(message)

    def _drain_log_queue(self) -> None:
        while not self.log_queue.empty():
            self.log_text.insert(tk.END, self.log_queue.get() + "\n")
            self.log_text.see(tk.END)
        self.root.after(100, self._drain_log_queue)

    def _parse_int(self, value: str, field_name: str) -> int:
        try:
            return int(value)
        except ValueError as exc:
            raise ValueError(f"{field_name} must be an integer.") from exc

    def _parse_float(self, value: str, field_name: str) -> float:
        try:
            return float(value)
        except ValueError as exc:
            raise ValueError(f"{field_name} must be a number.") from exc

    def _run(self) -> None:
        if self.worker_thread and self.worker_thread.is_alive():
            messagebox.showinfo("Running", "A task is already running.")
            return

        try:
            input_path = Path(self.input_var.get().strip())
            output_root = Path(self.output_var.get().strip())
            stage = self.stage_var.get()
            top_n = self._parse_int(self.top_n_var.get().strip(), "Top N")
            workers = self._parse_int(self.workers_var.get().strip(), "Stage 1 Workers")
            check_timeout = self._parse_int(self.check_timeout_var.get().strip(), "Stage 1 Timeout")
            check_retries = self._parse_int(self.check_retries_var.get().strip(), "Stage 1 Retries")
            batch_size = self._parse_int(self.batch_size_var.get().strip(), "Stage 2 Batch Size")
            fetch_timeout = self._parse_int(self.fetch_timeout_var.get().strip(), "Stage 2 Timeout")
            fetch_retries = self._parse_int(self.fetch_retries_var.get().strip(), "Stage 2 Retries")
            sleep_sec = self._parse_float(self.sleep_sec_var.get().strip(), "Stage 2 Sleep Sec")
            sample_size = self._parse_int(self.sample_size_var.get().strip(), "Sample Size")
            seed = self._parse_int(self.seed_var.get().strip(), "Sample Seed")
            api_key = self.api_key_var.get().strip()

            if not input_path.exists():
                raise ValueError(f"Input file not found: {input_path}")
            output_root.mkdir(parents=True, exist_ok=True)
            if stage in {"fetch", "pipeline", "test-pipeline"}:
                get_api_key(api_key)
        except Exception as exc:
            messagebox.showerror("Invalid Input", str(exc))
            return

        def worker() -> None:
            try:
                self._log(f"Running mode: {stage}")
                if stage == "check":
                    run_check(
                        CheckConfig(
                            input_path=input_path,
                            output_root=output_root,
                            top_n=top_n,
                            workers=workers,
                            timeout=check_timeout,
                            retries=check_retries,
                        ),
                        log=self._log,
                    )
                elif stage == "fetch":
                    run_fetch(
                        FetchConfig(
                            input_path=input_path,
                            output_root=output_root,
                            api_key=api_key,
                            top_n=top_n,
                            batch_size=batch_size,
                            sleep_sec=sleep_sec,
                            timeout=fetch_timeout,
                            retries=fetch_retries,
                        ),
                        log=self._log,
                    )
                elif stage == "pipeline":
                    run_pipeline(
                        input_path=input_path,
                        output_root=output_root,
                        api_key=api_key,
                        top_n=top_n,
                        workers=workers,
                        check_timeout=check_timeout,
                        check_retries=check_retries,
                        batch_size=batch_size,
                        sleep_sec=sleep_sec,
                        fetch_timeout=fetch_timeout,
                        fetch_retries=fetch_retries,
                        log=self._log,
                    )
                elif stage == "test-check":
                    run_test(
                        input_path=input_path,
                        output_root=output_root,
                        api_key=None,
                        mode="check",
                        sample_size=sample_size,
                        seed=seed,
                        top_n=top_n,
                        workers=workers,
                        check_timeout=check_timeout,
                        check_retries=check_retries,
                        batch_size=batch_size,
                        sleep_sec=sleep_sec,
                        fetch_timeout=fetch_timeout,
                        fetch_retries=fetch_retries,
                        log=self._log,
                    )
                elif stage == "test-pipeline":
                    run_test(
                        input_path=input_path,
                        output_root=output_root,
                        api_key=api_key,
                        mode="pipeline",
                        sample_size=sample_size,
                        seed=seed,
                        top_n=top_n,
                        workers=workers,
                        check_timeout=check_timeout,
                        check_retries=check_retries,
                        batch_size=batch_size,
                        sleep_sec=sleep_sec,
                        fetch_timeout=fetch_timeout,
                        fetch_retries=fetch_retries,
                        log=self._log,
                    )
                else:
                    raise RuntimeError(f"Unsupported mode: {stage}")
                self._log("Finished.")
            except Exception as exc:
                self._log(f"ERROR: {exc}")

        self.worker_thread = threading.Thread(target=worker, daemon=True)
        self.worker_thread.start()


def main() -> int:
    root = tk.Tk()
    App(root)
    root.mainloop()
    return 0
