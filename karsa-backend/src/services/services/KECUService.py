import asyncio

from karsaecu.app import KarsaClient
from karsaecu.meas import KarsaMeasClient

from karsalib.client import BaseClientNamespace, BaseServiceClient
from karsalib.util import parse_cmd_args


kecu = None


class KECU():
    def __init__(self) -> None:
        self._app = KarsaClient()
        self._meas = KarsaMeasClient()
        self.nodes = {}

    async def connect(self):
        await self._app.connect()
        await self._meas.connect()

    async def initialize(self):
        await self._app.get_node_list()
        self.nodes = self._app._node_dict
        # for node_id, node in self._app._node_dict.items():
        #     node.start_measurement(interval=10)

    async def wait_for_notification(self):
        return await self._meas.get_data()



class KECUServiceNamespace(BaseClientNamespace):
    """ python-socket.io client namespace for connecting to Router """

    endpoints = []


class KECUServiceClient(BaseServiceClient):
    async def init_service(self):
        global kecu

        kecu = KECU()
        await kecu.connect()
        await kecu.initialize()

    async def service_main():
        global kecu

        while True:
            node_id, ntf, data = await kecu.wait_for_notification()
            # Notify app
            ntf_handler = getattr(kecu._app, 'on_{}'.format(ntf))
            await ntf_handler(node_id)
            # Notify node
            ntf_handler = getattr(kecu.nodes[node_id], 'on_{}'.format(ntf))
            await ntf_handler(data)


def run():
    args = parse_cmd_args()
    client = KECUServiceClient(args['url'],
                               args['port'],
                               (args['ns'], KECUServiceNamespace)
                               )
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(client.run())
    except KeyboardInterrupt:
        print(f"KeyboardInterrupt for {client.__class__.__name__}")
    except Exception as e:
        print(f"Exception '{str(e)}' for {client.__class__.__name__}")
    finally:
        print(f'Service stopped.')



if __name__=='__main__':
    run()