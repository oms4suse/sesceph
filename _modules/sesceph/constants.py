import os.path

try:
    from salt.utils import which as find_executable
except:
    from distutils.spawn import find_executable


_path_lsblk = find_executable('lsblk')
_path_ceph_disk = find_executable('ceph-disk')
_path_partprobe = find_executable('partprobe')
_path_sgdisk = find_executable('sgdisk')
_path_ceph_authtool = find_executable('ceph-authtool')
_path_ceph = find_executable('ceph')
_path_ceph_mon = find_executable('ceph-mon')
_path_systemctl = find_executable('systemctl')

JOURNAL_UUID = '45b0969e-9b03-4f30-b4c6-b4b80ceff106'
OSD_UUID = '4fbd7e29-9d25-41b8-afd0-062c0ceff05d'


_path_ceph_lib = "/var/lib/ceph/"
_path_ceph_lib_osd = os.path.join(_path_ceph_lib,"osd")
_path_ceph_lib_mon = os.path.join(_path_ceph_lib,"mon")
_path_ceph_lib_rgw = os.path.join(_path_ceph_lib,"radosgw")


