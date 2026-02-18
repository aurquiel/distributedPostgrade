## 21 Blackjack Distribuido

Juego cliente-servidor en Python (pygame + sockets) para 1-3 jugadores contra el crupier. El cliente incluye un botón “README” que abre esta documentación desde la interfaz.

### Reglas del juego

-   1. El objetivo es llegar a 21 sin pasarse.
-   2. J, Q, K valen 10; el As vale 1 u 11; el resto vale su número.
-   3. El crupier se planta entre 17 y 21.
-   4. Si empatas recuperas la apuesta; si ganas la duplicas.
-   5. Flujo de apuesta: recargar saldo → apostar → pedir carta o plantarse.
-   6. Solo puedes doblar la apuesta con exactamente dos cartas.
-   7. La partida inicia con 3 jugadores; si hay cupos, se pueden unir nuevos en medio de la partida (activos desde la siguiente ronda).

### Arquitectura y decisiones de diseño

- Autoridad central: el servidor es la fuente de verdad. Valida saldo, aplica apuestas, reparte cartas, asigna turnos y calcula resultados. Los clientes solo muestran estado y envían comandos.
- Concurrencia: cada cliente se maneja en su propio hilo; el servidor ejecuta un hilo principal para aceptar conexiones y uno de lógica por cliente para procesar sus eventos sin bloquear al resto.
- Procesamiento de comandos: los mensajes entrantes se encolan en una cola thread-safe y se consumen en serie con un `lock` que asegura exclusión mutua; esto evita condiciones de carrera al validar saldo, actualizar apuestas y rotar turnos.
- Comunicación TCP con protocolo de texto y encabezado fijo de 10 bytes para la longitud, evitando lecturas truncadas y simplificando el parseo.
- Manejo de cupos: arranque con 3 jugadores; si alguien se desconecta (`\u`), se libera el cupo y otro puede entrar.
- Tolerancia a desconexiones: el servidor limpia sockets al recibir `\u`; el cliente reinicia su estado local ante fallos y puede reintentar conexión.

### Protocolo de mensajes (exhaustivo)

- `\n <jugador>`: Solicitar unirse; el servidor responde con lista completa vía `\n ...` o con `\f` si está lleno.
- `\f`: Partida llena; el cliente muestra “Servidor Full”.
- `\y <jugador>`: Señal de partida activa (inicio o aceptación tardía). El cliente marca la partida como lista.
- `\x <jugador>`: Otorga turno.
- `\z <jugador>`: Fin de turno; el servidor rota o finaliza ronda.
- `\m <jugador> <monto>`: Recarga de saldo.
- `\a <jugador> <monto> <balance>`: Apuesta aplicada; incluye balance actualizado.
- `\c <jugador> <nueva_apuesta> <balance>`: Doble apuesta aplicada.
- `\t`: Saldo insuficiente para apostar/doblar; el cliente muestra aviso.
- `\k <jugador> <c1> <c2>`: Reparto inicial de dos cartas al jugador.
- `\h <jugador> <carta...>`: Mano completa del jugador tras pedir carta.
- `\s <carta...>`: Cartas visibles del crupier.
- `\v <valor>`: Valor actual del crupier.
- `\w <jugador> <balance>`: El jugador gana la ronda; incluye nuevo balance.
- `\g <jugador> <balance>`: Empate.
- `\l <jugador> <balance>`: El jugador pierde.
- `\b`: Limpia mesa y apuestas para siguiente ronda.
- `\u <jugador>`: Jugador desconectado; el servidor lo quita y reasigna turno si es necesario.

### Flujo de comunicación (alto nivel)

1. Conexión: cliente envía `\n`; servidor acepta o responde `\f` si lleno.
2. Inicio de partida: cuando hay 3 jugadores, servidor emite `\y` y `\x` al primero.
3. Apuestas: clientes envían `\a`/`\c`; el servidor valida saldo y difunde el estado.
4. Acciones de turno: `\h` para pedir carta, `\z` para cerrar turno. El servidor rota con `\x`.
5. Cierre de ronda: tras todos los turnos, el crupier juega (`\s`, `\v`), se envían resultados (`\w`, `\g`, `\l`) y limpieza (`\b`).
6. Desconexiones: `\u` libera el cupo; si no hay ronda, el servidor asigna turno al siguiente disponible.

### Requisitos técnicos

- Python 3.9+ recomendado.
- Dependencias: `pygame` (cliente y servidor), `opencv-python` opcional para el video promocional.
- Red: los clientes deben alcanzar la IP/puerto del servidor (por defecto 12345 TCP).
- El juego tiene un resolución de 1200 X 800 px.

### Ejecución

1. (Opcional, recomendado) Crea y activa un entorno virtual:

```bash
python -m venv .venv
.venv\Scripts\activate
```

2. Instala dependencias:

```bash
pip install pygame opencv-python
```

3. Servidor:

```bash
cd Server
python main.py
```

4. Cliente (uno por jugador):

```bash
cd Client
python main.py
```

En el menú del cliente, configura IP/puerto si es necesario, usa “README” para abrir esta guía y pulsa “Iniciar Juego”.
