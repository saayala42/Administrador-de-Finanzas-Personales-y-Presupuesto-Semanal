import json
import os
import random
from datetime import date, datetime, timedelta

import pandas as pd
import gradio as gr

try:
    from zoneinfo import ZoneInfo
    ZONA = ZoneInfo("America/Bogota")
except Exception:
    ZONA = None

ARCHIVO = "finanzas.json"

CATEGORIAS_GASTO = ["Alimentación", "Transporte", "Ocio", "Vivienda",
                    "Servicios", "Salud", "Educación", "Otros"]
CATEGORIAS_INGRESO = ["Salario", "Mesada", "Trabajo independiente", "Saldo inicial", "Otros ingresos"]
DIAS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]


def hoy():
    # Colab usa hora UTC, por eso se toma la fecha de Colombia
    if ZONA is not None:
        return datetime.now(ZONA).date()
    return date.today()


def convertir_fecha(valor):
    if isinstance(valor, date):
        return valor
    try:
        return datetime.strptime(str(valor).strip(), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        raise ValueError("la fecha debe tener el formato AAAA-MM-DD")


def pesos(valor):
    texto = f"{abs(valor):,.0f}".replace(",", ".")
    return f"-${texto}" if valor < 0 else f"${texto}"


# ==================================================
# 1. ESTRUCTURAS DE DATOS
# ==================================================

class Node:
    def __init__(self, data=None):
        self._data = data
        self._next = None

    def getData(self):
        return self._data

    def getNext(self):
        return self._next

    def setNext(self, n):
        self._next = n


class ListaSimple:
    def __init__(self):
        self._head = None
        self._tail = None
        self._size = 0

    def size(self):
        return self._size

    def isEmpty(self):
        return self._size == 0

    def first(self):
        return self._head

    def addFirst(self, e):
        n = Node(e)
        if self.isEmpty():
            self._head = n
            self._tail = n
        else:
            n.setNext(self._head)
            self._head = n
        self._size += 1

    def addLast(self, e):
        n = Node(e)
        if self.isEmpty():
            self._head = n
            self._tail = n
        else:
            self._tail.setNext(n)
            self._tail = n
        self._size += 1

    def removeFirst(self):
        if self.isEmpty():
            return None
        temp = self._head
        self._head = temp.getNext()
        temp.setNext(None)
        self._size -= 1
        if self.isEmpty():
            self._tail = None
        return temp.getData()

    def __iter__(self):
        temp = self._head
        while temp is not None:
            yield temp.getData()
            temp = temp.getNext()


# Pila (LIFO) para deshacer acciones
class Pila:
    def __init__(self):
        self._lista = ListaSimple()

    def push(self, e):
        self._lista.addFirst(e)

    def pop(self):
        return self._lista.removeFirst()

    def top(self):
        if self.isEmpty():
            return None
        return self._lista.first().getData()

    def isEmpty(self):
        return self._lista.isEmpty()

    def size(self):
        return self._lista.size()


# Cola (FIFO) para los pagos pendientes
class Cola:
    def __init__(self):
        self._lista = ListaSimple()

    def enqueue(self, e):
        self._lista.addLast(e)

    def dequeue(self):
        return self._lista.removeFirst()

    def first(self):
        if self.isEmpty():
            return None
        return self._lista.first().getData()

    def isEmpty(self):
        return self._lista.isEmpty()

    def size(self):
        return self._lista.size()

    def __iter__(self):
        return iter(self._lista)


class DoubleNode:
    def __init__(self, data=None):
        self._data = data
        self._prev = None
        self._next = None

    def getData(self):
        return self._data

    def getNext(self):
        return self._next

    def setNext(self, n):
        self._next = n

    def getPrev(self):
        return self._prev

    def setPrev(self, n):
        self._prev = n


# Lista doble para el historial, ordenada por fecha
class ListaDoble:
    def __init__(self):
        self._head = None
        self._tail = None
        self._size = 0

    def size(self):
        return self._size

    def isEmpty(self):
        return self._size == 0

    def first(self):
        return self._head

    def last(self):
        return self._tail

    def addFirst(self, e):
        n = DoubleNode(e)
        if self.isEmpty():
            self._head = n
            self._tail = n
        else:
            n.setNext(self._head)
            self._head.setPrev(n)
            self._head = n
        self._size += 1

    def addLast(self, e):
        n = DoubleNode(e)
        if self.isEmpty():
            self._head = n
            self._tail = n
        else:
            n.setPrev(self._tail)
            self._tail.setNext(n)
            self._tail = n
        self._size += 1

    def addBefore(self, nodo, e):
        if nodo is self._head:
            self.addFirst(e)
            return
        n = DoubleNode(e)
        anterior = nodo.getPrev()
        n.setPrev(anterior)
        n.setNext(nodo)
        anterior.setNext(n)
        nodo.setPrev(n)
        self._size += 1

    def remove(self, nodo):
        anterior = nodo.getPrev()
        siguiente = nodo.getNext()
        if anterior is None:
            self._head = siguiente
        else:
            anterior.setNext(siguiente)
        if siguiente is None:
            self._tail = anterior
        else:
            siguiente.setPrev(anterior)
        nodo.setPrev(None)
        nodo.setNext(None)
        self._size -= 1
        return nodo.getData()

    # igual que sortList: busca la posición y usa addBefore
    def insertarOrdenado(self, e, clave):
        if self.isEmpty():
            self.addFirst(e)
            return
        temp = self.first()
        while temp is not None and clave(e) >= clave(temp.getData()):
            temp = temp.getNext()
        if temp is None:
            self.addLast(e)
        else:
            self.addBefore(temp, e)

    def buscarNodo(self, condicion):
        temp = self._head
        while temp is not None:
            if condicion(temp.getData()):
                return temp
            temp = temp.getNext()
        return None

    def recorrer(self):
        temp = self._head
        while temp is not None:
            yield temp.getData()
            temp = temp.getNext()

    def recorrerInverso(self):
        temp = self._tail
        while temp is not None:
            yield temp.getData()
            temp = temp.getPrev()


class NodoArbol:
    def __init__(self, dato):
        self.dato = dato
        self.izquierdo = None
        self.derecho = None


# Árbol binario de búsqueda ordenado por monto (para los gastos más grandes)
class ArbolBinarioBusqueda:
    def __init__(self, clave):
        self._raiz = None
        self._clave = clave

    def isEmpty(self):
        return self._raiz is None

    def insertar(self, dato):
        self._raiz = self._insertarNodo(dato, self._raiz)

    def _insertarNodo(self, dato, nodo):
        if nodo is None:
            return NodoArbol(dato)
        if self._clave(dato) < self._clave(nodo.dato):
            nodo.izquierdo = self._insertarNodo(dato, nodo.izquierdo)
        else:
            nodo.derecho = self._insertarNodo(dato, nodo.derecho)
        return nodo

    def inOrden(self):
        resultado = []
        self._inOrden(self._raiz, resultado)
        return resultado

    def _inOrden(self, nodo, resultado):
        if nodo is not None:
            self._inOrden(nodo.izquierdo, resultado)
            resultado.append(nodo.dato)
            self._inOrden(nodo.derecho, resultado)

    # inorden al revés (derecha - raíz - izquierda) hasta tener n datos
    def mayores(self, n):
        resultado = []
        self._mayores(self._raiz, resultado, n)
        return resultado

    def _mayores(self, nodo, resultado, n):
        if nodo is None or len(resultado) >= n:
            return
        self._mayores(nodo.derecho, resultado, n)
        if len(resultado) < n:
            resultado.append(nodo.dato)
        self._mayores(nodo.izquierdo, resultado, n)

    def minimo(self):
        if self._raiz is None:
            return None
        nodo = self._raiz
        while nodo.izquierdo is not None:
            nodo = nodo.izquierdo
        return nodo.dato

    def maximo(self):
        if self._raiz is None:
            return None
        nodo = self._raiz
        while nodo.derecho is not None:
            nodo = nodo.derecho
        return nodo.dato
      
# ==================================================
# 2. CLASES
# ==================================================

class Transaccion:
    TIPO = "Transacción"

    def __init__(self, id_transaccion, categoria, monto, fecha, descripcion=""):
        self._id = id_transaccion
        self.set_categoria(categoria)
        self.set_monto(monto)
        self.set_fecha(fecha)
        self.set_descripcion(descripcion)

    def get_id(self):
        return self._id

    def get_tipo(self):
        return self.TIPO

    def get_categoria(self):
        return self._categoria

    def get_monto(self):
        return self._monto

    def get_fecha(self):
        return self._fecha

    def get_descripcion(self):
        return self._descripcion

    def set_categoria(self, categoria):
        if not categoria:
            raise ValueError("selecciona una categoría")
        self._categoria = categoria

    def set_monto(self, monto):
        if monto is None or float(monto) <= 0:
            raise ValueError("ingresa un monto mayor que cero")
        self._monto = float(monto)

    def set_fecha(self, fecha):
        self._fecha = convertir_fecha(fecha)

    def set_descripcion(self, descripcion):
        self._descripcion = (descripcion or "").strip()

    # cada clase hija define si suma o resta al saldo
    def efecto_en_saldo(self):
        raise NotImplementedError

    def to_dict(self):
        return {
            "id": self._id,
            "tipo": self.TIPO,
            "categoria": self._categoria,
            "monto": self._monto,
            "fecha": self._fecha.isoformat(),
            "descripcion": self._descripcion
        }

    @staticmethod
    def desde_dict(d):
        clase = Ingreso if d["tipo"] == "Ingreso" else Gasto
        return clase(int(d["id"]), d["categoria"], float(d["monto"]),
                     d["fecha"], d.get("descripcion", ""))

    def __str__(self):
        return f"{self.TIPO} de {self._categoria} por {pesos(self._monto)} ({self._fecha})"


class Ingreso(Transaccion):
    TIPO = "Ingreso"

    def efecto_en_saldo(self):
        return self._monto


class Gasto(Transaccion):
    TIPO = "Gasto"

    def efecto_en_saldo(self):
        return -self._monto


class PagoPendiente:
    def __init__(self, descripcion, categoria, monto, fecha_limite):
        if not (descripcion or "").strip():
            raise ValueError("escribe una descripción")
        if monto is None or float(monto) <= 0:
            raise ValueError("ingresa un monto mayor que cero")
        self._descripcion = descripcion.strip()
        self._categoria = categoria
        self._monto = float(monto)
        self._fecha_limite = convertir_fecha(fecha_limite)

    def get_descripcion(self):
        return self._descripcion

    def get_categoria(self):
        return self._categoria

    def get_monto(self):
        return self._monto

    def get_fecha_limite(self):
        return self._fecha_limite

    def esta_vencido(self):
        return self._fecha_limite < hoy()

    def a_gasto(self, id_transaccion):
        return Gasto(id_transaccion, self._categoria, self._monto, hoy(),
                     "Pago: " + self._descripcion)

    def to_dict(self):
        return {
            "descripcion": self._descripcion,
            "categoria": self._categoria,
            "monto": self._monto,
            "fecha_limite": self._fecha_limite.isoformat()
        }

    @staticmethod
    def desde_dict(d):
        return PagoPendiente(d["descripcion"], d["categoria"], d["monto"], d["fecha_limite"])


class Presupuesto:
    def __init__(self):
        self._limites = {}

    def set_limite(self, categoria, monto):
        if monto is None or float(monto) < 0:
            raise ValueError("ingresa un límite válido (0 para quitarlo)")
        if float(monto) == 0:
            self._limites.pop(categoria, None)
        else:
            self._limites[categoria] = float(monto)

    def get_limite(self, categoria):
        return self._limites.get(categoria, 0.0)

    def total(self):
        return sum(self._limites.values())

    def tiene_limites(self):
        return len(self._limites) > 0

    def to_dict(self):
        return dict(self._limites)


class Accion:
    # tipo puede ser "registrar", "eliminar" o "pagar"
    def __init__(self, tipo, transaccion, pago=None):
        self.tipo = tipo
        self.transaccion = transaccion
        self.pago = pago


# ==================================================
# 3. ADMINISTRADOR DE FINANZAS
# ==================================================

class AdministradorFinanzas:

    def __init__(self, archivo=ARCHIVO):
        self._archivo = archivo
        self.historial = ListaDoble()
        self.deshacer_pila = Pila()
        self.pendientes = Cola()
        self.presupuesto = Presupuesto()
        self._siguiente_id = 1
        self.aviso = ""
        self.cargar()

    # ---------- archivos ----------
    def cargar(self):
        try:
            with open(self._archivo, "r", encoding="utf-8") as archivo:
                datos = json.load(archivo)
            if isinstance(datos, list):  # formato de la versión anterior
                datos = {"transacciones": datos}
            for i, d in enumerate(datos.get("transacciones", []), start=1):
                d.setdefault("id", i)
                self._insertar(Transaccion.desde_dict(d))
            for d in datos.get("pendientes", []):
                self.pendientes.enqueue(PagoPendiente.desde_dict(d))
            for categoria, monto in datos.get("presupuesto", {}).items():
                self.presupuesto.set_limite(categoria, monto)
            ids = [t.get_id() for t in self.historial.recorrer()]
            self._siguiente_id = max(ids, default=0) + 1
        except FileNotFoundError:
            pass
        except (json.JSONDecodeError, KeyError, TypeError, ValueError, AttributeError):
            # no se borra el archivo dañado, se guarda una copia
            copia = self._archivo + ".danado"
            os.replace(self._archivo, copia)
            self.historial = ListaDoble()
            self.pendientes = Cola()
            self.presupuesto = Presupuesto()
            self._siguiente_id = 1
            self.aviso = f"El archivo de datos estaba dañado. Se guardó una copia en {copia}."

    def guardar(self):
        datos = {
            "transacciones": [t.to_dict() for t in self.historial.recorrer()],
            "pendientes": [p.to_dict() for p in self.pendientes],
            "presupuesto": self.presupuesto.to_dict()
        }
        try:
            with open(self._archivo + ".tmp", "w", encoding="utf-8") as archivo:
                json.dump(datos, archivo, indent=4, ensure_ascii=False)
            os.replace(self._archivo + ".tmp", self._archivo)
            return True
        except OSError:
            return False

    # ---------- operaciones ----------
    def _nuevo_id(self):
        self._siguiente_id += 1
        return self._siguiente_id - 1

    def _insertar(self, t):
        self.historial.insertarOrdenado(t, lambda x: x.get_fecha())

    def registrar(self, tipo, categoria, monto, fecha, descripcion=""):
        fecha = convertir_fecha(fecha)
        if fecha > hoy():
            raise ValueError("la fecha no puede ser futura")
        if tipo == "Ingreso":
            if categoria not in CATEGORIAS_INGRESO:
                raise ValueError("esa categoría no es de ingreso")
            t = Ingreso(self._nuevo_id(), categoria, monto, fecha, descripcion)
        else:
            if categoria not in CATEGORIAS_GASTO:
                raise ValueError("esa categoría no es de gasto")
            t = Gasto(self._nuevo_id(), categoria, monto, fecha, descripcion)
        self._insertar(t)
        self.deshacer_pila.push(Accion("registrar", t))
        return t

    def eliminar(self, id_transaccion):
        nodo = self.historial.buscarNodo(lambda t: t.get_id() == id_transaccion)
        if nodo is None:
            raise ValueError(f"no hay ningún movimiento con ID {id_transaccion}")
        t = self.historial.remove(nodo)
        self.deshacer_pila.push(Accion("eliminar", t))
        return t

    def agregar_pendiente(self, descripcion, categoria, monto, fecha_limite):
        pago = PagoPendiente(descripcion, categoria, monto, fecha_limite)
        self.pendientes.enqueue(pago)
        return pago

    def pagar_siguiente(self):
        if self.pendientes.isEmpty():
            raise ValueError("no hay pagos pendientes")
        pago = self.pendientes.dequeue()
        gasto = pago.a_gasto(self._nuevo_id())
        self._insertar(gasto)
        self.deshacer_pila.push(Accion("pagar", gasto, pago))
        return pago

    def deshacer(self):
        if self.deshacer_pila.isEmpty():
            raise ValueError("no hay movimientos recientes para deshacer")
        accion = self.deshacer_pila.pop()
        t = accion.transaccion
        if accion.tipo == "eliminar":
            self._insertar(t)
            return "Se restauró el movimiento eliminado."
        nodo = self.historial.buscarNodo(lambda x: x is t)
        if nodo is not None:
            self.historial.remove(nodo)
        if accion.tipo == "pagar":
            self.pendientes.enqueue(accion.pago)
            return "Se deshizo el pago. Volvió a la lista de pendientes."
        return "Se deshizo el último movimiento."

    # ---------- consultas ----------
    def entre(self, desde, hasta):
        # como la lista está ordenada por fecha, se puede parar al pasar 'hasta'
        resultado = []
        for t in self.historial.recorrer():
            if t.get_fecha() > hasta:
                break
            if t.get_fecha() >= desde:
                resultado.append(t)
        return resultado

    def totales(self, lista=None):
        if lista is None:
            lista = list(self.historial.recorrer())
        ingresos = sum(t.get_monto() for t in lista if isinstance(t, Ingreso))
        gastos = sum(t.get_monto() for t in lista if isinstance(t, Gasto))
        saldo = sum(t.efecto_en_saldo() for t in lista)
        return ingresos, gastos, saldo

    def total_pendientes(self):
        return sum(p.get_monto() for p in self.pendientes)

    @staticmethod
    def lunes_de(fecha):
        return fecha - timedelta(days=fecha.weekday())

    # matriz de 7 filas (días) x 8 columnas (categorías de gasto)
    def matriz_semana(self, fecha):
        lunes = self.lunes_de(fecha)
        matriz = [[0.0] * len(CATEGORIAS_GASTO) for _ in range(7)]
        for t in self.entre(lunes, lunes + timedelta(days=6)):
            if isinstance(t, Gasto):
                fila = (t.get_fecha() - lunes).days
                columna = CATEGORIAS_GASTO.index(t.get_categoria())
                matriz[fila][columna] += t.get_monto()
        return matriz

    def estado_presupuesto(self, fecha):
        matriz = self.matriz_semana(fecha)
        estado = []
        for j, categoria in enumerate(CATEGORIAS_GASTO):
            gastado = sum(matriz[i][j] for i in range(7))
            limite = self.presupuesto.get_limite(categoria)
            if gastado > 0 or limite > 0:
                porcentaje = gastado / limite * 100 if limite > 0 else None
                estado.append((categoria, gastado, limite, porcentaje))
        return estado

    def gastos_mas_grandes(self, fecha, n=5):
        lunes = self.lunes_de(fecha)
        arbol = ArbolBinarioBusqueda(lambda g: g.get_monto())
        for t in self.entre(lunes, lunes + timedelta(days=6)):
            if isinstance(t, Gasto):
                arbol.insertar(t)
        return arbol.mayores(n)

    def resumen_meses(self, fecha, cantidad=6):
        if self.historial.isEmpty():
            return []
        primer_mes = self.historial.first().getData().get_fecha().replace(day=1)
        mes = fecha.replace(day=1)
        meses = []
        while len(meses) < cantidad and mes >= primer_mes:
            meses.insert(0, mes)
            mes = (mes - timedelta(days=1)).replace(day=1)
        resultado = []
        for inicio in meses:
            fin = (inicio + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            ingresos, gastos, _ = self.totales(self.entre(inicio, fin))
            resultado.append((inicio, ingresos, gastos))
        return resultado

    def saldo_por_dia(self):
        fechas, saldos = [], []
        saldo = 0
        for t in self.historial.recorrer():
            saldo += t.efecto_en_saldo()
            if fechas and fechas[-1] == t.get_fecha():
                saldos[-1] = saldo
            else:
                fechas.append(t.get_fecha())
                saldos.append(saldo)
        return fechas, saldos

    # ---------- avisos para el usuario ----------
    def avisos(self, fecha):
        lista = []
        lunes = self.lunes_de(fecha)
        domingo = lunes + timedelta(days=6)
        semana_actual = lunes <= hoy() <= domingo
        dias_pasados = (hoy() - lunes).days + 1 if semana_actual else 7
        dias_quedan = 7 - dias_pasados + 1

        for categoria, gastado, limite, porcentaje in self.estado_presupuesto(fecha):
            if limite == 0:
                continue
            if gastado > limite:
                lista.append(f"**{categoria}:** te pasaste del presupuesto por {pesos(gastado - limite)}.")
            elif porcentaje >= 80:
                lista.append(f"**{categoria}:** ya usaste el {porcentaje:.0f}% del presupuesto, "
                             f"te quedan {pesos(limite - gastado)}.")
            elif semana_actual and gastado > 0:
                proyeccion = gastado / dias_pasados * 7
                if proyeccion > limite:
                    por_dia = (limite - gastado) / dias_quedan
                    lista.append(f"**{categoria}:** a este ritmo terminarías la semana en {pesos(proyeccion)}. "
                                 f"Para no pasarte puedes gastar {pesos(por_dia)} por día.")

        _, _, saldo = self.totales()
        pendiente = self.total_pendientes()
        vencidos = [p for p in self.pendientes if p.esta_vencido()]
        if vencidos:
            lista.append(f"Tienes {len(vencidos)} pago(s) vencido(s).")
        if pendiente > saldo:
            lista.append(f"Los pagos pendientes ({pesos(pendiente)}) son más que tu saldo ({pesos(saldo)}).")
        elif pendiente > 0:
            lista.append(f"Después de pagar los pendientes te quedarían {pesos(saldo - pendiente)}.")

        inicio_mes = fecha.replace(day=1)
        fin_mes = (inicio_mes + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        ingresos_mes, gastos_mes, _ = self.totales(self.entre(inicio_mes, fin_mes))
        if ingresos_mes > 0:
            ahorro = (ingresos_mes - gastos_mes) / ingresos_mes * 100
            if ahorro < 0:
                lista.append("Este mes llevas más gastos que ingresos.")
            else:
                lista.append(f"Este mes has ahorrado el {ahorro:.0f}% de tus ingresos.")

        if not self.presupuesto.tiene_limites():
            lista.append("Todavía no has definido un presupuesto semanal.")
        if self.historial.isEmpty():
            lista = ["No hay movimientos registrados."]
        return lista

    # datos de prueba para mostrar la aplicación
    def cargar_ejemplo(self):
        if not self.historial.isEmpty():
            raise ValueError("solo se pueden cargar datos de ejemplo si el historial está vacío")
        r = random.Random(13)
        dia = self.lunes_de(hoy()) - timedelta(weeks=7)
        self._insertar(Ingreso(self._nuevo_id(), "Saldo inicial", 900000, dia, "Ahorros"))
        while dia <= hoy():
            if dia.day in (1, 15):
                self._insertar(Ingreso(self._nuevo_id(), "Salario", 1300000, dia, "Quincena"))
            if dia.day == 5:
                self._insertar(Gasto(self._nuevo_id(), "Vivienda", 650000, dia, "Arriendo"))
            if dia.day == 10:
                self._insertar(Gasto(self._nuevo_id(), "Servicios", 185000, dia, "Servicios públicos"))
            if dia.weekday() < 5:
                self._insertar(Gasto(self._nuevo_id(), "Transporte", 6400, dia, "Bus"))
            if r.random() < 0.8:
                self._insertar(Gasto(self._nuevo_id(), "Alimentación", r.randrange(12000, 48000, 500), dia, "Comida"))
            if dia.weekday() >= 4 and r.random() < 0.5:
                self._insertar(Gasto(self._nuevo_id(), "Ocio", r.randrange(20000, 75000, 1000), dia, "Salida"))
            if r.random() < 0.06:
                self._insertar(Gasto(self._nuevo_id(), "Salud", r.randrange(20000, 80000, 1000), dia, "Droguería"))
            dia += timedelta(days=1)
        for categoria, limite in [("Alimentación", 180000), ("Transporte", 35000),
                                  ("Ocio", 90000), ("Salud", 40000)]:
            self.presupuesto.set_limite(categoria, limite)
        self.pendientes.enqueue(PagoPendiente("Curso de inglés", "Educación", 420000, hoy() + timedelta(days=5)))
        self.pendientes.enqueue(PagoPendiente("Plan de celular", "Servicios", 55000, hoy() + timedelta(days=9)))
        self.deshacer_pila = Pila()


# ==================================================
# 4. FUNCIONES DE LA INTERFAZ
# ==================================================

admin = AdministradorFinanzas()


def ejecutar(funcion, *args):
    try:
        mensaje = funcion(*args)
        if not admin.guardar():
            mensaje += " (no se pudo guardar el archivo)"
        return mensaje
    except ValueError as error:
        return f"Error: {error}."


def registrar(tipo, categoria, monto, fecha, descripcion):
    admin.registrar(tipo, categoria, monto, fecha, descripcion)
    return "Transacción registrada correctamente."


def eliminar(id_transaccion):
    if id_transaccion is None:
        raise ValueError("escribe el ID del movimiento")
    admin.eliminar(int(id_transaccion))
    return "Movimiento eliminado."


def agregar_pendiente(descripcion, categoria, monto, fecha_limite):
    admin.agregar_pendiente(descripcion, categoria, monto, fecha_limite)
    return "Pago agregado a la lista de pendientes."


def pagar():
    pago = admin.pagar_siguiente()
    return f"Se pagó: {pago.get_descripcion()} ({pesos(pago.get_monto())})."


def guardar_limite(categoria, limite):
    admin.presupuesto.set_limite(categoria, limite)
    return "Presupuesto actualizado."


def cargar_ejemplo():
    admin.cargar_ejemplo()
    return "Datos de ejemplo cargados."


def cambiar_categorias(tipo):
    opciones = CATEGORIAS_INGRESO if tipo == "Ingreso" else CATEGORIAS_GASTO
    return gr.Dropdown(choices=opciones, value=opciones[0])


def tabla_historial():
    filas = []
    for t in admin.historial.recorrerInverso():
        filas.append([t.get_id(), t.get_fecha().isoformat(), t.get_tipo(),
                      t.get_categoria(), t.get_descripcion(), pesos(t.get_monto())])
    return pd.DataFrame(filas, columns=["ID", "Fecha", "Tipo", "Categoría", "Descripción", "Monto"])


def tabla_pendientes():
    filas = []
    for p in admin.pendientes:
        estado = "Vencido" if p.esta_vencido() else "Pendiente"
        filas.append([p.get_fecha_limite().isoformat(), p.get_descripcion(),
                      p.get_categoria(), pesos(p.get_monto()), estado])
    return pd.DataFrame(filas, columns=["Fecha límite", "Descripción", "Categoría", "Monto", "Estado"])


def tabla_presupuesto(fecha):
    filas = []
    for categoria, gastado, limite, porcentaje in admin.estado_presupuesto(fecha):
        if limite > 0:
            filas.append([categoria, pesos(limite), pesos(gastado),
                          pesos(limite - gastado), f"{porcentaje:.0f}%"])
    return pd.DataFrame(filas, columns=["Categoría", "Límite", "Gastado", "Disponible", "Usado"])


def tabla_mayores(fecha):
    filas = []
    for g in admin.gastos_mas_grandes(fecha):
        filas.append([g.get_fecha().isoformat(), g.get_categoria(),
                      g.get_descripcion(), pesos(g.get_monto())])
    return pd.DataFrame(filas, columns=["Fecha", "Categoría", "Descripción", "Monto"])


# ----- datos para las gráficas -----
def datos_presupuesto(fecha):
    filas = []
    for categoria, gastado, limite, porcentaje in admin.estado_presupuesto(fecha):
        if limite == 0:
            filas.append([categoria, "Sin límite", gastado])
        elif gastado <= limite:
            filas.append([categoria, "Gastado", gastado])
            filas.append([categoria, "Por gastar", limite - gastado])
        else:
            filas.append([categoria, "Gastado", limite])
            filas.append([categoria, "Sobrepasado", gastado - limite])
    return pd.DataFrame(filas, columns=["Categoría", "Estado", "Monto"])


def datos_dias(fecha):
    matriz = admin.matriz_semana(fecha)
    filas = []
    for i in range(7):
        for j in range(len(CATEGORIAS_GASTO)):
            if matriz[i][j] > 0:
                filas.append([DIAS[i], CATEGORIAS_GASTO[j], matriz[i][j]])
    return pd.DataFrame(filas, columns=["Día", "Categoría", "Monto"])


def datos_saldo():
    fechas, saldos = admin.saldo_por_dia()
    return pd.DataFrame({"Fecha": pd.to_datetime(fechas), "Saldo": saldos})


def datos_meses(fecha):
    filas = []
    for inicio, ingresos, gastos in admin.resumen_meses(fecha):
        nombre = f"{inicio.year}-{inicio.month:02d} {MESES[inicio.month - 1]}"
        neto = ingresos - gastos
        filas.append([nombre, neto, "Ahorro" if neto >= 0 else "Déficit"])
    return pd.DataFrame(filas, columns=["Mes", "Ahorro", "Resultado"])


def actualizar(fecha_texto):
    try:
        fecha = convertir_fecha(fecha_texto)
    except ValueError:
        fecha = hoy()
    lunes = admin.lunes_de(fecha)
    domingo = lunes + timedelta(days=6)

    _, _, saldo = admin.totales()
    _, gastos_semana, _ = admin.totales(admin.entre(lunes, domingo))
    if admin.presupuesto.tiene_limites():
        usado = sum(g for _, g, l, _ in admin.estado_presupuesto(fecha) if l > 0)
        restante = pesos(admin.presupuesto.total() - usado)
    else:
        restante = "No definido"

    texto = f"**Semana del {lunes:%d/%m/%Y} al {domingo:%d/%m/%Y}**\n\n"
    if admin.aviso:
        texto += admin.aviso + "\n\n"
    texto += "\n".join("- " + a for a in admin.avisos(fecha))

    return (pesos(saldo), pesos(gastos_semana), restante, pesos(admin.total_pendientes()),
            texto, datos_presupuesto(fecha), datos_dias(fecha), datos_saldo(), datos_meses(fecha),
            tabla_mayores(fecha), tabla_historial(), tabla_pendientes(), tabla_presupuesto(fecha))


# ==================================================
# 5. INTERFAZ GRÁFICA
# ==================================================

with gr.Blocks(title="Administrador de Finanzas") as aplicacion:

    gr.Markdown(
        """
        # Administrador de Finanzas Personales
        ### Controla tus ingresos, gastos y presupuesto semanal.
        """
    )

    with gr.Row():
        caja_saldo = gr.Textbox(label="Saldo disponible", interactive=False)
        caja_gasto = gr.Textbox(label="Gastos de la semana", interactive=False)
        caja_restante = gr.Textbox(label="Presupuesto restante", interactive=False)
        caja_pendientes = gr.Textbox(label="Pagos pendientes", interactive=False)

    with gr.Tabs():

        with gr.Tab("Resumen"):
            with gr.Row():
                fecha_resumen = gr.Textbox(label="Semana a consultar (AAAA-MM-DD)", value=str(hoy()))
                boton_actualizar = gr.Button("Actualizar")
            texto_avisos = gr.Markdown()
            with gr.Row():
                grafica_presupuesto = gr.BarPlot(
                    x="Categoría", y="Monto", color="Estado",
                    color_map={"Gastado": "#2a78d6", "Por gastar": "#d9d8d2",
                               "Sobrepasado": "#d03b3b", "Sin límite": "#8a8984"},
                    sort=CATEGORIAS_GASTO, title="Presupuesto de la semana",
                    x_title="", y_title="Pesos", x_label_angle=-30, height=350)
                grafica_dias = gr.BarPlot(
                    x="Día", y="Monto", color="Categoría", sort=DIAS,
                    title="Gastos por día", x_title="", y_title="Pesos", height=350)
            with gr.Row():
                grafica_saldo = gr.LinePlot(
                    x="Fecha", y="Saldo", title="Saldo en el tiempo",
                    x_title="", y_title="Pesos", height=300)
                grafica_meses = gr.BarPlot(
                    x="Mes", y="Ahorro", color="Resultado",
                    color_map={"Ahorro": "#0ca30c", "Déficit": "#d03b3b"},
                    sort="x", title="Ahorro por mes", x_title="", y_title="Pesos", height=300)
            gr.Markdown("### Gastos más grandes de la semana")
            tabla_top = gr.Dataframe(interactive=False)

        with gr.Tab("Registrar movimiento"):
            with gr.Row():
                tipo = gr.Radio(["Gasto", "Ingreso"], value="Gasto", label="Tipo de movimiento")
                categoria = gr.Dropdown(CATEGORIAS_GASTO, value="Alimentación", label="Categoría")
            with gr.Row():
                monto = gr.Number(label="Monto", minimum=0, precision=0)
                fecha = gr.Textbox(label="Fecha (AAAA-MM-DD)", value=str(hoy()))
                descripcion = gr.Textbox(label="Descripción")
            with gr.Row():
                boton_registrar = gr.Button("Registrar transacción", variant="primary")
                boton_deshacer = gr.Button("Deshacer último movimiento")
            mensaje_registro = gr.Textbox(label="Estado del movimiento", interactive=False)

        with gr.Tab("Historial"):
            tabla_movimientos = gr.Dataframe(interactive=False)
            with gr.Row():
                id_eliminar = gr.Number(label="ID a eliminar", precision=0)
                boton_eliminar = gr.Button("Eliminar")
                boton_deshacer2 = gr.Button("Deshacer")
            mensaje_historial = gr.Textbox(label="Estado", interactive=False)

        with gr.Tab("Pagos pendientes"):
            with gr.Row():
                pendiente_desc = gr.Textbox(label="Descripción")
                pendiente_cat = gr.Dropdown(CATEGORIAS_GASTO, value="Vivienda", label="Categoría")
                pendiente_monto = gr.Number(label="Monto", minimum=0, precision=0)
                pendiente_fecha = gr.Textbox(label="Fecha límite (AAAA-MM-DD)",
                                             value=str(hoy() + timedelta(days=7)))
            with gr.Row():
                boton_agregar = gr.Button("Agregar pago", variant="primary")
                boton_pagar = gr.Button("Pagar el siguiente")
            mensaje_pendientes = gr.Textbox(label="Estado", interactive=False)
            tabla_pend = gr.Dataframe(interactive=False)

        with gr.Tab("Presupuesto"):
            with gr.Row():
                presupuesto_cat = gr.Dropdown(CATEGORIAS_GASTO, value="Alimentación", label="Categoría")
                presupuesto_limite = gr.Number(label="Límite semanal", minimum=0, precision=0)
                boton_limite = gr.Button("Guardar", variant="primary")
            mensaje_presupuesto = gr.Textbox(label="Estado", interactive=False)
            tabla_pres = gr.Dataframe(interactive=False)
            boton_ejemplo = gr.Button("Cargar datos de ejemplo")

    salidas = [caja_saldo, caja_gasto, caja_restante, caja_pendientes, texto_avisos,
               grafica_presupuesto, grafica_dias, grafica_saldo, grafica_meses,
               tabla_top, tabla_movimientos, tabla_pend, tabla_pres]

    # cada botón ejecuta su función y después actualiza el resumen y las tablas
    def conectar(boton, funcion, entradas, mensaje):
        boton.click(lambda *args: ejecutar(funcion, *args), inputs=entradas, outputs=mensaje).then(
            actualizar, inputs=fecha_resumen, outputs=salidas)

    conectar(boton_registrar, registrar, [tipo, categoria, monto, fecha, descripcion], mensaje_registro)
    conectar(boton_deshacer, admin.deshacer, [], mensaje_registro)
    conectar(boton_deshacer2, admin.deshacer, [], mensaje_historial)
    conectar(boton_eliminar, eliminar, [id_eliminar], mensaje_historial)
    conectar(boton_agregar, agregar_pendiente,
             [pendiente_desc, pendiente_cat, pendiente_monto, pendiente_fecha], mensaje_pendientes)
    conectar(boton_pagar, pagar, [], mensaje_pendientes)
    conectar(boton_limite, guardar_limite, [presupuesto_cat, presupuesto_limite], mensaje_presupuesto)
    conectar(boton_ejemplo, cargar_ejemplo, [], mensaje_presupuesto)

    tipo.change(cambiar_categorias, inputs=tipo, outputs=categoria)
    boton_actualizar.click(actualizar, inputs=fecha_resumen, outputs=salidas)
    aplicacion.load(actualizar, inputs=fecha_resumen, outputs=salidas)


# ==================================================
# 6. EJECUTAR APLICACION
# ==================================================

aplicacion.launch(share=True, debug=True)
