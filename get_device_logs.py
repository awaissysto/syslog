import netmiko
from netmiko import ConnectHandler
from datetime import datetime

# Device credentials and details (modify this with your actual device info)
devices = [
   {
        'device_type': 'cisco_nxos',
        'host': '172.16.17.254',  # Cisco Nexus IP
        'username': 'admin',
        'password': 'GiS@35201',
    },
    {
        'device_type': 'juniper',
        'host': '172.16.17.253',  # Juniper IP
        'username': 'awais',
        'password': 'Dell@1122',
    }
]

# Commands to retrieve logs
cisco_commands = [
    'show logging',  # Complete logs for Cisco Nexus
]

juniper_commands = [
    'show log messages',  # Complete logs for Juniper
]

# Log file to store the output
LOG_FILE = "/var/log/network_device_logs.log"  # Adjust this path as needed

# Dictionary to store the last retrieved logs for each device and command
last_log_entries = {}  # Store last log snapshot


def log_to_file(logs):
    """Append logs to the log file with current timestamp."""
    with open(LOG_FILE, "a") as log_file:
        log_file.write("\n".join(logs))
        log_file.write("\n" + "=" * 40 + "\n")


def add_timestamp(log_entry):
    """Add current timestamp to each log entry."""
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return f"[{current_time}] {log_entry}"


def establish_connections():
    """Establish persistent connections to all devices."""
    connections = {}

    for device in devices:
        try:
            print(f"Connecting to {device['host']}...")
            connection = ConnectHandler(**device)
            connections[device['host']] = connection
            print(f"Connected to {device['host']}.")
        except netmiko.NetMikoTimeoutException:
            print(f"Connection timed out for device {device['host']}")
        except netmiko.NetMikoAuthenticationException:
            print(f"Authentication failed for device {device['host']}")
    
    return connections


def get_initial_log_snapshot(connections):
    """Capture the last log entry when the script starts to ignore previous logs."""
    for device in devices:
        connection = connections.get(device['host'])
        if not connection:
            continue

        # Cisco Nexus
        if device['device_type'] == 'cisco_nxos':
            output = connection.send_command(cisco_commands[0])
            last_log_entries[device['host']] = output.splitlines()[-1]  # Store the last log entry

        # Juniper
        elif device['device_type'] == 'juniper':
            output = connection.send_command(juniper_commands[0])
            last_log_entries[device['host']] = output.splitlines()[-1]  # Store the last log entry


def get_device_logs(connections):
    """Retrieve only new logs generated after the initial snapshot."""
    logs = []

    for device in devices:
        connection = connections.get(device['host'])
        if not connection:
            continue

        # Cisco Nexus
        if device['device_type'] == 'cisco_nxos':
            output = connection.send_command(cisco_commands[0])
            logs += get_new_logs(output, device['host'])

        # Juniper
        elif device['device_type'] == 'juniper':
            output = connection.send_command(juniper_commands[0])
            logs += get_new_logs(output, device['host'])

    return logs


def get_new_logs(log_output, device_host):
    """Compare current logs with the initial snapshot and return only new logs."""
    current_logs = log_output.splitlines()
    last_log = last_log_entries.get(device_host)

    if last_log in current_logs:
        last_log_index = current_logs.index(last_log)
        new_logs = current_logs[last_log_index + 1:]  # Only logs after the last snapshot
    else:
        new_logs = current_logs  # If last log is missing, return all logs

    if new_logs:
        last_log_entries[device_host] = current_logs[-1]  # Update the last log snapshot

    return [add_timestamp(log) for log in new_logs]  # Add timestamps to new logs


if __name__ == "__main__":
    print("Starting real-time continuous logging...")

    # Step 1: Establish persistent connections
    device_connections = establish_connections()

    # Step 2: Capture initial log snapshot to ignore old logs
    get_initial_log_snapshot(device_connections)

    # Step 3: Continuously gather only new logs in real-time
    try:
        while True:
            logs = get_device_logs(device_connections)
            if logs:  # Only log if there are new changes
                log_to_file(logs)

    except KeyboardInterrupt:
        print("Stopping logging and closing connections...")

    # Close all connections when the script ends
    finally:
        for connection in device_connections.values():
            connection.disconnect()
