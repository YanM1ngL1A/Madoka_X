import csv
import json
import os
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

import requests


CHECK_URL = "https://publish.twitter.com/oembed?url=https://twitter.com/x/status/{tweet_id}"
FETCH_URL = "https://api.twitterapi.io/twitter/tweets"
DEFAULT_WORKERS = 12
DEFAULT_TIMEOUT = 20
DEFAULT_FETCH_TIMEOUT = 60
DEFAULT_BATCH_SIZE = 100
DEFAULT_SLEEP_SEC = 0.5
DEFAULT_SAMPLE_SIZE = 100
DEFAULT_SAMPLE_SEED = 42
API_KEY_ENV = "TWITTERAPI_IO_KEY"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)
_thread_local = threading.local()


class UserCancelledError(RuntimeError):
    pass


@dataclass
class CheckConfig:
    input_path: Path
    output_root: Path
    top_n: int = 0
    workers: int = DEFAULT_WORKERS
    timeout: int = DEFAULT_TIMEOUT
    retries: int = 2


@dataclass
class FetchConfig:
    input_path: Path
    output_root: Path
    api_key: str
    top_n: int = 0
    batch_size: int = DEFAULT_BATCH_SIZE
    sleep_sec: float = DEFAULT_SLEEP_SEC
    timeout: int = DEFAULT_FETCH_TIMEOUT
    retries: int = 3
    resume: bool = True


def ensure_not_cancelled(stop_event: threading.Event | None) -> None:
    if stop_event is not None and stop_event.is_set():
        raise UserCancelledError("Operation cancelled by user.")


def emit_progress(progress, stage: str, processed: int, total: int) -> None:
    if progress is not None:
        progress(stage, processed, total)


def get_api_key(explicit_api_key: str | None = None) -> str:
    api_key = (explicit_api_key or os.getenv(API_KEY_ENV, "")).strip()
    if not api_key:
        raise RuntimeError(
            f"Missing API key. Set {API_KEY_ENV} or pass --api-key for fetch-related stages."
        )
    return api_key


def get_id_fieldname(fieldnames: list[str] | None, csv_path: Path) -> str:
    if not fieldnames:
        raise ValueError(f"CSV has no header row: {csv_path}")
    if "id" in fieldnames:
        return "id"
    for name in fieldnames:
        if name and "id" in name.lower():
            return name
    non_empty = [name for name in fieldnames if name]
    if len(non_empty) == 1:
        return non_empty[0]
    raise ValueError(f"CSV missing an identifiable ID column: {csv_path}")


def read_ids(path: Path, top_n: int = 0) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")
    ids = read_ids_from_csv(path) if path.suffix.lower() == ".csv" else read_ids_from_text(path)
    if top_n > 0:
        return ids[:top_n]
    return ids


def read_ids_from_csv(path: Path) -> list[str]:
    ids: list[str] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        id_field = get_id_fieldname(reader.fieldnames, path)
        for row in reader:
            tweet_id = (row.get(id_field) or "").strip()
            if tweet_id:
                ids.append(tweet_id)
    return ids


def read_ids_from_text(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    return [token for token in text.replace(",", "\n").split() if token.strip()]


def iter_ids(path: Path):
    if path.suffix.lower() == ".csv":
        yield from iter_ids_from_csv(path)
    else:
        yield from iter_ids_from_text(path)


def iter_ids_from_csv(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        id_field = get_id_fieldname(reader.fieldnames, path)
        for row in reader:
            tweet_id = (row.get(id_field) or "").strip()
            if tweet_id:
                yield tweet_id


def iter_ids_from_text(path: Path):
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            for token in line.replace(",", " ").split():
                tweet_id = token.strip()
                if tweet_id:
                    yield tweet_id


def count_ids(path: Path, top_n: int = 0) -> int:
    count = 0
    for _ in iter_ids(path):
        count += 1
        if top_n > 0 and count >= top_n:
            return top_n
    return count


def iter_id_batches(path: Path, batch_size: int, start_index: int = 0, top_n: int = 0):
    current_batch: list[str] = []
    current_start = start_index
    for idx, tweet_id in enumerate(iter_ids(path)):
        if top_n > 0 and idx >= top_n:
            break
        if idx < start_index:
            continue
        if not current_batch:
            current_start = idx
        current_batch.append(tweet_id)
        if len(current_batch) >= batch_size:
            yield current_start, current_batch
            current_batch = []
    if current_batch:
        yield current_start, current_batch


def write_ids_csv(path: Path, ids: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["id"])
        writer.writeheader()
        writer.writerows({"id": tweet_id} for tweet_id in ids)


def write_txt(path: Path, values: list[str]) -> None:
    path.write_text("\n".join(values), encoding="utf-8")


def append_txt(path: Path, values: list[str]) -> None:
    if not values:
        return
    with path.open("a", encoding="utf-8") as handle:
        for value in values:
            handle.write(f"{value}\n")


def append_jsonl(path: Path, records: list[dict]) -> None:
    if not records:
        return
    with path.open("a", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False))
            handle.write("\n")


def fetch_state_path(out_dir: Path, stem: str) -> Path:
    return out_dir / f"{stem}_fetch_state.json"


def build_input_signature(path: Path) -> dict:
    stat = path.stat()
    return {
        "path": str(path.resolve()),
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
    }


def load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def save_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def is_compatible_fetch_state(state: dict, signature: dict, top_n: int, batch_size: int, total_count: int) -> bool:
    return (
        state.get("input_signature") == signature
        and state.get("top_n") == top_n
        and state.get("batch_size") == batch_size
        and state.get("requested_count") == total_count
    )


def create_session(headers: dict | None = None) -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }
    )
    if headers:
        session.headers.update(headers)
    return session


def get_check_session() -> requests.Session:
    session = getattr(_thread_local, "check_session", None)
    if session is None:
        session = create_session()
        _thread_local.check_session = session
    return session


def ensure_output_root(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def normalize_job_name(input_path: Path) -> str:
    stem = input_path.stem
    if stem.endswith("_available_ids"):
        return stem[: -len("_available_ids")]
    return stem


def job_dir(output_root: Path, input_path: Path) -> Path:
    root = ensure_output_root(output_root.resolve())
    job = root / normalize_job_name(input_path)
    job.mkdir(parents=True, exist_ok=True)
    return job


def check_output_dir(output_root: Path, input_path: Path) -> Path:
    path = job_dir(output_root, input_path) / "stage1_check"
    path.mkdir(parents=True, exist_ok=True)
    return path


def fetch_output_dir(output_root: Path, input_path: Path) -> Path:
    path = job_dir(output_root, input_path) / "stage2_fetch"
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_output_dir(output_root: Path, input_path: Path, sample_stem: str) -> Path:
    path = job_dir(output_root, input_path) / "tests" / sample_stem
    path.mkdir(parents=True, exist_ok=True)
    return path


def classify_check_response(tweet_id: str, response: requests.Response) -> dict:
    final_url = str(response.url)
    status_code = response.status_code
    if status_code == 200:
        try:
            payload = response.json()
        except ValueError:
            return build_check_result(tweet_id, "error", status_code, final_url, "invalid_json")
        if payload.get("html") and payload.get("url"):
            return build_check_result(tweet_id, "available", status_code, final_url, "oembed_found")
        return build_check_result(tweet_id, "blocked", status_code, final_url, "oembed_empty")
    if status_code in (404, 410):
        return build_check_result(tweet_id, "unavailable", status_code, final_url, "oembed_not_found")
    if status_code == 429:
        return build_check_result(tweet_id, "blocked", status_code, final_url, "rate_limited")
    if status_code >= 500:
        return build_check_result(tweet_id, "error", status_code, final_url, "server_error")
    return build_check_result(tweet_id, "blocked", status_code, final_url, "unexpected_status")


def build_check_result(tweet_id: str, status: str, http_status: int, final_url: str, reason: str) -> dict:
    return {
        "id": tweet_id,
        "status": status,
        "http_status": http_status,
        "final_url": final_url,
        "reason": reason,
    }


def check_one(tweet_id: str, timeout: int, retries: int) -> dict:
    url = CHECK_URL.format(tweet_id=tweet_id)
    session = get_check_session()
    last_error: Exception | None = None
    for _ in range(retries + 1):
        try:
            response = session.get(url, timeout=timeout, allow_redirects=True)
            return classify_check_response(tweet_id, response)
        except requests.RequestException as exc:
            last_error = exc
    assert last_error is not None
    return build_check_result(tweet_id, "error", 0, url, last_error.__class__.__name__)


def run_check(config: CheckConfig, log=print, progress=None, stop_event: threading.Event | None = None) -> dict:
    ids = read_ids(config.input_path, config.top_n)
    if not ids:
        raise ValueError(f"No tweet IDs found in: {config.input_path}")

    out_dir = check_output_dir(config.output_root, config.input_path)
    stem = normalize_job_name(config.input_path)
    results: list[dict] = []
    emit_progress(progress, "check", 0, len(ids))

    log(f"[Stage 1] Checking {len(ids)} tweet IDs with {config.workers} workers...")
    with ThreadPoolExecutor(max_workers=config.workers) as executor:
        futures = {executor.submit(check_one, tweet_id, config.timeout, config.retries): tweet_id for tweet_id in ids}
        for index, future in enumerate(as_completed(futures), start=1):
            ensure_not_cancelled(stop_event)
            results.append(future.result())
            emit_progress(progress, "check", index, len(ids))
            if index % 50 == 0 or index == len(ids):
                log(f"[Stage 1] Completed {index}/{len(ids)}")
        if stop_event is not None and stop_event.is_set():
            executor.shutdown(wait=False, cancel_futures=True)
            raise UserCancelledError("Operation cancelled by user.")

    order_map = {tweet_id: idx for idx, tweet_id in enumerate(ids)}
    results.sort(key=lambda item: order_map.get(item["id"], 10**12))
    available_ids = [item["id"] for item in results if item["status"] == "available"]
    unavailable_ids = [item["id"] for item in results if item["status"] == "unavailable"]
    blocked_ids = [item["id"] for item in results if item["status"] == "blocked"]
    error_ids = [item["id"] for item in results if item["status"] == "error"]

    report_csv = out_dir / f"{stem}_status.csv"
    available_csv = out_dir / f"{stem}_available_ids.csv"
    available_txt = out_dir / f"{stem}_available_ids.txt"
    unavailable_txt = out_dir / f"{stem}_unavailable_ids.txt"
    blocked_txt = out_dir / f"{stem}_blocked_ids.txt"
    error_txt = out_dir / f"{stem}_error_ids.txt"
    summary_json = out_dir / f"{stem}_summary.json"

    with report_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["id", "status", "http_status", "final_url", "reason"])
        writer.writeheader()
        writer.writerows(results)

    write_ids_csv(available_csv, available_ids)
    write_txt(available_txt, available_ids)
    write_txt(unavailable_txt, unavailable_ids)
    write_txt(blocked_txt, blocked_ids)
    write_txt(error_txt, error_ids)

    summary = {
        "stage": "check",
        "input": str(config.input_path),
        "output_dir": str(out_dir),
        "checked_count": len(ids),
        "available_count": len(available_ids),
        "unavailable_count": len(unavailable_ids),
        "blocked_count": len(blocked_ids),
        "error_count": len(error_ids),
        "available_rate": round(len(available_ids) / len(ids), 6),
        "report_csv": str(report_csv),
        "available_csv": str(available_csv),
        "workers": config.workers,
        "timeout": config.timeout,
        "summary_path": str(summary_json),
    }
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"[Stage 1] Saved summary: {summary_json}")
    return summary


def chunk_ids(ids: list[str], size: int) -> list[list[str]]:
    return [ids[index : index + size] for index in range(0, len(ids), size)]


def parse_json_or_default(text: str) -> dict:
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def fetch_batch(session: requests.Session, tweet_ids: list[str], timeout: int, retries: int) -> dict:
    params = {"tweet_ids": ",".join(tweet_ids)}
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            response = session.get(FETCH_URL, params=params, timeout=timeout)
            if response.status_code == 200:
                return response.json()

            payload = parse_json_or_default(response.text)
            if response.status_code == 403 and payload.get("error_name") == "browser_signature_banned":
                ray_id = payload.get("ray_id", "N/A")
                ts = payload.get("timestamp", "N/A")
                raise RuntimeError(
                    f"Cloudflare blocked request (error 1010), ray_id={ray_id}, timestamp={ts}."
                )
            if response.status_code == 402:
                raise RuntimeError(f"HTTP 402: credits not enough.\n{response.text}")
            if response.status_code in (429, 500, 502, 503, 504) and attempt < retries:
                time.sleep(1.5 * attempt)
                continue
            raise RuntimeError(f"HTTP {response.status_code}: {response.reason}\n{response.text}")
        except requests.RequestException as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(1.5 * attempt)
                continue

    if last_error is not None:
        raise RuntimeError(f"Network error: {last_error}") from last_error
    raise RuntimeError("Unexpected fetch retry fallthrough.")


def run_fetch(config: FetchConfig, log=print, progress=None, stop_event: threading.Event | None = None) -> dict:
    if config.batch_size <= 0:
        raise ValueError("batch_size must be > 0")

    out_dir = fetch_output_dir(config.output_root, config.input_path)
    stem = normalize_job_name(config.input_path)
    total_count = count_ids(config.input_path, config.top_n)
    if total_count <= 0:
        raise ValueError(f"No tweet IDs found in: {config.input_path}")

    output_jsonl = out_dir / f"{stem}.jsonl"
    output_missing = out_dir / f"{stem}_missing_ids.txt"
    output_summary = out_dir / f"{stem}_summary.json"
    state_path = fetch_state_path(out_dir, stem)
    signature = build_input_signature(config.input_path)

    processed_count = 0
    returned_count = 0
    missing_count = 0
    completed_batches = 0
    resume_used = False

    existing_state = load_json(state_path) if config.resume else None
    if existing_state and is_compatible_fetch_state(
        existing_state, signature, config.top_n, config.batch_size, total_count
    ):
        processed_count = int(existing_state.get("processed_count", 0))
        returned_count = int(existing_state.get("returned_count", 0))
        missing_count = int(existing_state.get("missing_count", 0))
        completed_batches = int(existing_state.get("completed_batches", 0))
        processed_count = max(0, min(processed_count, total_count))
        resume_used = processed_count > 0 and existing_state.get("status") != "completed"
        if resume_used:
            log(
                f"[Stage 2] Resuming from checkpoint: processed={processed_count}/{total_count}, "
                f"completed_batches={completed_batches}"
            )
    elif existing_state:
        log("[Stage 2] Existing checkpoint is incompatible with current input/options; starting fresh.")

    if not resume_used:
        output_jsonl.write_text("", encoding="utf-8")
        output_missing.write_text("", encoding="utf-8")
        processed_count = 0
        returned_count = 0
        missing_count = 0
        completed_batches = 0

    def save_fetch_state(status: str) -> None:
        payload = {
            "status": status,
            "input": str(config.input_path),
            "output_dir": str(out_dir),
            "input_signature": signature,
            "top_n": config.top_n,
            "batch_size": config.batch_size,
            "requested_count": total_count,
            "processed_count": processed_count,
            "returned_count": returned_count,
            "missing_count": missing_count,
            "completed_batches": completed_batches,
            "output_jsonl": str(output_jsonl),
            "missing_txt": str(output_missing),
            "summary_path": str(output_summary),
            "updated_epoch": int(time.time()),
        }
        save_json(state_path, payload)

    save_fetch_state("running")
    session = create_session({"x-api-key": get_api_key(config.api_key), "Accept": "application/json"})
    remaining_batches = (max(total_count - processed_count, 0) + config.batch_size - 1) // config.batch_size
    emit_progress(progress, "fetch", processed_count, total_count)
    log(
        f"[Stage 2] Fetching {total_count} IDs with batch_size={config.batch_size}, "
        f"remaining_batches={remaining_batches}"
    )

    for index, (batch_start, batch_ids) in enumerate(
        iter_id_batches(config.input_path, config.batch_size, start_index=processed_count, top_n=config.top_n),
        start=1,
    ):
        ensure_not_cancelled(stop_event)
        data = fetch_batch(session, batch_ids, config.timeout, config.retries)
        tweets = data.get("tweets") or []
        append_jsonl(output_jsonl, tweets)
        returned_batch_ids: set[str] = set()
        for tweet in tweets:
            tweet_id = str(tweet.get("id", "")).strip()
            if tweet_id:
                returned_batch_ids.add(tweet_id)
        missing_batch_ids = [tweet_id for tweet_id in batch_ids if tweet_id not in returned_batch_ids]
        append_txt(output_missing, missing_batch_ids)

        processed_count += len(batch_ids)
        returned_count += len(tweets)
        missing_count += len(missing_batch_ids)
        completed_batches += 1
        emit_progress(progress, "fetch", processed_count, total_count)
        save_fetch_state("running")

        log(
            f"[Stage 2] Batch {index}/{remaining_batches}: start={batch_start}, "
            f"requested={len(batch_ids)} returned={len(tweets)} missing={len(missing_batch_ids)}"
        )
        if processed_count < total_count and config.sleep_sec > 0:
            if stop_event is not None and stop_event.wait(config.sleep_sec):
                raise UserCancelledError("Operation cancelled by user.")

    summary = {
        "stage": "fetch",
        "input": str(config.input_path),
        "output_dir": str(out_dir),
        "requested_count": total_count,
        "processed_count": processed_count,
        "returned_count": returned_count,
        "missing_count": missing_count,
        "returned_rate": round(returned_count / total_count, 6),
        "output_json": str(output_jsonl),
        "output_jsonl": str(output_jsonl),
        "missing_txt": str(output_missing),
        "batch_size": config.batch_size,
        "completed_batches": completed_batches,
        "resume_enabled": config.resume,
        "resume_used": resume_used,
        "checkpoint_file": str(state_path),
        "summary_path": str(output_summary),
    }
    save_json(output_summary, summary)
    save_fetch_state("completed")
    log(f"[Stage 2] Saved summary: {output_summary}")
    return summary


def write_pipeline_summary(output_root: Path, input_path: Path, summary_name: str, summary: dict) -> Path:
    out_dir = job_dir(output_root, input_path) / "runs"
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / f"{summary_name}.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary_path


def run_pipeline(
    input_path: Path,
    output_root: Path,
    api_key: str,
    top_n: int = 0,
    workers: int = DEFAULT_WORKERS,
    check_timeout: int = DEFAULT_TIMEOUT,
    check_retries: int = 2,
    batch_size: int = DEFAULT_BATCH_SIZE,
    sleep_sec: float = DEFAULT_SLEEP_SEC,
    fetch_timeout: int = DEFAULT_FETCH_TIMEOUT,
    fetch_retries: int = 3,
    fetch_resume: bool = True,
    log=print,
    progress=None,
    stop_event: threading.Event | None = None,
) -> dict:
    check_summary = run_check(
        CheckConfig(
            input_path=input_path,
            output_root=output_root,
            top_n=top_n,
            workers=workers,
            timeout=check_timeout,
            retries=check_retries,
        ),
        log=log,
        progress=progress,
        stop_event=stop_event,
    )
    fetch_summary = None
    if check_summary["available_count"] > 0:
        ensure_not_cancelled(stop_event)
        fetch_summary = run_fetch(
            FetchConfig(
                input_path=Path(check_summary["available_csv"]),
                output_root=output_root,
                api_key=api_key,
                batch_size=batch_size,
                sleep_sec=sleep_sec,
                timeout=fetch_timeout,
                retries=fetch_retries,
                resume=fetch_resume,
            ),
            log=log,
            progress=progress,
            stop_event=stop_event,
        )
    summary = {
        "stage": "pipeline",
        "input": str(input_path),
        "check_summary": check_summary,
        "fetch_summary": fetch_summary,
        "fetched": fetch_summary is not None,
    }
    summary_path = write_pipeline_summary(output_root, input_path, f"{normalize_job_name(input_path)}_pipeline", summary)
    summary["summary_path"] = str(summary_path)
    log(f"[Pipeline] Saved run summary: {summary_path}")
    return summary


def create_sample_file(input_path: Path, output_root: Path, sample_size: int, seed: int, top_n: int = 0) -> Path:
    ids = read_ids(input_path, top_n)
    if not ids:
        raise ValueError(f"No tweet IDs found in: {input_path}")
    actual_size = min(sample_size, len(ids))
    sampled_ids = random.Random(seed).sample(ids, actual_size)
    sample_stem = f"{normalize_job_name(input_path)}_sample{actual_size}_seed{seed}"
    out_dir = test_output_dir(output_root, input_path, sample_stem)
    sample_path = out_dir / f"{sample_stem}.csv"
    write_ids_csv(sample_path, sampled_ids)
    return sample_path


def run_test(
    input_path: Path,
    output_root: Path,
    api_key: str | None,
    mode: str,
    sample_size: int = DEFAULT_SAMPLE_SIZE,
    seed: int = DEFAULT_SAMPLE_SEED,
    top_n: int = 0,
    workers: int = DEFAULT_WORKERS,
    check_timeout: int = DEFAULT_TIMEOUT,
    check_retries: int = 2,
    batch_size: int = DEFAULT_BATCH_SIZE,
    sleep_sec: float = DEFAULT_SLEEP_SEC,
    fetch_timeout: int = DEFAULT_FETCH_TIMEOUT,
    fetch_retries: int = 3,
    fetch_resume: bool = True,
    log=print,
    progress=None,
    stop_event: threading.Event | None = None,
) -> dict:
    if mode not in {"check", "pipeline"}:
        raise ValueError("Test mode must be 'check' or 'pipeline'.")
    sample_path = create_sample_file(input_path, output_root, sample_size, seed, top_n)
    log(f"[Test] Saved sample file: {sample_path}")

    if mode == "check":
        run_result = run_check(
            CheckConfig(
                input_path=sample_path,
                output_root=output_root,
                workers=workers,
                timeout=check_timeout,
                retries=check_retries,
            ),
            log=log,
            progress=progress,
            stop_event=stop_event,
        )
    else:
        run_result = run_pipeline(
            input_path=sample_path,
            output_root=output_root,
            api_key=get_api_key(api_key),
            workers=workers,
            check_timeout=check_timeout,
            check_retries=check_retries,
            batch_size=batch_size,
            sleep_sec=sleep_sec,
            fetch_timeout=fetch_timeout,
            fetch_retries=fetch_retries,
            fetch_resume=fetch_resume,
            log=log,
            progress=progress,
            stop_event=stop_event,
        )

    summary = {
        "stage": "test",
        "mode": mode,
        "input": str(input_path),
        "sample_file": str(sample_path),
        "sample_size": sample_size,
        "seed": seed,
        "result": run_result,
    }
    summary_path = write_pipeline_summary(output_root, input_path, f"{sample_path.stem}_{mode}_test", summary)
    summary["summary_path"] = str(summary_path)
    log(f"[Test] Saved test summary: {summary_path}")
    return summary
