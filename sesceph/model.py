import ConfigParser


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


    def kargs_apply(self, **kwargs):
        self.cluster_name = kwargs.get("cluster_name")
        self.cluster_uuid = kwargs.get("cluster_uuid")

