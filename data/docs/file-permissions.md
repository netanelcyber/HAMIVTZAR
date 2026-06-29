# File Permissions and Ownership

## Permission model

Every file and directory in Linux has an owner, a group, and a set of
permissions for three classes of users: the owner (`u`), the group (`g`), and
others (`o`). Each class has three permission bits: read (`r`), write (`w`),
and execute (`x`).

You can view permissions with `ls -l`. The first column shows the type and the
nine permission bits, for example `-rwxr-xr--`. The leading character is the
file type (`-` regular file, `d` directory, `l` symlink).

## Changing permissions with chmod

`chmod` changes permission bits. It accepts symbolic or numeric (octal) modes.

Symbolic mode adds (`+`), removes (`-`), or sets (`=`) bits:

```
chmod u+x script.sh      # make the file executable for its owner
chmod go-w file.txt      # remove write for group and others
chmod a=r file.txt       # set everyone to read-only
```

Numeric mode uses one octal digit per class, where read=4, write=2, execute=1:

```
chmod 755 script.sh      # rwx for owner, r-x for group and others
chmod 644 file.txt       # rw- for owner, r-- for group and others
chmod 600 secret.key     # rw- for owner only
```

Use `-R` to apply changes recursively to a directory tree.

## Changing ownership with chown and chgrp

`chown` changes the owner (and optionally the group). `chgrp` changes only the
group. These usually require root.

```
chown alice file.txt          # change owner to alice
chown alice:devs file.txt     # change owner to alice and group to devs
chgrp devs file.txt           # change group to devs
chown -R alice:alice /srv/app # recurse through a directory
```

## The umask

The `umask` controls the default permissions for newly created files. It is a
mask subtracted from the base permissions (666 for files, 777 for directories).
A umask of `022` yields new files as `644` and new directories as `755`. Run
`umask` with no arguments to print the current value.

## Special bits

The setuid (`u+s`) and setgid (`g+s`) bits make an executable run with the
owner's or group's privileges. The sticky bit (`+t`) on a directory, such as
`/tmp`, lets users delete only their own files. Set it with `chmod 1777 dir`.
