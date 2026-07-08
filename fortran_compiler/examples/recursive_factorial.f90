! Recursion needs no special codegen support: every call already gets its
! own fresh stack frame, so a function is free to call itself. RECURSIVE
! is accepted (and, since nothing special is required, ignored).
program recursive_factorial
  integer :: fact
  integer :: i

  do i = 0, 10
    print *, i, fact(i)
  end do
end program recursive_factorial

recursive function fact(n)
  integer :: fact, n
  if (n <= 1) then
    fact = 1
  else
    fact = n * fact(n - 1)
  end if
end function fact
