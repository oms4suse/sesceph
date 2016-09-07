include:
  - ses.ceph
  - ses.common.admin_key
  - ses.common.mon_key

mon_create:
    module.run:
    - name: ceph.mon_create
    - kwargs: {
        mon_name: {{ grains['localhost'] }}
        }
    - require:
      - module: keyring_admin_save
      - module: keyring_mon_save

cluster_status:
    ceph.quorum:
    - require:
      - module: mon_create

