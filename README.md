# Administrador de finanzas personales y presupuesto semanal
Aplicación desarrollada en Python que permite administrar ingresos, gastos y presupuestos semanales mediante una interfaz gráfica.  El proyecto busca ayudar a las personas a llevar un mejor control de sus finanzas personales, identificar gastos innecesarios, organizar pagos pendientes y consultar su comportamiento financiero.

# Funcionalidades principales
Registro de movimientos: permite registrar ingresos y gastos con categoría, monto, fecha y descripción.

Historial: consulta los movimientos registrados y permite eliminar transacciones mediante su ID.

Deshacer acciones: permite revertir registros, eliminaciones y pagos.

Pagos pendientes: administra cuentas por pagar y permite procesarlas en orden.

Presupuesto semanal: establece límites de gasto por categoría.

Resumen financiero: muestra saldo disponible, gastos semanales, presupuesto restante y pagos pendientes.

Avisos: identifica presupuestos excedidos y advierte cuando el ritmo de gasto puede superar el límite.

Gráficas: visualiza gastos por categoría, comportamiento diario, evolución del saldo y ahorro mensual.

Persistencia de datos: guarda y recupera la información mediante un archivo JSON.

# Estructuras de datos implementadas
- Lista simplemente enlazada
- Lista doblemente enlazada
- Pila (LIFO)
- Cola (FIFO)
- Árbol binario de búsqueda
- Matriz

# Guia de uso
1. Registrar movimiento:
   
Seleccionar si se desea registrar un ingreso o un gasto.
Elegir la categoría correspondiente.
Introducir el monto.
Seleccionar la fecha.
Agregar una descripción opcional.
Presionar Registrar transacción.

2. Historial

Permite consultar los movimientos registrados. Cada transacción tiene un identificador que puede utilizarse para eliminarla.

3. Deshacer

Permite revertir la última operación compatible realizada, como registrar, eliminar o pagar una cuenta.

4. Pagos pendientes

Permite agregar cuentas por pagar y procesarlas utilizando el botón Pagar el siguiente. Los pagos se atienden en el orden en que fueron agregados.

5. Presupuesto

Permite establecer límites semanales para las diferentes categorías de gastos. También incluye una opción para cargar datos de ejemplo y probar la aplicación.

# Objetivo académico
Demostrar la aplicación práctica de los conceptos de estructuras de datos mediante el desarrollo de una herramienta funcional para administrar finanzas personales y presupuestos semanales.

El proyecto integra estructuras lineales y no lineales, manejo de archivos, validaciones, procesamiento de información e interfaz gráfica.

# Desarrollado por Samuel Ayala Cardona y David Chavarriaga Escudero.

Proyecto académico de Estructuras de Datos – Institución Universitaria ITM
