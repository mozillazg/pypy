	.type	main, @function
main:
	call	somewhere
	;; expected {(%rsp) | %rbp, %rbx, %r12, %r13, %r14, %r15 | }

	pushq   %r13
	call	somewhere
	;; expected {8(%rsp) | %rbp, %rbx, %r12, (%rsp), %r14, %r15 | }

	pushq   %rbx
	call	somewhere
	;; expected {16(%rsp) | %rbp, (%rsp), %r12, 8(%rsp), %r14, %r15 | }

	pushq   %r12
	call	somewhere
	;; expected {24(%rsp) | %rbp, 8(%rsp), (%rsp), 16(%rsp), %r14, %r15 | }

	pushq   %r15
	call	somewhere
	;; expected {32(%rsp) | %rbp, 16(%rsp), 8(%rsp), 24(%rsp), %r14, (%rsp) | }

	pushq   %rbp
	call	somewhere
	;; expected {40(%rsp) | (%rsp), 24(%rsp), 16(%rsp), 32(%rsp), %r14, 8(%rsp) | }

	pushq   %r14
	call	somewhere
	;; expected {48(%rsp) | 8(%rsp), 32(%rsp), 24(%rsp), 40(%rsp), (%rsp), 16(%rsp) | }

	popq	%r14
	popq	%rbp
	popq	%r15
	popq	%r12
	popq	%rbx
	popq	%r13
	ret

	.size	main, .-main
