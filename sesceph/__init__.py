import logging
import shlex
import tempfile
import stat
import ConfigParser
import os.path
import os
import platform
import json
import shutil
import constants

# local modules
import utils
from model import _model
from mdl_updater import _model_updator
from presenter import _mdl_presentor
from mdl_query import _mdl_query
from utils import _excuete_local_command
import keyring

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



class Error(Exception):
    """
    Error
    """

    def __str__(self):
        doc = self.__doc__.strip()
        return ': '.join([doc] + [str(a) for a in self.args])


def __virtual__():
    if not constants._path_lsblk:
        log.info("Error 'lsblk' command not find.")
        return False
    return __virtualname__


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
             constants._path_partprobe,
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
                constants._path_sgdisk,
                '--zap-all',
                '--',
                dev,
            ],
        )
        _excuete_local_command(
            [
                constants._path_sgdisk,
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
        cluster_uuid = utils._get_cluster_uuid_from_name(cluster_name)
    if cluster_name == None and cluster_uuid != None:
        cluster_name = utils._get_cluster_name_from_uuid(cluster_name)

    fs_type = kwargs.get("fs_type","xfs")
    # Check required variables are set
    if osd_dev_raw == None:
        raise Error("osd_dev not specified")

    # Check boot strap key exists
    bootstrap_path_osd = keyring._get_path_keyring_osd(cluster_name)
    if not os.path.isfile(bootstrap_path_osd):
        raise Error(bootstrap_path_osd)

    # normalise paths
    osd_dev = os.path.realpath(osd_dev_raw)
    # get existing state and see if action needed

    m = _model(**kwargs)
    u = _model_updator(m)
    u.defaults_refresh()
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


    if not constants._path_ceph_disk:
        raise Error("Error 'ceph-disk' command not find")
    arguments = [
        constants._path_ceph_disk,
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





def _create_monmap(model, path_monmap):
    """
    create_monmap file
    """
    if not os.path.isfile(path_monmap):
        arguments = [
            "monmaptool",
            "--create",
            "--fsid",
            model.cluster_uuid,
            path_monmap
            ]
        output = _excuete_local_command(arguments)
        if output["retcode"] != 0:
                raise Error("Failed executing '%s' Error rc=%s, stdout=%s stderr=%s" % (
                    " ".join(arguments),
                    output["retcode"],
                    output["stdout"],
                    output["stderr"])
                    )
        for name, addr in model.mon_members:
            arguments = [
                    "monmaptool",
                    "--add",
                    name,
                    addr,
                    path_monmap
                    ]
            output = _excuete_local_command(arguments)
            if output["retcode"] != 0:
                raise Error("Failed executing '%s' Error rc=%s, stdout=%s stderr=%s" % (
                    " ".join(arguments),
                    output["retcode"],
                    output["stdout"],
                    output["stderr"])
                    )
    return True





def keyring_admin_create(**kwargs):
    """
    Create admin keyring for cluster

    CLI Example:

        salt '*' sesceph.key_mon_create
                'cluster_name'='ceph' \
                'cluster_uuid'='cluster_uuid' \
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    """
    m = _model(**kwargs)
    u = _model_updator(m)
    u.hostname_refresh()
    if m.cluster_name == None:
        u.defaults_refresh()

    keyring_path_admin = keyring._get_path_keyring_admin(m.cluster_name)
    if os.path.isfile(keyring_path_admin):
        return keyring._keying_read(keyring_path_admin)
    try:
        tmpd = tempfile.mkdtemp()
        key_path = os.path.join(tmpd,"keyring")
        arguments = [
            "ceph-authtool",
            "--create-keyring",
            key_path,
            "--gen-key",
            "-n",
            "client.admin",
            "--set-uid=0",
            "--cap",
            "mon",
            "allow *",
            "--cap",
            "mds",
            "allow *",
            "--cap",
            "osd",
            "allow *"
            ]
        cmd_out = _excuete_local_command(arguments)
        if cmd_out["retcode"] != 0:
            raise Error("Failed executing '%s' Error rc=%s, stdout=%s stderr=%s" % (
                " ".join(arguments),
                cmd_out["retcode"],
                cmd_out["stdout"],
                cmd_out["stderr"])
                )
        output = keyring._keying_read(key_path)
    finally:
        shutil.rmtree(tmpd)
    return output

def keyring_admin_write(key_content, **kwargs):
    """
    Write admin keyring for cluster

    CLI Example:

        salt '*' sesceph.keyring_admin_write \
                '[mon.]\n\tkey = AQA/vZ9WyDwsKRAAxQ6wjGJH6WV8fDJeyzxHrg==\n\tcaps mon = \"allow *\"\n' \
                'cluster_name'='ceph' \
                'cluster_uuid'='cluster_uuid' \
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    """
    m = _model(**kwargs)
    u = _model_updator(m)
    if m.cluster_name == None:
        u.defaults_refresh()
    keyring_path_admin = keyring._get_path_keyring_admin(m.cluster_name)
    if os.path.isfile(keyring_path_admin):
        return True
    keyring._keying_write(keyring_path_admin, key_content)
    return True


def keyring_mon_create(**kwargs):
    """
    Create mon keyring for cluster

    CLI Example:

        salt '*' sesceph.key_mon_create
                'cluster_name'='ceph' \
                'cluster_uuid'='cluster_uuid' \
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    """
    m = _model(**kwargs)
    u = _model_updator(m)
    u.hostname_refresh()
    if m.cluster_name == None:
        u.defaults_refresh()
    u.load_confg(m.cluster_name)
    u.mon_members_refresh()
    q = _mdl_query(m)
    if not q.mon_is():
        raise Error("Not a mon server")
    keyring_path_mon = keyring._get_path_keyring_mon(m.cluster_name, m.hostname)
    if os.path.isfile(keyring_path_mon):
        return keyring._keying_read(keyring_path_mon)
    try:
        tmpd = tempfile.mkdtemp()
        key_path = os.path.join(tmpd,"keyring")
        arguments = [
            "ceph-authtool",
            "--create-keyring",
            key_path,
            "--gen-key",
            "-n",
            "mon.",
            "--cap",
            "mon",
            "allow *"
            ]
        cmd_out = _excuete_local_command(arguments)
        output = keyring._keying_read(key_path)
    finally:
        shutil.rmtree(tmpd)
    return output

def keyring_mon_write(key_content, **kwargs):
    """
    Write admin keyring for cluster

    CLI Example:

        salt '*' sesceph.keyring_mon_write \
                '[mon.]\n\tkey = AQA/vZ9WyDwsKRAAxQ6wjGJH6WV8fDJeyzxHrg==\n\tcaps mon = \"allow *\"\n' \
                'cluster_name'='ceph' \
                'cluster_uuid'='cluster_uuid' \
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    """
    m = _model(**kwargs)
    u = _model_updator(m)
    u.hostname_refresh()
    if m.cluster_name == None:
        u.defaults_refresh()
    u.load_confg(m.cluster_name)
    u.mon_members_refresh()
    q = _mdl_query(m)
    if not q.mon_is():
        raise Error("Not a mon server")

    keyring_path_mon = keyring._get_path_keyring_mon(m.cluster_name, m.hostname)
    if os.path.isfile(keyring_path_mon):
        return True
    keyring_path_mon_bootstrap = keyring._get_path_keyring_mon_bootstrap(m.cluster_name, m.hostname)
    if os.path.isfile(keyring_path_mon_bootstrap):
        return True
    keyring._keying_write(keyring_path_mon_bootstrap, key_content)
    return True

def keyring_mon_delete(**kwargs):
    """
    Delete Mon keyring for cluster

    CLI Example:

        salt '*' sesceph.keyring_mds_write \
                '[mds.]\n\tkey = AQA/vZ9WyDwsKRAAxQ6wjGJH6WV8fDJeyzxHrg==\n\tcaps mds = \"allow *\"\n' \
                'cluster_name'='ceph' \
                'cluster_uuid'='cluster_uuid' \
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".

    If no ceph config file is found, this command will fail.
    """
    m = _model(**kwargs)
    u = _model_updator(m)
    u.hostname_refresh()
    if m.cluster_name == None:
        u.defaults_refresh()
    u.load_confg(m.cluster_name)
    u.mon_members_refresh()
    q = _mdl_query(m)
    if not q.mon_is():
        raise Error("Not a mon server")
    keyring_path_mon = keyring._get_path_keyring_mon(m.cluster_name, m.hostname)
    if os.path.isfile(keyring_path_mon):
        try:
            os.remove(keyring_path_mon)
        except:
            raise Error("Keyring could not be deleted")
    keyring_path_mon_bootstrap = keyring._get_path_keyring_mon_bootstrap(m.cluster_name, m.hostname)
    if os.path.isfile(keyring_path_mon_bootstrap):
        try:
            os.remove(keyring_path_mon_bootstrap)
        except:
            raise Error("Keyring could not be deleted")
    return True



def keyring_osd_create(**kwargs):
    """
    Create osd keyring for cluster

    CLI Example:

        salt '*' sesceph.key_osd_create
                'cluster_name'='ceph' \
                'cluster_uuid'='cluster_uuid' \
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    """
    keyobj = keyring.keyring_facard()
    keyobj.key_type = "osd"
    return keyobj.create(**kwargs)

def keyring_osd_write(key_content, **kwargs):
    """
    Write admin keyring for cluster

    CLI Example:

        salt '*' sesceph.keyring_osd_write \
                '[osd.]\n\tkey = AQA/vZ9WyDwsKRAAxQ6wjGJH6WV8fDJeyzxHrg==\n\tcaps osd = \"allow *\"\n' \
                'cluster_name'='ceph' \
                'cluster_uuid'='cluster_uuid' \
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    """
    keyobj = keyring.keyring_facard()
    keyobj.key_type = "osd"
    return keyobj.write(key_content, **kwargs)

def keyring_osd_authorise(**kwargs):
    """
    Write admin keyring for cluster

    CLI Example:

        salt '*' sesceph.keyring_osd_write \
                '[osd.]\n\tkey = AQA/vZ9WyDwsKRAAxQ6wjGJH6WV8fDJeyzxHrg==\n\tcaps osd = \"allow *\"\n' \
                'cluster_name'='ceph' \
                'cluster_uuid'='cluster_uuid' \
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    """
    keyobj = keyring.keyring_facard()
    keyobj.key_type = "osd"
    return keyobj.auth_add(**kwargs)


def keyring_osd_auth_del(**kwargs):
    """
    Write rgw keyring for cluster

    CLI Example:

        salt '*' sesceph.keyring_osd_auth_del \
                'cluster_name'='ceph' \
                'cluster_uuid'='cluster_uuid' \
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    """
    keyobj = keyring.keyring_facard()
    keyobj.key_type = "osd"
    return keyobj.auth_del(**kwargs)


def keyring_osd_delete(**kwargs):
    """
    Write admin keyring for cluster

    CLI Example:

        salt '*' sesceph.keyring_osd_write \
                '[osd.]\n\tkey = AQA/vZ9WyDwsKRAAxQ6wjGJH6WV8fDJeyzxHrg==\n\tcaps osd = \"allow *\"\n' \
                'cluster_name'='ceph' \
                'cluster_uuid'='cluster_uuid' \
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    """
    keyobj = keyring.keyring_facard()
    keyobj.key_type = "osd"
    return keyobj.remove(**kwargs)



def keyring_mds_create(**kwargs):
    """
    Create mds keyring for cluster

    CLI Example:

        salt '*' sesceph.key_mds_create
                'cluster_name'='ceph' \
                'cluster_uuid'='cluster_uuid' \
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    """
    keyobj = keyring.keyring_facard()
    keyobj.key_type = "mds"
    return keyobj.create(**kwargs)

def keyring_mds_write(key_content, **kwargs):
    """
    Write mds keyring for cluster

    CLI Example:

        salt '*' sesceph.keyring_mds_write \
                '[mds.]\n\tkey = AQA/vZ9WyDwsKRAAxQ6wjGJH6WV8fDJeyzxHrg==\n\tcaps mds = \"allow *\"\n' \
                'cluster_name'='ceph' \
                'cluster_uuid'='cluster_uuid' \
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".

    If the value is set, it will not be changed untill the keyring is deleted.
    """
    keyobj = keyring.keyring_facard()
    keyobj.key_type = "mds"
    return keyobj.write(key_content, **kwargs)

def keyring_mds_authorise(**kwargs):
    """
    Write mds keyring for cluster

    CLI Example:

        salt '*' sesceph.keyring_mds_write \
                '[mds.]\n\tkey = AQA/vZ9WyDwsKRAAxQ6wjGJH6WV8fDJeyzxHrg==\n\tcaps mds = \"allow *\"\n' \
                'cluster_name'='ceph' \
                'cluster_uuid'='cluster_uuid' \
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    """
    keyobj = keyring.keyring_facard()
    keyobj.key_type = "mds"
    return keyobj.auth_add(**kwargs)


def keyring_mds_auth_del(**kwargs):
    """
    Write rgw keyring for cluster

    CLI Example:

        salt '*' sesceph.keyring_mds_auth_del \
                'cluster_name'='ceph' \
                'cluster_uuid'='cluster_uuid' \
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    """
    keyobj = keyring.keyring_facard()
    keyobj.key_type = "mds"
    return keyobj.auth_del(**kwargs)


def keyring_mds_delete(**kwargs):
    """
    Delete MDS keyring for cluster

    CLI Example:

        salt '*' sesceph.keyring_mds_write \
                '[mds.]\n\tkey = AQA/vZ9WyDwsKRAAxQ6wjGJH6WV8fDJeyzxHrg==\n\tcaps mds = \"allow *\"\n' \
                'cluster_name'='ceph' \
                'cluster_uuid'='cluster_uuid' \
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".

    If no ceph config file is found, this command will fail.
    """
    keyobj = keyring.keyring_facard()
    keyobj.key_type = "mds"
    return keyobj.remove(**kwargs)


def keyring_rgw_create(**kwargs):
    """
    Create rgw keyring for cluster

    CLI Example:

        salt '*' sesceph.key_rgw_create
                'cluster_name'='ceph' \
                'cluster_uuid'='cluster_uuid' \
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    """
    keyobj = keyring.keyring_facard()
    keyobj.key_type = "rgw"
    return keyobj.create(**kwargs)


def keyring_rgw_write(key_content, **kwargs):
    """
    Write rgw keyring for cluster

    CLI Example:

        salt '*' sesceph.keyring_rgw_write \
                '[rgw.]\n\tkey = AQA/vZ9WyDwsKRAAxQ6wjGJH6WV8fDJeyzxHrg==\n\tcaps rgw = \"allow *\"\n' \
                'cluster_name'='ceph' \
                'cluster_uuid'='cluster_uuid' \
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".

    If the value is set, it will not be changed untill the keyring is deleted.
    """
    keyobj = keyring.keyring_facard()
    keyobj.key_type = "rgw"
    return keyobj.write(key_content, **kwargs)

def keyring_rgw_authorise(**kwargs):
    """
    Write rgw keyring for cluster

    CLI Example:

        salt '*' sesceph.keyring_rgw_write \
                '[rgw.]\n\tkey = AQA/vZ9WyDwsKRAAxQ6wjGJH6WV8fDJeyzxHrg==\n\tcaps rgw = \"allow *\"\n' \
                'cluster_name'='ceph' \
                'cluster_uuid'='cluster_uuid' \
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    """
    keyobj = keyring.keyring_facard()
    keyobj.key_type = "rgw"
    return keyobj.auth_add(**kwargs)


def keyring_rgw_auth_del(**kwargs):
    """
    Write rgw keyring for cluster

    CLI Example:

        salt '*' sesceph.keyring_rgw_auth_del \
                'cluster_name'='ceph' \
                'cluster_uuid'='cluster_uuid' \
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    """
    keyobj = keyring.keyring_facard()
    keyobj.key_type = "rgw"
    return keyobj.auth_del(**kwargs)


def keyring_rgw_delete(**kwargs):
    """
    Delete rgw keyring for cluster

    CLI Example:

        salt '*' sesceph.keyring_rgw_write \
                '[rgw.]\n\tkey = AQA/vZ9WyDwsKRAAxQ6wjGJH6WV8fDJeyzxHrg==\n\tcaps rgw = \"allow *\"\n' \
                'cluster_name'='ceph' \
                'cluster_uuid'='cluster_uuid' \
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".

    If no ceph config file is found, this command will fail.
    """
    keyobj = keyring.keyring_facard()
    keyobj.key_type = "mds"
    return keyobj.remove(**kwargs)



def mon_is(**kwargs):
    """
    Is this a mon node

    CLI Example:

        salt '*' sesceph.keys_create
                'cluster_name'='ceph' \
                'cluster_uuid'='cluster_uuid' \
    Notes:

    cluster_name
        Set the cluster name. Defaults to "ceph".

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.
    """
    m = _model(**kwargs)
    u = _model_updator(m)
    u.hostname_refresh()
    try:
        u.defaults_refresh()
    except:
        return False
    u.load_confg(m.cluster_name)
    u.mon_members_refresh()
    q = _mdl_query(m)
    return q.mon_is()


def mon_status(**kwargs):
    """
    Get status from mon deamon

    CLI Example:

        salt '*' sesceph.prepare
                'cluster_name'='ceph' \
                'cluster_uuid'='cluster_uuid' \
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    """

    hostname = platform.node()
    m = _model(**kwargs)
    u = _model_updator(m)
    u.hostname_refresh()
    try:
        u.defaults_refresh()
    except:
        return {}
    u.load_confg(m.cluster_name)
    u.mon_members_refresh()
    q = _mdl_query(m)
    if not q.mon_is():
        raise Error("Not a mon node")
    u.mon_status()
    p = _mdl_presentor(m)
    return p.mon_status()


def mon_quorum(**kwargs):
    """
    Is mon deamon in quorum

    CLI Example:

        salt '*' sesceph.prepare
                'cluster_name'='ceph' \
                'cluster_uuid'='cluster_uuid' \
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    """

    hostname = platform.node()
    m = _model(**kwargs)
    u = _model_updator(m)
    u.hostname_refresh()
    try:
        u.defaults_refresh()
    except:
        raise Error("Could not get cluster details")
    u.load_confg(m.cluster_name)
    u.mon_members_refresh()
    u.mon_status()
    q = _mdl_query(m)
    return q.mon_quorum()


def mon_create(**kwargs):
    """
    Create a mon node

    CLI Example:

        salt '*' sesceph.prepare
                'cluster_name'='ceph' \
                'cluster_uuid'='cluster_uuid' \
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    """
    cluster_name = kwargs.get("cluster_name")
    cluster_uuid = kwargs.get("cluster_uuid")

    hostname = kwargs.get("hostname")

    # Default cluster name / uuid values
    if cluster_name == None and cluster_uuid == None:
        cluster_name = "ceph"
    if cluster_name != None and cluster_uuid == None:
        cluster_uuid = utils._get_cluster_uuid_from_name(cluster_name)
    if cluster_name == None and cluster_uuid != None:
        cluster_name = utils._get_cluster_name_from_uuid(cluster_name)

    m = _model(**kwargs)

    u = _model_updator(m)
    u.hostname_refresh()
    u.defaults_refresh()
    u.load_confg(cluster_name)
    u.mon_members_refresh()
    p = _mdl_presentor(m)

    try:
        mon_initial_members_name_raw = m.ceph_conf.get("global","mon_initial_members")
    except ConfigParser.NoOptionError:
        raise Error("Cluster confg file does not set mon_initial_members")
    mon_initial_members_name_cleaned = []

    for mon_split in mon_initial_members_name_raw.split(","):
        mon_initial_members_name_cleaned.append(mon_split.strip())
    hostname = platform.node()

    try:
        index = mon_initial_members_name_cleaned.index(hostname)
    except:
        log.debug("Mon not needed on %s" % (hostname))
        raise Error("Not a mon server")
    try:
        mon_initial_members_addr_raw = m.ceph_conf.get("global","mon_host")
    except ConfigParser.NoOptionError:
        raise Error("Cluster confg file does not set mon_host")

    mon_initial_members_addr_cleaned = []
    for mon_split in mon_initial_members_addr_raw.split(","):
        mon_initial_members_addr_cleaned.append(mon_split.strip())
    try:
        ipaddress = mon_initial_members_addr_cleaned[index]
    except:
        raise Error("addr for %s not found in config" % (hostname))



    path_done_file = "/var/lib/ceph/mon/%s-%s/done" % (
            cluster_name,
            hostname
        )
    keyring_path_mon = keyring._get_path_keyring_mon_bootstrap(m.cluster_name, m.hostname)
    path_adm_sock = "/var/run/ceph/%s-mon.%s.asok" % (
            cluster_name,
            hostname
        )
    path_mon_dir = "/var/lib/ceph/mon/%s-%s" % (
            cluster_name,
            hostname
        )

    path_admin_keyring = keyring._get_path_keyring_admin(cluster_name)

    path_monmap = "/var/lib/ceph/tmp/%s.monmap" % (
            cluster_name
        )
    path_tmp_keyring = "/var/lib/ceph/tmp/%s.keyring" % (
            cluster_name
        )
    if os.path.isfile(path_done_file):
        log.debug("Mon done file exists:%s" % (path_done_file))
        return True

    if not os.path.isfile(keyring_path_mon):
        raise Error("Mon keyring missing")
    if not os.path.isfile(path_admin_keyring):
        raise Error("Admin keyring missing")

    if not os.path.isfile(path_monmap):
        _create_monmap(m, path_monmap)



    if not os.path.isdir(path_mon_dir):
        os.makedirs(path_mon_dir)


    try:
        tmpd = tempfile.mkdtemp()
        key_path = os.path.join(tmpd,"keyring")
        arguments = [
            "ceph-authtool",
            "--create-keyring",
            key_path,
            "--import-keyring",
            keyring_path_mon,
            ]
        output = _excuete_local_command(arguments)
        if output["retcode"] != 0:
            raise Error("Failed executing '%s' Error rc=%s, stdout=%s stderr=%s" % (
                " ".join(arguments),
                output["retcode"],
                output["stdout"],
                output["stderr"]
                ))
        arguments = [
            "ceph-authtool",
            key_path,
            "--import-keyring",
            path_admin_keyring,
            ]
        output = _excuete_local_command(arguments)
        if output["retcode"] != 0:
            raise Error("Failed executing '%s' Error rc=%s, stdout=%s stderr=%s" % (
                " ".join(arguments),
                output["retcode"],
                output["stdout"],
                output["stderr"]
                ))
        arguments = [
                "ceph-mon",
                "--mkfs",
                "-i",
                hostname,
                "--monmap",
                path_monmap,
                '--keyring',
                key_path
                ]
        output = _excuete_local_command(arguments)
        if output["retcode"] != 0:
            raise Error("Failed executing '%s' Error rc=%s, stdout=%s stderr=%s" % (
                " ".join(arguments),
                output["retcode"],
                output["stdout"],
                output["stderr"]
                ))
        open(path_done_file, 'a').close()
    finally:
        shutil.rmtree(tmpd)
    arguments = [
        "systemctl",
        "enable",
        "ceph-mon@%s" % (hostname)
        ]
    output = _excuete_local_command(arguments)
    if output["retcode"] != 0:
        raise Error("Failed executing '%s' Error rc=%s, stdout=%s stderr=%s" % (
            " ".join(arguments),
            output["retcode"],
            output["stdout"],
            output["stderr"])
            )
    arguments = [
        "systemctl",
        "start",
        "ceph-mon@%s" % (hostname)
        ]
    output = _excuete_local_command(arguments)
    if output["retcode"] != 0:
        raise Error("Failed executing '%s' Error rc=%s, stdout=%s stderr=%s" % (
            " ".join(arguments),
            output["retcode"],
            output["stdout"],
            output["stderr"])
            )
    arguments = [
        "ceph",
        "--cluster=%s" % (cluster_name),
        "--admin-daemon",
        "/var/run/ceph/ceph-mon.%s.asok" % (hostname),
        "mon_status"
        ]

    output = _excuete_local_command(arguments)
    if output["retcode"] != 0:
        raise Error("Failed executing '%s' Error rc=%s, stdout=%s stderr=%s" % (
            " ".join(arguments),
            output["retcode"],
            output["stdout"],
            output["stderr"])
            )
    return True





def auth_list(**kwargs):
    """
    List all cephx authorization keys

    CLI Example:

        salt '*' sesceph.auth_list
                'cluster_name'='ceph' \
                'cluster_uuid'='cluster_uuid' \
    Notes:

    cluster_name
        Set the cluster name. Defaults to "ceph".

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.
    """
    m = _model(**kwargs)
    u = _model_updator(m)
    u.hostname_refresh()
    try:
        u.defaults_refresh()
    except:
        return {}
    u.load_confg(m.cluster_name)
    u.mon_members_refresh()
    u.auth_list()
    p = _mdl_presentor(m)
    return p.auth_list()

