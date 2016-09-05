packages:
  pkg.installed:
    - names:
      - ceph
      - python-ceph-cfg

/etc/ceph/ceph.conf:
  file:
    - managed
    - source:
      - salt://ses/ceph/ceph.conf
    - user: root
    - group: root
    - mode: 644
    - makedirs: True
    - require:
      - pkg: packages
