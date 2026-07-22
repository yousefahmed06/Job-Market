"""
Fetches current remote job postings from the RemoteOK public API and appends
a full snapshot to jobs_data.csv on every run (fetch_timestamp marks when
each snapshot was taken).

RemoteOK's /api endpoint always returns the current pool of live listings --
there's no per-tag URL that returns a different/larger set (their own client
libraries filter tags locally after fetching this same feed). So a handful
of scheduled runs is what gets you to a large row count, not a single trick
call. The upside of NOT deduping: since the same job can appear across
several snapshots, you can group by "id" later and see how long a listing
stayed active, in addition to counts/trends over time.

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
    "slug",
    "epoch",
    "date_posted",
    "company",
    "position",
    "tags",
    "tag_count",
    "location",
    "salary_min",
    "salary_max",
    "has_salary",
    "apply_url",
    "url",
    "description_length",
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
    # The first element is a legal/notice object, not a job listing -- skip it
    return [item for item in data if "id" in item]


def main():
    jobs = fetch_jobs()
    fetch_time = datetime.now(timezone.utc).isoformat()
    file_exists = os.path.isfile(CSV_FILE)

    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()

        for job in jobs:
            tags = job.get("tags", [])
            salary_min = job.get("salary_min", 0) or 0
            salary_max = job.get("salary_max", 0) or 0
            writer.writerow({
                "fetch_timestamp": fetch_time,
                "id": job.get("id", ""),
                "slug": job.get("slug", ""),
                "epoch": job.get("epoch", ""),
                "date_posted": job.get("date", ""),
                "company": job.get("company", ""),
                "position": job.get("position", ""),
                "tags": "; ".join(tags),
                "tag_count": len(tags),
                "location": job.get("location", ""),
                "salary_min": salary_min,
                "salary_max": salary_max,
                "has_salary": bool(salary_min or salary_max),
                "apply_url": job.get("apply_url", job.get("url", "")),
                "url": job.get("url", ""),
                "description_length": len(job.get("description", "")),
            })

    print(f"Wrote {len(jobs)} rows for this snapshot")


if __name__ == "__main__":
    main()
