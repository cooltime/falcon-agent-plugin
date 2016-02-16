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

class Log:

    __tmpDir = ''
    __log = ''
    __pattern = ''
    __filter = ''
    __debug = False

    def __init__(self, debug, tmpDir, log, pattern = '', filter = ''):
        self.__tmpDir = tmpDir
        self.__pattern = pattern
        self.__log = log
        self.__filter = filter
        self.__debug = debug
        if not os.path.exists(tmpDir):
            os.mkdir(tmpDir)

    def gatherLog(self):
        logName = self.__log.replace('/', '_')
        if self.__debug:
            logName += ".debug"
        tmpDir = self.__tmpDir
        outLog = tmpDir + '/' + logName
        command = '/usr/sbin/logtail2 -f ' + self.__log + ' -o ' + tmpDir + '/' + logName + '.offset > ' + outLog
        (status, output) = commands.getstatusoutput(command)
        return outLog

    def getResult(self, outLog):
        command = 'grep -E "' + self.__pattern + '" ' + outLog
        if self.__filter != '':
            command += ' | grep -vE "' + self.__filter + '"'
        command += ' | wc -l'
        (status, output) = commands.getstatusoutput(command)
        return int(output)
        

class LogCollector(Collector):

    _type = "LOG"

    def __init__(self, config, keys):
        self.__keys = keys
        dictLogConf = config[self._type]

        if int(dictLogConf['entityNum']) == 0:
            sys.exit(0)

        Collector.__init__(self, self._type, config, keys)

    def collect(self, isDebug):
        dictLogConf = config[self._type]
        tmpDir = dictLogConf['tmpdir']

        if int(dictLogConf['entityNum']) == 0:
            sys.exit(0)

        baseInfo = {
                'endpoint' : dictLogConf['host'],
                'timestamp' : dictLogConf['timestamp'],
                'step' : dictLogConf['step'],
                }

        gatheredLogs = {}
        for i in range(1, dictLogConf['entityNum'] + 1):
            entity = dictLogConf['entities'][i]
            logger = Log(isDebug, tmpDir, entity['log'], entity['pattern'], entity['filter'])
            if not entity['log'] in gatheredLogs:
                outFile = logger.gatherLog()
                gatheredLogs[entity['log']] = outFile

            rawResult = logger.getResult(gatheredLogs[entity['log']])

            item = baseInfo.copy()
            item['metric'] = 'log.' + entity['name'] 
            if entity['type'] == 'AVG':
                item['value'] = int(rawResult / 60)
                item['counterType'] = 'GAUGE'
            else:
                item['value'] = rawResult
                item['counterType'] = entity['type']
            item['tags'] = 'log=' + entity['key']
            self._result.append(item)

    def getResult(self):
        return self._result

if __name__ == '__main__':

    isDebug = False
    if len(sys.argv) > 1 and sys.argv[1] == 'debug':
        isDebug = True
    statKeys = {}
    collector = LogCollector(config, statKeys)
    collector.collect(isDebug)
    result = collector.getResult()
    print json.dumps(result, sort_keys=True, indent=4) 

