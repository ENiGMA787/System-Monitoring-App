# Title: System Monitoring Tool

# Abstract:
The System Monitoring Tool is a Python-based application designed to allow users to monitor their system's CPU and memory usage in real-time. It provides a web-based interface through which users can access current usage statistics as well as historical data for analysis. The tool incorporates features such as real-time monitoring using the 'psutil' library, a warning system for high CPU or memory usage, and a user-friendly web interface created using the Flask web framework.

# Table of Contents:

Introduction
Project Overview
System Architecture
Key Features
Technologies Used
Implementation
User Guide
Conclusion
Future Work
References

1. Introduction:
In today's computing environment, it's essential for users to have visibility into their system's resource utilization. Whether it's a personal computer or a server in a data center, monitoring CPU and memory usage in real-time can help identify performance bottlenecks, prevent system crashes, and optimize resource allocation. The System Monitoring Tool addresses this need by providing users with a simple yet effective way to monitor their system's performance.

2. Project Overview:
The System Monitoring Tool is a final semester project developed as part of the Bachelor of Technology (B Tech) program. The project aims to demonstrate the practical application of Python programming, web development, and system monitoring concepts. By creating a user-friendly interface for monitoring CPU and memory usage, the project showcases how modern technologies can be leveraged to enhance system administration tasks.

3. System Architecture:
The architecture of the System Monitoring Tool consists of several components:

Python script for collecting system metrics using the 'psutil' library.
Flask web framework for creating the web-based interface.
HTML, CSS, and JavaScript for designing the user interface.
Chart.js for visualizing usage statistics.
Flask-Session for managing user sessions.

4. Key Features:

Real-time monitoring of CPU and memory usage.
Warning system for high CPU or memory usage.
Web interface for accessing usage statistics.
Historical data analysis.

5. Technologies Used:
The project is built using the following technologies:

Python
Flask
psutil
Chart.js
Flask-Session
HTML
CSS
JavaScript

6. Implementation:
The implementation of the System Monitoring Tool involves writing Python scripts to collect system metrics, creating web pages using HTML, CSS, and JavaScript, and integrating everything together using the Flask web framework. The 'psutil' library is used to fetch real-time CPU and memory usage information, while Chart.js is utilized for visualizing the data on the web interface.

7. User Guide:
To use the System Monitoring Tool, follow these steps:

Install Python, Flask, psutil, and Flask-Session.
Clone the project repository.
Navigate to the project directory and run the command: python3 app.py.
Open a web browser and go to http://localhost:5000/.
Register or log in to access the monitoring dashboard.
Monitor your system's CPU and memory usage in real-time and analyze historical data as needed.

8. Conclusion:
The System Monitoring Tool provides users with a convenient way to monitor their system's performance in real-time. By leveraging Python and web development technologies, the project demonstrates how modern tools can be used to simplify system administration tasks and improve overall system reliability.

9. Future Work:
Future enhancements to the System Monitoring Tool could include:

Adding support for monitoring additional system metrics such as disk usage, network activity, etc.
Implementing advanced data visualization techniques for better analysis.
Enhancing the user interface for improved usability and accessibility.
Adding support for notifications/alerts when critical thresholds are exceeded.

10. References:

psutil documentation: https://psutil.readthedocs.io/
Flask documentation: https://flask.palletsprojects.com/
Chart.js documentation: https://www.chartjs.org/docs/latest/
Flask-Session documentation: https://pythonhosted.org/Flask-Session/
This concludes the project report for the System Monitoring Tool.
