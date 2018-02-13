import asyncio
import random
import string
import sys
from aiozk import ZKClient
from aiozk.exc import NoNode
from aiozk.protocol import AuthRequest


class ZookeeperDriver:

    def __init__(self, servers, working_path=None, auth=None):
        self._servers = servers
        self._working_path = working_path or '/vmgr'
        if auth is not None:
            self._auth = {
                'scheme': auth.get('scheme', 'digest'),
                'auth': auth.get('credentials', 'vmgr:vmgr'),
            }
        else:
            self._auth = None
        self._zk = None

    async def _assure_connected(self):
        if self._zk is None:
            self._zk = ZKClient(servers=self._servers, chroot=self._working_path)
        await self._zk.start()
        if self._auth is not None:
            auth_req = AuthRequest(type=0, **self._auth)
            await self._zk.send(auth_req)

    async def set_runtime_data(self, preset_name, data):
        await self._assure_connected()
        try:
            await self._zk.set_data(preset_name, data)
        except NoNode:
            await self._zk.create(preset_name)
            await self._zk.set_data(preset_name, data)

    async def get_runtime_data(self, preset_name):
        await self._assure_connected()
        res = await self._zk.get_data(preset_name)
        return res.decode('utf-8')


async def simple_test(servers, working_path=None, credentials=None):
    if credentials:
        auth = {'credentials': credentials}

    preset_name = 'TEST-zk-vmgr'
    print(f'Simple test with preset: {preset_name}')

    print(f'Creating driver: {servers} {working_path} {credentials}')
    driver = ZookeeperDriver(servers, working_path, auth)
    try:
        res = await driver.get_runtime_data(preset_name)
        print(f'Old data: {res}')
    except Exception:
        print('No node/data yet')

    data = ''.join(random.choices(string.ascii_uppercase + string.digits, k=32))
    print(f'Setting new random data {data}')
    await driver.set_runtime_data(preset_name, data)
    res = await driver.get_runtime_data(preset_name)
    print(f'Fetched data {res}')
    assert res == data
    print('Everything\'s ok')


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    future = simple_test(*sys.argv[1:])
    loop.run_until_complete(future)
