import argparse
import sys

from engine.pipeline.flow_spike import run_pipeline_entry
from engine.pipeline.runner import print_run_summary, print_run_summary_list


def main():
    parser = argparse.ArgumentParser(description="AI Content Engine Industrial Pipelined")
    parser.add_argument("--topic", type=str, help="Specific topic to process")
    parser.add_argument(
        "--spoke-limit",
        type=int,
        default=2,
        help="Max spokes to write per topic",
    )
    parser.add_argument(
        "--topic-limit",
        type=int,
        default=None,
        help="Max number of topics to process from prioritized queue (ignored when --topic is used)",
    )
    parser.add_argument(
        "--cluster-size",
        type=int,
        default=6,
        help="Target total cluster size for planning (1 pillar + remaining spokes, default 6)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Backward-compatible alias for --spoke-limit",
    )
    parser.add_argument(
        "--last-run",
        action="store_true",
        help="Print the latest run summary from outputs/run_summaries",
    )
    parser.add_argument(
        "--run-id",
        type=str,
        help="Print a specific run summary by run_id",
    )
    parser.add_argument(
        "--run-list",
        type=int,
        nargs="?",
        const=10,
        default=None,
        help="List recent run summaries (optionally provide max rows, default 10)",
    )
    parser.add_argument(
        "--failed-only",
        action="store_true",
        help="With --run-list, show only failed runs",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output inspector results as JSON (use with --last-run, --run-id, or --run-list)",
    )
    args = parser.parse_args()

    summary_flags_used = sum(
        [
            1 if args.last_run else 0,
            1 if bool(args.run_id) else 0,
            1 if args.run_list is not None else 0,
        ]
    )
    if summary_flags_used > 1:
        print("Use only one of --last-run, --run-id, or --run-list.")
        sys.exit(2)

    if args.json and summary_flags_used == 0:
        print("--json can only be used with --last-run, --run-id, or --run-list")
        sys.exit(2)

    if args.last_run:
        sys.exit(print_run_summary(latest=True, as_json=args.json))

    if args.run_id:
        sys.exit(print_run_summary(run_id=args.run_id, as_json=args.json))

    if args.run_list is not None:
        if args.run_list < 1:
            print("--run-list must be >= 1")
            sys.exit(2)
        sys.exit(
            print_run_summary_list(
                limit=args.run_list,
                failed_only=args.failed_only,
                as_json=args.json,
            )
        )

    if args.failed_only:
        print("--failed-only can only be used with --run-list")
        sys.exit(2)

    if args.cluster_size < 2:
        print("--cluster-size must be >= 2")
        sys.exit(2)

    spoke_limit = args.limit if args.limit is not None else args.spoke_limit
    run_pipeline_entry(
        topic=args.topic,
        spoke_limit=spoke_limit,
        topic_limit=args.topic_limit,
        cluster_size=args.cluster_size,
    )


if __name__ == "__main__":
    main()
