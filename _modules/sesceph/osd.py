# Python imports
import logging
import os
import stat

# Local imports
import utils
import keyring
import constants
import model
import mdl_updater
import mdl_query


log = logging.getLogger(__name__)


class Error(Exception):
    """
    Error
    """

    def __str__(self):
        doc = self.__doc__.strip()
        return ': '.join([doc] + [str(a) for a in self.args])


class osd_ctrl(object):
    def __init__(self, **kwargs):
        self.model = model.model(**kwargs)
        self.model.init = "systemd"


    def update_model(self):
        u = mdl_updater.model_updater(self.model)
        u.symlinks_refresh()
        u.defaults_refresh()
        u.partitions_all_refresh()
        u.discover_partitions_refresh()


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


    def _get_osd_partitons_by_disk(self, disk):
        output = set()
        disk_details = self.model.lsblk.get(disk)
        if disk_details is None:
            return output
        part_details = disk_details.get('PARTITION')
        if part_details is None:
            return output
        for part_name in part_details.keys():
            if part_name in self.model.partitions_osd:
                output.add(part_name)
        return output


    def _activate_targets_item(self, osd_dev_raw):
        activate_list = set()
        osd_dev_norm = os.path.realpath(osd_dev_raw)
        if self.is_partition(osd_dev_norm):
            activate_list.add(osd_dev_norm)
        else:
            for partition in self._get_osd_partitons_by_disk(osd_dev_norm):
                activate_list.add(partition)
        return activate_list


    def activate_partiion(self, partiion):
        arguments = [
                'ceph-disk',
                '-v',
                'activate',
                '--mark-init',
                self.model.init,
                '--mount',
                partiion,
            ]
        output = utils.execute_local_command(arguments)
        if output["retcode"] != 0:
                raise Error("Failed executing '%s' Error rc=%s, stdout=%s stderr=%s" % (
                    " ".join(arguments),
                    output["retcode"],
                    output["stdout"],
                    output["stderr"])
                    )
        return True


    def activate_targets(self, **kwargs):
        osd_dev_raw = kwargs.get("osd_dev")
        osd_dev_list_raw = kwargs.get("osd_dev_list")
        if osd_dev_raw is None and osd_dev_list_raw is None:
            return self.model.partitions_osd

        activate_list = set()
        if osd_dev_raw is not None:
            for dev_norm in self._activate_targets_item(osd_dev_raw):
                activate_list.add(dev_norm)
        if osd_dev_list_raw is not None:
            for dev_raw in osd_dev_list_raw:
                for dev_norm in self._activate_targets_item(dev_raw):
                    activate_list.add(dev_norm)
        for part in activate_list:
            self.activate_partiion(part)
        return True


    def _get_part_details(self,partition):
        disk_name = self.model.part_pairent.get(partition)
        if disk_name is None:
            raise Error("Programming error")
        disk_details = self.model.lsblk.get(disk_name)
        if disk_details is None:
            raise Error("Programming error")
        disk_parts = disk_details.get('PARTITION')
        if disk_parts is None:
            raise Error("Programming error")
        return disk_parts.get(partition)


    def _get_part_type(self,partition):
        part_details = self._get_part_details(partition)
        if part_details is None:
            raise Error("Programming error")
        return part_details.get("PARTTYPE")


    def _get_part_table_type(self,disk_name):
        disk_details = self.model.lsblk.get(disk_name)
        return disk_details.get("PARTTABLE")


    def _prepare_check_partition_type_data(self, partition):
        import json
        part_type = self._get_part_type(partition)
        if part_type == constants.OSD_UUID:
            return True
        # Ok so its wrong type Now we check if we can fix it.
        disk_name = self.model.part_pairent.get(partition)
        part_table_type = self._get_part_table_type(disk_name)
        if part_table_type != "gpt":
            raise Error("Unsupported partition table type:'%s' for '%s'",
                (part_table_type, disk_name))
        return True


    def _prepare_check_partition_type_journel(self, partition):
        # Make go away
        part_type = self._get_part_type(partition)
        if part_type == constants.JOURNAL_UUID:
            return True
        # Ok so its wrong type Now we check if we can fix it.
        disk_name = self.model.part_pairent.get(partition)
        part_table_type = self._get_part_table_type(disk_name)
        if part_table_type != "gpt":
            raise Error("Unsupported partition table type:'%s' for '%s'",
                (part_table_type, disk_name))
        return True


    def prepare(self, **kwargs):
        osd_dev_raw = kwargs.get("osd_dev")
        journal_dev = kwargs.get("journal_dev")
        cluster_name = kwargs.get("cluster_name")
        cluster_uuid = kwargs.get("cluster_uuid")
        fs_type = kwargs.get("osd_fs_type")
        osd_uuid = kwargs.get("osd_uuid")
        journal_uuid = kwargs.get("journal_uuid")
        # Default cluster name / uuid values
        if cluster_name is None and cluster_uuid is None:
            cluster_name = "ceph"
        if cluster_name is not None and cluster_uuid is None:
            cluster_uuid = utils._get_cluster_uuid_from_name(cluster_name)
        if cluster_name is None and cluster_uuid is not None:
            cluster_name = utils._get_cluster_name_from_uuid(cluster_name)

        fs_type = kwargs.get("fs_type","xfs")
        # Check required variables are set
        if osd_dev_raw is None:
            raise Error("osd_dev not specified")

        # Check boot strap key exists
        bootstrap_path_osd = keyring._get_path_keyring_osd(cluster_name)
        if not os.path.isfile(bootstrap_path_osd):
            raise Error(bootstrap_path_osd)
        if not os.path.isdir(constants._path_ceph_lib_osd):
            log.info("mkdir %s")
            os.makedirs(constants._path_ceph_lib_osd)
        # normalise paths
        osd_dev = os.path.realpath(osd_dev_raw)
        log.debug("Transfromed from '%s' to '%s'" % (osd_dev_raw, osd_dev))
        # get existing state and see if action needed
        u = mdl_updater.model_updater(self.model)
        u.partition_table_refresh()

        # Validate the osd_uuid and journal_uuid dont already exist

        osd_list_existing = self.model.discovered_osd.get(cluster_uuid)
        if osd_list_existing is not None:
            for osd_existing in osd_list_existing:
                if osd_uuid is not None:
                    osd_existing_fsid = osd_existing.get("fsid")
                    if osd_existing_fsid == osd_uuid:
                        log.debug("osd_uuid already exists:%s" % (osd_uuid))
                        return True

                if journal_uuid is not None:
                    journal_existing_uuid = osd_existing.get("journal_uuid")
                    if journal_existing_uuid == journal_uuid:
                        log.debug("journal_uuid already exists:%s" % (journal_uuid))
                        return True
        if self.is_partition(osd_dev):
            if osd_dev in self.model.partitions_journal:
                return True
            partion_details = self._get_part_details(osd_dev)
            osd_mountpoint = partion_details.get("MOUNTPOINT")
            if osd_mountpoint is not None:
                return True
            if journal_dev is None:
                # We could try and default journal_dev if a journel disk is found.
                raise Error("Journel device must be specified")
            self._prepare_check_partition_type_data(osd_dev)
            self._prepare_check_partition_type_journel(journal_dev)
        else:
            # If partions exist on osd_dev disk assume its used
            block_details_osd = self.model.lsblk.get(osd_dev)
            if block_details_osd is None:
                raise Error("Not a block device")
            part_table = block_details_osd.get("PARTITION")
            if part_table is not None:
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
        if osd_dev is not None:
            arguments.append("--data-dev")
        if journal_dev is not None:
            arguments.append("--journal-dev")
        if cluster_name is not None:
            arguments.append("--cluster")
            arguments.append(cluster_name)
        if cluster_uuid is not None:
            arguments.append("--cluster-uuid")
            arguments.append(cluster_uuid)
        if osd_uuid is not None:
            arguments.append("--osd-uuid")
            arguments.append(osd_uuid)
        if journal_uuid is not None:
            arguments.append("--journal-uuid")
            arguments.append(journal_uuid)
        if osd_dev is not None:
            arguments.append(osd_dev)
        if journal_dev is not None:
            arguments.append(journal_dev)
        output = utils.execute_local_command(arguments)
        if output["retcode"] != 0:
            raise Error("Failed executing '%s' Error rc=%s, stdout=%s stderr=%s" % (
                    " ".join(arguments),
                    output["retcode"],
                    output["stdout"],
                    output["stderr"])
                    )
        return True


def osd_prepare(**kwargs):
    osdc = osd_ctrl(**kwargs)
    osdc.update_model()
    return osdc.prepare(**kwargs)


def osd_activate(**kwargs):
    osdc = osd_ctrl(**kwargs)
    osdc.update_model()
    return osdc.activate_targets(**kwargs)
