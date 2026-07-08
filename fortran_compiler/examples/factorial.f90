program factorial
  integer :: n, i, result
  n = 10
  result = 1
  do i = 1, n
    result = result * i
  end do
  print *, 'factorial of', n, 'is', result
end program factorial
