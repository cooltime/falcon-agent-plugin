#!/usr/bin/python

class Collector:

    _type = ''
    _config = {}
    _keys = {}
    _result = []

    def __init__(self, type, config, keys):
        self._type = type
        self._config = config[self._type]
        self._keys = keys
        self._result = []

    def getConfig(self):
        return self._config

    def getKeys(self):
        return self._keys

    def getResult(self):
        return self._result

    def collect(self):
        pass
    
