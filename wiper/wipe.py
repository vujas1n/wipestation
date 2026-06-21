import subprocess
import json
import csv
import os
import threading
from datetime import datetime
from wiper.detect import get_os_drive
from certs.generator import generate_certificate

STATUS_FILE = "logs/status.json"
LOG_FILE = "logs/wipe_log.csv"

# lock to prevent two threads writing status.json at the same time
status_lock = threading.Lock()

def update_status(drive_name, state, message=""):
    with status_lock:
        status = {}
        if os.path.exists(STATUS_FILE):
            with open(STATUS_FILE, "r") as f:
                try:
                    status = json.load(f)
                except json.JSONDecodeError:
                    status = {}

        status[drive_name] = {
            "state": state,
            "message": message,
            "updated_at": datetime.now().isoformat()
        }

        with open(STATUS_FILE, "w") as f:
            json.dump(status, f, indent=2)

def log_to_csv(drive, result, start_time, end_time):
    with status_lock:  # reuse the same lock since csv writes need protection too
        file_exists = os.path.exists(LOG_FILE)
        with open(LOG_FILE, "a", newline="") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["name", "model", "serial", "size", "type", "result", "start_time", "end_time"])
            writer.writerow([
                drive["name"], drive["model"], drive["serial"], drive["size"],
                drive["type"], result, start_time, end_time
            ])

def wipe_drive(drive):
    # this stays exactly the same — wipes a single drive
    os_drive = get_os_drive()
    if drive["name"] == os_drive:
        raise Exception(f"Refusing to wipe OS drive: {drive['name']}")

    device_path = f"/dev/{drive['name']}"
    start_time = datetime.now().isoformat()

    print(f"starting wipe on {device_path} ({drive['type']})")
    update_status(drive["name"], "in_progress")

    try:
        if drive["type"] == "HDD":
            wipe_hdd(device_path)
        elif drive["type"] == "SSD":
            wipe_ssd(device_path)
        elif drive["type"] == "NVMe":
            wipe_nvme(device_path)
        else:
            raise Exception(f"Unknown drive type: {drive['type']}")

        result = "PASS"
        print(f"wipe finished on {device_path}")
        update_status(drive["name"], "done")

    except Exception as e:
        result = "FAIL"
        print(f"wipe failed on {device_path}: {e}")
        update_status(drive["name"], "failed", str(e))

    end_time = datetime.now().isoformat()
    log_to_csv(drive, result, start_time, end_time)

    cert_path = generate_certificate(drive, result, start_time, end_time)
    print(f"certificate saved to {cert_path}")

    return result

def wipe_multiple(drives):
    # takes a list of selected drives and wipes them all in parallel
    threads = []
    for drive in drives:
        t = threading.Thread(target=wipe_drive, args=(drive,))
        threads.append(t)
        t.start()

    # wait for all wipes to finish before returning
    for t in threads:
        t.join()

    print("all selected drives finished wiping")

def wipe_hdd(device_path):
    subprocess.run(["nwipe", "--autonuke", device_path], check=True)

def wipe_ssd(device_path):
    subprocess.run(["hdparm", "--security-erase", "NULL", device_path], check=True)

def wipe_nvme(device_path):
    subprocess.run(["nvme", "format", device_path, "--ses=1"], check=True)