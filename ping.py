import threading
import multiprocessing
import concurrent.futures
import subprocess
import datetime
import pymysql
import logging
import atexit
import os

try:
    from alert import alert as alert_func
except Exception:
    pass


logging.basicConfig(level=logging.DEBUG)

class Monitor:

    cpu_count = os.cpu_count()

    def __init__(self, ip_list=None, capture_problem=True, realtime_alert=True, db_conn=True):

        self.cpu_count = os.cpu_count()
        self.ip_list = ip_list if ip_list else self.get_ip_list()
        self.all_results = []
        self.failed_results = []
        self.capture_problem = capture_problem
        self.realtime_alert = realtime_alert
        self.db_conn = False
        if db_conn:
            self.db_conn = db_conn if hasattr(db_conn, 'cursor') else self.get_db_conn()
            self.cursor = self.db_conn.cursor()

            atexit.register(self.cursor.close)
            atexit.register(self.db_conn.close)

    def get_db_conn(self):
        logging.info('getting connection to test database')
        db_conn = pymysql.connect(db='test')
        return db_conn

    def get_ip_list(self):
        logging.info('getting ip list')
        ip_list = []
        for i in range(1, 100):
            for j in range(2, 202):
                ip_list.append("23.94.{}.{}".format(i, j))
        return ip_list

    def alert(self, ip_status):

        ip, status = ip_status
        try:
            if self.capture_problem:
                if status !=0:
                    if self.db_conn:
                        if not self.cursor.execute("SELECT ip FROM alert WHERE ip = %s", (ip, )):
                            self.cursor.execute("INSERT INTO alert (ip, create_time) VALUES (%s, %s)", (ip, datetime.datetime.now()))
                    alert_func((ip, 'problem'))
            else:
                if status == 0:
                    alert_func((ip, 'ok'))

        except Exception as e:
            print("alert err: {}".format(e))

    def ping(self, ip, results):

        status,_ = subprocess.getstatusoutput("ping -c 5 -w 5 {}".format(ip))
        if self.realtime_alert:
            self.alert((ip, status))
        results.append((ip, status))

    def process(self, ip_list):
        logging.info('processing ')
        threads = []
        results = []
        for ip in ip_list:
            threads.append(threading.Thread(target=self.ping, args=(ip, results)))
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.all_results.append(results)

    def run(self):
        logging.info('running ')
        partcount = len(self.ip_list) // self.cpu_count
        processes = []
        for i in range(self.cpu_count):
            if i == (self.cpu_count - 1):
                process = multiprocessing.Process(target=self.process, args=(self.ip_list[i*partcount:], ))
            else:
                process = multiprocessing.Process(target=self.process, args=(self.ip_list[i*partcount:(i+1)*partcount],))
            processes.append(process)
        for p in processes:
            p.start()
        for p in processes:
            p.join()
        
        self.__format_data()
        self.__filter_failed()
        self.__update_failed()
        return self.all_results

    def __format_data(self):
        all_results = []
        for results in self.all_results:
            for r in results:
                all_results.append(r)

        self.all_results = all_results
    
    def __filter_failed(self):
        for ip, status in self.all_results:
            if status != 0:
                self.failed_results.append(ip)

    def __update_failed(self):
        self.cursor.executemany('INSERT INTO alert (ip) VALUES (%s)', self.failed_results)

        
if __name__ == "__main__":
    monitor = Monitor()
    results = monitor.run()
    print(results[:10])
