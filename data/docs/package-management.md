# Package Management

Linux distributions install software through package managers. The commands
differ by distribution family.

## Debian / Ubuntu (APT)

```
sudo apt update                 # refresh the package lists
sudo apt upgrade                # upgrade installed packages
sudo apt install nginx          # install a package
sudo apt remove nginx           # remove a package, keep config
sudo apt purge nginx            # remove a package and its config
apt search keyword              # search for packages
apt show nginx                  # show package details
sudo apt autoremove             # remove unused dependencies
```

The lower-level tool `dpkg` installs a local `.deb` file: `sudo dpkg -i pkg.deb`.

## Fedora / RHEL / CentOS (DNF)

```
sudo dnf check-update           # see available updates
sudo dnf upgrade                # apply updates
sudo dnf install nginx          # install a package
sudo dnf remove nginx           # remove a package
dnf search keyword              # search
dnf info nginx                  # package details
sudo dnf autoremove             # remove unused dependencies
```

`dnf` is the successor to `yum`; the same commands work under the `yum` name on
older systems. The low-level tool is `rpm` (e.g. `rpm -i pkg.rpm`,
`rpm -qa` to list installed packages).

## Arch Linux (pacman)

```
sudo pacman -Syu                # sync databases and upgrade everything
sudo pacman -S nginx            # install a package
sudo pacman -R nginx            # remove a package
sudo pacman -Rns nginx          # remove with dependencies and config
pacman -Ss keyword              # search remote packages
pacman -Qi nginx                # info on an installed package
```

## openSUSE (zypper)

```
sudo zypper refresh             # refresh repositories
sudo zypper update              # apply updates
sudo zypper install nginx       # install
sudo zypper remove nginx        # remove
zypper search keyword           # search
```

## Universal package formats

`Flatpak` and `Snap` distribute sandboxed applications that work across
distributions:

```
flatpak install flathub org.gimp.GIMP
snap install code --classic
```
