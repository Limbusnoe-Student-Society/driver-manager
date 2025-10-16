import asyncio
import json
from aiohttp import web

class HttpServer:
    def __init__(self, host = 'localhost', http_port=8766):
        self.host = host
        self.http_port = http_port
        self.http_app = web.Application()

    # Регистрация HTTP-эндпоинтов
    def setup_post(self, name, handler):
        self.http_app.router.add_post(name, handler)
        
    # Запуск HTTP сервера
    async def start(self):
        self.runner = web.AppRunner(self.http_app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, self.host, self.http_port)
        await self.site.start()
        print(f"HTTP server started at {self.host}:{self.http_port}")
    
    async def terminate(self):
        self.runner.shutdown()
        self.site.stop()