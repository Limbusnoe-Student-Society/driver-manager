import asyncio
import websockets
import json

class WebServer:
    def __init__(self, host = 'localhost', port=8765):
        self.host = host
        self.port = port
        self.connected_clients = set()
        self.client_os = dict()

    # Отправка TCP-пейлоада всем сокетам с подходящей ОС   
    async def broadcast(self, message, targetOs):
        sent = 0
        tasks = list()
        for client in self.connected_clients:
            if(self.client_os[id(client)] in targetOs):
                task = asyncio.create_task(client.send(message))
                tasks.append(task)
                sent+=1
        await asyncio.gather(*tasks)
        return sent
        
    # Обработка подключения сокета к серверу
    async def handle(self, websocket):
        self.connected_clients.add(websocket)
        client_id = id(websocket)
        print(f"Client {client_id} connected")
        try:
            async for message in websocket:
                json_msg = json.loads(message)
                await self.handle_handshake(client_id, json_msg)
        except websockets.exceptions.ConnectionClosed:
            print(f"Client {client_id} disconnected")
        except json.decoder.JSONDecodeError:
            print(f"Client {client_id} sent non-JSON message. Ignored")
        finally:
            self.connected_clients.remove(websocket)
            self.client_os.pop(client_id, None)
    async def handle_handshake(self, client_id, json):
        if 'os' in json:
            os = json['os']
            self.client_os[client_id] = os
            print(f"Client {client_id} sent OS: {os}")
    # Запуск веб сервера
    async def start(self):
        self.server = await websockets.serve(self.handle, self.host, self.port)
        print(f"Web server started at {self.host}:{self.port}")
        await self.server.serve_forever()

    async def terminate(self):
        self.server.close()
