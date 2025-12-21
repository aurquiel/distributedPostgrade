import os
import subprocess

print(f"Hola, soy el proceso padre. Mi PID es: {os.getpid()}")
print("Creando procesos hijos...")

array = []
for i in range(5):
    # Iniciar el proceso hijo con stdout por pipe (el hijo enviará datos al padre)
    nuevo = subprocess.Popen(
        ["python", "hijo.py", f"Mensaje_desde_padre_{i}", str(i * 2)],
        stdout=subprocess.PIPE,  # Redirigir stdout del hijo a una tubería
        stderr=subprocess.PIPE,
        text=True,  # Trabajar con texto en lugar de bytes
        bufsize=1,  # Buffer en línea (line-buffered)
        universal_newlines=True  # Compatibilidad con nuevas líneas
    )
    array.append(nuevo)

for p in array:
    print(f"El proceso hijo se ha creado con el PID: {p.pid}")

# Esperar a cada hijo y leer lo que envió por stdout
for p in array:
    p.wait()  # espera a que el hijo termine
    if p.stdout:
        salida = p.stdout.read()  # leer todo lo enviado por el hijo
        p.stdout.close()
    else:
        salida = ""
    print(f"Salida del hijo PID {p.pid}:\n{salida.strip()}")
    print(f"El proceso hijo con PID {p.pid} ha terminado.")

print("Adiós, soy el proceso padre.")
