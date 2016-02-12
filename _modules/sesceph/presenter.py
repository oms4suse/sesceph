class mdl_presentor():
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
                'NAME',
                'PARTTABLE',
                'ROTA',
                'RQ-SIZE',
                'SCHED',
                'SIZE',
                'VENDOR'
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
                if key in [ "dev", "dev_journal"]:
                    osd_out[key] = self.lsblk_partition_by_disk_part(osd_in.get(key))
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

    def mon_status(self):
        """
        Present the monitor status
        """
        if (None == self.model.mon_status):
            return {}
        fsid = None
        output = {}
        for key in self.model.mon_status.keys():
            if key == 'monmap':
                monmap_in = self.model.mon_status.get(key)
                monmap_out = {}
                for monmap_key in monmap_in.keys():
                    if monmap_key == 'fsid':
                        fsid = monmap_in.get(monmap_key)
                        continue
                    monmap_out[monmap_key] = monmap_in.get(monmap_key)
                output[key] = monmap_out
                continue
            output[key] = self.model.mon_status.get(key)
        if fsid == None:
            return {}
        return {fsid : output}

    def auth_list(self):
        output = {}
        for keyname in self.model.auth_list.keys():
            section = {}
            keydetails = self.model.auth_list.get(keyname)
            for keysection in keydetails.keys():
                if keysection == "name":
                    continue
                section[keysection] = keydetails.get(keysection)
            output[keyname] = section
        return output


    def pool_list(self):
        return self.model.pool_list


    def ceph_version(self):
        output = {
            "major" : self.model.ceph_version.major,
            "minor" : self.model.ceph_version.minor,
            "revision" : self.model.ceph_version.revision,
            "uuid" : self.model.ceph_version.uuid
        }
        return output
