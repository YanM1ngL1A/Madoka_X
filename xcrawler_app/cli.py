import argparse
from pathlib import Path

from xcrawler_app.pipeline import (
    API_KEY_ENV,
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


def default_output_root() -> Path:
    return Path(__file__).resolve().parents[1] / "outputs"


def add_shared_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--input", type=Path, required=True, help="CSV or TXT file containing tweet IDs.")
    parser.add_argument("--output-root", type=Path, default=default_output_root(), help="Root directory for outputs.")
    parser.add_argument("--top-n", type=int, default=0, help="Only use the first N IDs. 0 means all.")


def add_check_only_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS, help="Concurrent worker count for stage 1.")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="HTTP timeout in seconds for stage 1.")
    parser.add_argument("--retries", type=int, default=2, help="Retry count for stage 1.")


def add_fetch_only_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--api-key", default="", help=f"twitterapi.io API key. Falls back to {API_KEY_ENV}.")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE, help="Tweet IDs per API request.")
    parser.add_argument("--sleep-sec", type=float, default=DEFAULT_SLEEP_SEC, help="Sleep between API batches.")
    parser.add_argument("--timeout", type=int, default=DEFAULT_FETCH_TIMEOUT, help="HTTP timeout in seconds for stage 2.")
    parser.add_argument("--retries", type=int, default=3, help="Retry count for stage 2.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Standalone X crawler project.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    check_parser = subparsers.add_parser("check", help="Run stage 1 only.")
    add_shared_args(check_parser)
    add_check_only_args(check_parser)

    fetch_parser = subparsers.add_parser("fetch", help="Run stage 2 only.")
    add_shared_args(fetch_parser)
    add_fetch_only_args(fetch_parser)

    pipeline_parser = subparsers.add_parser("pipeline", help="Run stage 1 then stage 2.")
    add_shared_args(pipeline_parser)
    add_check_only_args(pipeline_parser)
    pipeline_parser.add_argument("--api-key", default="", help=f"twitterapi.io API key. Falls back to {API_KEY_ENV}.")
    pipeline_parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE, help="Tweet IDs per API request.")
    pipeline_parser.add_argument("--sleep-sec", type=float, default=DEFAULT_SLEEP_SEC, help="Sleep between API batches.")
    pipeline_parser.add_argument("--fetch-timeout", type=int, default=DEFAULT_FETCH_TIMEOUT, help="HTTP timeout in seconds for stage 2.")
    pipeline_parser.add_argument("--fetch-retries", type=int, default=3, help="Retry count for stage 2.")

    test_parser = subparsers.add_parser("test", help="Randomly sample IDs and test the flow.")
    add_shared_args(test_parser)
    add_check_only_args(test_parser)
    test_parser.add_argument("--mode", choices=["check", "pipeline"], default="check", help="Whether to run only stage 1 or stage 1+2.")
    test_parser.add_argument("--sample-size", type=int, default=DEFAULT_SAMPLE_SIZE, help="Random sample size.")
    test_parser.add_argument("--seed", type=int, default=DEFAULT_SAMPLE_SEED, help="Random sample seed.")
    test_parser.add_argument("--api-key", default="", help=f"twitterapi.io API key. Falls back to {API_KEY_ENV}.")
    test_parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE, help="Tweet IDs per API request.")
    test_parser.add_argument("--sleep-sec", type=float, default=DEFAULT_SLEEP_SEC, help="Sleep between API batches.")
    test_parser.add_argument("--fetch-timeout", type=int, default=DEFAULT_FETCH_TIMEOUT, help="HTTP timeout in seconds for stage 2.")
    test_parser.add_argument("--fetch-retries", type=int, default=3, help="Retry count for stage 2.")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "check":
            run_check(
                CheckConfig(
                    input_path=args.input,
                    output_root=args.output_root,
                    top_n=args.top_n,
                    workers=args.workers,
                    timeout=args.timeout,
                    retries=args.retries,
                )
            )
        elif args.command == "fetch":
            run_fetch(
                FetchConfig(
                    input_path=args.input,
                    output_root=args.output_root,
                    api_key=get_api_key(args.api_key),
                    top_n=args.top_n,
                    batch_size=args.batch_size,
                    sleep_sec=args.sleep_sec,
                    timeout=args.timeout,
                    retries=args.retries,
                )
            )
        elif args.command == "pipeline":
            run_pipeline(
                input_path=args.input,
                output_root=args.output_root,
                api_key=get_api_key(args.api_key),
                top_n=args.top_n,
                workers=args.workers,
                check_timeout=args.timeout,
                check_retries=args.retries,
                batch_size=args.batch_size,
                sleep_sec=args.sleep_sec,
                fetch_timeout=args.fetch_timeout,
                fetch_retries=args.fetch_retries,
            )
        elif args.command == "test":
            run_test(
                input_path=args.input,
                output_root=args.output_root,
                api_key=args.api_key,
                mode=args.mode,
                sample_size=args.sample_size,
                seed=args.seed,
                top_n=args.top_n,
                workers=args.workers,
                check_timeout=args.timeout,
                check_retries=args.retries,
                batch_size=args.batch_size,
                sleep_sec=args.sleep_sec,
                fetch_timeout=args.fetch_timeout,
                fetch_retries=args.fetch_retries,
            )
        else:
            raise RuntimeError(f"Unsupported command: {args.command}")
        return 0
    except Exception as exc:
        print(str(exc))
        return 1
