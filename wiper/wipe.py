import subprocess
import json
import csv
import os
from datetime import datetime
from wiper.detect import get_os_drive
from certs.generator import generate_certificate

STATUS_FILE = "logs/status.json"
LOG_FILE = "logs/wipe_log.csv"

def update_status(drive_name, state, message=""):
    # writes current wipe status to a json file so the gui can poll it later
    status = {}
    if os.path.exists(STATUS_FILE):
        with open(STATUS_FILE, "r") as f:
            try:
                status = json.load(f)
            except json.JSONDecodeError:
                status = {}

    status[drive_name] = {
        "state": state,  # e.g. "in_progress", "done", "failed"
        "message": message,
        "updated_at": datetime.now().isoformat()
    }

    with open(STATUS_FILE, "w") as f:
        json.dump(status, f, indent=2)

def log_to_csv(drive, result, start_time, end_time):
    # appends a row to the audit log csv, creates the file with headers if missing
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

    # generate the pdf certificate for this drive regardless of pass/fail
    cert_path = generate_certificate(drive, result, start_time, end_time)
    print(f"certificate saved to {cert_path}")

    return result

def wipe_hdd(device_path):
    # nwipe for hdds — multiple overwrite passes
    subprocess.run(["nwipe", "--autonuke", device_path], check=True)

def wipe_ssd(device_path):
    # hdparm ata secure erase for sata ssds
    subprocess.run(["hdparm", "--security-erase", "NULL", device_path], check=True)

def wipe_nvme(device_path):
    # nvme-cli format/sanitize for nvme drives
    subprocess.run(["nvme", "format", device_path, "--ses=1"], check=True)