"""
Fetches current remote job postings from the RemoteOK public API and appends
NEW postings (deduped by job id) to jobs_data.csv.

RemoteOK returns a live snapshot of active listings on every call, so we only
write rows for job ids we haven't seen before -- otherwise the same postings
would get duplicated every run. This turns the CSV into a growing archive of
"jobs as they appeared," useful for tracking hiring trends over time.

Note: RemoteOK's API terms ask that any public use of this data link back to
the job's RemoteOK URL and credit RemoteOK as the source.

Run manually:
    python fetch_jobs.py
"""

import csv
import os
from datetime import datetime, timezone

import requests

API_URL = "https://remoteok.com/api"
CSV_FILE = "jobs_data.csv"
FIELDNAMES = [
    "fetch_timestamp",
    "id",
    "date_posted",
    "company",
    "position",
    "tags",
    "tag_count",
    "location",
    "salary_min",
    "salary_max",
    "apply_url",
]

# RemoteOK blocks requests with a generic/default User-Agent, so we send a
# normal browser-like one.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}


def fetch_jobs() -> list[dict]:
    response = requests.get(API_URL, headers=HEADERS, timeout=15)
    response.raise_for_status()
    data = response.json()
    # The first element is a legal/notice object, not a job listing — skip it
    return [item for item in data if "id" in item]


def load_existing_ids() -> set:
    if not os.path.isfile(CSV_FILE):
        return set()
    with open(CSV_FILE, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return {row["id"] for row in reader}


def main():
    jobs = fetch_jobs()
    existing_ids = load_existing_ids()
    fetch_time = datetime.now(timezone.utc).isoformat()

    file_exists = os.path.isfile(CSV_FILE)
    new_count = 0

    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()

        for job in jobs:
            job_id = str(job.get("id", ""))
            if not job_id or job_id in existing_ids:
                continue  # already recorded on a previous run — skip

            tags = job.get("tags", [])
            writer.writerow({
                "fetch_timestamp": fetch_time,
                "id": job_id,
                "date_posted": job.get("date", ""),
                "company": job.get("company", ""),
                "position": job.get("position", ""),
                "tags": "; ".join(tags),
                "tag_count": len(tags),
                "location": job.get("location", ""),
                "salary_min": job.get("salary_min", 0),
                "salary_max": job.get("salary_max", 0),
                "apply_url": job.get("apply_url", job.get("url", "")),
            })
            existing_ids.add(job_id)
            new_count += 1

    print(f"Added {new_count} new job postings out of {len(jobs)} fetched")


if __name__ == "__main__":
    main()
