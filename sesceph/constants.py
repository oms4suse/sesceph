
try:
    from salt.utils import which as _find_executable
except:
    from distutils.spawn import _find_executable

_path_lsblk = _find_executable('lsblk')
_path_ceph_disk = _find_executable('ceph-disk')
_path_partprobe = _find_executable('partprobe')
_path_sgdisk = _find_executable('sgdisk')

JOURNAL_UUID = '45b0969e-9b03-4f30-b4c6-b4b80ceff106'
OSD_UUID = '4fbd7e29-9d25-41b8-afd0-062c0ceff05d'
