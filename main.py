import argparse

from engine.pipeline.runner import run_pipeline


def main():
    parser = argparse.ArgumentParser(description="AI Content Engine Industrial Pipelined")
    parser.add_argument("--topic", type=str, help="Specific topic to process")
    parser.add_argument("--limit", type=int, default=2, help="Max spokes to write per topic")
    args = parser.parse_args()

    run_pipeline(topic=args.topic, limit=args.limit)


if __name__ == "__main__":
    main()
