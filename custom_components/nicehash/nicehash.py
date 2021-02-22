""" Implementation of the NiceHash API """

from datetime import datetime
from time import mktime
import uuid
import hmac
import json
from hashlib import sha256
import aiohttp


class NiceHashPrivateAPI:
    """ Implementation of the API calls """

    def __init__(self, host, organisation_id, key, secret, verbose=False):
        """Init the API"""
        self.key = key
        self.secret = secret
        self.organisation_id = organisation_id
        self.host = host
        self.verbose = verbose

    async def request(self, method, path, query="", query2=None, body=None):
        """NiceHash API Request"""

        xtime = self.get_epoch_ms_from_now()
        xnonce = str(uuid.uuid4())

        message = bytearray(self.key, "utf-8")
        message += bytearray("\x00", "utf-8")
        message += bytearray(str(xtime), "utf-8")
        message += bytearray("\x00", "utf-8")
        message += bytearray(xnonce, "utf-8")
        message += bytearray("\x00", "utf-8")
        message += bytearray("\x00", "utf-8")
        message += bytearray(self.organisation_id, "utf-8")
        message += bytearray("\x00", "utf-8")
        message += bytearray("\x00", "utf-8")
        message += bytearray(method, "utf-8")
        message += bytearray("\x00", "utf-8")
        message += bytearray(path, "utf-8")
        message += bytearray("\x00", "utf-8")
        message += bytearray(query, "utf-8")

        if body:
            body_json = json.dumps(body, separators=(",", ":"))
            message += bytearray("\x00", "utf-8")
            message += bytearray(body_json, "utf-8")

        digest = hmac.new(bytearray(self.secret, "utf-8"), message, sha256).hexdigest()
        xauth = self.key + ":" + digest

        headers = {
            "X-Time": str(xtime),
            "X-Nonce": xnonce,
            "X-Auth": xauth,
            "Content-Type": "application/json",
            "X-Organization-Id": self.organisation_id,
            "X-Request-Id": str(uuid.uuid4()),
        }

        url = self.host + path

        if self.verbose:
            print(method, url)

        async with aiohttp.ClientSession(headers=headers) as session:
            if method == "GET":
                async with session.get(url, params=query2) as response:
                    if response.status == 200:
                        return await response.json()
                    if response.content:
                        raise Exception(
                            str(response.status)
                            + ": "
                            + response.reason
                            + ": "
                            + str(await response.text())
                        )
                    raise Exception(str(response.status) + ": " + response.reason)
            if method == "POST":
                async with session.post(
                    url, data=json.dumps(body, separators=(",", ":"))
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    if response.content:
                        raise Exception(
                            str(response.status)
                            + ": "
                            + response.reason
                            + ": "
                            + str(await response.text())
                        )
                    raise Exception(str(response.status) + ": " + response.reason)

    async def get_mining_address(self):
        """Return the mining address"""
        return await self.request("GET", "/main/api/v2/mining/miningAddress")

    async def get_rigs_data(self):
        """Return the rigs object"""
        return await self.request("GET", "/main/api/v2/mining/rigs2")

    async def get_account_data(self, fiat="USD"):
        """Return the account object"""
        return await self.request(
            "GET",
            "/main/api/v2/accounting/accounts2",
            "fiat={}".format(fiat),
            {"fiat": fiat},
        )

    async def set_rig_status(self, rig_id: str, status: bool):
        """Set a rig status"""
        action = "START" if status else "STOP"
        return await self.request(
            "POST",
            "/main/api/v2/mining/rigs/status2",
            "",
            None,
            {"rigId": rig_id, "action": action},
        )

    def get_epoch_ms_from_now(self):
        """Return epoch from now"""
        now = datetime.now()
        now_ec_since_epoch = mktime(now.timetuple()) + now.microsecond / 1000000.0
        return int(now_ec_since_epoch * 1000)
