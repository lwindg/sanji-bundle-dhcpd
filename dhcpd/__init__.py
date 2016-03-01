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
    Required("netmask"): All(Any(unicode, str), Length(7, 15)),
    Required("startIP"): All(Any(unicode, str), Length(7, 15)),
    Required("endIP"): All(Any(unicode, str), Length(7, 15)),
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
                output = sh.service(self.service_name, command, _bg=bg)
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
    range %(startIP)s %(endIP)s;
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
            (unicode(self["startIP"]), self["netmask"]), strict=False)

        subnetIP = [_ for _ in ipv4.subnets(prefixlen_diff=0)][0]\
            .network_address

        domainNameServers = [_ for _ in self["domainNameServers"]
                             if len(_) > 0]
        subnet = {
            "name": self["name"],
            "subnetIP": subnetIP,
            "netmask": self["netmask"],
            "startIP": self["startIP"],
            "endIP": self["endIP"],
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

    def update_service(self, restart=True):
        """Update dhcpd.config and restart service if restart set to True"""
        subnets = []
        for subnet in self.getAll():
            if subnet["enable"] is False:
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

        newSubnet = super(DHCPD, self).update(id=id, newObj=newObj)
        self.update_service()

        return newSubnet
