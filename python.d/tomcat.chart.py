# -*- coding: utf-8 -*-
# Description: tomcat netdata python.d module
# Author: Pawel Krupa (paulfantom)

# Python version higher than 2.7 is needed to run this module.

from base import UrlService
import xml.etree.ElementTree as ET  # phone home...
#from xml.parsers.expat import errors

# default module values (can be overridden per job in `config`)
# update_every = 2
priority = 60000
retries = 60

# charts order (can be overridden if you want less charts, or different order)
ORDER = ['accesses', 'volume', 'threads', 'jvm']

CHARTS = {
    'accesses': {
        'options': [None, "tomcat requests", "requests/s", "statistics", "tomcat.accesses", "area"],
        'lines': [
            ["accesses"]
        ]},
    'volume': {
        'options': [None, "tomcat volume", "KB/s", "volume", "tomcat.volume", "area"],
        'lines': [
            ["volume", None, 'incremental']
        ]},
    'threads': {
        'options': [None, "tomcat threads", "current threads", "statistics", "tomcat.threads", "line"],
        'lines': [
            ["current", None, "absolute"],
            ["busy", None, "absolute"]
        ]},
    'jvm': {
        'options': [None, "JVM Free Memory", "MB", "statistics", "tomcat.jvm", "area"],
        'lines': [
            ["jvm", None, "absolute"]
        ]}
}


class Service(UrlService):
    def __init__(self, configuration=None, name=None):
        UrlService.__init__(self, configuration=configuration, name=name)
        if len(self.url) == 0:
            self.url = "http://localhost:8080/manager/status?XML=true"
        self.order = ORDER
        self.definitions = CHARTS
        self.port = 8080

    def check(self):
        if UrlService.check(self):
            return True

        # get port from url
        self.port = 0
        for i in self.url.split('/'):
            try:
                int(i[-1])
                self.port = i.split(':')[-1]
                break
            except:
                pass
        if self.port == 0:
            self.port = 80

        if self._get_data() is None or len(self._get_data()) == 0:
            return False
        else:
            return True

    def _get_data(self):
        """
        Format data received from http request
        :return: dict
        """
        try:
            raw = self._get_raw_data()
            try:
                data = ET.fromstring(raw)
            except ET.ParseError as e:
                #if e.code == errors.codes[errors.XML_ERROR_JUNK_AFTER_DOC_ELEMENT]:
                if e.code == 9:
                    # cut rest of invalid string
                    pos = 0
                    for i in range(e.position[0] - 1):
                        pos += raw.find('\n', pos)
                    raw = raw[:47604 + pos + e.position[0] - 1]
                    data = ET.fromstring(raw)
                else:
                    raise Exception(e)

            memory = data.find('./jvm/memory')
            threads = data.find("./connector[@name='\"http-bio-" + str(self.port) + "\"']/threadInfo")
            requests = data.find("./connector[@name='\"http-bio-" + str(self.port) + "\"']/requestInfo")

            return {'accesses': requests.attrib['requestCount'],
                    'volume': requests.attrib['bytesSent'],
                    'current': threads.attrib['currentThreadCount'],
                    'busy': threads.attrib['currentThreadsBusy'],
                    'jvm': memory.attrib['free']}
        except (ValueError, AttributeError) as e:
            self.debug(str(e))
            return None
        except SyntaxError as e:
            self.error("Tomcat module needs python 2.7 at least. Stopping")
            self.debug(str(e))
        except Exception as e:
            self.debug(str(e))
