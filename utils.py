from datetime import datetime
from colorama import Fore
import paramiko
import time
import sqlite3
import os, httpx

RED = Fore.RED
GREEN = Fore.GREEN
BLUE = Fore.BLUE
YELLOW = Fore.YELLOW
CYAN = Fore.CYAN
WHITE = Fore.WHITE
GRAY = Fore.WHITE

STAR = "-"

vps_ip, vps_user, vps_pass, prefix, queue_channel_id, queue_message_id, success_msg_channel, send_success_msg, embed_success_msg, ping_role, success_msg, token, vps_delay, tempo_path, main_token, tempo_executable = "", "", "", ".", 1, 1, 1, True, True, True, "", "", 0, "/root/sniper/", "/root/sniper/data/", "Tempo"
velocity_folder_name = list(filter(None, tempo_path.split("/")))[-1]

def get_config():
    try:
        with sqlite3.connect("queue.db") as db:
            cursor = db.execute("SELECT key, value FROM config")
            rows = cursor.fetchall()
            return rows
        db.close()
    except:
        log("Issue with database", RED)
        os._exit(1)


def log(text=None, color="", doInput=False, end=True):
    if text is None:
        print()
        return

    now = datetime.now()

    second = now.second
    minute = now.minute
    hour = now.hour

    if second < 10:
        second = "0" + str(second)
    if minute < 10:
        minute = "0" + str(minute)
    if hour < 10:
        hour = "0" + str(hour)

    time = f"{hour}:{minute}:{second}"

    if doInput:
        if end:
            print(f"{BLUE}{time} {WHITE}{STAR} {color}{text}{WHITE}")
        else:
            print(f"{BLUE}{time} {WHITE}{STAR} {color}{text}{WHITE}", end="")
        try:
            return input("")
        except KeyboardInterrupt:
            os._exit(1)

    if end:
        print(f"{BLUE}{time} {WHITE}{STAR} {color}{text}{WHITE}")
    else:
        print(f"{BLUE}{time} {WHITE}{STAR} {color}{text}{WHITE}", end="")

def update_token(token):
    with sqlite3.connect("queue.db") as db:
        cursor = db.execute("SELECT * FROM vps")
        rows = cursor.fetchall()
        for row in rows:
            print("Updating VPS:", row[0], row[1], row[2])
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(row[0], username=row[1], password=row[2])
            stdin, stdout, stderr = client.exec_command(
                f"echo '{token}' > {main_token}mainToken.txt"
            )
            stdin.close()
    db.close()


def restart():
    with sqlite3.connect("queue.db") as db:
        cursor = db.execute("SELECT * FROM vps")
        rows = cursor.fetchall()
        for row in rows:
            try:
                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                client.connect(row[0], username=row[1], password=row[2])
                client.exec_command('screen -XS tempo quit')
                time.sleep(2)
                stdin, stdout, stderr = client.exec_command(
                    f"screen -dmS tempo bash -c 'cd {tempo_path} && ./{tempo_executable}; exec bash'"
                )
                time.sleep(vps_delay)
            except:
                log(f"Failed to restart {row[0]}")
                continue
    db.close()

def getstats():
    stats=[]
    with sqlite3.connect("queue.db") as db:
        cursor = db.execute("SELECT * FROM vps")
        rows = cursor.fetchall()
        for row in rows:
            try:
                stats.append(httpx.get(f'https://genefit.to/velocity/api/stats?key={row[3]}'))
            except httpx.HTTPError as exc:
                log(f"Failed to get stats from {row[0]}")
                continue
    db.close()
    currentstats={'total_servers':0,'alts':0}
    for i in range(len(stats)):
        print(1)
        currentstats['total_servers']+=stats[i].json()['total_servers']
        print(2)
        currentstats['alts']+=stats[i].json()['alts']
        print(3)
    return currentstats

def get_txids(address, currency):
    try:
        data = httpx.get(
            f"https://api.blockcypher.com/v1/{currency.lower()}/main/addrs/{address}/full"
        ).json()
        txids = []
        for tx in data["txs"]:
            hash = tx["hash"]
            inputs = [x["addresses"][0] for x in tx["inputs"]]
            if address in inputs:
                continue  # is not sent to address but sent by address
            value = tx["outputs"][-1]["value"] / 100000000
            txids.append([hash, value])
        return txids
    except Exception as E:
        log(f"Invalid Address : {address} ({E})")
        return None


def get_confirmations(txid, currency):
    try:
        data = httpx.get(
            f"https://api.blockcypher.com/v1/{currency.lower()}/main/txs/{txid}"
        ).json()
        return data["confirmations"]
    except Exception as E:
        log(data)
        log(f"Confirmation Check Error : {E}")
        return 0


def load_config():
    for key, value in get_config():
        if value is None: value = None
        if isinstance(value, str):
            if value.lower() == "true": value = True
            elif value.lower() == "false": value = False
        globals().__setitem__(key, value)


load_config()
