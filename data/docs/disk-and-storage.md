# Disk and Storage

## Checking disk usage

```
df -h               # free space per mounted filesystem, human-readable
df -i               # inode usage (useful when "no space" but df -h looks fine)
du -sh /var/log     # total size of a directory
du -h --max-depth=1 /var   # size of each immediate subdirectory
ncdu /var           # interactive disk usage explorer (if installed)
```

## Listing block devices

```
lsblk               # tree of disks and partitions
lsblk -f            # include filesystem type and UUID
blkid               # show UUIDs and types of block devices
fdisk -l            # detailed partition tables (as root)
```

## Mounting filesystems

```
mount /dev/sdb1 /mnt/data     # mount a device
umount /mnt/data              # unmount
mount                         # list current mounts
findmnt                       # tree view of mounts
```

Persistent mounts are defined in `/etc/fstab`, one line per filesystem with the
device (often by UUID), mount point, type, options, and dump/pass fields. After
editing it you can test with `mount -a`.

## Creating filesystems

```
mkfs.ext4 /dev/sdb1     # format as ext4
mkfs.xfs /dev/sdb1      # format as xfs
mkswap /dev/sdb2        # prepare a swap partition
swapon /dev/sdb2        # enable swap
```

## Checking and repairing

`fsck` checks and repairs a filesystem. Only run it on an unmounted
filesystem.

```
umount /dev/sdb1
fsck /dev/sdb1
```

## Symbolic and hard links

```
ln -s /path/to/target linkname   # symbolic (soft) link
ln /path/to/target linkname      # hard link (same inode)
readlink -f linkname             # resolve a symlink to its target
```
