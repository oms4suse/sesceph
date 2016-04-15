# Python imports
import logging

# Local imports
import utils
import service

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
        self.model.init = "systemd"


    def mon_is(self):
        if self.model.hostname is None:
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
        arguments = {
                'identifier' : self.model.hostname,
                'service' : "ceph-mon",
            }
        init_system = service.init_system(init_type=self.model.init)
        return init_system.is_running(**arguments)

    def cluster_quorum(self):
        """
        Present the cluster quorum status
        """
        if self.model.cluster_status is None:
            log.debug("self.model.cluster_status is None")
            return False
        return True


    def ceph_daemon_user(self):
        if self.model.ceph_version.major == 0:
            if self.model.ceph_version.minor < 95:
                return "root"
        return "ceph"
