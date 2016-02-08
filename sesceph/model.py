import ConfigParser


class ceph_version:
    def __init__(self, **kwargs):
        self.major = kwargs.get("major")
        self.minor = kwargs.get("minor")
        self.revision = kwargs.get("revision")
        self.uuid = kwargs.get("uuid")


class model:
    """
    Basic model class to store detrived data
    """
    def __init__(self, **kwargs):
        # map device to symlinks
        self.symlinks = {}
        self.lsblk = {}
        # map partition to pairent
        self.part_pairent = {}
        self.partitions_osd = {}
        self.partitions_journal = {}
        self.ceph_conf = ConfigParser.ConfigParser()
        # list of (hostname,addr) touples
        self.mon_members = []
        self.hostname = None
        self.kargs_apply(**kwargs)
        self.ceph_version = ceph_version()
        # Result of local query of mon status
        self.mon_status = None


    def kargs_apply(self, **kwargs):
        self.cluster_name = kwargs.get("cluster_name")
        self.cluster_uuid = kwargs.get("cluster_uuid")
