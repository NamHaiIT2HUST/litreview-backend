@echo off
cd /d "d:\AI Thực chiến\Project\P-165"
".venv\Scripts\python.exe" -u "tmp\check_ports.py" > "tmp\check_ports_out.txt" 2>&1
