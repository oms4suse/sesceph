import os
import stat

import utils
import keyring
import constants
import model
import mdl_updater
import mdl_query

class Error(Exception):
    """
    Error
    """

    def __str__(self):
        doc = self.__doc__.strip()
        return ': '.join([doc] + [str(a) for a in self.args])


class osd_ctrl(object):
    def _get_dev_name(self, path):
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

    def is_partition(self, dev):
        """
        Check whether a given device path is a partition or a full disk.
        """
        if not os.path.exists(dev):
            raise Error('device not found', dev)
        
        dev = os.path.realpath(dev)
        if not stat.S_ISBLK(os.lstat(dev).st_mode):
            raise Error('not a block device', dev)

        name = self._get_dev_name(dev)
        if os.path.exists(os.path.join('/sys/block', name)):
            return False

        # make sure it is a partition of something else
        for basename in os.listdir('/sys/block'):
            if os.path.exists(os.path.join('/sys/block', basename, name)):
                return True
        raise Error('not a disk or partition', dev)
 

def osd_prepare(**kwargs):
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
    if not os.path.isdir(constants._path_ceph_lib_osd):
        os.makedirs(constants._path_ceph_lib_osd)
    # normalise paths
    osd_dev = os.path.realpath(osd_dev_raw)
    # get existing state and see if action needed

    m = model.model(**kwargs)
    u = mdl_updater.model_updater(m)
    u.defaults_refresh()
    u.partitions_all_refresh()
    u.discover_partitions_refresh()

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

    output = utils.excuete_local_command(arguments)
    if output["retcode"] != 0:
        raise Error("Error rc=%s, stdout=%s stderr=%s" % (output["retcode"], output["stdout"], output["stderr"]))
    return True





def osd_activate(**kwargs):
    distro_init = "systemd"
    osd_dev_raw = kwargs.get("osd_dev")
    m = model.model(**kwargs)
    u = mdl_updater.model_updater(m)
    arguments = [
            'ceph-disk',
            '-v',
            'activate',
            '--mark-init',
            distro_init,
            '--mount',
            osd_dev_raw,
        ]
    output = utils.excuete_local_command(arguments)
    if output["retcode"] != 0:
            raise Error("Failed executing '%s' Error rc=%s, stdout=%s stderr=%s" % (
                " ".join(arguments),
                output["retcode"],
                output["stdout"],
                output["stderr"])
                )
    return True
