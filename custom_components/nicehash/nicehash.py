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

    async def request(self, method, path, query, body):
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
            body_json = json.dumps(body)
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
        if query:
            url += "?" + query

        if self.verbose:
            print(method, url)

        response = {}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                if response.content:
                    raise Exception(
                        str(response.status_code)
                        + ": "
                        + response.reason
                        + ": "
                        + str(response.content)
                    )
                raise Exception(str(response.status_code) + ": " + response.reason)

    async def get_mining_address(self):
        """Return the mining address"""
        return await self.request("GET", "/main/api/v2/mining/miningAddress", "", None)

    async def get_rigs_data(self):
        """Return the rigs object"""
        return await self.request("GET", "/main/api/v2/mining/rigs2", "", None)

    def get_epoch_ms_from_now(self):
        """Return epoch from now"""
        now = datetime.now()
        now_ec_since_epoch = mktime(now.timetuple()) + now.microsecond / 1000000.0
        return int(now_ec_since_epoch * 1000)
