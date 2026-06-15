import asyncio

class CacheManager():
    _instance = None
    _initialized = False
    _lock = asyncio.Lock()  # Ensures atomic execution across async events

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.cacheData = None  
            self.Renew = False
            self._initialized = True 
            
    def retrieveCache(self):
        if self.cacheData is None:
            return None
        return self.cacheData

    def setCache(self, data):
        self.cacheData = data[0]
