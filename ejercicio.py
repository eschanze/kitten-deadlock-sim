while True:
    cantidad = int(input("¿A cuantas personas quieres saludar? "))
    if cantidad > 0:
        break

# Ejecutamos el for la cantidad de veces que nos dijieron en "cantidad"
for i in range(1, cantidad + 1):
    print(f"Saludé a Persona #{i}")