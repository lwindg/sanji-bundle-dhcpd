#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import logging
import os

from sanji.core import Sanji
from sanji.core import Route
from sanji.connection.mqtt import Mqtt
from dhcpd import DHCPD


class Index(Sanji):
    _logger = logging.getLogger("sanji.dhcpd.index")

    def init(self, *args, **kwargs):
        path_root = os.path.abspath(os.path.dirname(__file__))
        self.dhcpd = DHCPD(name="dhcpd", path=path_root)
        self.dhcpd.update_service()

    @Route(methods="get", resource="/network/dhcpd")
    def get(self, message, response):
        status = self.dhcpd.service.status()
        return response(data={
            "status": True if status == 0 else False,
            "collection": self.dhcpd.getAll()
        })

    @Route(methods="get", resource="/network/dhcpd/:id")
    def get_id(self, message, response):
        data = self.dhcpd.get(id=int(message.param["id"]))
        if data is None:
            return response(code=404)

        return response(data=data)

    @Route(methods="put", resource="/network/dhcpd/:id")
    def put_id(self, message, response):
        data = self.dhcpd.update(
            id=int(message.param["id"]), newObj=message.data)
        if data is None:
            return response(code=404)
        return response(data=data)

    @Route(methods="put", resource="/network/interface/:ifname")
    def _event_interface_info(self, message):
        name = message.param["ifname"]
        deps = [iface for iface in self.dhcpd.getAll() if
                iface["enable"] == 1 and iface["name"] == name]

        if len(deps) == 0:
            return

        self.dhcpd.gererate_config()
        self._logger.info(
            "DHCP server is restarted. Due to %s setting had been chanaged" %
            message.data["name"])


if __name__ == "__main__":
    FORMAT = '%(asctime)s - %(levelname)s - %(lineno)s - %(message)s'
    logging.basicConfig(level=0, format=FORMAT)
    logging.getLogger("sh").setLevel(logging.WARN)
    index = Index(connection=Mqtt())
    index.start()
