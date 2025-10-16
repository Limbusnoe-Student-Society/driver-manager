from serverAgent import ServerAgent
from serverConfig import *
import asyncio
 
if __name__ == "__main__":           
    agent = ServerAgent(HOST, WEB_PORT, HTTP_PORT)
    asyncio.run(agent.start())