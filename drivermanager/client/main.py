from clientAgent import ClientAgent
import asyncio
if __name__ == "__main__":
    client = ClientAgent()
    try:
        asyncio.run(client.run())
    except KeyboardInterrupt:
        client.logger.info("Client stopped by user")