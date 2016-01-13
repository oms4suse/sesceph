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



class Error(Exception):
    """
    Error
    """

    def __str__(self):
        doc = self.__doc__.strip()
        return ': '.join([doc] + [str(a) for a in self.args])



JOURNAL_UUID = '45b0969e-9b03-4f30-b4c6-b4b80ceff106'
OSD_UUID = '4fbd7e29-9d25-41b8-afd0-062c0ceff05d'


def _excuete_local_command(command_attrib_list):
    output= __salt__['cmd.run_all'](command_attrib_list,
                                      output_loglevel='trace',
                                      python_shell=False)
    return output



def partions_all():
    '''
    List all partion details

    CLI Example::

        salt '*' sesceph.partions_all
    '''
    cmd = ["lsblk", "--ascii", "--output-all", "--pairs", "--paths", "--bytes"]
    output = __salt__['cmd.run_all'](cmd,
                                      output_loglevel='trace',
                                      python_shell=False)
    if output['retcode'] != 0:
        raise Error("Failed running: lsblk --ascii --output-all")
    all_parts = {}
    for line in output['stdout'].split('\n'):
        partion = {}
        for token in shlex.split(line):
            token_split = token.split("=")
            if len(token_split) == 1:
                continue
            key = token_split[0]
            value = "=".join(token_split[1:])
            if len(value) == 0:
                continue
            partion[key] = value

        part_name = partion.get("NAME")
        if part_name == None:
            continue
        part_type = partion.get("TYPE")
        if part_type == "disk":
            all_parts[part_name] = partion
            continue
        disk_name = partion.get("PKNAME")
        if not disk_name in all_parts:
            continue
        if None == all_parts[disk_name].get("PARTITION"):
            all_parts[disk_name]["PARTITION"] = {}
        all_parts[disk_name]["PARTITION"][part_name] = partion
    return all_parts




def discover_osd_partions():
    '''
    List all OSD and journel partions

    CLI Example::

        salt '*' sesceph.discover_osd_partions
    '''
    osd_all = {}
    journel_all = {}
    try:
        partions_struct = partions_all()
    except Error, e:
        log.info(" dir(e)")
        return osd_all,journel_all
    for diskname in partions_struct.keys():
        disk = partions_struct.get(diskname)
        if disk == None:
            continue
        part_struct = disk.get("PARTITION")
        if part_struct == None:
            continue
        for partname in part_struct.keys():
            part_details = part_struct.get(partname)
            part_type = part_details.get("PARTTYPE")
            if part_type == OSD_UUID:
                osd_all[partname] = part_details
            if part_type == JOURNAL_UUID:
                journel_all[partname] = part_details
    return osd_all,journel_all

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


def discover_osd():
    discovered_osd = {}
    discovered_osd_ret = discover_osd_partions()
    if discovered_osd_ret == None:
        return discovered_osd
    partions_osd_struct, partions_journel_struct = discovered_osd_ret
    # now we map UUID to NAME for both osd and journel

    unmounted_parts = set()
    for part_name in partions_osd_struct.keys():
        part_details = partions_osd_struct.get(part_name)
        output = _retrive_osd_details(part_details)
        if output == None:
            print "we have more to code here"
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
    return discovered_osd

def get_dev_name(path):
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

    name = get_dev_name(dev)
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
             'partprobe',
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
                'sgdisk',
                '--zap-all',
                '--',
                dev,
            ],
        )
        _excuete_local_command(
            [
                'sgdisk',
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
    prepare takes a lot of variables

    CLI Example::

        salt '*' sesceph.prepare "{'osd' : '/dev/vdc', 'partion' : 'ding' }"
    """
    cluster_name = kwargs.get("cluster_name","ceph")
    osd_dev = kwargs.get("osd_dev")
    journel_dev = kwargs.get("journel_dev")
    cluster_name = kwargs.get("cluster_name")
    cluster_uuid = kwargs.get("cluster_uuid")

    # Default cluster name / uuid values
    if cluster_name == None and cluster_uuid == None:
        cluster_name = "ceph"
    if cluster_name != None and cluster_uuid == None:
        cluster_uuid = _get_cluster_uuid_from_name(cluster_name)
    if cluster_name == None and cluster_uuid != None:
        cluster_name = _get_cluster_name_from_uuid(cluster_name)

    fs_type = kwargs.get("fs_type","xfs")
    # Check required variables are set
    if osd_dev == None:
        raise Error("osd_dev not specified")

    # normalise paths
    osd_dev = os.path.realpath(osd_dev)
    # get existing state and see if action needed

    storage_tree = partions_all()
    block_details_osd = storage_tree.get(osd_dev)
    if block_details_osd == None:
        raise Error("Not a block device")

    part_table = block_details_osd.get("PARTITION")
    if part_table == None:
        raise Error("Programming error")
    if len(part_table.keys()) > 0:
        return True
    arguments = [
        'ceph-disk',
        '-v',
        'prepare',
        '--fs-type',
        fs_type
        ]
    if osd_dev != None:
        arguments.append("--data-dev")
        arguments.append(osd_dev)
    if journel_dev != None:
        arguments.append("--journal-dev")
        arguments.append(journel_dev)
    if cluster_name != None:
        arguments.append("--cluster")
        arguments.append(cluster_name)
    if cluster_uuid != None:
        arguments.append("--cluster-uuid")
        arguments.append(cluster_uuid)

    output = _excuete_local_command(arguments)
    if output["retcode"] != 0:
        raise Error("Error rc=%s, stdout=%s stderr=%s" % (output["retcode"], output["stdout"], output["stderr"]))
    return True



def __virtual__():
    return __virtualname__
