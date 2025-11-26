# Simulador MIPS Pipeline

Este projeto implementa um simulador visual de um processador MIPS de 32 bits com Pipeline de 5 estágios. Desenvolvido em Python com interface Tkinter.

## Funcionalidades
- Visualização ciclo a ciclo.
- Pipeline completo: IF, ID, EX, MEM, WB.
- Detecção de Hazards (Load-Use via NOP).
- Forwarding (Adiantamento de dados).

## Como Rodar
1. Certifique-se de ter o Python instalado.
2. Execute o arquivo principal:
   ```bash
   python main.py

## Grupo do Projeto
-João Vitor Prissão Oliveira
-José Matheus Cristo

## Casos de Teste

Forwarding (Dependência):

addi $t1, $zero, 10
addi $t2, $zero, 20
add $t3, $t1, $t2
sub $t4, $t3, $t1

Resultado: $t3=30, $t4=20

Load-Use (Stall):

addi $t5, $zero, 50
sw $t5, 0($zero)
lw $s0, 0($zero)
add $s1, $s0, $s0

Resultado: $s0=50, $s1=100

Branch:

addi $t0, $zero, 5
addi $t1, $zero, 5
beq $t0, $t1, 1
addi $s2, $zero, 999
addi $s2, $zero, 777

Resultado: $s2=777