#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2014 KenV99
#
# This program is free software: you can redistribute it and/or modify
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

import sys
import pyro4
import pyro4.util

if 'win' in sys.platform:
    isKodi = 'xbmc' in sys.executable.lower() or 'kodi' in sys.executable.lower()
else:
    isKodi = True
if isKodi:
    import xbmcaddon


class IPCClient(object):
    """
    Initializes the client to use a named proxy for data communication with the server. The method 'get_data_object'
    should be invoked just before running a server based method and then destroyed promptly to prevent running out
    of data sockets on the server and preventing dropped connections. This can be done by dropping out of context
    and need not be done explicitly. See pyro4 docs at https://pythonhosted.org/Pyro4/index.html for details.

    """

    def __init__(self, add_on_id='', name='kodi-IPC', host='localhost', port=9099, datatype='pickle'):
        """
        :param add_on_id: *Optional keyword*. The id of an addon which has stored server settings in its settings.xml
                            file. This supercedes any explicit eyword assignments for name, host and port.
        :type add_on_id: str
        :param name: *Optional keyword*. Arbitrary name for the object being used, must match the name used by server
        :type name: str
        :param host: *Optional keyword*. The resolvable name or IP address where the server is running
        :type host: str
        :param port: *Optional keyword*. Port matching server port
        :type port: int
        :param datatype: *Optional keyword*. Type of data transport being used options: pickle, serpent, json, marshall.
                         Must match server.
        :type datatype: str

        """
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
        if (datatype in pyro4.config.SERIALIZERS_ACCEPTED) is False:
            pyro4.config.SERIALIZERS_ACCEPTED.add(datatype)
        pyro4.config.SERIALIZER = datatype
        pyro4.config.DETAILED_TRACEBACK = True
        pyro4.config.COMMTIMEOUT = 5

    def get_exposed_object(self):
        """
        :return: Retrieves a reference to the object being shared by the server via proxy as pyro4 remote object
        :rtype: object

        """
        return pyro4.Proxy(self.uri)

    def server_available(self):
        """
        Checks to see if a connection can be made to the shared object

        :return: Return True if connection is successful, False if not
        :rtype: bool

        """
        try:
            p = pyro4.Proxy(self.uri)
            p._pyroBind()
        except:
            return False
        else:
            p._pyroRelease()
            return True

    @staticmethod
    def get_traceback():
        """
        Useful for exceptions that occur within the logic of the shared object. The normal system traceback will not be
        informative for these types of errors.

        :return: A detailed traceback of the last error
        :rtype: str

        """
        return "".join(pyro4.util.getPyroTraceback())