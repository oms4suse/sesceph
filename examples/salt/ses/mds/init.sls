include:
  - ses.ceph
  - ses.common.mds_key

keyring_mds_auth_add:
  module.run:
    - name: ceph.keyring_mds_auth_add
    - require:
      - module: keyring_mds_save
      - ceph: cluster_status

mds_create:
  module.run:
    - name: ceph.mds_create
    - kwargs: {
        name: mds.{{ grains['machine_id'] }},
        port: 1000,
        addr:{{ grains['fqdn_ip4'] }}
        }
    - require:
      - module: keyring_mds_auth_add

