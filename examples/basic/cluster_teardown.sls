# Remove the ceph cluster from node
run_purge:
  module.run:
    - name: ceph_cfg.purge

# Wipe data on drives

zap_vdb:
   module.run:
    - name: ceph_cfg.zap
    - dev: /dev/vdb


zap_vdc:
   module.run:
    - name: ceph_cfg.zap
    - dev: /dev/vdc

