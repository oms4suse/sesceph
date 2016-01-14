import logging
import shlex
import tempfile
import stat
import ConfigParser
import os.path
import os

log = logging.getLogger(__name__)

__virtualname__ = 'sesceph'

__has_salt = True

try:
    import salt.client
    import salt.config
except :
    __has_salt = False

try:
    from salt.utils import which as _find_executable
except:
    from distutils.spawn import _find_executable


_path_lsblk = _find_executable('lsblk')
_path_ceph_disk = _find_executable('ceph-disk')
_path_partprobe = _find_executable('partprobe')
_path_sgdisk = _find_executable('sgdisk')

class Error(Exception):
    """
    Error
    """

    def __str__(self):
        doc = self.__doc__.strip()
        return ': '.join([doc] + [str(a) for a in self.args])


def __virtual__():
    if not _path_lsblk:
        log.info("Error 'lsblk' command not find.")
        return False
    return __virtualname__


JOURNAL_UUID = '45b0969e-9b03-4f30-b4c6-b4b80ceff106'
OSD_UUID = '4fbd7e29-9d25-41b8-afd0-062c0ceff05d'


def _excuete_local_command(command_attrib_list):
    if '__salt__' in locals():
        return __salt__['cmd.run_all'](command_attrib_list,
                                      output_loglevel='trace',
                                      python_shell=False)

    # if we cant exute subprocess with salt, use python
    import subprocess
    output= {}
    proc=subprocess.Popen(command_attrib_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
    output['stdout'], output['stderr'] = proc.communicate()

    output['retcode'] = proc.returncode
    return output


def _retrive_osd_details_from_dir(directory):
    osd_required_files = set(["ceph_fsid","fsid"])
    osd_details = {}
    dir_content = os.listdir(directory)
    if not osd_required_files.issubset(dir_content):
        return None
    with open('%s/ceph_fsid' % (directory), 'r') as infile:
        osd_details["ceph_fsid"] = infile.read().strip()
    with open('%s/fsid' % (directory), 'r') as infile:
        osd_details["fsid"] = infile.read().strip()
    with open('%s/journal_uuid' % (directory), 'r') as infile:
        osd_details["journal_uuid"] = infile.read().strip()
    with open('%s/magic' % (directory), 'r') as infile:
        osd_details["magic"] = infile.read().strip()
    path_whoami = '%s/whoami' % (directory)
    if os.path.isfile(path_whoami):
        with open('%s/whoami' % (directory), 'r') as infile:
            osd_details["whoami"] = infile.read().strip()
    path_link = '%s/journal' % (directory)
    if os.path.islink(path_link):
        osd_details["dev_journal"] = os.path.realpath(path_link)

    return osd_details



def _retrive_osd_details(part_details):
    osd_details = {}
    device_name = part_details.get("NAME")
    if device_name == None:
        return None
    try:
        tmpd = tempfile.mkdtemp()
        try:
            out_mnt = _excuete_local_command(['mount',device_name,tmpd])
            if out_mnt['retcode'] == 0:
                osd_details = _retrive_osd_details_from_dir(tmpd)
        finally:
            _excuete_local_command(['umount',tmpd])
    finally:
        os.rmdir(tmpd)
    return osd_details


class _model:
    """
    Basic model class to store detrived data
    """
    def __init__(self):
        # map device to symlinks
        self.symlinks = {}
        self.lsblk = {}
        # map partition to pairent
        self.part_pairent = {}
        self.partitions_osd = {}
        self.partitions_journal = {}


class _model_updator():
    """
    Basic model updator retrives data and adds to model
    """
    def __init__(self, model):
        self.model = model

    def symlinks_refresh(self):
        '''
        List all symlinks under /dev/disk/
        '''
        interesting_dirs = set(["by-path","by-id","by-uuid","by-partuuid"])
        paths = {}
        for root, dirs, files in os.walk("/dev/disk/"):
            path_head, path_tail = os.path.split(root)
            if not path_tail in interesting_dirs:
                continue
            for file_name in files:
                file_path = os.path.join(root,file_name)
                if not os.path.islink(file_path):
                    continue
                real_path = os.path.realpath(file_path)
                if not real_path in paths.keys():
                    paths[real_path] = []
                paths[real_path].append(file_path)
        self.model.symlinks = paths

    def partitions_all_refresh(self):
        '''
        List all partition details

        CLI Example:

            salt '*' sesceph.partitions_all
        '''
        part_map = {}
        cmd = [ _path_lsblk, "--ascii", "--output-all", "--pairs", "--paths", "--bytes"]
        output = _excuete_local_command(cmd)
        if output['retcode'] != 0:
            raise Error("Failed running: lsblk --ascii --output-all")
        all_parts = {}
        for line in output['stdout'].split('\n'):
            partition = {}
            for token in shlex.split(line):
                token_split = token.split("=")
                if len(token_split) == 1:
                    continue
                key = token_split[0]
                value = "=".join(token_split[1:])
                if len(value) == 0:
                    continue
                partition[key] = value

            part_name = partition.get("NAME")
            if part_name == None:
                continue
            part_type = partition.get("TYPE")
            if part_type == "disk":
                all_parts[part_name] = partition
                continue
            disk_name = partition.get("PKNAME")
            if not disk_name in all_parts:
                continue
            part_map[part_name] = disk_name
            if None == all_parts[disk_name].get("PARTITION"):
                all_parts[disk_name]["PARTITION"] = {}
            all_parts[disk_name]["PARTITION"][part_name] = partition
        self.model.lsblk = all_parts
        self.model.part_pairent = part_map






    def discover_partitions_refresh(self):
        '''
        List all OSD and journal partitions

        CLI Example:

            salt '*' sesceph.discover_osd_partitions
        '''
        osd_all = set()
        journal_all = set()
        for diskname in self.model.lsblk.keys():
            disk = self.model.lsblk.get(diskname)
            if disk == None:
                continue
            part_struct = disk.get("PARTITION")
            if part_struct == None:
                continue
            for partname in part_struct.keys():
                part_details = part_struct.get(partname)
                if part_details == None:

                    continue
                part_type = part_details.get("PARTTYPE")
                if part_type == OSD_UUID:
                    osd_all.add(partname)
                if part_type == JOURNAL_UUID:
                    journal_all.add(partname)
        self.model.partitions_osd = osd_all
        self.model.partitions_journal = journal_all



    def discover_osd_refresh(self):
        discovered_osd = {}
        # now we map UUID to NAME for both osd and journal
        unmounted_parts = set()
        for part_name in self.model.partitions_osd:
            diskname = self.model.part_pairent.get(part_name)
            if diskname == None:
                continue
            disk = self.model.lsblk.get(diskname)
            if disk == None:
                continue
            part_struct = disk.get("PARTITION")
            if part_struct == None:
                continue
            part_details = part_struct.get(part_name)
            output = _retrive_osd_details(part_details)
            if output == None:
                continue
            output["dev"] = part_details.get("NAME")
            output["dev_parent"] = part_details.get("PKNAME")
            ceph_fsid = output.get("ceph_fsid")
            if not ceph_fsid in discovered_osd.keys():
                discovered_osd[ceph_fsid] = []
            discovered_osd[ceph_fsid].append(output)
        for cluser_id in discovered_osd.keys():
            osd_data_list = discovered_osd.get(cluser_id)
            for osd_data in osd_data_list:
                fsid = osd_data.get("fsid")
                journal_uuid = osd_data.get("journal_uuid")
        self.model.discovered_osd = discovered_osd


class _mdl_presentor():
    """
    Since presentation should be clean to the end user
    We abstract such functiosn in this class.
    """
    def __init__(self, model):
        self.model = model

    def lsblk_partition_by_disk_part(self, part):
        output = {}
        disk = self.model.part_pairent.get(part)
        if disk == None:
            return None
        disk_details = self.model.lsblk.get(disk)
        if disk_details == None:
            return None
        symlinks = self.model.symlinks.get(part)
        if symlinks != None:
            output["LINK"] = symlinks
        wanted_keys = set([
                'SIZE',
                'NAME',
                'VENDOR',
                'UUID',
                'PARTLABEL',
                'PKNAME',
                'FSTYPE',
                'PARTTYPE',
                'MOUNTPOINT',
                'PARTUUID',
                'ROTA',
                'SCHED',
                'RQ-SIZE'
            ])

        all_parts = disk_details.get('PARTITION')
        if all_parts == None:
            return None
        part_details = all_parts.get(part)
        if part_details == None:
            return None
        for key in part_details:
            if not key in wanted_keys:
                continue
            output[key] = part_details.get(key)

        return output

    def lsblk_disk_by_disk(self, disk):
        output = {}
        disk_details = self.model.lsblk.get(disk)
        if disk_details == None:
            return None
        symlinks = self.model.symlinks.get(disk)
        if symlinks != None:
            output["LINK"] = symlinks
        wanted_keys = set([
                'SIZE',
                'NAME',
                'VENDOR',
                'ROTA',
                'SCHED',
                'RQ-SIZE'
            ])
        for key in disk_details:
            if key == 'PARTITION':
                part_list = []
                for part in disk_details['PARTITION'].keys():
                    part_info = self.lsblk_partition_by_disk_part(part)
                    if part_info == None:
                        continue
                    part_list.append(part_info)
                output["PARTITION"] = part_list
            if not key in wanted_keys:
                continue
            output[key] = disk_details.get(key)

        return output




    def partitions_all(self):
        '''
        List all partition details

        CLI Example::

            salt '*' sesceph.partitions_all
        '''
        output = {}
        for disk in self.model.lsblk.keys():
            output[disk] = self.lsblk_disk_by_disk(disk)

        return output



    def discover_osd_by_cluster_uuid(self,cluster_uuid):
        osd_out_list = []
        osd_in_list = self.model.discovered_osd.get(cluster_uuid)
        if osd_in_list == None:
            return osd_out_list
        for osd_in in osd_in_list:
            osd_out = {}
            for key in osd_in.keys():
                if key in ["ceph_fsid", "dev_parent"]:
                    continue
                osd_out[key] = osd_in.get(key)
            osd_out_list.append(osd_out)
        return osd_out_list

    def discover_osd(self):
        output = {}
        for cluster in self.model.discovered_osd.keys():
            output[cluster] = self.discover_osd_by_cluster_uuid(cluster)
        return output

    def discover_osd_partitions(self):
        '''
        List all OSD and journal partitions

        CLI Example:

            salt '*' sesceph.discover_osd_partitions
        '''
        output = []
        for part_name in self.model.partitions_osd:
            part_info = self.lsblk_partition_by_disk_part(part_name)
            if part_info == None:
                continue
            output.append(part_info)
        return output

    def discover_journal_partitions(self):
        '''
        List all OSD and journal partitions

        CLI Example:

            salt '*' sesceph.discover_osd_partitions
        '''
        output = []
        for part_name in self.model.partitions_journal:
            part_info = self.lsblk_partition_by_disk_part(part_name)
            if part_info == None:
                continue
            output.append(part_info)
        return output

def partitions_all():
    '''
    List partitions by disk

    CLI Example:

        salt '*' sesceph.partitions_all
    '''
    m = _model()
    u = _model_updator(m)
    u.symlinks_refresh()
    u.partitions_all_refresh()
    p = _mdl_presentor(m)
    return p.partitions_all()

def osd_partitions():
    '''
    List all OSD data partitions by partition

    CLI Example:

        salt '*' sesceph.osd_partitions
    '''
    m = _model()
    u = _model_updator(m)
    u.symlinks_refresh()
    u.partitions_all_refresh()
    u.discover_partitions_refresh()
    p = _mdl_presentor(m)
    return p.discover_osd_partitions()


def journal_partitions():
    '''
    List all OSD journal partitions by partition

    CLI Example:

        salt '*' sesceph.journal_partitions
    '''
    m = _model()
    u = _model_updator(m)
    u.symlinks_refresh()
    u.partitions_all_refresh()
    u.discover_partitions_refresh()
    p = _mdl_presentor(m)
    return p.discover_journal_partitions()

def discover_osd():
    """
    List all OSD by cluster

    CLI Example:

        salt '*' sesceph.discover_osd

    """
    m = _model()
    u = _model_updator(m)

    u.symlinks_refresh()
    u.partitions_all_refresh()
    u.discover_partitions_refresh()
    u.discover_osd_refresh()
    p = _mdl_presentor(m)
    return p.discover_osd()


def _get_dev_name(path):
    """
    get device name from path.  e.g.::

        /dev/sda -> sdas, /dev/cciss/c0d1 -> cciss!c0d1

    a device "name" is something like::

        sdb
        cciss!c0d1

    """
    assert path.startswith('/dev/')
    base = path[5:]
    return base.replace('/', '!')

def is_partition(dev):
    """
    Check whether a given device path is a partition or a full disk.
    """
    dev = os.path.realpath(dev)
    if not stat.S_ISBLK(os.lstat(dev).st_mode):
        raise Error('not a block device', dev)

    name = _get_dev_name(dev)
    if os.path.exists(os.path.join('/sys/block', name)):
        return False

    # make sure it is a partition of something else
    for basename in os.listdir('/sys/block'):
        if os.path.exists(os.path.join('/sys/block', basename, name)):
            return True

    raise Error('not a disk or partition', dev)


def _update_partition(action, dev, description):
    # try to make sure the kernel refreshes the table.  note
    # that if this gets ebusy, we are probably racing with
    # udev because it already updated it.. ignore failure here.

    # On RHEL and CentOS distros, calling partprobe forces a reboot of the
    # server. Since we are not resizing partitons so we rely on calling
    # partx

    _excuete_local_command(
        [
             _path_partprobe,
             dev,
        ],
    )



def zap(dev):
    """
    Destroy the partition table and content of a given disk.
    """
    dmode = os.stat(dev).st_mode
    if not stat.S_ISBLK(dmode) or is_partition(dev):
        raise Error('not full block device; cannot zap', dev)
    try:
        log.debug('Zapping partition table on %s', dev)

        # try to wipe out any GPT partition table backups.  sgdisk
        # isn't too thorough.
        lba_size = 4096
        size = 33 * lba_size
        with file(dev, 'wb') as dev_file:
            dev_file.seek(-size, os.SEEK_END)
            dev_file.write(size*'\0')

        _excuete_local_command(
            [
                _path_sgdisk,
                '--zap-all',
                '--',
                dev,
            ],
        )
        _excuete_local_command(
            [
                _path_sgdisk,
                '--clear',
                '--mbrtogpt',
                '--',
                dev,
            ],
        )


        _update_partition('-d', dev, 'zapped')
        return 0
    except subprocess.CalledProcessError as e:
        raise Error(e)
    return 0



def _get_cluster_uuid_from_name(cluster_name):
    configfile = "/etc/ceph/%s.conf" % (cluster_name)
    if not os.path.isfile(configfile):
        raise Error("Cluster confg file does not exist:'%s'" % configfile)
    config = ConfigParser.ConfigParser()
    config.read(configfile)
    try:
        fsid = config.get("global","fsid")
    except ConfigParser.NoOptionError:
        raise Error("Cluster confg file does not sewt fsid:'%s'" % configfile)
    return fsid

def _get_cluster_name_from_uuid(cluster_uuid):
    output = None
    dir_content = os.listdir("/etc/ceph/")
    for file_name in dir_content:
        if file_name[-5:] != ".conf":
            continue
        fullpath = os.path.join("/etc/ceph/", file_name)
        print fullpath

        config = ConfigParser.ConfigParser()
        config.read(fullpath)
        try:
            fsid = config.get("global","fsid")
            if fsid != None:
                output = file_name[:-5]
        except:
            continue
    return output

def osd_prepare(**kwargs):
    """
    prepare an OSD

    CLI Example:

        salt '*' sesceph.osd_prepare 'osd_dev'='/dev/vdc' \
                'journal_dev'='device' \
                'cluster_name'='ceph' \
                'cluster_uuid'='cluster_uuid' \
                'osd_fs_type'='xfs' \
                'osd_uuid'='2a143b73-6d85-4389-a9e9-b8a78d9e1e07' \
                'journal_uuid'='4562a5db-ff6f-4268-811d-12fd4a09ae98'
    Notes:

    cluster_uuid
        Set the deivce to store the osd data on.

    journal_dev
        Set the journal device. defaults to osd_dev.

    cluster_name
        Set the cluster name. Defaults to "ceph".

    cluster_uuid
        Set the cluster date will be added too. Defaults to the value found in local config.

    osd_fs_type
        set the file system to store OSD data with. Defaults to "xfs".

    osd_uuid
        set the OSD data UUID. If set will return if OSD with data UUID already exists.

    journal_uuid
        set the OSD journal UUID. If set will return if OSD with journal UUID already exists.
    """
    osd_dev_raw = kwargs.get("osd_dev")
    journal_dev = kwargs.get("journal_dev")
    cluster_name = kwargs.get("cluster_name")
    cluster_uuid = kwargs.get("cluster_uuid")
    fs_type = kwargs.get("osd_fs_type")
    osd_uuid = kwargs.get("osd_uuid")
    journal_uuid = kwargs.get("journal_uuid")
    # Default cluster name / uuid values
    if cluster_name == None and cluster_uuid == None:
        cluster_name = "ceph"
    if cluster_name != None and cluster_uuid == None:
        cluster_uuid = _get_cluster_uuid_from_name(cluster_name)
    if cluster_name == None and cluster_uuid != None:
        cluster_name = _get_cluster_name_from_uuid(cluster_name)

    fs_type = kwargs.get("fs_type","xfs")
    # Check required variables are set
    if osd_dev_raw == None:
        raise Error("osd_dev not specified")

    # Check boot strap key exists
    if os.path.isfile("/var/lib/ceph/bootstrap-osd/ceph.keyring"):
        raise Error("File not found /var/lib/ceph/bootstrap-osd/ceph.keyring")

    # normalise paths
    osd_dev = os.path.realpath(osd_dev_raw)
    # get existing state and see if action needed

    m = _model()
    u = _model_updator(m)
    u.partitions_all_refresh()
    u.discover_partitions_refresh()
    u.discover_osd_refresh()

    # Validate the osd_uuid and journal_uuid dont already exist

    osd_list_existing = m.discovered_osd.get(cluster_uuid)
    if osd_list_existing != None:
        for osd_existing in osd_list_existing:
            if osd_uuid != None:
                osd_existing_fsid = osd_existing.get("fsid")
                if osd_existing_fsid == osd_uuid:
                    log.debug("osd_uuid already exists:%s" % (osd_uuid))
                    return True

            if journal_uuid != None:
                journal_existing_uuid = osd_existing.get("journal_uuid")
                if journal_existing_uuid == journal_uuid:
                    log.debug("journal_uuid already exists:%s" % (journal_uuid))
                    return True

    block_details_osd = m.lsblk.get(osd_dev)
    if block_details_osd == None:
        raise Error("Not a block device")

    part_table = block_details_osd.get("PARTITION")
    if part_table != None:
        if len(part_table.keys()) > 0:
            return True


    if not _path_ceph_disk:
        raise Error("Error 'ceph-disk' command not find")
    arguments = [
        _path_ceph_disk,
        '-v',
        'prepare',
        '--fs-type',
        fs_type
        ]
    if osd_dev != None:
        arguments.append("--data-dev")
        arguments.append(osd_dev)
    if journal_dev != None:
        arguments.append("--journal-dev")
        arguments.append(journal_dev)
    if cluster_name != None:
        arguments.append("--cluster")
        arguments.append(cluster_name)
    if cluster_uuid != None:
        arguments.append("--cluster-uuid")
        arguments.append(cluster_uuid)
    if osd_uuid != None:
        arguments.append("--osd-uuid")
        arguments.append(osd_uuid)
    if journal_uuid != None:
        arguments.append("--journal-uuid")
        arguments.append(journal_uuid)

    output = _excuete_local_command(arguments)
    if output["retcode"] != 0:
        raise Error("Error rc=%s, stdout=%s stderr=%s" % (output["retcode"], output["stdout"], output["stderr"]))
    return True



