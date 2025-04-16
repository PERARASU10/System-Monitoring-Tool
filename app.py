import psutil
import time
import datetime
import platform
import os
import json
from flask import Flask, render_template, jsonify

app = Flask(__name__)

class SystemMonitor:
    def get_system_info(self):
        """Get basic system information."""
        return {
            "system": platform.system(),
            "node": platform.node(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor()
        }
        
    def get_cpu_info(self):
        """Get CPU usage information."""
        return {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "cpu_count": psutil.cpu_count(),
            "cpu_freq": psutil.cpu_freq().current if psutil.cpu_freq() else "N/A",
            "per_cpu": psutil.cpu_percent(interval=0.1, percpu=True)
        }
        
    def get_memory_info(self):
        """Get memory usage information."""
        memory = psutil.virtual_memory()
        return {
            "total": memory.total,
            "available": memory.available,
            "used": memory.used,
            "percent": memory.percent,
            "total_formatted": self._format_bytes(memory.total),
            "available_formatted": self._format_bytes(memory.available),
            "used_formatted": self._format_bytes(memory.used)
        }
        
    def get_disk_info(self):
        """Get disk usage information."""
        disk = psutil.disk_usage('/')
        io_counters = psutil.disk_io_counters()
        
        # Get all disk partitions
        partitions = []
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                partitions.append({
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "fstype": partition.fstype,
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "percent": usage.percent,
                    "total_formatted": self._format_bytes(usage.total),
                    "used_formatted": self._format_bytes(usage.used),
                    "free_formatted": self._format_bytes(usage.free)
                })
            except (PermissionError, OSError):
                # Some mount points may not be accessible
                pass
                
        return {
            "main_disk": {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": disk.percent,
                "total_formatted": self._format_bytes(disk.total),
                "used_formatted": self._format_bytes(disk.used),
                "free_formatted": self._format_bytes(disk.free)
            },
            "io": {
                "read_bytes": io_counters.read_bytes if io_counters else 0,
                "write_bytes": io_counters.write_bytes if io_counters else 0,
                "read_bytes_formatted": self._format_bytes(io_counters.read_bytes) if io_counters else "N/A",
                "write_bytes_formatted": self._format_bytes(io_counters.write_bytes) if io_counters else "N/A"
            },
            "partitions": partitions
        }
        
    def get_network_info(self):
        """Get network usage information."""
        net_io = psutil.net_io_counters()
        
        # Get network interfaces
        interfaces = []
        for interface, stats in psutil.net_if_stats().items():
            if stats.isup:  # Only include active interfaces
                try:
                    interface_io = psutil.net_io_counters(pernic=True).get(interface)
                    if interface_io:
                        interfaces.append({
                            "name": interface,
                            "speed": stats.speed,
                            "mtu": stats.mtu,
                            "bytes_sent": interface_io.bytes_sent,
                            "bytes_recv": interface_io.bytes_recv,
                            "bytes_sent_formatted": self._format_bytes(interface_io.bytes_sent),
                            "bytes_recv_formatted": self._format_bytes(interface_io.bytes_recv)
                        })
                except (KeyError, AttributeError):
                    pass
                    
        return {
            "total": {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv,
                "bytes_sent_formatted": self._format_bytes(net_io.bytes_sent),
                "bytes_recv_formatted": self._format_bytes(net_io.bytes_recv)
            },
            "interfaces": interfaces
        }
        
    def get_process_info(self, top_n=10):
        """Get information about top processes by CPU usage."""
        processes = []
        for proc in sorted(psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent', 'create_time']), 
                           key=lambda p: p.info['cpu_percent'] or 0, reverse=True)[:top_n]:
            try:
                # Get process creation time
                create_time = datetime.datetime.fromtimestamp(proc.info['create_time']).strftime('%Y-%m-%d %H:%M:%S') if proc.info['create_time'] else "Unknown"
                
                # Get memory info in a readable format
                memory_info = proc.memory_info() if hasattr(proc, 'memory_info') else None
                rss_formatted = self._format_bytes(memory_info.rss) if memory_info else "Unknown"
                
                processes.append({
                    'pid': proc.info['pid'],
                    'name': proc.info['name'],
                    'username': proc.info['username'],
                    'cpu_percent': proc.info['cpu_percent'],
                    'memory_percent': round(proc.info['memory_percent'], 1) if proc.info['memory_percent'] else 0,
                    'memory_rss': rss_formatted,
                    'create_time': create_time
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return processes
    
    def _format_bytes(self, bytes_value):
        """Format bytes to human-readable format."""
        if not isinstance(bytes_value, (int, float)):
            return "N/A"
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024:
                return f"{bytes_value:.2f} {unit}"
            bytes_value /= 1024
        return f"{bytes_value:.2f} PB"
    
    def get_all_info(self):
        """Get all system information."""
        return {
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "system": self.get_system_info(),
            "cpu": self.get_cpu_info(),
            "memory": self.get_memory_info(),
            "disk": self.get_disk_info(),
            "network": self.get_network_info(),
            "processes": self.get_process_info()
        }

# Create the monitor instance
system_monitor = SystemMonitor()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/system_info')
def api_system_info():
    return jsonify(system_monitor.get_all_info())

# Create templates directory and index.html if they don't exist
def create_templates():
    if not os.path.exists('templates'):
        os.makedirs('templates')
        
    index_html = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>System Monitor Dashboard</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.3.0/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        body {
            background-color: #f8f9fa;
            padding-top: 20px;
        }
        .card {
            margin-bottom: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .card-header {
            background-color: #007bff;
            color: white;
            border-radius: 10px 10px 0 0 !important;
            font-weight: bold;
        }
        .system-info {
            background-color: #f1f1f1;
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 15px;
        }
        .gauge-container {
            width: 100%;
            height: 150px;
            position: relative;
            margin: 0 auto;
        }
        .gauge {
            width: 100%;
            height: 100%;
        }
        .process-table {
            font-size: 0.85rem;
        }
        .progress {
            height: 20px;
            margin-bottom: 10px;
        }
        .refresh-control {
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1 class="text-center mb-4">System Monitor Dashboard</h1>
        
        <div class="refresh-control">
            <label for="refresh-rate" class="me-2">Refresh rate:</label>
            <select id="refresh-rate" class="form-select form-select-sm" style="width:auto">
                <option value="1000">1 second</option>
                <option value="2000" selected>2 seconds</option>
                <option value="5000">5 seconds</option>
                <option value="10000">10 seconds</option>
                <option value="30000">30 seconds</option>
            </select>
            <span class="ms-3">Last updated: <span id="last-update">Never</span></span>
        </div>
        
        <div class="row">
            <!-- System Info Card -->
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <i class="fas fa-server me-2"></i>System Information
                    </div>
                    <div class="card-body">
                        <div class="system-info">
                            <div id="system-details"></div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- CPU Card -->
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <i class="fas fa-microchip me-2"></i>CPU Usage
                    </div>
                    <div class="card-body">
                        <div class="gauge-container">
                            <canvas id="cpu-gauge" class="gauge"></canvas>
                        </div>
                        <div id="cpu-info" class="mt-3"></div>
                        <div id="per-cpu" class="mt-3"></div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="row">
            <!-- Memory Card -->
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <i class="fas fa-memory me-2"></i>Memory Usage
                    </div>
                    <div class="card-body">
                        <div class="gauge-container">
                            <canvas id="memory-gauge" class="gauge"></canvas>
                        </div>
                        <div id="memory-info" class="mt-3"></div>
                    </div>
                </div>
            </div>
            
            <!-- Disk Card -->
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <i class="fas fa-hdd me-2"></i>Disk Usage
                    </div>
                    <div class="card-body">
                        <div class="gauge-container">
                            <canvas id="disk-gauge" class="gauge"></canvas>
                        </div>
                        <div id="disk-info" class="mt-3"></div>
                        <div id="disk-partitions" class="mt-3"></div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="row">
            <!-- Network Card -->
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <i class="fas fa-network-wired me-2"></i>Network
                    </div>
                    <div class="card-body">
                        <div id="network-info"></div>
                        <div id="network-interfaces" class="mt-3"></div>
                    </div>
                </div>
            </div>
            
            <!-- Processes Card -->
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <i class="fas fa-tasks me-2"></i>Top Processes
                    </div>
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-striped table-sm process-table">
                                <thead>
                                    <tr>
                                        <th>PID</th>
                                        <th>Name</th>
                                        <th>User</th>
                                        <th>CPU %</th>
                                        <th>Memory %</th>
                                        <th>Memory</th>
                                    </tr>
                                </thead>
                                <tbody id="processes-body">
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/jquery/3.6.0/jquery.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.3.0/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
    
    <script>
        // Define gauge chart objects
        let cpuGauge, memoryGauge, diskGauge;
        
        // Initialize the charts
        function initCharts() {
            // CPU Gauge
            const cpuContext = document.getElementById('cpu-gauge').getContext('2d');
            cpuGauge = new Chart(cpuContext, {
                type: 'doughnut',
                data: {
                    labels: ['Used', 'Free'],
                    datasets: [{
                        data: [0, 100],
                        backgroundColor: ['#dc3545', '#e9ecef'],
                        borderWidth: 0
                    }]
                },
                options: {
                    circumference: 180,
                    rotation: -90,
                    cutout: '70%',
                    plugins: {
                        legend: {
                            display: false
                        },
                        tooltip: {
                            enabled: false
                        }
                    },
                    maintainAspectRatio: false
                }
            });
            
            // Memory Gauge
            const memoryContext = document.getElementById('memory-gauge').getContext('2d');
            memoryGauge = new Chart(memoryContext, {
                type: 'doughnut',
                data: {
                    labels: ['Used', 'Free'],
                    datasets: [{
                        data: [0, 100],
                        backgroundColor: ['#fd7e14', '#e9ecef'],
                        borderWidth: 0
                    }]
                },
                options: {
                    circumference: 180,
                    rotation: -90,
                    cutout: '70%',
                    plugins: {
                        legend: {
                            display: false
                        },
                        tooltip: {
                            enabled: false
                        }
                    },
                    maintainAspectRatio: false
                }
            });
            
            // Disk Gauge
            const diskContext = document.getElementById('disk-gauge').getContext('2d');
            diskGauge = new Chart(diskContext, {
                type: 'doughnut',
                data: {
                    labels: ['Used', 'Free'],
                    datasets: [{
                        data: [0, 100],
                        backgroundColor: ['#28a745', '#e9ecef'],
                        borderWidth: 0
                    }]
                },
                options: {
                    circumference: 180,
                    rotation: -90,
                    cutout: '70%',
                    plugins: {
                        legend: {
                            display: false
                        },
                        tooltip: {
                            enabled: false
                        }
                    },
                    maintainAspectRatio: false
                }
            });
        }
        
        // Update gauge charts with new data
        function updateGauges(data) {
            // Update CPU gauge
            cpuGauge.data.datasets[0].data = [data.cpu.cpu_percent, 100 - data.cpu.cpu_percent];
            cpuGauge.update();
            
            // Update Memory gauge
            memoryGauge.data.datasets[0].data = [data.memory.percent, 100 - data.memory.percent];
            memoryGauge.update();
            
            // Update Disk gauge
            diskGauge.data.datasets[0].data = [data.disk.main_disk.percent, 100 - data.disk.main_disk.percent];
            diskGauge.update();
        }
        
        // Update the system information panel
        function updateSystemInfo(data) {
            const sysInfo = data.system;
            let html = `
                <p><strong>OS:</strong> ${sysInfo.system} ${sysInfo.release}</p>
                <p><strong>Hostname:</strong> ${sysInfo.node}</p>
                <p><strong>Architecture:</strong> ${sysInfo.machine}</p>
                <p><strong>Processor:</strong> ${sysInfo.processor}</p>
            `;
            $("#system-details").html(html);
        }
        
        // Update CPU information
        function updateCpuInfo(data) {
            const cpuInfo = data.cpu;
            let html = `
                <div class="text-center mb-3">
                    <span class="display-4">${cpuInfo.cpu_percent}%</span>
                </div>
                <p><strong>CPU Count:</strong> ${cpuInfo.cpu_count}</p>
                <p><strong>CPU Frequency:</strong> ${cpuInfo.cpu_freq} MHz</p>
            `;
            $("#cpu-info").html(html);
            
            // Per CPU display
            let perCpuHtml = `<h6>Per CPU Usage:</h6>`;
            cpuInfo.per_cpu.forEach((usage, index) => {
                perCpuHtml += `
                <div class="mb-1">
                    <small>CPU ${index}:</small>
                    <div class="progress">
                        <div class="progress-bar ${getProgressBarColor(usage)}" 
                             role="progressbar" 
                             style="width: ${usage}%" 
                             aria-valuenow="${usage}" 
                             aria-valuemin="0" 
                             aria-valuemax="100">
                            ${usage.toFixed(1)}%
                        </div>
                    </div>
                </div>
                `;
            });
            $("#per-cpu").html(perCpuHtml);
        }
        
        // Update Memory information
        function updateMemoryInfo(data) {
            const memInfo = data.memory;
            let html = `
                <div class="text-center mb-3">
                    <span class="display-4">${memInfo.percent}%</span>
                </div>
                <p><strong>Total:</strong> ${memInfo.total_formatted}</p>
                <p><strong>Used:</strong> ${memInfo.used_formatted}</p>
                <p><strong>Available:</strong> ${memInfo.available_formatted}</p>
                <div class="progress">
                    <div class="progress-bar bg-warning" 
                         role="progressbar" 
                         style="width: ${memInfo.percent}%" 
                         aria-valuenow="${memInfo.percent}" 
                         aria-valuemin="0" 
                         aria-valuemax="100">
                        ${memInfo.percent}%
                    </div>
                </div>
            `;
            $("#memory-info").html(html);
        }
        
        // Update Disk information
        function updateDiskInfo(data) {
            const diskInfo = data.disk.main_disk;
            let html = `
                <div class="text-center mb-3">
                    <span class="display-4">${diskInfo.percent}%</span>
                </div>
                <p><strong>Total:</strong> ${diskInfo.total_formatted}</p>
                <p><strong>Used:</strong> ${diskInfo.used_formatted}</p>
                <p><strong>Free:</strong> ${diskInfo.free_formatted}</p>
                <div class="progress">
                    <div class="progress-bar bg-success" 
                         role="progressbar" 
                         style="width: ${diskInfo.percent}%" 
                         aria-valuenow="${diskInfo.percent}" 
                         aria-valuemin="0" 
                         aria-valuemax="100">
                        ${diskInfo.percent}%
                    </div>
                </div>
            `;
            $("#disk-info").html(html);
            
            // Partitions info
            if (data.disk.partitions.length > 0) {
                let partitionsHtml = `<h6>Disk Partitions:</h6>`;
                data.disk.partitions.forEach(partition => {
                    partitionsHtml += `
                    <div class="mb-2">
                        <small>${partition.mountpoint} (${partition.fstype}):</small>
                        <div class="progress">
                            <div class="progress-bar bg-success" 
                                role="progressbar" 
                                style="width: ${partition.percent}%" 
                                aria-valuenow="${partition.percent}" 
                                aria-valuemin="0" 
                                aria-valuemax="100">
                                ${partition.percent}%
                            </div>
                        </div>
                        <small>${partition.used_formatted} of ${partition.total_formatted}</small>
                    </div>
                    `;
                });
                $("#disk-partitions").html(partitionsHtml);
            }
        }
        
        // Update Network information
        function updateNetworkInfo(data) {
            const netInfo = data.network.total;
            let html = `
                <h5 class="mb-3">Network Traffic</h5>
                <p><strong>Total Sent:</strong> ${netInfo.bytes_sent_formatted}</p>
                <p><strong>Total Received:</strong> ${netInfo.bytes_recv_formatted}</p>
                <p><strong>Packets Sent:</strong> ${netInfo.packets_sent.toLocaleString()}</p>
                <p><strong>Packets Received:</strong> ${netInfo.packets_recv.toLocaleString()}</p>
            `;
            $("#network-info").html(html);
            
            // Network interfaces
            if (data.network.interfaces.length > 0) {
                let interfacesHtml = `<h6>Network Interfaces:</h6>`;
                data.network.interfaces.forEach(iface => {
                    interfacesHtml += `
                    <div class="mb-2">
                        <p><strong>${iface.name}</strong> (${iface.speed} Mbps, MTU: ${iface.mtu})</p>
                        <p>Sent: ${iface.bytes_sent_formatted} | Received: ${iface.bytes_recv_formatted}</p>
                    </div>
                    `;
                });
                $("#network-interfaces").html(interfacesHtml);
            }
        }
        
        // Update Processes table
        function updateProcesses(data) {
            const processes = data.processes;
            let tableHtml = "";
            
            processes.forEach(proc => {
                tableHtml += `
                <tr>
                    <td>${proc.pid}</td>
                    <td title="${proc.name}">${proc.name.length > 15 ? proc.name.substring(0, 15) + '...' : proc.name}</td>
                    <td>${proc.username}</td>
                    <td>${proc.cpu_percent.toFixed(1)}%</td>
                    <td>${proc.memory_percent.toFixed(1)}%</td>
                    <td>${proc.memory_rss}</td>
                </tr>
                `;
            });
            
            $("#processes-body").html(tableHtml);
        }
        
        // Get color for progress bar based on value
        function getProgressBarColor(value) {
            if (value < 60) return "bg-success";
            if (value < 85) return "bg-warning";
            return "bg-danger";
        }
        
        // Refresh data from API
        function refreshData() {
            $.ajax({
                url: '/api/system_info',
                type: 'GET',
                dataType: 'json',
                success: function(data) {
                    // Update last update time
                    $("#last-update").text(data.timestamp);
                    
                    // Update all components
                    updateSystemInfo(data);
                    updateCpuInfo(data);
                    updateMemoryInfo(data);
                    updateDiskInfo(data);
                    updateNetworkInfo(data);
                    updateProcesses(data);
                    updateGauges(data);
                },
                error: function() {
                    console.error("Failed to fetch system information");
                }
            });
        }
        
        // Document ready
        $(document).ready(function() {
            // Initialize charts
            initCharts();
            
            // Initial data load
            refreshData();
            
            // Set up refresh timer
            let refreshInterval = parseInt($("#refresh-rate").val());
            let refreshTimer = setInterval(refreshData, refreshInterval);
            
            // Handle refresh rate change
            $("#refresh-rate").change(function() {
                clearInterval(refreshTimer);
                refreshInterval = parseInt($(this).val());
                refreshTimer = setInterval(refreshData, refreshInterval);
            });
        });
    </script>
</body>
</html>
    '''
    
    with open('templates/index.html', 'w') as f:
        f.write(index_html)

if __name__ == '__main__':
    create_templates()
    print("System Monitor Dashboard is starting...")
    print("Access the dashboard at http://localhost:5000")
    app.run(debug=True, host='0.0.0.0')