program arrays
  integer :: a(10)
  integer :: i, total
  real :: avg

  do i = 1, 10
    a(i) = i * i
  end do

  total = 0
  do i = 1, 10
    total = total + a(i)
  end do

  avg = real(total) / real(10)
  print *, 'sum of squares 1..10 =', total
  print *, 'average =', avg
end program arrays
