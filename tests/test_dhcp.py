#!/usr/bin/env python
# -*- coding: UTF-8 -*-


import os
import sys
import unittest
import logging

from sanji.connection.mockup import Mockup
# from sanji.message import Message
from mock import patch
from string import Template
from mock import Mock
from mock import mock_open

logger = logging.getLogger()

# retry times when model initialize
retry_times = 5

try:
    sys.path.append(os.path.dirname(os.path.realpath(__file__)) + '/../')
    from dhcp import Dhcp
except ImportError as e:
    print "Please check the python PATH for import test module. (%s)" \
        % __file__
    exit(1)


class TestDhcpClass(unittest.TestCase):

    def setUp(self):
        self.dhcp = Dhcp(connection=Mockup())

    def tearDown(self):
        self.dhcp.stop()
        self.dhcp = None

    def test_loadTemplate(self):
        # check template is read success or not
        m = mock_open(read_data="mock read $str")
        with patch("dhcp.open", m, create=True):
            mock_str = Template("mock read ${str}").substitute(str="string")
            # call loadTemplate
            self.dhcp.loadTemplate()
            # check subnet template
            subnet_template = self.dhcp.template["subnet"]
            # replace string
            r = dict(str="string")
            subnet_str = subnet_template.substitute(r)
            self.assertEqual(mock_str, subnet_str)
            # check dhcpd.conf template
            dhcp_template = self.dhcp.template["dhcpd.conf"]
            dhcp_str = dhcp_template.substitute(r)
            self.assertEqual(mock_str, dhcp_str)

    def test_model_init(self):
        # dhcp_restart = True
        # mock dhcp_restart()
        with patch("dhcp.Dhcp.dhcp_restart") as dhcp_restart:
            dhcp_restart.return_value = True
            with patch("dhcp.logger.info") as log:
                self.dhcp.model_init()
                log.assert_called_once_with("DHCP server initialize success")

        # dhcp_restart = False
        # mock dhcp_restart()
        with patch("dhcp.Dhcp.dhcp_restart") as dhcp_restart:
            dhcp_restart.return_value = False
            with patch("dhcp.logger.info") as log:
                self.dhcp.model_init()
                log.assert_called_once_with("DHCP server initialize failed")

if __name__ == "__main__":
    logger = logging.getLogger("TestDhcpClass")
    unittest.main()
