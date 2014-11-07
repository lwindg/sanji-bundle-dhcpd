#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import logging
import os
import subprocess
import time
from sanji.core import Sanji
from sanji.core import Route
from sanji.model_initiator import ModelInitiator
from sanji.connection.mqtt import Mqtt
from string import Template

logger = logging.getLogger()
path_root = os.path.abspath(os.path.dirname(__file__))
dhcpd_config_path = "/etc/dhcp/dhcpd.conf"


class Dhcpd(Sanji):

    def init(self, *args, **kwargs):
        self.model = ModelInitiator("dhcpd", path_root)
        self.permittedName = ["eth0"]
        self.permittedKeys = ["id", "enable", "subnet", "netmask", "startIP",
                              "endIP", "dns", "name",
                              "domainName", "leaseTime"]
        # retry times when model initialize
        self.retry_times = 5

        self.rsp = {}
        self.rsp["code"] = 0
        self.rsp["data"] = None
        # save dhcpd.conf template
        self.template = dict()
        # load config template
        self.loadTemplate()
        # restart dhcp server
        self.model_init()

    def loadTemplate(self):
        # open template
        with open(path_root + "/template/subnet", "r") as f:
            self.template["subnet"] = Template(f.read())
        with open(path_root + "/template/dhcpd.conf", "r") as f:
            self.template["dhcpd.conf"] = Template(f.read())

    def model_init(self):
        retry_cnt = 0
        # restart dhcp server 5 times
        while retry_cnt < self.retry_times:
            # restart model
            restart_rc = self.dhcp_restart()
            if restart_rc is True:
                logger.info("DHCP server initialize success")
                return
            retry_cnt = retry_cnt + 1
            time.sleep(5)
        if retry_cnt == self.retry_times:
            logger.info("DHCP server initialize failed")

    @Route(methods="get", resource="/network/dhcpd")
    def get(self, message, response):
        # default is collection=true, return all db data
        # check current status
        currentStatus = 1 if self.get_status() else 0
        return response(data={"currentStatus": currentStatus,
                              "collection": self.model.db["collection"]})

    @Route(methods="get", resource="/network/dhcpd/:id")
    def get_id(self, message, response):
        iface_list = self.get_ifcg_interface()
        for item in self.model.db["collection"]:
            # /network/dhcpd/:id
            # check interface exist in ifconfig and db
            if (item["id"] == int(message.param["id"])) and \
               item["name"] in iface_list:
                return response(data=item)
        return response(code=400, data={"message": "Invaild ID"})

    @Route(methods="put", resource="/network/dhcpd/:id")
    def put_id(self, message, response):
        if not hasattr(message, "data"):
            return response(code=400, data={"message": "Invaild Input"})
        logger.debug("input message: %s" % message.data)
        # check put id and db collection id is match
        id_match = False
        for item in self.model.db["collection"]:
            if item["id"] == message.data["id"]:
                id_match = True
        if id_match is False:
            return response(code=400, data={"message": "Invaild ID"})
        put_name = message.data["name"]
        # check name
        if put_name in self.permittedName:
            # update db by put data
            update_rc = self.update_db(message)
            self.model.save_db()
            if update_rc is not True:
                return response(code=400, data={"message": "Update DB error"})
            # update config file
            update_config_rc = self.update_config_file()
            if update_config_rc is not True:
                return response(code=400, data={"message":
                                "Update config error."})
            # restart model
            restart_rc = self.dhcp_restart()
            # check dhcpd process exist
            status_rc = self.get_status()
            # check enable data of id
            enable_flag = False
            if int(message.data["enable"]) == 1:
                enable_flag = True

            if (enable_flag is True) and \
               (restart_rc is False or status_rc is False):
                return response(code=400, data={"message":
                                                "Restart DHCP failed"})
            # save to db
            self.model.save_db()
            collection_index = message.data["id"] - 1
            return response(data=self.model.db["collection"][collection_index])
        return response(code=400, data={"message": "Invaild input ID"})

    @Route(methods="put", resource="/network/ethernets/:id")
    def hook(self, message, response):
        # get ethernet interface name
        if "name" not in message.data:
            return response(code=400, data={"message":
                                            "name not exist"})
        name = message.data["name"]
        logger.info("DHCP server is restarting.\
                     Due to %s setting had been chanaged" % name)
        update_rc = self.update_db(dict(id=id, enable=0))
        self.model.save_db()
        if update_rc is not True:
            return response(code=400, data={"message": "DHCP server hook\
                                             ethernet: Update db error"})
        # update config
        update_config_rc = self.update_config_file()
        if update_config_rc is not True:
            return response(code=400, data={"message": "DHCP server hook\
                                             ethernet: Update config error"})
        # restart model
        restart_rc = self.dhcp_restart()
        # check dhcpd process exist
        status_rc = self.get_status()
        if restart_rc is False or status_rc is False:
            return response(code=400, data={"message": "DHCP server hook\
                                            ethernet: Restart DHCP failed"})
        # save to db
        self.model.save_db()
        return response(data=self.model.db)

    def update_db(self, message):
        data = dict((key, value) for key, value in message.data.items()
                    if key in self.permittedKeys)
        logger.debug("update_db data: %s" % data)
        # find id correspond collection data
        try:
            # assign put request data to db
            for index, item in enumerate(self.model.db["collection"]):
                # check request data id and db id is match or not
                if item["id"] == data["id"]:
                    # self.collectionIndex = index
                    db_data = self.model.db["collection"]
                    # update db data by dictionary add
                    db_data[index] = dict(db_data[index].items() +
                                          data.items())
        except Exception as e:
            logger.info("Exception error: %s" % e)
            return False
        return True

    def get_ifcg_interface(self):
        try:
            interfaces = os.listdir("/sys/class/net")
            rc_interface = [x for x in interfaces if x != "lo"]
            return rc_interface
        except Exception as e:
            logger.info("cannot get interfaces: %s" % e)

    def dhcp_restart(self):
        self.dhcp_stop()
        restart_rc = self.dhcp_start()
        if restart_rc is True:
            return True
        return False

    def dhcp_stop(self):
        stop_rc = subprocess.call(["killall", "dhcpd"])
        if stop_rc == 0:
            logger.info("DHCP server is stopped")
        return True

    def dhcp_start(self):
        interfaces = self.get_ifcg_interface()
        start_rc = subprocess.call("dhcpd %s" % " ".join(interfaces),
                                   shell=True)
        if start_rc == 0:
            logger.info("DHCP Server start success")
            return True
        else:
            logger.info("DHCP Server start failed")
            return False

    def update_config_file(self):
        subnets = ""
        try:
            iface_list = self.get_ifcg_interface()
            for item in [v for v in self.model.db["collection"]]:
                # check if id exist in ifconfig interface or not
                if item["name"] not in iface_list:
                    continue

                # check if enable equal to 1 or not
                if item.get("enable", 0) != 1:
                    continue

                # get IP from ifconfig and assign to default route
                print "in update_config_file"
                item["routers"] = self.get_interface_ip(item["name"])

                # if dns_list is empty, we don't put option in settings
                if len(item["dns"]) != 0:
                    cmd = ""
                    cmd = "option domain-name-servers " + \
                        ", ".join(item["dns"]) + \
                        ";"
                    item["domainNameServers"] = cmd
                else:
                    item["domainNameServers"] = ""

                # executing template
                subnets += self.template["subnet"].substitute(item) + \
                    "\n\n"

            # all subnets template replace in dhcpd.conf
            conf_str = self.template["dhcpd.conf"].substitute(subnets=subnets)
            # write to dhcpd.conf
            with open(dhcpd_config_path, "w") as f:
                f.write(conf_str)
            logger.info("DHCPD config is updated")
            return True
        except Exception as e:
            logger.debug("update config file error: %s" % e)
            return False

    def get_interface_ip(self, iface):
        cmd = ""
        cmd = ("ip addr show %s | grep inet | grep -v inet6 | awk '{print $2}'"
               % iface)
        try:
            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)
            out = process.communicate()[0]
            ip = out.split("/")[0]
            return ip
        except Exception as e:
            logger.debug("get interface ip error: %s" % e)

    def get_status(self):
        cmd = ("ps aux | grep dhcpd | grep -v grep | grep -v python")
        out = subprocess.call(cmd, shell=True)
        if out == 0:
            return True
        else:
            return False

if __name__ == '__main__':
    FORMAT = '%(asctime)s - %(levelname)s - %(lineno)s - %(message)s'
    logging.basicConfig(level=0, format=FORMAT)
    logger = logging.getLogger("ssh")

    dhcpd = Dhcpd(connection=Mqtt())
    dhcpd.start()
