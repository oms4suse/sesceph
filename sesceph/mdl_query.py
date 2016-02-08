import logging

import utils

log = logging.getLogger(__name__)


class Error(Exception):
    """
    Error
    """

    def __str__(self):
        doc = self.__doc__.strip()
        return ': '.join([doc] + [str(a) for a in self.args])


class mdl_query():
    """
    This is for querying the model with common queries,
    that are internal.
    """
    def __init__(self, model):
        self.model = model

    def mon_is(self):
        if self.model.hostname == None:
            raise Error("Programming error: Hostname not detected")
        for hostname, addr in self.model.mon_members:
            if hostname == self.model.hostname:
                return True
        return False

    def mon_quorum(self):
        """
        Present the monitor status
        """
        if (None == self.model.mon_status):
            return False
        name = self.model.mon_status.get("name")
        outside_quorum = self.model.mon_status.get("outside_quorum")
        if name in outside_quorum:
            return False
        return True


    def mon_active(self):
        systemctl_name = "ceph-mon@%s.service" % (self.model.hostname)
        arguments = [
            'systemctl',
            'show',
            '--property',
            'ActiveState',
            systemctl_name,
            ]
        log.debug("Running:%s" % (" ".join(arguments)))
        output = utils.excuete_local_command(arguments)
        if output["retcode"] != 0:
            raise Error("Failed executing '%s' Error rc=%s, stdout=%s stderr=%s" % (
                " ".join(arguments),
                output["retcode"],
                output["stdout"],
                output["stderr"]
                ))
        running = None
        for raw_line in output["stdout"].split('\n'):
            stripline = raw_line.strip()
            if len(stripline) == 0:
                continue
            splitline = stripline.split('=')
            if len(splitline) < 2:
                continue
            key = splitline[0]
            value = "=".join(splitline[1:])
            if key == "ActiveState":
                if value == "active":
                    running = True
                else:
                    running = False
        if running == None:
            raise Error("failed to get ActiveState from %s" % (systemctl_name))
        return running
    def ceph_daemon_user(self):
        if self.model.ceph_version.major == 0:
            if self.model.ceph_version.minor < 81:
                return "root"
        return "ceph"
