#!/usr/bin/python

import os.path
import sys
baseDir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(baseDir)
from lib import config
from lib.collector import Collector

import re
import commands
import json
import psutil
import sys

# For nginx's response time
class NginxRT:

    __tmpDir = ''
    __log = ''
    __debug = False

    def __init__(self, debug, tmpDir, log):
        self.__tmpDir = tmpDir
        self.__log = log
        if not os.path.exists(tmpDir):
            os.mkdir(tmpDir)

    def gatherNginxRT(self):
        logName = self.__log.replace('/', '_')
        logName += '_rt'
        if self.__debug:
            logName += ".debug"
        tmpDir = self.__tmpDir
        outNginxRT = tmpDir + '/' + logName
        command = '/usr/sbin/logtail2 -f ' + self.__log + ' -o ' + tmpDir + '/' \
            + logName + '.offset > ' + outNginxRT
        (status, output) = commands.getstatusoutput(command)
        return outNginxRT

    def getResult(self, outNginxRT):
        ret = {}
        command = """awk -F '"' '{print $2" "$6}' """ + outNginxRT \
            + """ | awk -F 'ac=' '{print $2}' | awk -F '&| ' '{print $1":"$NF}' """ \
            + """ | grep -E "^[a-z]" | grep -v '%' | grep -vE ".*[0-9].*:" """
        (status, output) = commands.getstatusoutput(command)

        dictAcCount = {}
        dictAcRt = {}
        totalCount = 0
        totalRt = 0

        for line in output.split("\n"):
            pair = line.split(':')
            if not len(pair) == 2 or pair[0] == '' or pair[1] == '':
                continue

            if pair[0] not in dictAcCount:
                dictAcCount[pair[0]] = 0
                dictAcRt[pair[0]] = 0

            dictAcCount[pair[0]] += 1
            dictAcRt[pair[0]] += float(pair[1])
            totalRt += float(pair[1])
            totalCount += 1

        for key, value in dictAcRt.items():
            count = dictAcCount[key]
            sumRt = dictAcRt[key]
            rt = sumRt / count
            ret[key] = rt

        ret['total'] = totalRt / totalCount

        return ret

class NginxRTCollector(Collector):
    _type = 'NGINXRT'

    def __init__(self, config, keys):
        self.__keys = keys
        dictNginxRTConf = config[self._type]

        if int(dictNginxRTConf['entityNum']) == 0:
            sys.exit(0)

        Collector.__init__(self, self._type, config, keys)

    def collect(self, isDebug):
        dictNginxRTConf = config[self._type]
        tmpDir = dictNginxRTConf['tmpdir']

        if int(dictNginxRTConf['entityNum']) == 0:
            sys.exit(0)

        baseInfo = {
                'endpoint' : dictNginxRTConf['host'],
                'timestamp' : dictNginxRTConf['timestamp'],
                'step' : dictNginxRTConf['step'],
                }

        for i in range(1, dictNginxRTConf['entityNum'] + 1):
            entity = dictNginxRTConf['entities'][i]
            nginxRT = NginxRT(isDebug, tmpDir, entity['log'])

            rawResult = nginxRT.getResult(nginxRT.gatherNginxRT())

            for k, v in rawResult.items():
                item = baseInfo.copy()
                item['metric'] = 'nginx-rt.' + k
                item['value'] = float(v) * 1000
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
    collector = NginxRTCollector(config, statKeys)
    collector.collect(isDebug)
    result = collector.getResult()
    print json.dumps(result, sort_keys=True, indent=4)
