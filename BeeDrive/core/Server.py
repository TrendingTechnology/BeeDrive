from os import path, makedirs
from time import sleep, time
from json import loads, dumps
from multiprocessing import cpu_count

from .base import BaseServer, BaseClient, BaseManager
from .constant import IsFull, NewTask, KillTask, Update, Stop, ALIVE
from .utils import build_connect
from .uploader import UploadWaiter
from .downloader import DownloadWaiter
from .logger import callback_info, callback_flush


WAITERS = {"upload": UploadWaiter, "download": DownloadWaiter}


class ExistMessager(BaseClient):
    def __init__(self, port):
        BaseClient.__init__(self, None, u"", ('127.0.0.1', port), 'exist')
        self.start()

    def run(self):
        with self:
            pass

            
class WorkerManager(BaseManager):
    def __init__(self, pipe, name, work_dir, pool_size):
        BaseManager.__init__(self, pipe, name, pool_size)
        self.work_dir = work_dir
        self.launch()

    def launch_task(self, socket, info, task, passwd):
        worker = WAITERS[task](info, socket, self.work_dir, passwd)
        self.pool[worker.info.uuid] = worker
        self.send(worker.info.uuid)



class LocalServer(BaseServer):
    def __init__(self, users, port, save_path, 
                 crypto, sign, max_manager, max_worker):
        BaseServer.__init__(self, users, port, crypto, sign)
        self.target = ("0.0.0.0", port)
        self.max_manager = max_manager
        self.max_worker = max_worker
        self.managers = set()
        self.workdir = path.abspath(save_path)

    def __enter__(self):
        self.build_socket()
        self.build_pipeline()
        self.build_server(self.max_worker * self.max_manager)
        self.active()
        callback_info("Server has been launched at %s" % (self.target,))

    def add_new_task(self, client, passwd, info, task):
        while True:
            for manager in self.managers:
                if manager.echo(IsFull) is False:
                    uuid = manager.echo(NewTask,
                                      socket=client,
                                      info=info,
                                      task=task,
                                      passwd=passwd)
                    return
                
            self.add_new_manager()
            if len(self.managers) == self.max_manager:
                sleep(1)

    def add_new_manager(self):
        if len(self.managers) < self.max_manager:
            manager = WorkerManager.get_controller(name=self.name,
                                         work_dir=self.workdir,
                                         pool_size=self.max_worker)
            self.managers.add(manager)

    def run(self):
        with self:
            while self._work.isSet():
                client, passwd, info, task = self.accept_connect()
                if task == 'exist':
                    self.close()
                if client is not None:
                    self.add_new_task(client, passwd, info, task)

    def stop(self):
        for manager in self.managers:
            manager.join_do(Stop)
        self._work.clear()
        ExistMessager(self.port).join()
        callback_flush()

    def update_schedule_status(self):
        for manager in self.managers:
            for uuid, state, stage, percent, msg in manager.echo(Update):
                pass

                        
if __name__ == '__main__':
    server = LocalServer(
                name='JacksonWoo',
                port=8888,
                save_path=r'C:\Users\JacksonWoo\Desktop',
                crypto=False,
                sign=False)
    server.start()
    sleep(3600)
    server.stop()
