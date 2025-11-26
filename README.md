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