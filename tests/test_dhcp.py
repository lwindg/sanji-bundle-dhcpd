#!/usr/bin/env python
# -*- coding: UTF-8 -*-


import os
import sys
import unittest
import logging

from sanji.connection.mockup import Mockup
from sanji.message import Message
from mock import patch
from mock import Mock

logger = logging.getLogger()

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

	def test_init(self):
		self.dhcp.loadTemplate = Mock()
		self.dhcp.model_init = Mock()

