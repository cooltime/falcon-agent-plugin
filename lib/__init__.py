#!/usr/bin/python

import struct
import fcntl
import socket
import time
import re
import os.path
import ConfigParser
import json

baseDir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
confFile = baseDir + "/conf/monitor.conf"

def generateConf(confDir, confFile):
    confSeqs = os.listdir(confDir)
    confContent = ""
    for confSeq in confSeqs:
        if confSeq == 'monitor.conf':
            continue
        fp = open(confDir + "/" + confSeq, 'r')
        confContent += "".join(fp.readlines())

    fp = open(confFile, 'w')
    fp.write(confContent)

def parseConf(confFile, defaults):
    config = {}

    fp = open(confFile, 'r')
    cf = ConfigParser.RawConfigParser()
    cf.read(confFile)
    config['GLOBAL'] = defaults

    #1. Parse global confs
    if cf.has_section('GLOBAL'):
        config['GLOBAL'].update(cf.items('GLOBAL'))

    #2. Parse other confs, base is GLOBAL, and update by local
    sections = cf.sections()
    for section in sections:
        if section == 'GLOBAL':
            continue

        config[section] = {}
        config[section].update(config['GLOBAL'])
        try:
            config[section]['entityNum'] = cf.getint(section, 'entityNum')
        except ConfigParser.NoOptionError:
            continue
        config[section]['entities'] = {}
        for i in range(1, config[section]['entityNum'] + 1):
            config[section]['entities'][i] = {}

        reg = re.compile('(\w+?)([0-9]+)')

        for key, value in cf.items(section):
            if key.lower() == 'entityNum'.lower():
                continue
            matches = reg.findall(key)
            if len(matches) != 1:
                pass
            match = matches[0]
            config[section]['entities'][int(match[1])][match[0]] = value

    return config

host = socket.gethostname()
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
try:
    ip = socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8915, struct.pack('256s', 'eth1'))[20:24])
    eth1Ip = ip
except IOError, e:
    ip = socket.gethostbyname(host)
    eth1Ip = '0.0.0.0'
try:
    eth0Ip = socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8915, struct.pack('256s', 'eth0'))[20:24])
except IOError, e:
    eth0Ip = '0.0.0.0'

timestamp = int(time.time())
step = 60
defaults = {
        'baseDir' : baseDir,
        'host' : host,
        'ip' : ip,
        'eth1Ip' : eth1Ip,
        'eth0Ip' : eth0Ip,
        'timestamp' : timestamp,
        'step' : step,
        }

generateConf(baseDir + '/conf', confFile)
config = parseConf(confFile, defaults)

if __name__ == '__main__':
    print json.dumps(config, indent=4, sort_keys=True)
