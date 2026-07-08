program ifelse
  integer :: i
  do i = 1, 15
    if (mod(i, 15) == 0) then
      print *, 'fizzbuzz'
    else if (mod(i, 3) == 0) then
      print *, 'fizz'
    else if (mod(i, 5) == 0) then
      print *, 'buzz'
    else
      print *, i
    end if
  end do
end program ifelse
