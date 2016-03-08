import ConfigParser


class version:
    def __init__(self, **kwargs):
        self.major = kwargs.get("major")
        self.minor = kwargs.get("minor")
        self.revision = kwargs.get("revision")
        self.uuid = kwargs.get("uuid")


    def __repr__(self):
        if self.major is None:
            return "<version(None)>"
        if self.minor is None:
            return "<version(%s)>" % (self.major)
        if self.revision is None:
            return "<version(%s,%s)>" % (self.major, self.minor)
        if self.uuid is None:
            return "<version(%s,%s,%s)>" % (self.major, self.minor, self.revision)
        return "<version(%s,%s,%s,%s)>" % (self.major, self.minor, self.revision, self.uuid)


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
        self.ceph_version = version()
        self.lsblk_version = version()
        # Result of local query of mon status
        self.mon_status = None


    def kargs_apply(self, **kwargs):
        self.cluster_name = kwargs.get("cluster_name")
        self.cluster_uuid = kwargs.get("cluster_uuid")
        self.secret = kwargs.get("secret", None)
