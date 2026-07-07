# Processes and Signals

## Inspecting processes

A process is a running instance of a program, identified by a numeric process
ID (PID). Common tools to inspect processes:

```
ps aux            # snapshot of all processes with CPU/memory
ps -ef            # alternative full-format listing
top               # live, interactive process view
htop              # friendlier interactive viewer (if installed)
pgrep nginx       # find PIDs by name
pidof sshd        # print the PID(s) of a running program
```

To see a process tree showing parent/child relationships, use `pstree`.

## Signals

Signals are asynchronous notifications sent to a process. Each has a number and
a name. Important ones:

- `SIGTERM` (15): polite request to terminate; the default for `kill`.
- `SIGKILL` (9): force kill; cannot be caught or ignored.
- `SIGINT` (2): interrupt, sent by Ctrl+C.
- `SIGHUP` (1): hang up; many daemons reload their config on this.
- `SIGSTOP` / `SIGCONT`: pause and resume a process.

## Sending signals

`kill` sends a signal to a PID; `killall` and `pkill` send by name.

```
kill 1234            # send SIGTERM to PID 1234
kill -9 1234         # send SIGKILL (force)
kill -HUP 1234       # ask the process to reload
killall firefox      # signal every process named firefox
pkill -f myscript.py # match against the full command line
```

Prefer `SIGTERM` first so the process can clean up; use `SIGKILL` only when it
will not exit.

## Jobs and background processes

In a shell you can manage jobs:

```
sleep 100 &      # run in the background
jobs             # list background jobs
fg %1            # bring job 1 to the foreground
bg %1            # resume job 1 in the background
Ctrl+Z           # suspend the foreground job (SIGTSTP)
```

To keep a process running after you log out, use `nohup command &` or run it
under a terminal multiplexer such as `tmux` or `screen`.

## Priority

`nice` starts a process with an adjusted scheduling priority, and `renice`
changes it for a running process. Niceness ranges from -20 (highest priority)
to 19 (lowest).

```
nice -n 10 ./batch.sh     # start with lower priority
renice -n 5 -p 1234       # change priority of PID 1234
```
