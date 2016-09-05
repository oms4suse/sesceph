keyring_osd_save:
  module.run:
    - name: ceph.keyring_save
    - kwargs: {
        'keyring_type' : 'osd',
        'secret' : {{ salt['pillar.get']('osd.secret', 'AQBR8KhWgKw6FhAA__DEFAULT_KEY__PKzIo6def') }}
        }
    - require:
      - sls: ses.ceph
