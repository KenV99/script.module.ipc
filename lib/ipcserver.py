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

def printlog(msg):
    print msg
if 'win' in sys.platform:
    isKodi = 'XBMC' in sys.executable
else:
    isKodi = True
if isKodi:
    import xbmc
    logger = xbmc.log
else:
    logger = printlog

class IPCServer(threading.Thread):

    def __init__(self, expose_obj, host='localhost', name='kodi-IPC', port=9099, serializer='pickle'):
        """
        Initializes all parameters needed to start the server using a specifically named server and port.
        (pyro4 allows for the use of a nameserver if desired. Details at: https://pythonhosted.org/Pyro4/index.html)
        Inherits from threading so that an EXTERNAL event loop can be used to exit gracefully when Kodi is shutting down
        by calling the stop() method. Note that if you plan to run more than one server, you should specify 'name' and
        'port' to prevent conflicts and errors.
        :param expose_obj: This is the python object whose methods will be exposed to the clients
        :type expose_obj: object or classic class
        :param host: The host that will be used for the server
        :type host: str
        :param name: The name used by the socket protocol for this datastore
        :type name: str
        :param port: The port for the socket used
        :type port: int
        :param serializer: The serialization protocol to be used. Options: pickle, serpent, marshall, json
        :type serializer: str
        """
        super(IPCServer, self).__init__()
        self.host = host
        self.name = name
        self.port = port
        self.serializer = serializer
        self.expose_obj = expose_obj
        self.p4daemon = None
        self.running = False

    def run(self):
        """
        Note that you must call .start() on the class instance to start the server in a separate thread.
        Do not call this routine directly with .run() or it will run in the same thread as the caller and lock when it
        hits daemon.requestLoop().
        """
        if (self.serializer in pyro4.config.SERIALIZERS_ACCEPTED) is False:
            pyro4.config.SERIALIZERS_ACCEPTED.add(self.serializer)
        pyro4.config.SERIALIZER = self.serializer
        try:
            daemon = pyro4.Daemon(host=self.host, port=self.port)
            daemon.register(self.expose_obj, self.name)
        except Exception as e:
            logger("'*&*&*&*& ipcdatastore: Error starting IPC Server")
            if hasattr(e, 'message'):
                logger(e.message)
        else:
            self.p4daemon = daemon
            self.running = True
            logger("'*&*&*&*& ipcdatastore: IPC Server Started: {0}".format(daemon.uriFor(self.name)))
            daemon.requestLoop()

    def stop(self):
        """
        Stops the server. Raises an exception on failure
        """
        try:
            self.p4daemon.shutdown()
        except Exception as e:
            raise
        else:
            self.running = False

    def test_pickle(self, test_obj):
        """
        Tests whether an object or instance is pickleable (serializable for default server sharing protocol).
        :param test_obj: The object to be tested
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

