"""Command-line entry point.

    python run_pipeline.py                      # default data, English labels
    python run_pipeline.py --lang zh            # Chinese figure labels
    python run_pipeline.py --input my.xlsx --mold 16
"""
from casting_viz.pipeline import main

if __name__ == "__main__":
    main()
