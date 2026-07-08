! Exercises argument passing beyond the register-argument count on both
! targets (4 on Windows x64, 6 on SysV): args 5+ (Windows) / 7+ (Linux)
! must be spilled to the stack at the exact offset the callee's prologue
! reads them from.
program many_args
  real :: total
  call sum8(1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, total)
  print *, 'total =', total
end program many_args

subroutine sum8(a, b, c, d, e, f, g, h, total)
  real :: a, b, c, d, e, f, g, h, total
  total = a + b + c + d + e + f + g + h
end subroutine sum8
