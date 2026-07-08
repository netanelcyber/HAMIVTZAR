program bubble_sort
  integer :: a(6)
  integer :: i

  a(1) = 5
  a(2) = 3
  a(3) = 8
  a(4) = 1
  a(5) = 9
  a(6) = 2

  call sort(a, 6)

  do i = 1, 6
    print *, a(i)
  end do
end program bubble_sort

subroutine sort(arr, n)
  integer :: n, arr(n)
  integer :: i, j, tmp
  do i = 1, n - 1
    do j = 1, n - i
      if (arr(j) > arr(j+1)) then
        tmp = arr(j)
        arr(j) = arr(j+1)
        arr(j+1) = tmp
      end if
    end do
  end do
end subroutine sort
