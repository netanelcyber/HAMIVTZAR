! A ptrace-based debugger, written in Fortran, using this project's own
! BIND(C)/CHARACTER extensions to reach fork/ptrace/waitpid directly (see
! runtime.c). Linux-only by nature -- ptrace has no Windows equivalent.
!
! Usage: fortran_dbg <executable> [breakpoint-vaddr-decimal]
!
! With no breakpoint address, just runs the target under ptrace and
! reports how it exited. With one, it sets a breakpoint (INT3 byte patch)
! at that address, runs to it, dumps a handful of registers, removes the
! breakpoint and restores the original instruction, single-steps a few
! instructions to show that working, then lets the target run to
! completion.
program fortran_dbg
  character(len=256) :: path
  character(len=32) :: addrarg
  integer :: n, pid, status, bp_addr, i
  integer :: orig_qword, patched_qword, rip

  integer, bind(c) :: rt_parse_int
  integer, bind(c) :: rt_fork
  integer, bind(c) :: rt_ptrace_traceme
  integer, bind(c) :: rt_execve_self
  integer, bind(c) :: rt_waitpid
  integer, bind(c) :: rt_wifexited
  integer, bind(c) :: rt_wexitstatus
  integer, bind(c) :: rt_wifstopped
  integer, bind(c) :: rt_wstopsig
  integer, bind(c) :: rt_ptrace_peektext
  integer, bind(c) :: rt_ptrace_poketext
  integer, bind(c) :: rt_ptrace_get_rip
  integer, bind(c) :: rt_ptrace_get_rax
  integer, bind(c) :: rt_ptrace_get_rsp
  integer, bind(c) :: rt_ptrace_get_rbp
  integer, bind(c) :: rt_ptrace_get_rdi
  integer, bind(c) :: rt_ptrace_get_rsi
  integer, bind(c) :: rt_ptrace_set_rip
  integer, bind(c) :: rt_ptrace_cont
  integer, bind(c) :: rt_ptrace_singlestep
  integer, bind(c) :: rt_ptrace_kill

  n = command_argument_count()
  if (n < 1) then
    print *, 'usage: fortran_dbg <executable> [breakpoint-vaddr-decimal]'
    stop
  end if
  call get_command_argument(1, path)

  bp_addr = -1
  if (n >= 2) then
    call get_command_argument(2, addrarg)
    bp_addr = rt_parse_int(addrarg, len(addrarg))
  end if

  pid = rt_fork()
  if (pid == 0) then
    call rt_ptrace_traceme()
    call rt_execve_self(path, len(path))
  else
    print *, 'debugger: launched pid', pid

    status = rt_waitpid(pid)   ! initial stop at exec

    if (bp_addr >= 0) then
      orig_qword = rt_ptrace_peektext(pid, bp_addr)
      patched_qword = ior(iand(orig_qword, -256), 204)   ! low byte -> 0xCC (INT3)
      call rt_ptrace_poketext(pid, bp_addr, patched_qword)
      print *, 'debugger: breakpoint set at', bp_addr

      call rt_ptrace_cont(pid)
      status = rt_waitpid(pid)

      if (rt_wifexited(status) == 1) then
        print *, 'debugger: target exited before hitting the breakpoint, code', &
                  rt_wexitstatus(status)
        stop
      end if

      rip = rt_ptrace_get_rip(pid)
      print *, ' '
      print *, 'debugger: breakpoint hit, registers:'
      print *, '  rip =', rip - 1, '(reported rip', rip, 'minus the INT3 byte)'
      print *, '  rax =', rt_ptrace_get_rax(pid)
      print *, '  rsp =', rt_ptrace_get_rsp(pid)
      print *, '  rbp =', rt_ptrace_get_rbp(pid)
      print *, '  rdi =', rt_ptrace_get_rdi(pid)
      print *, '  rsi =', rt_ptrace_get_rsi(pid)

      ! remove the breakpoint and rewind rip onto the real instruction
      call rt_ptrace_poketext(pid, bp_addr, orig_qword)
      call rt_ptrace_set_rip(pid, bp_addr)

      print *, ' '
      print *, 'debugger: single-stepping 5 instructions from the breakpoint:'
      do i = 1, 5
        call rt_ptrace_singlestep(pid)
        status = rt_waitpid(pid)
        if (rt_wifexited(status) == 1) then
          print *, 'debugger: target exited during single-step, code', rt_wexitstatus(status)
          stop
        end if
        print *, '  step', i, ': rip =', rt_ptrace_get_rip(pid)
      end do
    end if

    print *, ' '
    print *, 'debugger: resuming to completion'
    call rt_ptrace_cont(pid)
    status = rt_waitpid(pid)
    if (rt_wifexited(status) == 1) then
      print *, 'debugger: target exited with code', rt_wexitstatus(status)
    else if (rt_wifstopped(status) == 1) then
      print *, 'debugger: target stopped by signal', rt_wstopsig(status)
      call rt_ptrace_kill(pid)
    end if
  end if
end program fortran_dbg
