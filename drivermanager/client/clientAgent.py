import os
import json
import asyncio
import platform
import logging
import ssl
from typing import List, Optional
import websockets
from driverInstaller import install_drivers, install_driver, InstallResult

INSECURE_TLS = True
RECONNECT_DELAY_INITIAL = 5.0

class ClientAgent:
    logger = logging.getLogger("clientAgent")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s - %(message)s")

    def __init__(self, host: str = 'localhost', port: int = 8765):
        self.host = host
        self.port = port
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.running = False
        self.reconnectDelay = RECONNECT_DELAY_INITIAL
        self.currentOS = platform.system().lower()

        # build uri
        scheme = "ws"
        self.uri = f"{scheme}://{self.host}:{self.port}"

        # prepare ssl context if using wss
        self.ssl_context = None
        if scheme == "wss":
            if INSECURE_TLS:
                # Отключаем проверку сертификатов (НЕ рекомендовано для продакшна)
                self.ssl_context = ssl.create_default_context()
                self.ssl_context.check_hostname = False
                self.ssl_context.verify_mode = ssl.CERT_NONE
            else:
                self.ssl_context = ssl.create_default_context()

    async def connect(self) -> bool:
        try:
            self.logger.info("Connecting to master at %s", self.uri)
            self.websocket = await websockets.connect(self.uri, ssl=self.ssl_context)
            self.running = True
            # сразу отправляем информацию о клиенте
            await self.send({"os": self.currentOS})
            self.logger.info("Connected to %s", self.uri)
            return True
        except Exception as e:
            self.logger.warning("Error connecting to websocket: %s", e)
            self.websocket = None
            self.running = False
            return False

    async def handle_message(self, data: dict):
        """
        Ожидаемый формат сообщения:
        {
            "file": "path/to/driver.ext"
        }

        Клиент получает путь к одному файлу драйвера и выполняет установку.
        """
        try:
            # Получаем путь к файлу из JSON
            driver_path = data.get("file")

            # Проверяем наличие атрибута
            if not driver_path or not isinstance(driver_path, str):
                self.logger.warning("Invalid or missing 'file' attribute in payload")
                return
            self.logger.info(f"Starting installation of driver: {driver_path}")
            
            # Выполняем установку драйвера
            install_driver(driver_path)
        except Exception as e:
            self.logger.exception("Error handling driver installation")


    async def send(self, data: dict) -> bool:
        if self.websocket is None:
            self.logger.warning("WebSocket is not connected, cannot send")
            return False
        try:
            await self.websocket.send(json.dumps(data))
            return True
        except Exception as e:
            self.logger.exception("Error sending data: %s", e)
            return False

    async def receive_loop(self):
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                except json.JSONDecodeError:
                    self.logger.warning("Received non-json message: %s", message)
                    continue
                self.logger.info("Received message: %s", data)
                await self.handle_message(data)
        except websockets.exceptions.ConnectionClosed as e:
            self.logger.info("Connection closed: %s", e)
            self.running = False
        except Exception as e:
            self.logger.exception("Receive loop error")
            self.running = False

    async def run(self):
        # основной цикл: попытка подключения, receive loop, на обрыве — ожидание и повтор
        while True:
            connected = await self.connect()
            if connected:
                # сброс задержки при успешном подключении
                self.reconnectDelay = RECONNECT_DELAY_INITIAL
                await self.receive_loop()
            else:
                self.logger.info("Connect failed, will retry in %.1f seconds", self.reconnectDelay)

            # ожидание перед следующей попыткой
            await asyncio.sleep(self.reconnectDelay)
            # экспоненциальное увеличение задержки до 60с
            self.reconnectDelay = min(self.reconnectDelay * 1.5, 60.0)
