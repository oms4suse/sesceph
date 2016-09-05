include:
  - ses.ceph
  - ses.common.osd_key

keyring_osd_auth_add:
  module.run:
    - name: ceph.keyring_osd_auth_add
    - require:
      - module: keyring_osd_save
      - ceph: cluster_status

# Prepare disks for OSD use

prepare_vdb:
  module.run:
    - name: ceph.osd_prepare
    - kwargs: {
        osd_dev: /dev/vdb
        }
    - require:
      - module: keyring_osd_auth_add

# Activate OSD's on prepared disks

activate_vdb:
  module.run:
    - name: ceph.osd_activate
    - kwargs: {
        osd_dev: /dev/vdb
        }
