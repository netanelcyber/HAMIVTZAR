program fibonacci
  integer :: n, i, a, b, tmp
  n = 15
  a = 0
  b = 1
  do i = 1, n
    print *, a
    tmp = a + b
    a = b
    b = tmp
  end do
end program fibonacci
