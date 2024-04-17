import psutil
from flask import Flask, render_template, send_from_directory, url_for, flash,jsonify, request, redirect, session
from flask_session.__init__ import Session
import os
from flask_mysqldb import MySQL
import yaml
import hashlib
from datetime import datetime
import calendar
from random import randint
import paramiko
import winrm

app = Flask(__name__)

key = os.urandom(8)
app = Flask(__name__, static_folder='static')
app.secret_key = key
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# MySQL configurations
db = yaml.load(open('db.yaml'), Loader=yaml.FullLoader)
app.config['MYSQL_HOST'] = db['host']
app.config['MYSQL_USER'] = db['user']
app.config['MYSQL_PASSWORD'] = db['password']
app.config['MYSQL_DB'] = db['database']
mysql = MySQL(app)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        userDetails = request.form
        username = userDetails['username']
        password = userDetails['password'].encode('utf-8')
        hashed_password = hashlib.sha256(password).hexdigest()
        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO users(username, password) VALUES (%s, %s)", (username, hashed_password))
        mysql.connection.commit()
        cursor.close()
        flash('Registration successful! Please login.')
        return redirect("/")
    return render_template("register.html")


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        userDetails = request.form
        username = userDetails['username']
        password = userDetails['password'].encode('utf-8')
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        if user and hashlib.sha256(password).hexdigest() == user[2]:
            session["logged_in"] = True
            return redirect("/")
        else:
            error_msg = "Invalid username or password. Please try again."
            return render_template("login.html", error_msg=error_msg)

    if session.get("logged_in"):
        return redirect("/")

    return render_template("login.html")


@app.route('/images/background.jpeg')
def serve_static():
    return send_from_directory('static/images', 'background.jpeg')


@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    return redirect("/login")

@app.route("/indexdata")
def data():
    cpu_usage = psutil.cpu_percent()
    mem_usage = psutil.virtual_memory().percent
    disk_usage = psutil.disk_usage('/').percent
    msg = "OK"
    if cpu_usage > 80 or mem_usage > 80 or disk_usage > 80:
        msg = "Warning"
    return jsonify(cpu_usage=cpu_usage, mem_usage=mem_usage, disk_usage=disk_usage, msg=msg)

@app.route("/")
def index():    
    if not session.get("logged_in"):
        return redirect("/login")
    cpu_usage = psutil.cpu_percent()
    mem_usage = psutil.virtual_memory().percent
    disk_usage = psutil.disk_usage('/').percent
    return render_template("index.html", cpu_usage=cpu_usage, mem_usage=mem_usage, disk_usage=disk_usage)

# Load host configurations from YAML file
def load_host_config():
    with open('hosts.yaml', 'r') as file:
        return yaml.safe_load(file)

host_config = load_host_config()

# Define a function to execute SSH commands
def execute_ssh_command(ssh_client, command):
    stdin, stdout, stderr = ssh_client.exec_command(command)
    output = stdout.read().decode().strip()
    error = stderr.read().decode().strip()
    if error:
        raise Exception(f"Error executing SSH command: {error}")
    return output

# Define a function to execute WinRM commands
def execute_winrm_command(session, command):
    result = session.run_ps(command)
    if result.status_code != 0:
        raise Exception(f"Error executing WinRM command: {result.std_err}")
    return result.std_out.strip()

def get_linux_data(host_details):
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        if host_details['auth_method'] == 'password':
            ssh_client.connect(host_details['hostname'], username=host_details['username'], password=host_details['password'])
        elif host_details['auth_method'] == 'private_key':
            key = paramiko.RSAKey.from_private_key_file(host_details['key_path'])
            ssh_client.connect(host_details['hostname'], username=host_details['username'], pkey=key)

        # Commands to fetch metrics
        cpu_usage = execute_ssh_command(ssh_client, "top -bn1 | grep 'Cpu(s)' | sed 's/.*, *\([0-9.]*\)%* id.*/\\1/' | awk '{print 100 - $1}'")
        mem_usage = execute_ssh_command(ssh_client, "free | grep Mem | awk '{print $3/$2 * 100.0}'")
        disk_usage = execute_ssh_command(ssh_client, "df -h / | awk 'NR==2 {print $5}'").replace('%', '')

        return jsonify({
            "cpu_usage": float(cpu_usage),
            "mem_usage": float(mem_usage),
            "disk_usage": float(disk_usage),
            "status": "OK"
        })
    finally:
        ssh_client.close()

def get_windows_data(host_details):
    session = winrm.Session(host_details['hostname'], auth=(host_details['username'], host_details['password']))
    try:
        cpu_usage = execute_winrm_command(session, "(Get-Counter '\\Processor(_Total)\\% Processor Time').CounterSamples.CookedValue")
        mem_usage = execute_winrm_command(session, "$mem = Get-WmiObject Win32_OperatingSystem; 100 - ($mem.FreePhysicalMemory / $mem.TotalVisibleMemorySize * 100)")
        disk_usage = execute_winrm_command(session, "(Get-PSDrive C).Used / (Get-PSDrive C).Size * 100")

        return jsonify({
            "cpu_usage": float(cpu_usage),
            "mem_usage": float(mem_usage),
            "disk_usage": float(disk_usage),
            "status": "OK"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

#***********Endpoint to fetch hosts from the YAML file************
@app.route('/hosts')
def get_hosts():
    with open('hosts.yaml', 'r') as file:
        hosts = yaml.safe_load(file).get('hosts', {})
    return jsonify({host: details['hostname'] for host, details in hosts.items()})

#********Endpoint to fetch hosts from the database file******
# @app.route('/hosts')
# def get_hosts():
#     # Query MySQL database to retrieve the list of hosts
#     query = "SELECT DISTINCT hostname FROM cpu_utilization"
#     cursor = mysql.connection.cursor()
#     cursor.execute(query)
#     hosts = [row[0] for row in cursor.fetchall()]
#     cursor.close()
#     return jsonify(hosts)

@app.route('/host/<host_id>', methods=['GET'])
def get_host_data(host_id):
    if host_id not in host_config['hosts']:
        return jsonify({"error": "Host not found"}), 404

    host_details = host_config['hosts'][host_id]
    try:
        if host_details['type'] == 'linux':
            return get_linux_data(host_details)
        elif host_details['type'] == 'windows':
            return get_windows_data(host_details)
        else:
            return jsonify({"error": "Unsupported host type"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/latest")
def current():
    if not session.get("logged_in"):
        return redirect("/login")
    return render_template("latest.html")

@app.route('/historicaldata', methods=['POST'])
def get_data():
    start_date = request.form['start_date']
    end_date = request.form['end_date']
    host = request.form.get('host')

    # Adjust WHERE clause for host filtering
    where_clause = "WHERE cpu.timestamp BETWEEN %s AND %s"
    params = [start_date, end_date]

    if host:
        where_clause += " AND cpu.hostname = %s"
        params.append(host)

    # Join additional information for disk utilization per mount point
    query = f"""
        SELECT cpu.timestamp AS timestamp, 
               cpu.cpu_utilization AS cpu_usage, 
               disk.disk_usage_percent AS disk_usage, 
               disk.mount_point AS mount_point,  # Include mount point in the select
               memory.used_memory / memory.total_memory * 100 AS memory_usage
        FROM cpu_utilization cpu
        JOIN disk_utilization disk ON cpu.hostname = disk.hostname AND cpu.timestamp = disk.timestamp
        JOIN memory_utilization memory ON cpu.hostname = memory.hostname AND cpu.timestamp = memory.timestamp
        {where_clause}
        ORDER BY disk.mount_point, cpu.timestamp  # Ensure data is grouped by mount point
    """

    cursor = mysql.connection.cursor()
    cursor.execute(query, tuple(params))
    result = cursor.fetchall()
    cursor.close()

    # Prepare data for Chart.js with multiple datasets for disk usage
    labels = list(set([row[0] for row in result]))  # Get unique timestamps
    labels.sort()
    cpu_usage = []
    memory_usage = []
    disk_usage_by_mount = {}

    for row in result:
        if row[0] in labels:
            cpu_usage.append(row[1])
            memory_usage.append(row[4])  # Adjust index to get memory usage
            mount_point = row[3]
            if mount_point not in disk_usage_by_mount:
                disk_usage_by_mount[mount_point] = []
            disk_usage_by_mount[mount_point].append(row[2])

    disk_datasets = [{
        'label': f'Disk Usage - {mount_point}',
        'data': usage,
        'borderColor': f'rgb({randint(0,255)}, {randint(0,255)}, {randint(0,255)})',
        'fill': False
    } for mount_point, usage in disk_usage_by_mount.items()]

    data = {
        'labels': labels,
        'cpu_usage': cpu_usage,
        'memory_usage': memory_usage,
        'disk_usage_datasets': disk_datasets  # Adjusted to handle multiple disk datasets
    }

    return jsonify(data)

@app.route('/historical')
def historical():
    if not session.get("logged_in"):
        return redirect("/login")
    return render_template('historical.html')

if __name__ == "__main__":
    app.run(host='0.0.0.0')
