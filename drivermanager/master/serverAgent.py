import asyncio
from webServer import *
from httpServer import *
from serverConfig import *
from osManager import *
class ServerAgent:
    def __init__(self, host, web_port, http_port):
        self.http = HttpServer(host, http_port)
        self.web = WebServer(host, web_port)
        self.http.setup_post('/install-drivers', self.install_drivers)
    
    # Запуск приложения
    async def start(self):
        await asyncio.gather(self.web.start(), self.http.start())

    def terminate(self):
        self.web.terminate()
        self.http.terminate()
        
    # POST-эндпоинт для уведомления мастера от UI
    async def install_drivers(self, request):
        data = await request.json()
        print(request)
        files = data['files']
        response = ""
        for file in files:
            i = await self.web.broadcast(json.dumps({'file': file}), target_os(file))
            response += f"File \"{file}\" sent to {i} clients\n"
        return web.Response(text=response, status=200)