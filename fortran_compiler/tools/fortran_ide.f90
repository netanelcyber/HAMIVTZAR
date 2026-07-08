! A terminal-based IDE, written in Fortran: edit-compile-run-inspect loop
! for a single source file, built on this project's own BIND(C)/CHARACTER/
! EXECUTE_COMMAND_LINE extensions. Terminal UI, not a windowed GUI --
! this project's Fortran subset has no graphics FFI (no BIND(C) interface
! to a windowing library), so a text menu is the honest deliverable; it
! still ties the whole toolchain (compiler, disassembler, debugger)
! together interactively.
!
! Usage: fortran_ide <source.f90>
program fortran_ide
  character(len=256) :: source
  character(len=260) :: exe
  character(len=600) :: cmd
  character(len=32) :: numbuf
  integer :: n, choice, bp
  integer, bind(c) :: rt_make_exe_name
  integer, bind(c) :: rt_int_to_str

  n = command_argument_count()
  if (n < 1) then
    print *, 'usage: fortran_ide <source.f90>'
    stop
  end if
  call get_command_argument(1, source)
  call rt_make_exe_name(source, len(source), exe, len(exe))

  do while (.true.)
    print *, ' '
    print *, '========================================'
    print *, ' Fortran IDE --', source
    print *, ' compiled to  --', exe
    print *, '========================================'
    print *, '1) view source'
    print *, '2) compile'
    print *, '3) run'
    print *, '4) disassemble main (needs a compiled build)'
    print *, '5) debug: run to a breakpoint (decimal vaddr)'
    print *, '0) quit'
    print *, 'choice?'
    read *, choice

    if (choice == 0) then
      exit

    else if (choice == 1) then
      call view_file(source)

    else if (choice == 2) then
      cmd = 'python3 /home/user/HAMIVTZAR/fortran_compiler/fortranc.py ' &
            // source // ' -o ' // exe
      call execute_command_line(cmd)

    else if (choice == 3) then
      call execute_command_line(exe)

    else if (choice == 4) then
      cmd = '/home/user/HAMIVTZAR/fortran_compiler/tools/bin/fortran_disasm ' // exe
      call execute_command_line(cmd)

    else if (choice == 5) then
      print *, 'breakpoint vaddr (decimal, e.g. from option 4)?'
      read *, bp
      call rt_int_to_str(bp, numbuf, len(numbuf))
      cmd = '/home/user/HAMIVTZAR/fortran_compiler/tools/bin/fortran_dbg ' &
            // exe // ' ' // numbuf
      call execute_command_line(cmd)

    else
      print *, 'unknown choice'
    end if
  end do
end program fortran_ide

subroutine view_file(path)
  character(len=256) :: path
  integer :: h, b
  integer, bind(c) :: rt_open_read
  integer, bind(c) :: rt_read_byte
  integer, bind(c) :: rt_close
  integer, bind(c) :: rt_print_char

  h = rt_open_read(path, len(path))
  if (h < 0) then
    print *, 'cannot open', path
    return
  end if
  do while (.true.)
    b = rt_read_byte(h)
    if (b < 0) exit
    call rt_print_char(b)
  end do
  call rt_close(h)
end subroutine view_file
