program primes
  integer, parameter :: n = 30
  integer :: is_composite(30)
  integer :: i, j, count

  do i = 1, n
    is_composite(i) = 0
  end do

  count = 0
  do i = 2, n
    if (is_composite(i) == 0) then
      count = count + 1
      print *, i
      do j = i * i, n, i
        is_composite(j) = 1
      end do
    end if
  end do

  print *, 'total primes up to', n, '=', count
end program primes
