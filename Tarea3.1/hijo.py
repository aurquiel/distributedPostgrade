import os
import time
import sys

mensaje_desde_el_padre = sys.argv[1] if len(sys.argv) > 1 else "No se recibió ningún mensaje del padre."
sleep_desde_el_padre = int(sys.argv[2]) if len(sys.argv) > 2 else 1

sys.stdout.write(f"Hola, soy el proceso hijo. Mi PID es: {os.getpid()}.\n")
sys.stdout.flush()
sys.stdout.write(f"Mensaje recibido del padre: {mensaje_desde_el_padre}\n")
sys.stdout.flush()
time.sleep(sleep_desde_el_padre) # Simula una tarea que toma sleep_desde_el_padre segundos
sys.stdout.write("El proceso hijo ha terminado su tarea.\n")
sys.stdout.flush()