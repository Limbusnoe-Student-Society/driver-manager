from serverAgent import ServerAgent
import logging
import serverConfig as cfg
import asyncio
 
if __name__ == "__main__":           
    agent = ServerAgent(cfg.HOST, cfg.WEB_PORT, cfg.HTTP_PORT)
    try:
        asyncio.run(agent.start())
    except KeyboardInterrupt:
        agent.logger.info("Client stopped by user")