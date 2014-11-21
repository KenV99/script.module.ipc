#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2014 KenV99
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
#   Pyro is Copyright (c) by Irmen de Jong (irmen@razorvine.net)
#   Under the "MIT Software License" which is OSI-certified, and GPL-compatible.
#   See http://www.opensource.org/licenses/mit-license.php

import pyro4
import pyro4.util
import pyro4.errors
import threading
import sys
import socket
import time


def printlog(msg):
    print msg

if 'win' in sys.platform:
    isKodi = 'xbmc' in sys.executable.lower() or 'kodi' in sys.executable.lower()
else:
    isKodi = True
if isKodi:
    import xbmc
    import xbmcaddon
    logger = xbmc.log
else:
    logger = printlog


def sleep(msecs):
    if isKodi:
        xbmc.sleep(msecs)
    else:
        time.sleep(msecs / 1000.0)


class IPCServer(threading.Thread):
    """
    Initializes all parameters needed to start the server using a specifically named server and port.
    (pyro4 allows for the use of a nameserver if desired. Details at: https://pythonhosted.org/Pyro4/index.html)
    Inherits from threading so that an EXTERNAL event loop can be used to exit gracefully when Kodi is shutting down
    by calling the stop() method. Note that if you plan to run more than one server, you should specify 'name' and
    'port' to prevent conflicts and errors.

    """

    def __init__(self, expose_obj, add_on_id='', name='kodi-IPC', host='localhost', port=9099, serializer='pickle'):
        """
        :param expose_obj: *Required*. This is the python object whose methods will be exposed to the clients
        :type expose_obj: object or classic class
        :param add_on_id: *Optional keyword*. The id of an addon which has stored server settings in its settings.xml
                            file. This supercedes any explicit keyword assignments for name, host and port.
        :type add_on_id: str
        :param name: *Optional keyword*. The arbitrary name used by the socket protocol for this datastore.
        :type name: str
        :param host: *Optional keyword*. The host that will be used for the server.
        :type host: str
        :param port: *Optional keyword*. The port for the socket used.
        :type port: int
        :param serializer: *Optional keyword*. The serialization protocol to be used. Options: pickle, serpent,
                            marshall, json
        :type serializer: str

        """
        super(IPCServer, self).__init__()
        if add_on_id != '' and isKodi:
            try:
                settings = xbmcaddon.Addon(add_on_id).getSetting
                self.name = settings('data_name')
                self.host = settings('host')
                self.port = int(settings('port'))
            except:
                self.host = host
                self.name = name
                self.port = port
        else:
            self.host = host
            self.name = name
            self.port = port
        self.uri = 'PYRO:{0}@{1}:{2}'.format(name, host, port)
        self.serializer = serializer
        self.expose_obj = expose_obj
        self.p4daemon = None
        self.running = False
        self.shutdown = False
        self.exception = None

    def run(self):
        """
        Note that you must call .start() on the class instance to start the server in a separate thread.
        Do not call run() directly with IPCServer.run() or it will run in the same thread as the caller and
        lock when it hits daemon.requestLoop(). If port unavailable, retries 5 times with a 10ms delay between tries.

        """
        if (self.serializer in pyro4.config.SERIALIZERS_ACCEPTED) is False:
            pyro4.config.SERIALIZERS_ACCEPTED.add(self.serializer)
        pyro4.config.SERIALIZER = self.serializer
        retry = 5
        while retry > 0:
            try:
                self.p4daemon = pyro4.Daemon(host=self.host, port=self.port)
                self.p4daemon.register(self.expose_obj, self.name)
            except socket.error as e:
                if e.errno == 10048:  # Only one usage of each socket address
                    if retry > 1:
                        retry -= 1
                        sleep(10)
                    else:
                        logger("'*&*&*&*& ipcdatastore: Error starting IPC Server: {0}. Socket already in use."
                               .format(self.uri))
                        e.message = "Socket {0} already in use.".format(self.port)
                        self.exception = e
                        retry = 0
            except Exception as e:
                logger("'*&*&*&*& ipcdatastore: Error starting IPC Server: {0}".format(self.uri))
                if hasattr(e, 'message'):
                    if len(e.message) > 0:
                        logger(e.message)
                if hasattr(e, 'args'):
                    if len(e.args) > 1:
                        logger(str(e.args[1]))
                self.exception = e
                retry = 0
            else:
                self.running = True
                logger("'*&*&*&*& ipcdatastore: IPC Server Started: {0}".format(self.uri))
                self.p4daemon.requestLoop()
                logger("*&*&*&*& ipcdatastore: IPC Server Exited Event Loop: {0}".format(self.uri))
                retry = 0

    def stop(self):
        """
        Stops the server. If the exposed object has a method called 'close', this is called before the server stops.
        There is a 50msec delays to allow any pending data to propagate.

        """
        sleep(50)
        if hasattr(self.expose_obj, 'close'):
            self.expose_obj.close()
        self.running = False
        if self.is_alive():
            self.p4daemon.shutdown()
            self.join(2)
        self.p4daemon = None
        if self.is_alive():
            logger("*&*&*&*& ipcdatastore: IPC Server Failed to Shutdown: {0}".format(self.uri))
        self.shutdown = True

    @staticmethod
    def test_pickle(test_obj):
        """
        A convenience function that tests whether an object or instance can be pickled (serializable for default server
        sharing protocol).

        :param test_obj: Required. The object to be tested
        :type test_obj: object
        :return: True if pickleable, False if not
        :rtype: bool

        """
        import pickle
        try:
            x = pickle.dumps(test_obj)
        except (pickle.PickleError, pickle.PicklingError, ValueError):
            return False
        else:
            return True

    def start(self):
        """
        Overrides base start() and then calls it via super. Main purpose is to provide a way to monitor for exceptions
        during startup from the inside loop that otherwise could not be easily raised and caught.

        """
        super(IPCServer, self).start()
        while True:
            if self.running is True or self.exception is not None:
                break
        if self.exception:
            raise self.exception
