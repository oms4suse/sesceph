import os
import os.path
import platform
import logging
import shlex
import tempfile
import json
import ConfigParser

# local modules
import constants
import utils


log = logging.getLogger(__name__)



class Error(Exception):
    """
    Error
    """

    def __str__(self):
        doc = self.__doc__.strip()
        return ': '.join([doc] + [str(a) for a in self.args])

def _retrive_osd_details_from_dir(directory):
    osd_required_files = set(["ceph_fsid", "fsid", "magic"])
    osd_details = {}
    dir_content = os.listdir(directory)
    if not osd_required_files.issubset(dir_content):
        return None
    with open('%s/ceph_fsid' % (directory), 'r') as infile:
        osd_details["ceph_fsid"] = infile.read().strip()
    with open('%s/fsid' % (directory), 'r') as infile:
        osd_details["fsid"] = infile.read().strip()
    with open('%s/magic' % (directory), 'r') as infile:
        osd_details["magic"] = infile.read().strip()
    # Journel uuid may not exist when partition reused.
    path_journal_uuid = '%s/journal_uuid' % (directory)
    if os.path.isfile(path_journal_uuid):
        with open('%s/journal_uuid' % (directory), 'r') as infile:
            osd_details["journal_uuid"] = infile.read().strip()
    # whoami may not exist when OSD has never been activated.
    path_whoami = '%s/whoami' % (directory)
    if os.path.isfile(path_whoami):
        with open('%s/whoami' % (directory), 'r') as infile:
            osd_details["whoami"] = infile.read().strip()
    path_link = '%s/journal' % (directory)
    if os.path.islink(path_link):
        osd_details["dev_journal"] = os.path.realpath(path_link)
    return osd_details


def retrive_osd_details(device_name):
    osd_details = {}
    if device_name == None:
        return None
    try:
        tmpd = tempfile.mkdtemp()
        try:
            out_mnt = utils.execute_local_command(['mount',device_name,tmpd])
            if out_mnt['retcode'] == 0:
                osd_details = _retrive_osd_details_from_dir(tmpd)
        finally:
            utils.execute_local_command(['umount',tmpd])
    finally:
        os.rmdir(tmpd)
    return osd_details




class model_updater():
    """
    Basic model updator retrives data and adds to model
    """
    def __init__(self, model):
        self.model = model

    def hostname_refresh(self):
        self.model.hostname = platform.node()


    def defaults_refresh(self):
        # Default cluster name / uuid values
        if self.model.cluster_name == None and self.model.cluster_uuid == None:
            self.model.cluster_name = "ceph"
        if self.model.cluster_name != None and self.model.cluster_uuid == None:
            self.model.cluster_uuid = utils._get_cluster_uuid_from_name(self.model.cluster_name)
        if self.model.cluster_name == None and self.model.cluster_uuid != None:
            self.model.cluster_name = utils._get_cluster_name_from_uuid(self.model.cluster_uuid)

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


    def lsblk_version_refresh(self):
        """
        Get lsblk version as this is older on RHEL 7.2
        """
        arguments = [ constants._path_lsblk, "--version" ]
        output = utils.execute_local_command(arguments)
        if output["retcode"] != 0:
            raise Error("Failed executing '%s' Error rc=%s, stdout=%s stderr=%s" % (
                " ".join(arguments),
                output["retcode"],
                output["stdout"],
                output["stderr"]
                ))
        version_str = output["stdout"].strip()
        version_list = shlex.split(version_str)
        if len(version_list) < 4:
            raise Error("Failed processing lsblk version string '%s'" % (version_str))
        version_split = version_list[3].split(".")
        self.model.lsblk_version.major = int(version_split[0])
        if len(version_split) > 1:
            self.model.lsblk_version.minor = int(version_split[1])
        if len(version_split) > 2:
            self.model.lsblk_version.revision = int(version_split[2])
        else:
            self.model.lsblk_version.revision = 0


    def _lsblk_arguements(self):
        """
        Utility function for lsblk
        """
        if self.model.lsblk_version.major == None:
            self.lsblk_version_refresh()

        if self.model.lsblk_version.major < 2:
            raise Error("lsblk version too old '%s'" % (self.model.lsblk_version))
        if self.model.lsblk_version.major == 2 and self.model.lsblk_version.minor < 23:
            raise Error("lsblk version maybe too old '%s'" % (self.model.lsblk_version))
        # RHEL 7.2 uses version 2.23.2
        if self.model.lsblk_version.major == 2 and self.model.lsblk_version.minor < 25:
            # Note we dont have "PARTTYPE"
            return [
                "--ascii",
                "--output",
                "NAME,FSTYPE,MOUNTPOINT,PARTLABEL,PARTUUID,PKNAME,ROTA,RQ-SIZE,SCHED,SIZE,TYPE,UUID,VENDOR",
                "--pairs",
                "--paths",
                "--bytes"
                ]
        return [
            "--ascii",
            "--output-all",
            "--pairs",
            "--paths",
            "--bytes"
            ]


    def partitions_all_refresh(self):
        '''
        List all partition details

        CLI Example:

            salt '*' sesceph.partitions_all
        '''
        part_map = {}
        cmd = [ constants._path_lsblk] + self._lsblk_arguements()
        output = utils.execute_local_command(cmd)
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


    def partition_table_refresh(self):
        for disk_name in self.model.lsblk.keys():
            arguments = [
                'parted',
                disk_name,
                'print'
                ]
            log.debug("Running:%s" % (" ".join(arguments)))
            output = utils.execute_local_command(arguments)
            if output["retcode"] != 0:
                raise Error("Failed executing '%s' Error rc=%s, stdout=%s stderr=%s" % (
                    " ".join(arguments),
                    output["retcode"],
                    output["stdout"],
                    output["stderr"]
                    ))
            part_type = None
            for line in output["stdout"].split('\n'):
                split_line = line.split(':')
                if split_line[0] != 'Partition Table':
                    continue
                part_type = ":".join(split_line[1:]).strip()
            if part_type == None:
                continue
            self.model.lsblk[disk_name]["PARTTABLE"] = part_type


    def discover_partitions_refresh(self):
        '''
        List all OSD and journal partitions

        CLI Example:

            salt '*' sesceph.discover_osd_partitions
        '''
        osd_all = set()
        journal_all = set()
        osd_details = {}
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
                mount_point = part_details.get("MOUNTPOINT")
                if mount_point == '[SWAP]':
                    continue
                if mount_point != None:
                    osd_md = _retrive_osd_details_from_dir(mount_point)
                    if osd_md != None:
                        osd_details[partname] = osd_md
                part_type = part_details.get("PARTTYPE")
                if part_type == constants.OSD_UUID:
                    osd_all.add(partname)
                    if mount_point != None:
                        continue
                    osd_md = retrive_osd_details(partname)
                    if osd_md != None:
                        osd_details[partname] = osd_md
                    continue
                if part_type == constants.JOURNAL_UUID:
                    journal_all.add(partname)
                    continue
                if mount_point != None:
                    continue
                fs_type = part_details.get("FSTYPE")
                if fs_type == None:
                    continue
                if not fs_type in ['xfs', 'btrfs', 'ext4']:
                    continue
                osd_md = retrive_osd_details(partname)
                if osd_md != None:
                    osd_details[partname] = osd_md
        # Now we combine our data to find incorrectly labeled OSD's
        # and build osd data structure discovered_osd
        discovered_osd = {}
        for osd_dev_data in osd_details.keys():
            # Agregate data into osd_all.
            osd_all.add(osd_dev_data)
            osd_md = osd_details.get(osd_dev_data)
            if osd_md == None:
                continue
            # Agregate data into journal_all.
            osd_dev_journel_raw = osd_md.get("dev_journal")
            if osd_dev_journel_raw != None:
                journal_all.add(osd_dev_journel_raw)
            osd_md["dev"] = osd_dev_data
            disk_name = self.model.part_pairent.get(osd_dev_data)
            if disk_name != None:
                osd_md["dev_parent"] = disk_name
            ceph_fsid = osd_md.get("ceph_fsid")
            if not ceph_fsid in discovered_osd.keys():
                discovered_osd[ceph_fsid] = []
            discovered_osd[ceph_fsid].append(osd_md)
        self.model.partitions_osd = osd_all
        self.model.partitions_journal = journal_all
        self.model.discovered_osd = discovered_osd


    def load_confg(self, cluster_name):
        configfile = "/etc/ceph/%s.conf" % (cluster_name)
        if not os.path.isfile(configfile):
            raise Error("Cluster confg file does not exist:'%s'" % configfile)
        self.model.ceph_conf.read(configfile)

    def mon_members_refresh(self):
        try:
            mon_initial_members_name_raw = self.model.ceph_conf.get("global","mon_initial_members")
        except ConfigParser.NoOptionError:
            raise Error("Cluster config file does not set mon_initial_members")
        mon_initial_members_name_cleaned = []

        for mon_split in mon_initial_members_name_raw.split(","):
            mon_initial_members_name_cleaned.append(mon_split.strip())
        hostname = platform.node()

        try:
            index = mon_initial_members_name_cleaned.index(hostname)
        except:
            log.debug("Mon not needed on %s" % (hostname))
            print "Mon not needed on %s" % (hostname)
            return True
        try:
            mon_initial_members_addr_raw = self.model.ceph_conf.get("global","mon_host")
        except ConfigParser.NoOptionError:
            raise Error("Cluster config file does not set mon_host")
        mon_initial_members_addr_cleaned = []
        for mon_split in mon_initial_members_addr_raw.split(","):
            mon_initial_members_addr_cleaned.append(mon_split.strip())

        if len(mon_initial_members_name_cleaned) != len(mon_initial_members_addr_cleaned):
            raise Error("config has different numbers of mon 'names' and ip addresses")
        output = []
        items = len(mon_initial_members_name_cleaned)
        for idx in range(0,len(mon_initial_members_name_cleaned)):
            output.append((
                    mon_initial_members_name_cleaned[idx],
                    mon_initial_members_addr_cleaned[idx]
                ))
        self.model.mon_members = output


    def mon_status(self):
        if self.model.hostname == None:
            raise Error("Hostname not set")
        if self.model.cluster_name == None:
            raise Error("cluster_name not set")
        arguments = [
            "ceph",
            "--cluster=%s" % (self.model.cluster_name),
            "--admin-daemon",
            "/var/run/ceph/ceph-mon.%s.asok" % (self.model.hostname),
            "mon_status"
            ]
        output = utils.execute_local_command(arguments)
        if output["retcode"] != 0:
            raise Error("Failed executing '%s' Error rc=%s, stdout=%s stderr=%s" % (
                        " ".join(arguments),
                        output["retcode"],
                        output["stdout"],
                        output["stderr"])
                        )
        self.model.mon_status = json.loads(output['stdout'])



    def auth_list(self):
        arguments = [
            "ceph",
            "auth",
            "list"
            ]
        output = utils.execute_local_command(arguments)
        if output["retcode"] != 0:
            raise Error("Failed executing '%s' Error rc=%s, stdout=%s stderr=%s" % (
                        " ".join(arguments),
                        output["retcode"],
                        output["stdout"],
                        output["stderr"])
                        )
        auth_list_out = {}
        section = {}
        for line in output["stdout"].split('\n'):
            if len(line) == 0:
                continue
            if line[0] != '\t':
                prev_sec_name = section.get("name")
                if prev_sec_name != None:
                    auth_list_out[prev_sec_name] = section
                section = { "name" : line }
                continue
            tokenised_line = shlex.split(line)
            if len(tokenised_line) == 0:
                continue
            if tokenised_line[0] == 'key:':
                section['key'] = tokenised_line[1]
            if tokenised_line[0] == 'caps:':
                if not 'caps' in section:
                    section['caps'] = []
                cap_details = tokenised_line[1:]
                section["caps"].append(cap_details)


        prev_sec_name = section.get("name")
        if prev_sec_name != None:
            auth_list_out[prev_sec_name] = section
        self.model.auth_list = auth_list_out


    def pool_list(self):
        arguments = [
            "ceph",
            "-f",
            "json",
            "osd",
            "lspools"
            ]
        output = utils.execute_local_command(arguments)
        if output["retcode"] != 0:
            raise Error("Failed executing '%s' Error rc=%s, stdout=%s stderr=%s" % (
                        " ".join(arguments),
                        output["retcode"],
                        output["stdout"],
                        output["stderr"])
                        )
        details = {}
        for item in json.loads(output["stdout"].strip()):
            pool_num = item.get("poolnum")
            pool_name = item.get("poolname")
            details[pool_name] = {"poolnum" : pool_num }
        self.model.pool_list = details

    def _pool_adder(self, name, **kwargs):
        pg_num = kwargs.get("pg_num", 8)
        pgp_num = kwargs.get("pgp_num", pg_num)
        pool_type = kwargs.get("pool_type")
        er_profile = kwargs.get("erasure_code_profile")
        crush_ruleset_name = kwargs.get("crush_ruleset")

        arguments = [
            'ceph',
            'osd',
            'pool',
            'create',
            name,
            str(pg_num)
            ]
        if pgp_num != None:
            arguments.append(str(pgp_num))
        if pool_type == "replicated":
            arguments.append("replicated")
        if pool_type == "erasure":
            arguments.append("erasure")
            arguments.append("erasure-code-profile=%s" % (er_profile))
        if crush_ruleset_name != None:
            arguments.append(crush_ruleset_name)
        output = utils.execute_local_command(arguments)
        if output["retcode"] != 0:
            raise Error("Failed executing '%s' Error rc=%s, stdout=%s stderr=%s" % (
                        " ".join(arguments),
                        output["retcode"],
                        output["stdout"],
                        output["stderr"]))

    def pool_add(self, name, **kwargs):
        if not name in self.model.pool_list.keys():
            return self._pool_adder(name, **kwargs)

    def pool_del(self, name):
        if not name in self.model.pool_list.keys():
            return True
        arguments = [
            'ceph',
            'osd',
            'pool',
            'delete',
            name,
            name,
            '--yes-i-really-really-mean-it'
            ]
        output = utils.execute_local_command(arguments)
        if output["retcode"] != 0:
            raise Error("Failed executing '%s' Error rc=%s, stdout=%s stderr=%s" % (
                        " ".join(arguments),
                        output["retcode"],
                        output["stdout"],
                        output["stderr"]))
        return True


    def ceph_version_refresh(self):
        arguments = [
            "ceph",
            "--version"
            ]
        output = utils.execute_local_command(arguments)
        if output["retcode"] != 0:
            raise Error("Failed executing '%s' Error rc=%s, stdout=%s stderr=%s" % (
                        " ".join(arguments),
                        output["retcode"],
                        output["stdout"],
                        output["stderr"]))
        version_raw = output["stdout"].strip()
        version_raw_split = shlex.split(version_raw)
        if len(version_raw_split) != 4:
            raise Error("ceph returned an invalid version:'%s' " % (version_raw))
        if version_raw_split[0] != "ceph":
            raise Error("ceph returned an invalid version first value is not ceph:'%s' " % (version_raw))
        if version_raw_split[1] != "version":
            raise Error("ceph returned an invalid version second value is not 'version':'%s' " % (version_raw))
        version_public_raw = version_raw_split[2]
        version_git_raw = version_raw_split[2]
        version_public = version_public_raw.split(".")
        if len(version_public) < 3:
            raise Error("ceph returned an invalid version second value is not 'version':'%s' " % (version_raw))
        self.model.ceph_version.major = int(version_public[0])
        self.model.ceph_version.minor = int(version_public[1])
        self.model.ceph_version.revision = ".".join(version_public[2:])
        self.model.ceph_version.uuid = version_raw_split[3].strip("()")
