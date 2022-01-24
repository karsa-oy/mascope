import asyncio

HOST, PORT = '0.0.0.0', 65146


class SyslogProtocol(asyncio.DatagramProtocol):
    def __init__(self):
        super().__init__()

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        # Here is where you would push message to whatever methods/classes you want.
        print(f"Received Syslog message: {data}")


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    t = loop.create_datagram_endpoint(SyslogProtocol, local_addr=(HOST, PORT))
    loop.run_until_complete(t) # Server starts listening
    loop.run_forever()