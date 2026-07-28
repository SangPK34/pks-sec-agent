"""Update the benchmarks README file.

How to execute:
    python src/pks/pksbench/update_readme.py
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

from pks.pksbench.ctf import update_main_benchmarks_readme

if __name__ == "__main__":
    update_main_benchmarks_readme()