import win32serviceutil
import win32service
import win32event
from serverAgent import ServerAgent 
from serverConfig import *

#TODO: отложено
class PythonService(win32serviceutil.ServiceFramework):
    _svc_name_ = 'drvmanagermaster'
    _svc_display_name_ = 'Driver Manager Master'

    def __init__(self, args):
        super().__init__(args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.agent = ServerAgent(HOST, WEB_PORT, HTTP_PORT)

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        self.agent.terminate()

    def SvcDoRun(self):
        win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)
        self.agent.start()

if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(PythonService)