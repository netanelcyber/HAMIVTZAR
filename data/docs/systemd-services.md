# Managing Services with systemd

## systemctl basics

`systemd` is the init system and service manager on most modern Linux
distributions. You control services (units) with `systemctl`.

```
systemctl start nginx       # start a service now
systemctl stop nginx        # stop it now
systemctl restart nginx     # stop then start
systemctl reload nginx      # reload config without a full restart
systemctl status nginx      # show state, recent logs, and the PID
```

Enable or disable whether a service starts at boot:

```
systemctl enable nginx      # start automatically at boot
systemctl disable nginx     # do not start at boot
systemctl enable --now nginx  # enable and start in one step
systemctl is-enabled nginx  # check boot status
```

## Writing a unit file

Service units live in `/etc/systemd/system/` (for local units) or
`/usr/lib/systemd/system/` (for packaged ones). A minimal service:

```
[Unit]
Description=My application
After=network.target

[Service]
ExecStart=/usr/bin/myapp --config /etc/myapp.conf
Restart=on-failure
User=myapp

[Install]
WantedBy=multi-user.target
```

After adding or editing a unit, reload systemd's view of unit files:

```
systemctl daemon-reload
```

## Viewing logs with journalctl

`systemd` captures service output in the journal. Query it with `journalctl`:

```
journalctl -u nginx              # logs for one unit
journalctl -u nginx -f           # follow new log lines live
journalctl -u nginx --since today
journalctl -p err -b             # errors from the current boot
journalctl -b -1                 # logs from the previous boot
```

## Targets

systemd targets group units, replacing classic runlevels. `multi-user.target`
is a non-graphical multi-user system; `graphical.target` adds a display
manager. Set the default with `systemctl set-default multi-user.target`.
