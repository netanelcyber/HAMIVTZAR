! A from-scratch x86-64 disassembler, written in Fortran, using this
! project's own BIND(C)/CHARACTER/array-argument extensions. Honest scope:
! this is a disassembler (machine code -> assembly text), not a full
! decompiler (assembly -> structured high-level source) -- true
! decompilation (control-flow/type recovery) is a much larger undertaking
! than fits here. Coverage targets the instruction subset this project's
! own compiler (codegen.py) emits: integer ALU ops, stack-machine
! push/pop, SSE2 scalar-double arithmetic, jumps/calls, and common
! addressing forms ([reg], [reg+disp], [base+index*scale], RIP-relative).
! Unrecognized opcodes are reported and skipped one byte at a time rather
! than aborting, so the rest of the listing still comes out.
program fortran_disasm
  integer, parameter :: maxbuf = 65536
  integer :: buf(maxbuf)
  character(len=256) :: path
  integer :: n, h, i, b, sz
  integer :: e_entry, e_phoff, e_phentsize, e_phnum
  integer :: phoff, j, p_type, p_flags, p_offset, p_vaddr, p_filesz
  integer :: startoff, pos, curaddr, count
  integer :: override_addr
  character(len=32) :: addrarg
  integer, bind(c) :: rt_open_read
  integer, bind(c) :: rt_read_byte
  integer, bind(c) :: rt_close
  integer, bind(c) :: rt_parse_int

  n = command_argument_count()
  if (n < 1) then
    print *, 'usage: fortran_disasm <executable> [start-vaddr-decimal]'
    stop
  end if
  call get_command_argument(1, path)

  override_addr = -1
  if (n >= 2) then
    call get_command_argument(2, addrarg)
    override_addr = rt_parse_int(addrarg, len(addrarg))
  end if

  h = rt_open_read(path, len(path))
  if (h < 0) then
    print *, 'error: cannot open input file'
    stop
  end if
  sz = 0
  do i = 1, maxbuf
    b = rt_read_byte(h)
    if (b < 0) exit
    sz = sz + 1
    buf(sz) = b
  end do
  call rt_close(h)

  print *, 'read', sz, 'bytes'

  e_entry = u32(buf, maxbuf, 25)
  e_phoff = u32(buf, maxbuf, 33)
  e_phentsize = u16(buf, maxbuf, 55)
  e_phnum = u16(buf, maxbuf, 57)

  if (override_addr >= 0) e_entry = override_addr

  startoff = -1
  phoff = e_phoff
  do j = 1, e_phnum
    p_type = u32(buf, maxbuf, phoff + 1)
    p_flags = u32(buf, maxbuf, phoff + 5)
    p_offset = u32(buf, maxbuf, phoff + 9)
    p_vaddr = u32(buf, maxbuf, phoff + 17)
    p_filesz = u32(buf, maxbuf, phoff + 41)
    if (p_type == 1 .and. iand(p_flags, 1) == 1 .and. &
        e_entry >= p_vaddr .and. e_entry < p_vaddr + p_filesz) then
      startoff = e_entry - p_vaddr + p_offset
    end if
    phoff = phoff + e_phentsize
  end do

  if (startoff < 0) then
    print *, 'error: could not locate a segment containing vaddr', e_entry
    stop
  end if

  print *, 'disassembling from vaddr =', e_entry
  print *, ' '

  pos = startoff + 1
  curaddr = e_entry
  count = 0
  do while (count < 6000 .and. pos <= sz)
    call decode_one(buf, maxbuf, pos, curaddr)
    count = count + 1
  end do
end program fortran_disasm

integer function u8(buf, n, i)
  integer :: n, buf(n), i
  u8 = buf(i)
end function u8

integer function u16(buf, n, i)
  integer :: n, buf(n), i
  u16 = ior(buf(i), ishft(buf(i + 1), 8))
end function u16

integer function u32(buf, n, i)
  integer :: n, buf(n), i
  u32 = ior(ior(buf(i), ishft(buf(i + 1), 8)), &
            ior(ishft(buf(i + 2), 16), ishft(buf(i + 3), 24)))
end function u32

integer function s32(buf, n, i)
  integer :: n, buf(n), i
  integer :: v, u32
  v = u32(buf, n, i)
  if (iand(v, 2147483648) /= 0) then
    s32 = v - 4294967296
  else
    s32 = v
  end if
end function s32

integer function s8(buf, n, i)
  integer :: n, buf(n), i
  if (buf(i) >= 128) then
    s8 = buf(i) - 256
  else
    s8 = buf(i)
  end if
end function s8

subroutine regname(r, nm)
  integer :: r
  character(len=3) :: nm
  if (r == 0) then
    nm = 'rax'
  else if (r == 1) then
    nm = 'rcx'
  else if (r == 2) then
    nm = 'rdx'
  else if (r == 3) then
    nm = 'rbx'
  else if (r == 4) then
    nm = 'rsp'
  else if (r == 5) then
    nm = 'rbp'
  else if (r == 6) then
    nm = 'rsi'
  else if (r == 7) then
    nm = 'rdi'
  else if (r == 8) then
    nm = 'r8 '
  else if (r == 9) then
    nm = 'r9 '
  else if (r == 10) then
    nm = 'r10'
  else if (r == 11) then
    nm = 'r11'
  else if (r == 12) then
    nm = 'r12'
  else if (r == 13) then
    nm = 'r13'
  else if (r == 14) then
    nm = 'r14'
  else
    nm = 'r15'
  end if
end subroutine regname

subroutine xmmname(r, nm)
  integer :: r
  character(len=5) :: nm
  if (r == 0) then
    nm = 'xmm0'
  else if (r == 1) then
    nm = 'xmm1'
  else if (r == 2) then
    nm = 'xmm2'
  else if (r == 3) then
    nm = 'xmm3'
  else
    nm = 'xmmN'
  end if
end subroutine xmmname

! Decodes ModRM (+ SIB + displacement) starting at buf(pos). Always
! reports a "reg" field value (0-7, extend with rex_r*8 by the caller) and
! either a plain register number for rm (is_mem=0) or a memory operand
! described by (base, index, scale, disp, has_base, has_index, is_rip).
! Returns the number of bytes consumed (ModRM + SIB + displacement, NOT
! counting the opcode itself).
subroutine decode_modrm(buf, n, pos, rex_r, rex_x, rex_b, &
                         reg, is_mem, base, has_base, index, has_index, scale, disp, is_rip, consumed)
  integer :: n, buf(n), pos, rex_r, rex_x, rex_b
  integer :: reg, is_mem, base, has_base, index, has_index, scale, disp, is_rip, consumed
  integer :: modrm, mod_, rm, sib, s32
  integer :: p

  p = pos
  modrm = buf(p)
  p = p + 1
  mod_ = ishft(modrm, -6)
  reg = iand(ishft(modrm, -3), 7) + rex_r * 8
  rm = iand(modrm, 7)

  has_index = 0
  index = 0
  scale = 1
  is_rip = 0

  if (mod_ == 3) then
    is_mem = 0
    base = rm + rex_b * 8
    has_base = 1
    disp = 0
  else
    is_mem = 1
    if (rm == 4) then
      ! SIB byte follows
      sib = buf(p)
      p = p + 1
      scale = ishft(1, ishft(sib, -6))
      index = iand(ishft(sib, -3), 7) + rex_x * 8
      has_index = 0
      if (iand(ishft(sib, -3), 7) /= 4) has_index = 1
      base = iand(sib, 7) + rex_b * 8
      has_base = 1
      if (iand(sib, 7) == 5 .and. mod_ == 0) then
        has_base = 0
        disp = s32(buf, n, p)
        p = p + 4
      else
        disp = 0
      end if
    else if (rm == 5 .and. mod_ == 0) then
      is_rip = 1
      has_base = 0
      disp = s32(buf, n, p)
      p = p + 4
    else
      base = rm + rex_b * 8
      has_base = 1
      disp = 0
    end if

    if (mod_ == 1) then
      disp = disp + buf(p)
      if (buf(p) >= 128) disp = disp - 256
      p = p + 1
    else if (mod_ == 2) then
      disp = disp + s32(buf, n, p)
      p = p + 4
    end if
  end if

  consumed = p - pos
end subroutine decode_modrm

! Prints "[base+index*scale+disp]"-style text for a memory operand using
! whichever pieces are present, via a fixed set of shapes (Fortran PRINT
! can't build one line from a variable-length item list).
subroutine print_mem(base, has_base, index, has_index, scale, disp, is_rip)
  integer :: base, has_base, index, has_index, scale, disp, is_rip
  character(len=3) :: bn, xn

  if (is_rip == 1) then
    print *, '[rip', disp, ']'
    return
  end if
  if (has_base == 1 .and. has_index == 1) then
    call regname(base, bn)
    call regname(index, xn)
    print *, '[', bn, '+', xn, '*', scale, disp, ']'
  else if (has_base == 1) then
    call regname(base, bn)
    print *, '[', bn, disp, ']'
  else if (has_index == 1) then
    call regname(index, xn)
    print *, '[', xn, '*', scale, disp, ']'
  else
    print *, '[', disp, ']'
  end if
end subroutine print_mem

subroutine decode_one(buf, n, pos, addr)
  integer :: n, buf(n), pos, addr
  integer :: start_pos, rex, rex_w, rex_r, rex_x, rex_b, has_rex
  integer :: pfx66, pfxf2, pfxf3
  integer :: op, op2, modrm_pos
  integer :: reg, is_mem, base, has_base, index, has_index, scale, disp, is_rip, consumed
  integer :: s8v, s32v, imm
  integer :: s8, s32, u8, u32
  character(len=3) :: rn1, rn2
  character(len=5) :: xn1, xn2

  start_pos = pos
  rex = 0
  rex_w = 0
  rex_r = 0
  rex_x = 0
  rex_b = 0
  has_rex = 0
  pfx66 = 0
  pfxf2 = 0
  pfxf3 = 0

  ! legacy prefixes
  do while (.true.)
    if (buf(pos) == 102) then
      pfx66 = 1
      pos = pos + 1
    else if (buf(pos) == 242) then
      pfxf2 = 1
      pos = pos + 1
    else if (buf(pos) == 243) then
      pfxf3 = 1
      pos = pos + 1
    else
      exit
    end if
  end do

  ! REX prefix: 0100WRXB (0x40-0x4F)
  if (buf(pos) >= 64 .and. buf(pos) <= 79) then
    has_rex = 1
    rex = buf(pos)
    rex_w = iand(ishft(rex, -3), 1)
    rex_r = iand(ishft(rex, -2), 1)
    rex_x = iand(ishft(rex, -1), 1)
    rex_b = iand(rex, 1)
    pos = pos + 1
  end if

  op = buf(pos)
  pos = pos + 1

  ! ---- endbr64 (F3 0F 1E FA), already consumed the F3 prefix above ----
  if (pfxf3 == 1 .and. op == 15 .and. buf(pos) == 30 .and. buf(pos + 1) == 250) then
    pos = pos + 2
    print *, addr, ': endbr64'
    addr = addr + (pos - start_pos)
    return
  end if

  ! ---- no-ModRM, register-in-opcode: PUSH/POP r64 ----
  if (op >= 80 .and. op <= 87) then
    call regname(op - 80 + rex_b * 8, rn1)
    print *, addr, ': push', rn1
    addr = addr + (pos - start_pos)
    return
  end if
  if (op >= 88 .and. op <= 95) then
    call regname(op - 88 + rex_b * 8, rn1)
    print *, addr, ': pop', rn1
    addr = addr + (pos - start_pos)
    return
  end if

  ! ---- no-operand ----
  if (op == 195) then
    print *, addr, ': ret'
    addr = addr + (pos - start_pos)
    return
  end if
  if (op == 153) then
    print *, addr, ': cqo'
    addr = addr + (pos - start_pos)
    return
  end if

  ! ---- rel8 branches ----
  if (op == 235) then
    s8v = s8(buf, n, pos)
    pos = pos + 1
    print *, addr, ': jmp', addr + (pos - start_pos) + s8v
    addr = addr + (pos - start_pos)
    return
  end if
  if (op >= 112 .and. op <= 127) then
    s8v = s8(buf, n, pos)
    pos = pos + 1
    print *, addr, ': jcc(', op - 112, ')', addr + (pos - start_pos) + s8v
    addr = addr + (pos - start_pos)
    return
  end if

  ! ---- rel32 branches / call ----
  if (op == 233) then
    s32v = s32(buf, n, pos)
    pos = pos + 4
    print *, addr, ': jmp', addr + (pos - start_pos) + s32v
    addr = addr + (pos - start_pos)
    return
  end if
  if (op == 232) then
    s32v = s32(buf, n, pos)
    pos = pos + 4
    print *, addr, ': call', addr + (pos - start_pos) + s32v
    addr = addr + (pos - start_pos)
    return
  end if

  ! ---- MOV r64, imm64 (B8+r, only when REX.W and no shorter C7 form was used) ----
  if (op >= 184 .and. op <= 191 .and. rex_w == 1) then
    call regname(op - 184 + rex_b * 8, rn1)
    s32v = u32(buf, n, pos)
    print *, addr, ': movabs', rn1, u32(buf, n, pos + 4), s32v
    pos = pos + 8
    addr = addr + (pos - start_pos)
    return
  end if

  ! ---- two-byte opcode map (0F xx) ----
  if (op == 15) then
    op2 = buf(pos)
    pos = pos + 1
    if (op2 >= 128 .and. op2 <= 143) then
      s32v = s32(buf, n, pos)
      pos = pos + 4
      print *, addr, ': jcc(', op2 - 128, ')', addr + (pos - start_pos) + s32v
      addr = addr + (pos - start_pos)
      return
    end if
    if (op2 == 175) then
      call decode_modrm(buf, n, pos, rex_r, rex_x, rex_b, reg, is_mem, base, has_base, &
                         index, has_index, scale, disp, is_rip, consumed)
      pos = pos + consumed
      call regname(reg, rn1)
      if (is_mem == 0) then
        call regname(base, rn2)
        print *, addr, ': imul', rn1, rn2
      else
        print *, addr, ': imul', rn1, '<mem>'
      end if
      addr = addr + (pos - start_pos)
      return
    end if
    if (op2 == 182 .or. op2 == 183) then
      call decode_modrm(buf, n, pos, rex_r, rex_x, rex_b, reg, is_mem, base, has_base, &
                         index, has_index, scale, disp, is_rip, consumed)
      pos = pos + consumed
      call regname(reg, rn1)
      if (is_mem == 0) then
        call regname(base, rn2)
        print *, addr, ': movzx', rn1, rn2
      else
        print *, addr, ': movzx', rn1, '<mem>'
      end if
      addr = addr + (pos - start_pos)
      return
    end if
    if (op2 >= 144 .and. op2 <= 159) then
      call decode_modrm(buf, n, pos, rex_r, rex_x, rex_b, reg, is_mem, base, has_base, &
                         index, has_index, scale, disp, is_rip, consumed)
      pos = pos + consumed
      call regname(base, rn1)
      print *, addr, ': setcc(', op2 - 144, ')', rn1
      addr = addr + (pos - start_pos)
      return
    end if
    if (op2 == 47 .and. pfx66 == 1) then
      call decode_modrm(buf, n, pos, rex_r, rex_x, rex_b, reg, is_mem, base, has_base, &
                         index, has_index, scale, disp, is_rip, consumed)
      pos = pos + consumed
      call xmmname(reg, xn1)
      if (is_mem == 0) then
        call xmmname(base, xn2)
        print *, addr, ': comisd', xn1, xn2
      else
        print *, addr, ': comisd', xn1, '<mem>'
      end if
      addr = addr + (pos - start_pos)
      return
    end if
    if (op2 == 87 .and. pfx66 == 1) then
      call decode_modrm(buf, n, pos, rex_r, rex_x, rex_b, reg, is_mem, base, has_base, &
                         index, has_index, scale, disp, is_rip, consumed)
      pos = pos + consumed
      call xmmname(reg, xn1)
      call xmmname(base, xn2)
      print *, addr, ': xorpd', xn1, xn2
      addr = addr + (pos - start_pos)
      return
    end if
    if (pfxf2 == 1 .and. (op2 == 16 .or. op2 == 17 .or. op2 == 88 .or. op2 == 89 .or. &
                           op2 == 92 .or. op2 == 93 .or. op2 == 94 .or. op2 == 95 .or. &
                           op2 == 42 .or. op2 == 44 .or. op2 == 81)) then
      call decode_modrm(buf, n, pos, rex_r, rex_x, rex_b, reg, is_mem, base, has_base, &
                         index, has_index, scale, disp, is_rip, consumed)
      pos = pos + consumed
      call xmmname(reg, xn1)
      if (op2 == 42) then
        ! cvtsi2sd xmm, r/m64 (GP source register, not xmm)
        if (is_mem == 0) then
          call regname(base, rn1)
          print *, addr, ': cvtsi2sd', xn1, rn1
        else
          print *, addr, ': cvtsi2sd', xn1, '<mem>'
        end if
      else if (op2 == 44) then
        call regname(reg, rn1)
        if (is_mem == 0) then
          call xmmname(base, xn2)
          print *, addr, ': cvttsd2si', rn1, xn2
        else
          print *, addr, ': cvttsd2si', rn1, '<mem>'
        end if
      else
        if (is_mem == 0) then
          call xmmname(base, xn2)
        else
          xn2 = 'mem  '
        end if
        if (op2 == 16 .or. op2 == 17) then
          print *, addr, ': movsd', xn1, xn2
        else if (op2 == 88) then
          print *, addr, ': addsd', xn1, xn2
        else if (op2 == 89) then
          print *, addr, ': mulsd', xn1, xn2
        else if (op2 == 92) then
          print *, addr, ': subsd', xn1, xn2
        else if (op2 == 93) then
          print *, addr, ': minsd', xn1, xn2
        else if (op2 == 94) then
          print *, addr, ': divsd', xn1, xn2
        else if (op2 == 95) then
          print *, addr, ': maxsd', xn1, xn2
        else if (op2 == 81) then
          print *, addr, ': sqrtsd', xn1, xn2
        end if
      end if
      addr = addr + (pos - start_pos)
      return
    end if
    print *, addr, ': (unknown 0f opcode)', op2
    pos = start_pos + 1
    addr = addr + 1
    return
  end if

  ! ---- group1 imm8, register-direct only (add/or/and/sub/xor/cmp rm64,imm8) ----
  if (op == 131) then
    call decode_modrm(buf, n, pos, rex_r, rex_x, rex_b, reg, is_mem, base, has_base, &
                       index, has_index, scale, disp, is_rip, consumed)
    pos = pos + consumed
    s8v = s8(buf, n, pos)
    pos = pos + 1
    if (is_mem == 0) then
      call regname(base, rn1)
      print *, addr, ': group1(', iand(reg, 7), ')', rn1, s8v
    else
      print *, addr, ': group1(', iand(reg, 7), ') <mem>', s8v
    end if
    addr = addr + (pos - start_pos)
    return
  end if

  ! ---- MOV r/m64, imm32 (C7 /0) ----
  if (op == 199) then
    call decode_modrm(buf, n, pos, rex_r, rex_x, rex_b, reg, is_mem, base, has_base, &
                       index, has_index, scale, disp, is_rip, consumed)
    pos = pos + consumed
    s32v = s32(buf, n, pos)
    pos = pos + 4
    if (is_mem == 0) then
      call regname(base, rn1)
      print *, addr, ': mov', rn1, s32v
    else
      print *, addr, ': mov <mem>', s32v
    end if
    addr = addr + (pos - start_pos)
    return
  end if

  ! ---- group3 (F7 /2 not, /3 neg, /7 idiv, /5 imul, /4 mul) ----
  if (op == 247) then
    call decode_modrm(buf, n, pos, rex_r, rex_x, rex_b, reg, is_mem, base, has_base, &
                       index, has_index, scale, disp, is_rip, consumed)
    pos = pos + consumed
    if (is_mem == 0) then
      call regname(base, rn1)
      print *, addr, ': group3(', iand(reg, 7), ')', rn1
    else
      print *, addr, ': group3(', iand(reg, 7), ') <mem>'
    end if
    addr = addr + (pos - start_pos)
    return
  end if

  ! ---- INC/DEC r/m64 (FF /0, /1); also /2 call, /4 jmp indirect ----
  if (op == 255) then
    call decode_modrm(buf, n, pos, rex_r, rex_x, rex_b, reg, is_mem, base, has_base, &
                       index, has_index, scale, disp, is_rip, consumed)
    pos = pos + consumed
    if (is_mem == 0) then
      call regname(base, rn1)
      print *, addr, ': group5(', iand(reg, 7), ')', rn1
    else
      print *, addr, ': group5(', iand(reg, 7), ') <mem>'
    end if
    addr = addr + (pos - start_pos)
    return
  end if

  ! ---- ordinary ModRM ALU ops: add/or/and/sub/xor/cmp/mov/lea/test (r/m,r or r,r/m) ----
  if (op == 1 .or. op == 3 .or. op == 9 .or. op == 11 .or. op == 33 .or. op == 35 .or. &
      op == 41 .or. op == 43 .or. op == 49 .or. op == 51 .or. op == 57 .or. op == 59 .or. &
      op == 133 .or. op == 137 .or. op == 139 .or. op == 141) then
    call decode_modrm(buf, n, pos, rex_r, rex_x, rex_b, reg, is_mem, base, has_base, &
                       index, has_index, scale, disp, is_rip, consumed)
    pos = pos + consumed
    call regname(reg, rn1)
    if (op == 141) then
      ! LEA: rm side is always a memory operand (never mod==11 in valid code)
      print *, addr, ': lea', rn1
      call print_mem(base, has_base, index, has_index, scale, disp, is_rip)
    else if (is_mem == 0) then
      call regname(base, rn2)
      if (op == 137 .or. op == 1 .or. op == 9 .or. op == 33 .or. op == 41 .or. &
          op == 49 .or. op == 57 .or. op == 133) then
        print *, addr, ': alu', rn2, rn1
      else
        print *, addr, ': alu', rn1, rn2
      end if
    else
      print *, addr, ': alu', rn1, '<mem>'
    end if
    addr = addr + (pos - start_pos)
    return
  end if

  print *, addr, ': (unknown opcode)', op
  pos = start_pos + 1
  addr = addr + 1
end subroutine decode_one
