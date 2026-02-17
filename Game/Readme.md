## 21 Blackjack Distribuido

Juego cliente-servidor en Python (pygame + sockets) para 1-3 jugadores contra el crupier.

### Acerca del proyecto

- Cliente Pygame con interfaz para menú, reglas, video y mesa de juego.
- Servidor gráfico simple (Pygame) que muestra eventos y coordina la partida.
- Comunicación TCP con protocolo propio basado en comandos de texto con encabezado fijo (10 bytes para longitud).
- Soporta inicio con 3 jugadores; permite reingresos si hay cupos durante la partida.

### Arquitectura

- `Server/`: acepta conexiones, mantiene estado de partida, turnos, apuestas y crupier.
- `Client/`: interfaz de cada jugador, manejo de comandos y render de mesa/cartas.
- `domain/`: clases compartidas (Player, Game, Connection, Deck) especializadas por lado cliente/servidor.
- Flujo de red: cada mensaje lleva un encabezado de longitud (10 chars) seguido del comando UTF-8.

### Protocolo de mensajes

- `\n <jugador>`: Solicita unirse; el servidor responde con lista de jugadores vía `\n` o `\f` si está lleno.
- `\f`: Partida llena; el cliente muestra “Servidor Full”.
- `\y [<jugador>]`: Señal de partida activa (inicio o aceptación de nuevo jugador en partida en curso).
- `\x <jugador>`: Turno asignado.
- `\z <jugador>`: Jugador termina su turno; el servidor rota turno o termina la ronda.
- `\m <jugador> <monto>`: Recarga de saldo.
- `\a <jugador> <monto> <balance>`: Apuesta realizada; balance actualizado.
- `\c <jugador> <nueva_apuesta> <balance>`: Doble apuesta.
- `\h <jugador> <carta...>`: Mano completa tras pedir carta.
- `\k <jugador> <carta1> <carta2>`: Reparto inicial de dos cartas al jugador.
- `\s <carta...>`: Cartas del crupier en mesa.
- `\v <valor>`: Valor del crupier.
- `\w <jugador> <balance>`: Jugador gana la ronda.
- `\g <jugador> <balance>`: Jugador empata.
- `\l <jugador> <balance>`: Jugador pierde.
- `\b`: Fin de ronda; limpia manos y apuestas.
- `\u <jugador>`: Jugador desconectado; se elimina y se avanza turno/estado según corresponda.

### Reglas del juego

-   1. El objetivo es llegar a 21 sin pasarse.
-   2. Las figuras J, K, Q valen 10; el As vale 1 u 11. Las demás cartas valen su número.
-   3. El crupier se planta entre 17 y 21.
-   4. Si empatas, recuperas tu apuesta; si ganas, la duplicas.
-   5. Para apostar primero debes recargar tu saldo, luego apostar y finalmente plantarte o pedir carta.
-   6. Puedes doblar tu apuesta solo con dos cartas.

### Requisitos técnicos

- Python 3.9+ recomendado.
- Dependencias: `pygame` (cliente y servidor), `opencv-python` para video promocional.
- Red: los clientes deben poder alcanzar la IP/puerto del servidor (por defecto 12345 TCP).

### Ejecución

1. Instala dependencias:

```bash
pip install pygame opencv-python
```

2. Servidor:

```bash
cd Server
python main.py
```

3. Cliente (uno por jugador):

```bash
cd Client
python main.py
```

En el menú del cliente, configura IP/puerto si es necesario y pulsa “Iniciar Juego”.

### Flujo de partida

- El juego arranca cuando hay 3 jugadores; si se libera un cupo, nuevos jugadores pueden unirse y quedan activos desde la siguiente ronda.
- Cada jugador: recarga (`\m`), apuesta (`\a`), puede doblar con dos cartas (`\c`), pedir carta (`\h`) y finalizar turno (`\z`).
- Al terminar los jugadores, el crupier juega (`\s`, `\v`); se informan resultados (`\w`, `\g`, `\l`) y se limpia (`\b`).
