import subprocess
import json

def get_os_drive():
    # run lsblk and get mountpoints for all devices
    result = subprocess.run(["lsblk", "-J", "-o", "NAME,MOUNTPOINT"], capture_output=True, text=True)
    data = json.loads(result.stdout)

    for device in data["blockdevices"]:
        # check if the device itself is mounted at root
        if device.get("mountpoint") == "/":
            return device.get("name")
        # check partitions in case root is on a child partition
        for child in device.get("children", []):
            if child.get("mountpoint") == "/":
                return device.get("name")  # return parent disk, not the partition

    return None

def get_drives():
    # get the os drive name so it can be excluded
    os_drive = get_os_drive()

    # run lsblk with all the fields we need, output as json
    result = subprocess.run(["lsblk", "-J", "-o", "NAME,TYPE,MODEL,SERIAL,SIZE,ROTA,TRAN"], capture_output=True, text=True)
    data = json.loads(result.stdout)

    drives = []
    for device in data["blockdevices"]:
        # skip partitions and other non-disk entries
        if device["type"] != "disk":
            continue
        # skip the drive the os is running on
        if device["name"] == os_drive:
            continue

        # determine drive type based on transport and rotation flag
        tran = device.get("tran", "")
        rota = device.get("rota") == "1"

        if tran == "nvme":
            drive_type = "NVMe"
        elif rota:
            drive_type = "HDD"
        else:
            drive_type = "SSD"

        drive_info = {
            "name": device["name"],
            "model": device.get("model", ""),
            "serial": device.get("serial", ""),
            "size": device.get("size", ""),
            "type": drive_type,
            "tran": tran,
        }
        drives.append(drive_info)

    return drives

# entry point for testing — prints detected drives as formatted json
if __name__ == "__main__":
    drives = get_drives()
    print(json.dumps(drives, indent=2))