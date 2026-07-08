program matmul
  integer :: a(2,3), b(3,2), c(2,2)
  integer :: i, j, k

  do i = 1, 2
    do j = 1, 3
      a(i,j) = i * 10 + j
    end do
  end do
  do i = 1, 3
    do j = 1, 2
      b(i,j) = i + j
    end do
  end do

  do i = 1, 2
    do j = 1, 2
      c(i,j) = 0
      do k = 1, 3
        c(i,j) = c(i,j) + a(i,k) * b(k,j)
      end do
    end do
  end do

  do i = 1, 2
    do j = 1, 2
      print *, i, j, c(i,j)
    end do
  end do
end program matmul
