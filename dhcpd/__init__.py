import logging
import sh
import ipaddress

from sh import ErrorReturnCode
from sanji.model import Model
from voluptuous import Schema, REMOVE_EXTRA, Required, Any, Range, All, Length
_logger = logging.getLogger("sanji.dhcpd")

SUBNET_SCHEMA = Schema({
    "id": int,
    Required("name"): All(Any(unicode, str), Length(1, 255)),
    Required("enable"): bool,
    Required("available", default=False): bool,
    Required("netmask"): All(Any(unicode, str), Length(7, 15)),
    Required("startIp"): All(Any(unicode, str), Length(7, 15)),
    Required("endIp"): All(Any(unicode, str), Length(7, 15)),
    Required("domainNameServers"): [Any(unicode, str)],
    Required("domainName"): All(Any(unicode, str), Length(0, 255)),
    Required("leaseTime"): Range(min=60, max=65535)
}, extra=REMOVE_EXTRA)


def get_ip_by_interface(iface):
    ip = sh.awk(
        sh.grep(sh.grep(sh.ip("addr", "show", iface), "inet"),
                "-v", "inet6"), "{print $2}").split("/")[0]
    return ip


class Service(object):
    _logger = logging.getLogger("sanji.dhcpd.service")

    def __init__(self, service_name):
        self.service_name = service_name

    def __getattr__(self, command):
        if command not in ["start", "restart", "stop", "status"]:
            return super(Service, self).__getattr__(command)

        def do_command(bg=False):
            try:
                output = sh.systemctl(
                    "--no-page", command,
                    "{}.service".format(self.service_name),
                    _bg=bg, _no_out=True)
                self._logger.info(
                    "Service '%s' %s" % (self.service_name, command))
                return output.exit_code
            except ErrorReturnCode as e:
                self._logger.info(
                    "Service '%s' %s failed" %
                    (self.service_name, command))
                self._logger.debug(str(e))
                return e.exit_code

        return do_command


class Subnet(dict):
    SUBNET_TMPL = """##################### %(name)s ########################
subnet %(subnetIP)s netmask %(netmask)s {
    range %(startIp)s %(endIp)s;
    default-lease-time %(leaseTime)d;
    max-lease-time %(leaseTime)d;
    option domain-name-servers %(domainNameServers)s;
    %(domainNameString)s
    option routers %(routers)s;
}
"""

    def _convert(self):
        routers = get_ip_by_interface(self["name"])
        ipv4 = ipaddress.IPv4Network(
            (unicode(self["startIp"]), self["netmask"]), strict=False)

        subnetIP = [_ for _ in ipv4.subnets(prefixlen_diff=0)][0]\
            .network_address

        domainNameServers = [_ for _ in self["domainNameServers"]
                             if len(_) > 0]
        subnet = {
            "name": self["name"],
            "subnetIP": subnetIP,
            "netmask": self["netmask"],
            "startIp": self["startIp"],
            "endIp": self["endIp"],
            "leaseTime": self["leaseTime"],
            "routers": routers,
            "domainNameServers": ",".join(domainNameServers),
            "domainNameString": "" if len(self["domainName"]) == 0
            else "option domain-name \"%s\"" % (self["domainName"])
        }

        return subnet

    def to_config(self):
        subnet = self._convert()
        return self.SUBNET_TMPL % (subnet)


class DHCPD(Model):
    DHCPD_CONFIG = "/etc/dhcp/dhcpd.conf"
    DHCPD_TMPL = """# MOXA configuration file for ISC dhcpd for Debian
default-lease-time 600;
max-lease-time 7200;

# Use this to send dhcp log messages to a different log file (you also
# have to hack syslog.conf to complete the redirection).
log-facility local7;


#subnet 10.254.239.0 netmask 255.255.255.224 {
#  range 10.254.239.10 10.254.239.20;
#  option routers rtr-239-0-1.example.org, rtr-239-0-2.example.org;
#}
"""
    service = Service("isc-dhcp-server")

    def __init__(self, *args, **kwargs):
        kwargs["schema"] = SUBNET_SCHEMA
        kwargs["model_cls"] = Subnet
        super(DHCPD, self).__init__(*args, **kwargs)

        self.ifaces = []

    def update_service(self, restart=True):
        """Update dhcpd.config and restart service if restart set to True"""
        subnets = []
        for subnet in self.getAll():
            if not self._is_enable(subnet):
                continue
            subnets.append(subnet.to_config())
        dhcpd_config = self.DHCPD_TMPL + "\n\n".join(subnets)

        with open(self.DHCPD_CONFIG, "w") as f:
            f.write(dhcpd_config)
            _logger.debug("update dhcpd config: %s" % (self.DHCPD_CONFIG))

        if len(subnets) == 0:
            self.service.stop()
            return 0

        if restart is False:
            return 0

        self.service.restart(bg=True)

    def _is_available(self, iface):
        if iface["wan"] is False and \
                iface["mode"] == "static" and \
                (iface["type"] == "eth" or
                 iface["type"] == "wifi-ap"):
            return True
        else:
            return False

    def _is_enable(self, iface):
        if iface.get("available", False) is True and \
                iface["enable"] is True:
            return True
        else:
            return False

    def add(self, data):
        raise RuntimeError("Not support Add method")

    def remove(self, id):
        raise RuntimeError("Not support Remove method")

    def update(self, id, newObj):
        """Update an exist subnet, It will restart isc-dhcp-server
           only if update successfully > 0
           Returns:
               newLogProfile(logprofile): udpated logprofile
           Raises:
               ValueError: if device list contains invaild entry
        """
        subnet = self.get(id)
        if subnet is None:
            return None

        # use previous status
        newObj["available"] = subnet["available"]
        newSubnet = super(DHCPD, self).update(id=id, newObj=newObj)
        self.update_service()

        return newSubnet

    def update_iface_info(self, data):
        """Update the interface list.
        available: eth.static, wifi-aplstatic
        unavailable: eth.dhcp, wifi-client.static, wifi-client.dhcp, cellular

            Args:
                data: dict with interface name, type and mode

            type: eth/wifi-ap/wifi-client/cellular
            mode: static/dhcp
            [
                {
                    "name": "eth0",
                    "type": "eth",
                    "mode": "static"
                },
                {
                    "name": "wlan0",
                    "type": "wifi-ap",
                    "mode": "static"
                }
            ]
        """

        # update iface list
        for iface in self.ifaces:
            if iface["name"] == data["name"]:
                iface.update(data)
                break
        else:
            iface = data
            self.ifaces.append(iface)

        # update config
        for item in self.getAll():
            if item["name"] == iface["name"]:
                enable = self._is_enable(item)
                item["available"] = self._is_available(iface)
                super(DHCPD, self).update(id=item["id"], newObj=item)
                if enable != self._is_enable(item):
                    self.update_service()
                    _logger.info(
                        "DHCP server is restarted. Due to {} setting had"
                        "been changed".format(iface["name"]))
                break
