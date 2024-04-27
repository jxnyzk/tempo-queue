import auth.system
import auth.enc
import requests
import binascii
import json
import hashlib


aes = auth.enc.AESCipher()

def Auth(key):
    hwid = auth.system.GetCpuID()
    enc = binascii.hexlify(aes.encrypt('{"license": "%s", "hwid": "%s", "program": "QBOT"}' % (key, hwid)))
    res = requests.post('https://auth.spellman.vip:443/hwid', data=enc)

    res = aes.decrypt(binascii.unhexlify(res.text))

    res = json.loads(res)

    if not res["success"]:
        print("[-] Invalid license")
        return False
    

    hash = hashlib.md5(enc).hexdigest()

    if res["hash"] != hash:
        print("[-] Invalid hwid")
        return False
    
    return res["user"]