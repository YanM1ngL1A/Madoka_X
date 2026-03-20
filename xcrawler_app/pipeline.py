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


def write_ids_csv(path: Path, ids: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["id"])
        writer.writeheader()
        writer.writerows({"id": tweet_id} for tweet_id in ids)


def write_txt(path: Path, values: list[str]) -> None:
    path.write_text("\n".join(values), encoding="utf-8")


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


def run_check(config: CheckConfig, log=print) -> dict:
    ids = read_ids(config.input_path, config.top_n)
    if not ids:
        raise ValueError(f"No tweet IDs found in: {config.input_path}")

    out_dir = check_output_dir(config.output_root, config.input_path)
    stem = normalize_job_name(config.input_path)
    results: list[dict] = []

    log(f"[Stage 1] Checking {len(ids)} tweet IDs with {config.workers} workers...")
    with ThreadPoolExecutor(max_workers=config.workers) as executor:
        futures = {executor.submit(check_one, tweet_id, config.timeout, config.retries): tweet_id for tweet_id in ids}
        for index, future in enumerate(as_completed(futures), start=1):
            results.append(future.result())
            if index % 50 == 0 or index == len(ids):
                log(f"[Stage 1] Completed {index}/{len(ids)}")

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


def run_fetch(config: FetchConfig, log=print) -> dict:
    ids = read_ids(config.input_path, config.top_n)
    if not ids:
        raise ValueError(f"No tweet IDs found in: {config.input_path}")
    if config.batch_size <= 0:
        raise ValueError("batch_size must be > 0")

    out_dir = fetch_output_dir(config.output_root, config.input_path)
    stem = normalize_job_name(config.input_path)
    session = create_session({"x-api-key": get_api_key(config.api_key), "Accept": "application/json"})
    batches = chunk_ids(ids, config.batch_size)
    all_tweets: list[dict] = []
    returned_ids: set[str] = set()

    log(f"[Stage 2] Fetching {len(ids)} IDs in {len(batches)} batch(es)...")
    for index, batch_ids in enumerate(batches, start=1):
        data = fetch_batch(session, batch_ids, config.timeout, config.retries)
        tweets = data.get("tweets") or []
        all_tweets.extend(tweets)
        for tweet in tweets:
            tweet_id = str(tweet.get("id", "")).strip()
            if tweet_id:
                returned_ids.add(tweet_id)
        log(f"[Stage 2] Batch {index}/{len(batches)}: requested={len(batch_ids)} returned={len(tweets)}")
        if index < len(batches) and config.sleep_sec > 0:
            time.sleep(config.sleep_sec)

    missing_ids = [tweet_id for tweet_id in ids if tweet_id not in returned_ids]
    output_json = out_dir / f"{stem}.json"
    output_missing = out_dir / f"{stem}_missing_ids.txt"
    output_summary = out_dir / f"{stem}_summary.json"

    with output_json.open("w", encoding="utf-8") as handle:
        json.dump({"tweets": all_tweets}, handle, ensure_ascii=False, indent=2)
    write_txt(output_missing, missing_ids)

    summary = {
        "stage": "fetch",
        "input": str(config.input_path),
        "output_dir": str(out_dir),
        "requested_count": len(ids),
        "returned_count": len(all_tweets),
        "missing_count": len(missing_ids),
        "returned_rate": round(len(all_tweets) / len(ids), 6),
        "output_json": str(output_json),
        "missing_txt": str(output_missing),
        "batch_size": config.batch_size,
    }
    output_summary.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
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
    log=print,
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
    )
    fetch_summary = None
    if check_summary["available_count"] > 0:
        fetch_summary = run_fetch(
            FetchConfig(
                input_path=Path(check_summary["available_csv"]),
                output_root=output_root,
                api_key=api_key,
                batch_size=batch_size,
                sleep_sec=sleep_sec,
                timeout=fetch_timeout,
                retries=fetch_retries,
            ),
            log=log,
        )
    summary = {
        "stage": "pipeline",
        "input": str(input_path),
        "check_summary": check_summary,
        "fetch_summary": fetch_summary,
        "fetched": fetch_summary is not None,
    }
    summary_path = write_pipeline_summary(output_root, input_path, f"{normalize_job_name(input_path)}_pipeline", summary)
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
    log=print,
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
            log=log,
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
    log(f"[Test] Saved test summary: {summary_path}")
    return summary
