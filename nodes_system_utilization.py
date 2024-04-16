import paramiko
import yaml
import mysql.connector
import re
import time

def load_hosts(file_path):
    try:
        with open(file_path, 'r') as file:
            hosts = yaml.safe_load(file)
        return hosts
    except FileNotFoundError:
        print("Hosts file not found.")
        return {}

def connect_to_mysql(config_file):
    try:
        with open(config_file, 'r') as file:
            config = yaml.safe_load(file)
        connection = mysql.connector.connect(**config)
        if connection.is_connected():
            print("Connected to MySQL database")
            return connection
    except Exception as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def ssh_connect(node):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        if 'password' in node:
            client.connect(node['hostname'], username=node['username'], password=node['password'])
        elif 'key_path' in node:
            pkey = paramiko.RSAKey.from_private_key_file(node['key_path'])
            client.connect(node['hostname'], username=node['username'], pkey=pkey)
        else:
            print(f"Unsupported authentication method for {node['hostname']}")
            return None
        return client
    except Exception as e:
        print(f"Failed to connect to {node['hostname']}: {e}")
        return None

def execute_ssh_command(ssh_client, command):
    stdin, stdout, stderr = ssh_client.exec_command(command)
    return stdout.read().decode().strip()

def fetch_metrics_linux(ssh_client):
    # Fetching CPU, memory, and disk utilization for Linux
    cpu_utilization_command = "top -bn1 | grep 'Cpu(s)' | sed 's/.*, *\\([0-9.]*\\)%* id.*/\\1/' | awk '{print 100 - $1}'"
    memory_utilization_command = "free -m | grep Mem | awk '{print $2,$3,$4}'"
    disk_utilization_command = "df -h | grep -vE '^Filesystem|tmpfs|cdrom' | awk '{ print $1,$2,$3,$4,$5,$6 }'"
    
    cpu_utilization = execute_ssh_command(ssh_client, cpu_utilization_command)
    memory_utilization = execute_ssh_command(ssh_client, memory_utilization_command)
    disk_utilization = execute_ssh_command(ssh_client, disk_utilization_command)
    
    return cpu_utilization, memory_utilization, disk_utilization

def fetch_metrics_windows(ssh_client):
    # Fetching CPU, memory, and disk utilization for Windows
    cpu_utilization_command = "$cpu = Get-WmiObject win32_processor; $cpu.LoadPercentage"
    memory_utilization_command = "$mem = Get-WmiObject win32_operatingsystem; '{0} {1} {2}' -f $mem.TotalVisibleMemorySize, $mem.FreePhysicalMemory, ($mem.TotalVisibleMemorySize - $mem.FreePhysicalMemory)"
    disk_utilization_command = "Get-WmiObject Win32_LogicalDisk | Where-Object {$_.DriveType -eq 3} | ForEach-Object {'{0} {1} {2} {3} {4}' -f $_.DeviceID, $_.Size, $_.FreeSpace, ($_.Size - $_.FreeSpace), ($_.FreeSpace / $_.Size * 100)}"

    cpu_utilization = execute_ssh_command(ssh_client, cpu_utilization_command)
    memory_utilization = execute_ssh_command(ssh_client, memory_utilization_command)
    disk_utilization = execute_ssh_command(ssh_client, disk_utilization_command)
    
    return cpu_utilization, memory_utilization, disk_utilization

def insert_node_utilization(connection, hostname, cpu_utilization, memory_utilization, disk_utilization):
    cursor = connection.cursor()

    # Insert CPU utilization
    cpu_query = "INSERT INTO cpu_utilization (hostname, cpu_utilization) VALUES (%s, %s)"
    cursor.execute(cpu_query, (hostname, cpu_utilization))

    # Parse and insert memory utilization
    total_mem, used_mem, free_mem = map(int, memory_utilization.split())
    mem_query = "INSERT INTO memory_utilization (hostname, total_memory, used_memory, free_memory) VALUES (%s, %s, %s, %s)"
    cursor.execute(mem_query, (hostname, total_mem, used_mem, free_mem))

    # Parse and insert disk utilization
    for line in disk_utilization.splitlines():
        mount_point, total_disk, used_disk, free_disk, percent = line.split()[:5]
        total_disk = parse_disk_size(total_disk)
        used_disk = parse_disk_size(used_disk)
        free_disk = parse_disk_size(free_disk)
        try:
            disk_usage_percent = float(percent.strip('%'))
            if disk_usage_percent < 0 or disk_usage_percent > 100:
                raise ValueError("Disk usage percentage out of range")
            disk_query = "INSERT INTO disk_utilization (hostname, mount_point, total_disk, used_disk, free_disk, disk_usage_percent) VALUES (%s, %s, %s, %s, %s, %s)"
            cursor.execute(disk_query, (hostname, mount_point, total_disk, used_disk, free_disk, disk_usage_percent))
        except (ValueError, IndexError) as e:
            print(f"Error inserting disk utilization for {mount_point}: {e}")

    connection.commit()
    cursor.close()

def parse_disk_size(size_str):
    # Regular expression to match numeric value and unit
    match = re.match(r'(\d+)([KMGT]B?)', size_str.upper())
    if match:
        numeric_value = int(match.group(1))
        unit = match.group(2)
        if ((unit == 'K') or (unit == 'KB')):
            return numeric_value * 1024
        elif ((unit == 'M') or (unit == 'MB')):
            return numeric_value * 1024 ** 2
        elif ((unit == 'G') or (unit == 'GB')):
            return numeric_value * 1024 ** 3
        elif ((unit == 'T') or (unit == 'TB')):
            return numeric_value * 1024 ** 4
    return 0  # Default to 0 if size_str cannot be parsed

def fetch_and_insert_node_data(host, connection):
    ssh_client = ssh_connect(host)
    if ssh_client is None:
        return
    
    if host['type'].lower() == 'linux':
        cpu_utilization, memory_utilization, disk_utilization = fetch_metrics_linux(ssh_client)
    elif host['type'].lower() == 'windows':
        cpu_utilization, memory_utilization, disk_utilization = fetch_metrics_windows(ssh_client)
    else:
        print(f"OS type for {host['hostname']} not supported.")
        ssh_client.close()  # Close the SSH connection before returning
        return
    
    print(f"Data for {host['hostname']}: CPU {cpu_utilization}, Mem {memory_utilization}, Disk {disk_utilization}")

    # Call the insert_node_utilization() function with fetched data
    insert_node_utilization(connection, host['hostname'], cpu_utilization, memory_utilization, disk_utilization)

    # Optionally, print a message indicating successful insertion
    print(f"Data for {host['hostname']} inserted successfully.")

    # Close the SSH connection
    ssh_client.close()

def main():
    # Load hosts and connect to MySQL
    hosts = load_hosts('hosts.yaml')
    connection = connect_to_mysql('db.yaml')
    if not connection:
        print("Failed to connect to the database.")
        return

    # Main loop
    while True:
        for host_key, host_value in hosts['hosts'].items():
            # Fetch and insert node data
            fetch_and_insert_node_data(host_value, connection)

        # Sleep for 5 seconds before next iteration
        time.sleep(5)

    # Close the database connection when finished
    if connection:
        connection.close()

if __name__ == "__main__":
    main()
