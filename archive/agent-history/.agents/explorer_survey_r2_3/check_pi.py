import paramiko
import sys

sys.stdout.reconfigure(encoding='utf-8')
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.118', 22, 'pi5', '123456', timeout=5)

cmds = [
    'ls -la /var/lib/iot-drone',
    'ls -la /var/lib/iot-drone/maps',
    'cd /home/pi5/iot-drone && git status 2>&1',
    'cd /home/pi5/iot-drone && git log -n 10 --oneline 2>&1',
    'find /home/pi5 -name ".git" 2>/dev/null',
    'find /var/lib/iot-drone -type f 2>/dev/null',
]

for cmd in cmds:
    print('=== ' + cmd + ' ===')
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    if out:
        print(out)
    err = stderr.read().decode('utf-8', errors='replace').strip()
    if err:
        print('ERR: ' + err)
ssh.close()
