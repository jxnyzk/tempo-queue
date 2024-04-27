import auth.auth

if not auth.auth.Auth(open("key.txt").read().split("\n")[0]):
    exit()
    raise SystemExit
    int("Invalid License")


import warnings
warnings.filterwarnings(action='ignore',module='.*paramiko.*')
import re, ctypes, requests, sys, os, ssl, binascii, json, time, platform, subprocess, uuid
from base64 import b64decode
from uuid import uuid4
from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto.Util.Padding import pad, unpad
from colorama import Fore


##
from flask import Flask, request
from flask import render_template, redirect, url_for
import glob
import sqlite3
import socket
from utils import update_token, log, RED, GREEN, get_txids
import logging
from bot import start
import threading
from gevent.pywsgi import WSGIServer

HTTPResponse = requests.packages.urllib3.response.HTTPResponse
orig_HTTPResponse__init__ = HTTPResponse.__init__


def new_HTTPResponse__init__(self, *args, **kwargs):
    orig_HTTPResponse__init__(self, *args, **kwargs)
    try:
        self.peercert = self._connection.sock.getpeercert()
    except AttributeError:
        pass


HTTPResponse.__init__ = new_HTTPResponse__init__

HTTPAdapter = requests.adapters.HTTPAdapter
orig_HTTPAdapter_build_response = HTTPAdapter.build_response


def new_HTTPAdapter_build_response(self, request, resp):
    response = orig_HTTPAdapter_build_response(self, request, resp)
    try:
        response.peercert = resp.peercert
    except AttributeError:
        pass
    return response


HTTPAdapter.build_response = new_HTTPAdapter_build_response

ctx = ssl.SSLContext(protocol=ssl.PROTOCOL_TLS)


class others:
    @staticmethod
    def get_hwid():
        if platform.system() != "Windows":
            return "None"

        cmd = subprocess.Popen(
            "wmic useraccount where name='%username%' get sid",
            stdout=subprocess.PIPE,
            shell=True)

        (suppost_sid, error) = cmd.communicate()

        suppost_sid = suppost_sid.split(b'\n')[1].strip()

        return suppost_sid.decode()



def doExit():
    try:
        input("")
    except:
        pass

    sys.exit(0)


def vmcheck():
    def get_base_prefix_compat():
        return getattr(sys, "base_prefix", None) or getattr(
            sys, "real_prefix", None) or sys.prefix

    def in_virtualenv():
        return get_base_prefix_compat() != sys.prefix

    if in_virtualenv() == True:
        os._exit(1)

    else:
        pass

    def registry_check():
        reg1 = os.system(
            "REG QUERY HKEY_LOCAL_MACHINE\\SYSTEM\\ControlSet001\\Control\\Class\\{4D36E968-E325-11CE-BFC1-08002BE10318}\\0000\\DriverDesc 2> nul"
        )
        reg2 = os.system(
            "REG QUERY HKEY_LOCAL_MACHINE\\SYSTEM\\ControlSet001\\Control\\Class\\{4D36E968-E325-11CE-BFC1-08002BE10318}\\0000\\ProviderName 2> nul"
        )

        if reg1 != 1 and reg2 != 1:
            os._exit(1)

    def processes_and_files_check():
        vmware_dll = os.path.join(os.environ["SystemRoot"],
                                  "System32\\vmGuestLib.dll")
        virtualbox_dll = os.path.join(os.environ["SystemRoot"],
                                      "vboxmrxnp.dll")

        process = os.popen(
            'TASKLIST /FI "STATUS eq RUNNING" | find /V "Image Name" | find /V "="'
        ).read()
        processList = []
        for processNames in process.split(" "):
            if ".exe" in processNames:
                processList.append(
                    processNames.replace("K\n", "").replace("\n", ""))

        if "VMwareService.exe" in processList or "VMwareTray.exe" in processList:
            os._exit(1)

        if os.path.exists(vmware_dll):
            os._exit(1)

        if os.path.exists(virtualbox_dll):
            os._exit(1)

        try:
            ctypes.cdll.LoadLibrary("SbieDll.dll")
            os._exit(1)
        except:
            pass

    def mac_check():
        mac_address = ':'.join(re.findall('..', '%012x' % uuid.getnode()))
        vmware_mac_list = ["00:05:69", "00:0c:29", "00:1c:14", "00:50:56"]
        if mac_address[:8] in vmware_mac_list:
            os._exit(1)

    try:
        processes_and_files_check()
        mac_check()
    except:
        pass


#vmcheck()

stop = False
if not os.path.isfile("bot_token.txt"):
    stop = True
    open("bot_token.txt", "w+").write("")
    print("Please put your bot's token in bot_token.txt")
if not os.path.isfile("txids.txt"):
    open("txids.txt", "w+").write("")
if not os.path.isfile("sessions.txt"):
    open("sessions.txt", "w+").write("")
if os.path.isfile("bot_token.txt") and len(open("bot_token.txt",
                                                "r").read()) < 5:
    stop = True
    print("Please put your bot's token in bot_token.txt")
if stop:
    os._exit(1)

if getattr(sys, 'frozen', False):
    dir_path = os.path.abspath(sys.executable)
else:
    dir_path = os.path.abspath(__file__)

if "/" in dir_path:
    slash = "/"
elif "\\" in dir_path:
    slash = "\\"

try:
    os.chdir(dir_path)
except:
    os.chdir(slash.join(dir_path.split(slash)[:-1]))




logging.getLogger('werkzeug').disabled = True  # Disable Flask Logs
os.environ['WERKZEUG_RUN_MAIN'] = 'true'

vars = {}
for x in glob.glob("static/html/*"):
    vars[x.split(".")[0].split("/")[-1]] = open(x, "r").read()

app = Flask(__name__)

bot = None  # Ignore
login_token = open("bot_token.txt", "r").read().split(".")[-1]

log(f"WebApp URL: http://your_vps_ip")
log(f"Login Token: {login_token}")


def update_positions():
    with sqlite3.connect("queue.db") as db:
        cursor = db.execute("SELECT position FROM queue ORDER BY position")
        rows = cursor.fetchall()
        rows = [x[0] for x in rows]

        i = 0
        for row in rows:
            i += 1
            db.execute("UPDATE queue SET position = ? WHERE position = ?",
                       (i, row))
        db.commit()


def is_logged_in():
    sessions = open("sessions.txt", "r").read().splitlines()
    return request.remote_addr in sessions


@app.route("/login")
def _login():
    if is_logged_in(): return redirect(url_for('_index'))
    return render_template('login.html')


@app.route('/login/<path:path>')
def _login_update(path):
    path = path.split(" ")[0].split("\n")[0]
    lt = login_token.split(" ")[0].split("\n")[0]
    if path == lt:
        open("sessions.txt", "a").write(request.remote_addr + "\n")
    return redirect(url_for('_login'))


@app.route("/")
def _index():
    if not is_logged_in(): return redirect(url_for('_login'))
    return render_template('index.html')


@app.route("/config")
def _config():
    if not is_logged_in(): return redirect(url_for('_login'))
    with sqlite3.connect('queue.db') as db:
        cursor = db.cursor()
        data = []
        for row in cursor.execute(
                'SELECT key, value, title, desc, placeholder FROM config'):
            if row[-1] is None:
                continue
            data.append([x if x != None else "" for x in row])
        return render_template('config.html', len=len(data), data=data)


@app.route("/snipes")
def _snipes():
    if not is_logged_in(): return redirect(url_for('_login'))
    with sqlite3.connect('queue.db') as db:
        cursor = db.cursor()
        data = []
        i = 0
        for row in cursor.execute(
                'SELECT * FROM snipes ORDER BY rowid DESC LIMIT 8;'):
            i += 1
            type, delay, discord_id = row[0], row[1], row[2]
            data.append([i, type, delay, discord_id])
        return render_template('snipes.html', len=len(data), data=data)


@app.route("/payments")
def _payments():
    if not is_logged_in(): return redirect(url_for('_login'))
    with sqlite3.connect('queue.db') as db:
        cursor = db.cursor()
        data = []
        i = 0
        for row in cursor.execute(
                'SELECT * FROM payments ORDER BY rowid DESC LIMIT 8;'):
            i += 1
            txid, symbol, amount, sender, date = row[0], row[1], row[2], row[
                3], row[4]
            url = f"https://live.blockcypher.com/{symbol.lower()}/tx/{txid}"
            data.append([
                i, txid, symbol, amount,
                bot.get_user(int(sender)), date, url
            ])
        return render_template('payments.html', len=len(data), data=data)


@app.route("/queue")
def _queue():
    if not is_logged_in(): return redirect(url_for('_login'))
    with sqlite3.connect('queue.db') as db:
        cursor = db.cursor()
        data = []
        i = 0
        for row in cursor.execute('SELECT * FROM queue ORDER BY position'):
            i += 1
            userid, username, claims = row[0], bot.get_user(row[0]), row[1]
            data.append([i, username, userid, claims])
        return render_template('queue.html', len=len(data), data=data)


@app.route("/vps")
def _vps():
    if not is_logged_in(): return redirect(url_for('_login'))
    with sqlite3.connect('queue.db') as db:
        cursor = db.cursor()
        data = []
        for row in cursor.execute(
                'SELECT vps_ip, vps_user, vps_pass, api_key FROM vps ORDER BY rowid'
        ):
            data.append([x for x in row])
        return render_template('vps.html', len=len(data), data=data)


@app.route("/crypto")
def _crypto():
    if not is_logged_in(): return redirect(url_for('_login'))
    with sqlite3.connect('queue.db') as db:
        cursor = db.cursor()
        data = []
        for row in cursor.execute('SELECT symbol, address FROM crypto'):
            data.append([x if x != None else "" for x in row])
        return render_template('crypto.html', len=len(data), data=data)


@app.route("/<path:path>")
def catch_all(path):
    if not is_logged_in(): return redirect(url_for('_login'))

    def delete(pos):
        log(f"Deleting position : {pos}")
        with sqlite3.connect('queue.db') as db:
            db.execute("DELETE FROM queue WHERE position = ?", (pos, ))
            db.commit()
            update_positions()

            if pos == 1:
                cursor = db.execute("SELECT * FROM queue ORDER BY position")
                row = cursor.fetchone()
                token = row[2]
                log("Removed first user from queue, setting new main token")
                update_token(token)

    def edit(pos, claims):
        log(f"Editing position : {pos} for {claims} claims")
        with sqlite3.connect('queue.db') as db:
            db.execute("UPDATE queue SET queue_amount = ? WHERE position = ?",
                       (claims, pos))
            db.commit()

    def add(userid, claims, token):
        user = bot.get_user(userid)
        if user is None:
            log("Invalid User ID", RED)
        else:
            log(f"Adding row : {userid} - {claims} - {token}", GREEN)
            with sqlite3.connect('queue.db') as db:
                db.execute(
                    "INSERT INTO queue (discord_id, queue_amount, token, position) VALUES (?, ?, ?, (SELECT IFNULL(MAX(position) + 1, 1) FROM queue))",
                    (userid, claims, token))
                db.commit()
                log(f"{user} has been added to the queue for {claims} claims!")
                update_positions()

    def move(pos1, pos2):
        log(f"Moving {pos1} to {pos2}")
        with sqlite3.connect('queue.db') as db:
            db.execute(
                "UPDATE queue SET position = case when position = ? then ? else ? end WHERE position in (?,?)",
                (pos1, pos2, pos1, pos1, pos2))
            db.commit()
        update_positions()
        if int(pos1) == 1 or int(pos2) == 1:
            with sqlite3.connect('queue.db') as db:
                cursor = db.execute("SELECT * FROM queue ORDER BY position")
                row = cursor.fetchone()
                token = row[2]
                log("First position moved, setting new main token")
            update_token(token)

    def vps_add(vps_ip, vps_user, vps_pass, apikey):
        with sqlite3.connect('queue.db') as db:
            db.execute(
                "INSERT INTO vps (vps_ip, vps_user, vps_pass,api_key) VALUES (?, ?, ?, ?)",
                (vps_ip, vps_user, vps_pass, apikey))
            db.commit()
            log(f"{vps_ip} added")

    def vps_delete(rowid):
        with sqlite3.connect('queue.db') as db:
            cursor = db.cursor()
            data = []
            for row in cursor.execute(
                    'SELECT vps_ip, vps_user, vps_pass FROM vps ORDER BY rowid'
            ):
                data.append([x for x in row])
            vps_ip, vps_user, vps_pass = data[rowid]
            db.execute(
                "DELETE FROM vps WHERE vps_ip = ? AND vps_user = ? AND vps_pass = ?",
                (vps_ip, vps_user, vps_pass))
            db.commit()
            log(f"VPS ({rowid}) deleted")

    def config_edit(key, value):
        if key == "save-btn":
            return
        with sqlite3.connect('queue.db') as db:
            db.execute("UPDATE config SET value = ? WHERE key = ?",
                       (value, key))
            db.commit()
            log(f"Config : {key} -> {value}")

    def crypto_edit(symbol, address):
        if symbol == "save-btn":
            return
        with sqlite3.connect('queue.db') as db:
            db.execute("UPDATE crypto SET address = ? WHERE symbol = ?",
                       (address, symbol))
            db.commit()

            txids = open("txids.txt", "r").read().splitlines()
            txs = get_txids(address, symbol)
            if txs is None:
                db.execute("UPDATE crypto SET address = ? WHERE symbol = ?",
                           ("INVALID", symbol))
                db.commit()
                return
            for i in txs:
                txid = i[0]
                if txid not in txids:
                    open("txids.txt", "a").write(txid + "\n")

            log(f"Crypto : {symbol} -> {address}")

    splt = path.split("/")
    if path.startswith("delete/"):
        delete(int(splt[-1]))
    if path.startswith("edit/"):
        edit(int(splt[-2]), int(splt[-1]))
    if path.startswith("add/"):
        add(int(splt[-3]), int(splt[-2]), str(splt[-1]))
    if path.startswith("move/"):
        move(int(splt[-2]), int(splt[-1]))
    if path.startswith("vps_add/"):
        print(path)
        vps_add(splt[-4], splt[-3], splt[-2], splt[-1])
    if path.startswith("vps_delete/"):
        vps_delete(int(splt[-1]))
    if path.startswith("config_edit/"):
        config_edit(splt[-2], splt[-1])
    if path.startswith("crypto_edit/"):
        crypto_edit(splt[-2], splt[-1])

    return redirect(url_for('_index'))


def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


def set_bot(bot_inst):
    global bot
    bot = bot_inst


def run_app():
    #app.run("0.0.0.0", port=80)
    time.sleep(1)

    http_server = WSGIServer(('', 80), app, log=None)
    http_server.serve_forever()


threading.Thread(target=run_app).start()
start(set_bot)
