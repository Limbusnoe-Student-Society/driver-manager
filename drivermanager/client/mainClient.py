from clientAgent import ClientAgent
import clientConfig as cfg 
import asyncio
if __name__ == "__main__":
    client = ClientAgent(cfg.HOST, cfg.PORT)
    try:
        asyncio.run(client.run())
    except KeyboardInterrupt:
        client.logger.info("Client stopped by user")