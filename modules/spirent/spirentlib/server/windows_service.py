import servicemanager
import sys
import win32event
import win32service
import win32serviceutil
import logging
import time
from datetime import datetime
import spirent_ctrl


class SpirentCtrlService(win32serviceutil.ServiceFramework):
    _svc_name_ = "SpirentServerCtrl"
    _svc_display_name_ = "SpirentServerCtrl"
    _svc_description_ = "Service which runs spirent server"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)

    def SvcStop(self):
        self.Server.stop_server()
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        self.directory = 'C:\\SpirentServerCtrl\\logs\\'
        self.filename = datetime.now()
        self.filename = self.filename.strftime("%d %B %Y")

        if not os.path.exists(self.directory):
            os.makedirs(self.directory)

        logging.basicConfig(level=logging.WARNING,
                            filename='C:\\SpirentServerCtrl\\logs\\{}'.format(self.filename),
                            filemode='w')

        self.Server = spirent_ctrl.ServerController()
        self.Server.run_server()

if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(SpirentCtrlService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(SpirentCtrlService)
