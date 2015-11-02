#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import os
import sys
import glob
import unittest

from mock import Mock
from mock import patch
from mock import mock_open
from mock import ANY
from mock import call

try:
    sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../../")
    from dhcp import DHCPD
    from dhcp import Subnet
    from dhcp import Service
except ImportError as e:
    print "Please check the python PATH for import test module. (%s)"\
           % __file__
    exit(1)


class TestSubnetClass(unittest.TestCase):

    def setUp(self):
        self.subnet = Subnet({
            "id": 2,
            "name": "eth1",
            "enable": 0,
            "netmask": "",
            "startIP": "",
            "endIP": "",
            "domainNameServers": [],
            "domainName": "",
            "leaseTime": 3600
        })

    def tearDown(self):
        pass

    @patch("dhcp.get_ip_by_interface")
    def test__covert(self, get_ip_by_interface):
        """"""
        self.subnet._convert()


if __name__ == "__main__":
    unittest.main()
