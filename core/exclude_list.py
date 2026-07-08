"""Suppression list so contacted/existing-customer merchants don't resurface.

Share data/exclude_list.csv across a team to avoid two reps working the same
merchant -- known limitation of this single-user v1: there's no locking, so
concurrent writes from multiple people at once could race.
"""
import csv
from pathlib import Path
from typing import Set

EXCLUDE_PATH = Path(__file__).resolve().parent.parent / "data" / "exclude_list.csv"


def load_excluded_ids() -> Set[str]:
    if not EXCLUDE_PATH.exists():
        return set()
    with open(EXCLUDE_PATH, newline="") as f:
        return {row["place_id"] for row in csv.DictReader(f) if row.get("place_id")}


def add_excluded(place_id: str, name: str, reason: str = "contacted") -> None:
    EXCLUDE_PATH.parent.mkdir(exist_ok=True, parents=True)
    is_new = not EXCLUDE_PATH.exists()
    with open(EXCLUDE_PATH, "a", newline="") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(["place_id", "name", "reason"])
        writer.writerow([place_id, name, reason])
