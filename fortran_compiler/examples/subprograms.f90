program subprograms
  integer :: a, b

  a = 3
  b = 7
  call swap(a, b)
  print *, 'after swap a=', a, 'b=', b

  print *, 'factorial(5) =', fact(5)
end program subprograms

subroutine swap(x, y)
  integer :: x, y, tmp
  tmp = x
  x = y
  y = tmp
end subroutine swap

function fact(n)
  integer :: fact, n, i, acc
  acc = 1
  do i = 1, n
    acc = acc * i
  end do
  fact = acc
end function fact
