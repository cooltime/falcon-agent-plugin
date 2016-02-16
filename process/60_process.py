#!/usr/bin/python

import os.path
import sys
baseDir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(baseDir)
from lib import config
from lib.collector import Collector

import commands
import json
import psutil
import sys

class Process:

    __program = ""
    __pids = []
    __keys = {}

    def __init__(self, keys, program):
        self.__program = program
        self.__keys = keys

    def __calPids(self):
        command = 'for proc in `ls /proc/ | grep -E "[0-9]+"`; do program=$(readlink /proc/$proc/exe); test X"$program" = X"' + self.__program + '" && echo $proc; done'
        output = commands.getoutput(command)
        self.__pids = output.split()

    def getStats(self):
        ret = {}
        for metric in self.__keys.keys():
            ret[metric] = 0

        self.__calPids()

        for pid in self.__pids:
            try:
                process = psutil.Process(int(pid))
                self.statOne(process, ret)

            except psutil.NoSuchProcess, e:
                continue

        cmd = 'cat /proc/cpuinfo| grep "processor"| wc -l'
        processorNum = int(commands.getoutput(cmd))
        ret['cpu_percent'] = ret['cpu_percent'] / processorNum

        return ret

    def statOne(self, process, ret):
        meminfo = process.get_memory_info()
        for metric in self.__keys.keys():
            if metric == 'mem_rss':
                ret[metric] += meminfo[0]
            elif metric == 'mem_vms':
                ret[metric] += meminfo[1]
            elif metric == 'mem_percent':
                ret[metric] += process.get_memory_percent()
            elif metric == 'cpu_percent':
                ret[metric] += process.get_cpu_percent()
            elif metric == 'thread_num':
                ret[metric] += process.get_num_threads()
            elif metric == 'fd_num':
                ret[metric] += process.get_num_fds()
            else:
                continue

    def getPids(self):
        return self.__pids

class ProcessCollector(Collector):

    _type = "PROC"

    def __init__(self, config, keys):
        Collector.__init__(self, self._type, config, keys)

    def collect(self):
        dictProcessConf = config[self._type]

        if int(dictProcessConf['entityNum']) == 0:
            sys.exit(0)

        baseInfo = {
                'endpoint' : dictProcessConf['host'],
                'timestamp' : dictProcessConf['timestamp'],
                'step' : dictProcessConf['step'],
                }

        for i in range(1, dictProcessConf['entityNum'] + 1):
            entity = dictProcessConf['entities'][i]
            process = Process(self._keys, entity['program'])
            rawResult = process.getStats()

            for metric, value in rawResult.items():
                item = baseInfo.copy()
                item['metric'] = 'proc.' + metric
                item['value'] = value
                item['counterType'] = self._keys[metric]
                item['tags'] = 'proc=' + entity['program']
                self._result.append(item)

    def getResult(self):
        return self._result

if __name__ == '__main__':
    statKeys = {
            'mem_rss' : "GAUGE",
            'mem_vms' : "GAUGE",
            'mem_percent' : "GAUGE",
            'cpu_percent' : "GAUGE",
            'thread_num' : "GAUGE",
            'fd_num' : "GAUGE",
        }

    collector = ProcessCollector(config, statKeys)
    collector.collect()
    result = collector.getResult()
    print json.dumps(result, sort_keys=True, indent=4) 

