import argparse
import bz2
import os
import random
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List

import capnp
import requests

ACCOUNT = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NDg1ODI0NjUsIm5iZiI6MTcxNzA0NjQ2NSwiaWF0IjoxNzE3MDQ2NDY1LCJpZGVudGl0eSI6IjBkZWNkZGNmZGYyNDFhNjAifQ.g3khyJgOkNvZny6Vh579cuQj1HLLGSDeauZbfZri9jw"
DEVICE = "1d3dc3e03047b0c7"
ROUTE = "000000dd--455f14369d"

ROUTE_STORAGE_PATH = Path("./routes")
SCHEMA_BASE = Path(__file__).parent / "schema"
SCHEMAS = [
    "log.capnp",
    "custom.capnp",
    "legacy.capnp",
    "car.capnp",
    "include/c++.capnp",
]


def load_log_schema():
    if not all((SCHEMA_BASE / schema).is_file() for schema in SCHEMAS):
        (SCHEMA_BASE / "include").mkdir(parents=True, exist_ok=True)
        url = "https://raw.githubusercontent.com/commaai/openpilot/master/cereal/"
        for schema in SCHEMAS:
            response = requests.get(f"{url}{schema}")
            response.raise_for_status()
            (SCHEMA_BASE / schema).write_text(response.text)
    return capnp.load(str(SCHEMA_BASE / "log.capnp"))  # type: ignore


capnp.remove_import_hook()  # type: ignore
log = load_log_schema()


def download_file(url: str, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        for chunk in requests.get(url, stream=True).iter_content(chunk_size=8192):
            f.write(chunk)
    return str(path)


def download_route(account: str, device: str, route: str) -> Dict[str, List[str]]:
    url = f"https://api.commadotai.com/v1/route/{device}|{route}/files"
    response = requests.get(url, headers={"Authorization": f"JWT {account}"})
    response.raise_for_status()
    files = response.json()
    route_data = defaultdict(list)
    with ThreadPoolExecutor() as executor:
        future_to_url = {}
        for file_type in ("qlogs", "qcameras"):
            for i, url in enumerate(files[file_type]):
                path = (
                    ROUTE_STORAGE_PATH
                    / route
                    / f"{route}--{i}"
                    / f"{file_type[:-1]}.{'bz2' if file_type == 'qlogs' else 'ts'}"
                )
                future = executor.submit(download_file, url, path)
                future_to_url[future] = (file_type, url)
        for future in as_completed(future_to_url):
            file_type, url = future_to_url[future]
            try:
                path = future.result()
                route_data[file_type].append(path)
            except Exception as exc:
                print(f"{url} generated an exception: {exc}")
    return route_data


def verify_route(route_data):
    for i, qlog_path in enumerate(route_data["qlogs"]):
        with open(qlog_path, "rb") as f:
            data = bz2.decompress(f.read())
        events = list(log.Event.read_multiple_bytes(data))
        checks = {
            "starts at segment 0": i > 0
            or any(e.which() == "initData" for e in events),
            "has qlog": len(events) > 0,
            "has qcamera": os.path.exists(route_data["qcameras"][i]),
            "has GPS": any(e.which() == "gpsLocation" for e in events),
            "has thumbnail": any(e.which() == "thumbnail" for e in events),
        }
        event_types = {}
        for e in events:
            event_type = e.which()
            event_types[event_type] = event_types.get(event_type, 0) + 1

        print("  Event types:")
        for event_type, count in event_types.items():
            print(f"    {event_type}: {count}")

        if not all(checks.values()):
            raise ValueError(f"Segment {i} failed verification: {checks}")


def corrupt_route(route_data, corruption):
    new_route = f"{route_data['qlogs'][0].split('/')[-3][:9]}{''.join(random.choice('abcdefghijklmnopqrstuvwxyz') for _ in range(4))}"
    new_route_data = {"qlogs": [], "qcameras": []}

    for i, (qlog_path, qcam_path) in enumerate(
        zip(route_data["qlogs"], route_data["qcameras"])
    ):
        new_qlog_path = f"{ROUTE_STORAGE_PATH}/{new_route}/{new_route}--{i}/qlog.bz2"
        new_qcam_path = f"{ROUTE_STORAGE_PATH}/{new_route}/{new_route}--{i}/qcamera.ts"
        os.makedirs(os.path.dirname(new_qlog_path), exist_ok=True)

        with open(qlog_path, "rb") as f:
            data = bz2.decompress(f.read())
        events = list(log.Event.read_multiple_bytes(data))

        if corruption == "no_date_time":
            events = [e for e in events if e.which() != "initData"]
        elif corruption == "GPS_missing":
            events = [e for e in events if e.which() != "gpsLocation"]
        elif corruption == "thumbnail_missing":
            events = [e for e in events if e.which() != "thumbnail"]
        elif corruption == "segment_too_long":
            events = events + events[:1200]  # Add 60 more seconds (assuming 20 Hz)

        if corruption != "qlog_missing":
            with open(new_qlog_path, "wb") as f:
                f.write(
                    bz2.compress(b"".join(e.as_builder().to_bytes() for e in events))
                )
            new_route_data["qlogs"].append(new_qlog_path)

        if corruption != "qcam_missing":
            os.system(f"cp {qcam_path} {new_qcam_path}")
            new_route_data["qcameras"].append(new_qcam_path)

    return new_route_data


def main():
    parser = argparse.ArgumentParser(description="Corrupt openpilot routes for testing")
    parser.add_argument(
        "-a",
        "--account",
        type=str,
        default=ACCOUNT,
        help="JWT access token for comma account",
    )
    parser.add_argument(
        "-d",
        "--device",
        type=str,
        default=DEVICE,
        help="dongleId of the device",
    )
    parser.add_argument(
        "-r",
        "--route",
        type=str,
        default=ROUTE,
        help="Route ID to corrupt",
    )
    args = parser.parse_args()

    route_data = download_route(args.account, args.device, args.route)
    # verify_route(route_data)
    exit(1)

    corruptions = [
        "no_date_time",
        "GPS_missing",
        "qlog_missing",
        "qcam_missing",
        "thumbnail_missing",
        "segment_too_long",
    ]
    for corruption in corruptions:
        new_route_data = corrupt_route(route_data, corruption)
        if new_route_data["qlogs"]:
            print(
                f"Created corrupted route for case '{corruption}' at {os.path.dirname(new_route_data['qlogs'][0])}"
            )
        elif new_route_data["qcameras"]:
            print(
                f"Created corrupted route for case '{corruption}' at {os.path.dirname(new_route_data['qcameras'][0])}"
            )
        else:
            print(
                f"Created corrupted route for case '{corruption}', but no files were generated."
            )


if __name__ == "__main__":
    main()
