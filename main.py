import argparse

from engine.pipeline.flow_spike import run_pipeline_entry


def main():
    parser = argparse.ArgumentParser(description="AI Content Engine Industrial Pipelined")
    parser.add_argument("--topic", type=str, help="Specific topic to process")
    parser.add_argument("--limit", type=int, default=2, help="Max spokes to write per topic")
    args = parser.parse_args()

    run_pipeline_entry(topic=args.topic, limit=args.limit)


if __name__ == "__main__":
    main()
