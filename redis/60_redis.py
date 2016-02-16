#!/usr/bin/python

import struct
import fcntl
import socket
import commands
import time
import re
import json
import urllib2
import os

import sys
import os.path
baseDir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(baseDir)
from lib import config
from lib.collector import Collector

class RedisStat:

    __redisCli = '/usr/bin/redis-cli'
    __info = {}
    __keys = {}

    def __init__(self, keys, ip, port = 6379):
        self.__cmd = '%s -h %s info' % (self.__redisCli, ip)
        self.__keys = keys

    def __getInfo(self):
        info = commands.getoutput(self.__cmd)
        reg = re.compile(r'(\w+):([0-9]+\.?[0-9]*)\r')
        self.__info = dict(reg.findall(info))
        if (len(self.__info) == 0):
            self.__cmd = '%s -h %s info' % (self.__redisCli, '127.0.0.1')
            info = commands.getoutput(self.__cmd)
            self.__info = dict(reg.findall(info))

    def getStats(self):
        self.__getInfo()
        stats = {}

        for metric in self.__keys.keys():
            value = 0
            if metric == 'pv':
                value = self.__info['total_commands_processed']
            elif metric == 'keyspace_hit_ratio':
                try:
                    value = float(self.__info['keyspace_hits']) / (int(self.__info['keyspace_hits']) + int(self.__info['keyspace_misses']))
                except ZeroDivisionError:
                    value = 0
            elif metric == 'mem_fragmentation_ratio':
                value = float(self.__info[metric])
            else:
                try:
                    value = int(self.__info[metric])
                except:
                    continue

            stats[metric] = value

        return stats

class RedisCollector(Collector):

    _type = 'REDIS'

    def __init__(self, config, keys):
        Collector.__init__(self, self._type, config, keys)


    def collect(self):

        dictRedisConf = config[self._type]

        if int(dictRedisConf['entityNum']) == 0:
            sys.exit(0)

        baseInfo = {
                'endpoint' : dictRedisConf['host'],
                'timestamp' : dictRedisConf['timestamp'],
                'step' : dictRedisConf['step'],
                }

        for i in range(1, dictRedisConf['entityNum'] + 1):
            entity = dictRedisConf['entities'][i]
            if entity.has_key('port'):
                if not entity.has_key('ip'):
                    pass
                else:
                    stater = RedisStat(self._keys, entity['ip'], entity['port'])

            elif entity.has_key('ip'):
                stater = RedisStat(self._keys, entity['ip'])

            else:
                stater = RedisStat(self._keys, dictRedisConf['ip'])
            rawResult = stater.getStats()

            for metric, value in rawResult.items():
                item = baseInfo.copy()
                item['metric'] = self._type.lower() + "." + metric
                item['value'] = value
                item['counterType'] = self._keys[metric]
                self._result.append(item)

if __name__ == '__main__':

    statKeys = {
        'connected_clients' : 'GAUGE', 
        'blocked_clients' : 'GAUGE', 
        'used_memory' : 'GAUGE',
        'used_memory_rss' : 'GAUGE',
        'used_memory_peak' : 'GAUGE',
        'mem_fragmentation_ratio' : 'GAUGE',
        'pv' : 'COUNTER',
        'expired_keys' : 'COUNTER',
        'evicted_keys' : 'COUNTER',
        'keyspace_hits' : 'COUNTER',
        'keyspace_misses' : 'COUNTER',
        'keyspace_hit_ratio' : 'GAUGE',
        'rdb_bgsave_in_progress' : 'GAUGE',
        }

    collector = RedisCollector(config, statKeys)
    collector.collect()
    result = collector.getResult()
    print json.dumps(result, sort_keys=True, indent=4)

