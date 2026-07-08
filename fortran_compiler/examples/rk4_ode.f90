! Generic 4th-order Runge-Kutta ODE solver: the derivative function is
! passed in as a procedure argument (EXTERNAL), so RK4 itself has no
! knowledge of the specific equation being solved.
program rk4_ode
  real :: y0, t0, t1, y
  integer :: steps

  y0 = 1.0
  t0 = 0.0
  t1 = 1.0
  steps = 1000

  call rk4(decay, y0, t0, t1, steps, y)

  print *, 'RK4 solution y(1) =', y
  print *, 'exact exp(-1)     =', exp(-1.0)
end program rk4_ode

! dy/dt = -y  =>  y(t) = y0 * exp(-t)
real function decay(t, y)
  real :: t, y
  decay = -y
end function decay

subroutine rk4(f, y0, t0, t1, n, y)
  real, external :: f
  real :: y0, t0, t1, y
  integer :: n
  real :: h, t, k1, k2, k3, k4
  integer :: i

  h = (t1 - t0) / real(n)
  y = y0
  t = t0
  do i = 1, n
    k1 = f(t, y)
    k2 = f(t + h / 2.0, y + h / 2.0 * k1)
    k3 = f(t + h / 2.0, y + h / 2.0 * k2)
    k4 = f(t + h, y + h * k3)
    y = y + (h / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)
    t = t + h
  end do
end subroutine rk4
