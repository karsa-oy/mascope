import asyncio


class KarsaMeasProtocol(asyncio.DatagramProtocol):
    def __init__(self):
        super().__init__()

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        # Here is where you would push message to whatever methods/classes you want.
        print(f"Received Syslog message: {data}")


if __name__ == '__main__':
    from KECU import KECU_UDP_HOST, KECU_UDP_PORT

    loop = asyncio.get_event_loop()
    t = loop.create_datagram_endpoint(
                        KarsaMeasProtocol,
                        local_addr=(KECU_UDP_HOST, KECU_UDP_PORT)
                        )
    loop.run_until_complete(t) # Server starts listening
    loop.run_forever()