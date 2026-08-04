import csv
import html
import json
import os
import threading
from collections import Counter
from datetime import date, datetime
from pathlib import Path

import gradio as gr
try:
    from google.colab import drive
    EN_COLAB = True
except ImportError:
    EN_COLAB = False


# =========================================================
# CONFIGURACIÓN
# =========================================================

if EN_COLAB:
    drive.mount("/content/drive")
    CARPETA = Path("/content/drive/MyDrive/GymManager")
    ARCHIVO_EXPORTACION = Path("/content/gymmanager_socios.csv")
else:
    CARPETA = Path(__file__).resolve().parent / "data"
    ARCHIVO_EXPORTACION = CARPETA / "gymmanager_socios.csv"

ARCHIVO_SOCIOS = CARPETA / "socios.json"

# Las credenciales no se guardan en el repositorio.
USUARIO_WEB = os.getenv("GYM_USER", "admin")
CLAVE_WEB = os.getenv("GYM_PASSWORD", "").strip()

if EN_COLAB and not CLAVE_WEB:
    from getpass import getpass
    CLAVE_WEB = getpass("Creá una contraseña para la web: ").strip()

CARPETA.mkdir(parents=True, exist_ok=True)
BLOQUEO = threading.Lock()


# =========================================================
# DATOS
# =========================================================

def fecha_valida(valor):
    try:
        datetime.strptime(str(valor), "%Y-%m-%d")
        return True
    except (ValueError, TypeError):
        return False


def normalizar_socio(socio):
    socio.setdefault("nombre", "")
    socio.setdefault("apellido", "")
    socio.setdefault("dni", "")
    socio.setdefault("telefono", "")
    socio.setdefault("plan", "Musculación")
    socio.setdefault("precio", 0)
    socio.setdefault("fecha_vencimiento", date.today().isoformat())
    socio.setdefault("cuota_pagada", False)
    socio.setdefault("historial_pagos", [])

    try:
        socio["precio"] = float(socio["precio"])
    except (TypeError, ValueError):
        socio["precio"] = 0

    if not fecha_valida(socio["fecha_vencimiento"]):
        socio["fecha_vencimiento"] = date.today().isoformat()

    if not isinstance(socio["historial_pagos"], list):
        socio["historial_pagos"] = []

    return socio


def cargar_socios():
    if not ARCHIVO_SOCIOS.exists():
        ARCHIVO_SOCIOS.write_text("[]", encoding="utf-8")
        return []

    try:
        datos = json.loads(ARCHIVO_SOCIOS.read_text(encoding="utf-8"))

        if not isinstance(datos, list):
            return []

        return [normalizar_socio(socio) for socio in datos]

    except (json.JSONDecodeError, OSError):
        return []


def guardar_socios():
    temporal = ARCHIVO_SOCIOS.with_suffix(".tmp")
    temporal.write_text(
        json.dumps(socios, ensure_ascii=False, indent=4),
        encoding="utf-8",
    )
    temporal.replace(ARCHIVO_SOCIOS)


socios = cargar_socios()
guardar_socios()


# =========================================================
# FUNCIONES GENERALES
# =========================================================

def limpiar(texto):
    return str(texto or "").strip()


def dinero(valor):
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        numero = 0

    return f"${numero:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def buscar_por_dni(dni):
    dni = limpiar(dni)

    for socio in socios:
        if socio["dni"] == dni:
            return socio

    return None


def estado_cuota(socio):
    vencimiento = datetime.strptime(
        socio["fecha_vencimiento"],
        "%Y-%m-%d",
    ).date()

    if vencimiento < date.today():
        return "VENCIDA"

    if socio["cuota_pagada"]:
        return "PAGADA"

    return "PENDIENTE"


def clase_estado(estado):
    return {
        "PAGADA": "estado-pagada",
        "PENDIENTE": "estado-pendiente",
        "VENCIDA": "estado-vencida",
    }.get(estado, "")


def total_ingresos():
    total = 0.0

    for socio in socios:
        for pago in socio["historial_pagos"]:
            try:
                total += float(pago.get("monto", 0))
            except (TypeError, ValueError):
                continue

    return total


def tabla_socios(busqueda=""):
    termino = limpiar(busqueda).lower()

    filtrados = [
        socio
        for socio in socios
        if not termino
        or termino in socio["nombre"].lower()
        or termino in socio["apellido"].lower()
        or termino in socio["dni"].lower()
        or termino in socio["plan"].lower()
    ]

    filtrados.sort(
        key=lambda socio: (
            socio["apellido"].lower(),
            socio["nombre"].lower(),
        )
    )

    if not filtrados:
        return """
        <div class="vacio">
            <h3>No hay socios para mostrar</h3>
            <p>Registrá un socio o probá con otra búsqueda.</p>
        </div>
        """

    filas = []

    for socio in filtrados:
        estado = estado_cuota(socio)

        filas.append(
            f"""
            <tr>
                <td>
                    <strong>{html.escape(socio["apellido"])},
                    {html.escape(socio["nombre"])}</strong>
                    <small>{html.escape(socio["telefono"] or "Sin teléfono")}</small>
                </td>
                <td>{html.escape(socio["dni"])}</td>
                <td>{html.escape(socio["plan"])}</td>
                <td>{dinero(socio["precio"])}</td>
                <td>{html.escape(socio["fecha_vencimiento"])}</td>
                <td>
                    <span class="estado {clase_estado(estado)}">{estado}</span>
                </td>
            </tr>
            """
        )

    return f"""
    <div class="tabla-scroll">
        <table class="tabla-gym">
            <thead>
                <tr>
                    <th>Socio</th>
                    <th>DNI</th>
                    <th>Plan</th>
                    <th>Precio</th>
                    <th>Vencimiento</th>
                    <th>Estado</th>
                </tr>
            </thead>
            <tbody>
                {''.join(filas)}
            </tbody>
        </table>
    </div>
    """


def panel_estadisticas():
    estados = Counter(estado_cuota(socio) for socio in socios)
    planes = Counter(socio["plan"] for socio in socios)

    if planes:
        plan_popular, cantidad_plan = planes.most_common(1)[0]
        dato_plan = f"{html.escape(plan_popular)} ({cantidad_plan})"
    else:
        dato_plan = "Sin datos"

    cantidad_pagos = sum(
        len(socio["historial_pagos"])
        for socio in socios
    )

    return f"""
    <div class="panel-bienvenida">
        <p class="sobrelinea">PANEL DE ADMINISTRACIÓN</p>
        <h1>GymManager</h1>
        <p>Gestioná socios, vencimientos y pagos desde un solo lugar.</p>
    </div>

    <div class="tarjetas">
        <div class="tarjeta">
            <span>Socios</span>
            <strong>{len(socios)}</strong>
        </div>
        <div class="tarjeta">
            <span>Cuotas pagadas</span>
            <strong>{estados["PAGADA"]}</strong>
        </div>
        <div class="tarjeta">
            <span>Cuotas pendientes</span>
            <strong>{estados["PENDIENTE"]}</strong>
        </div>
        <div class="tarjeta">
            <span>Cuotas vencidas</span>
            <strong>{estados["VENCIDA"]}</strong>
        </div>
        <div class="tarjeta tarjeta-ancha">
            <span>Ingresos registrados</span>
            <strong>{dinero(total_ingresos())}</strong>
            <small>{cantidad_pagos} pagos cargados</small>
        </div>
        <div class="tarjeta tarjeta-ancha">
            <span>Plan más elegido</span>
            <strong class="dato-texto">{dato_plan}</strong>
        </div>
    </div>
    """


def mensaje(texto, tipo="ok"):
    icono = "✅" if tipo == "ok" else "⚠️"
    return f"### {icono} {texto}"


# =========================================================
# ACCIONES
# =========================================================

def registrar_socio(nombre, apellido, dni, telefono, plan, precio, vencimiento):
    nombre = limpiar(nombre).title()
    apellido = limpiar(apellido).title()
    dni = limpiar(dni)
    telefono = limpiar(telefono)
    plan = limpiar(plan)
    vencimiento = limpiar(vencimiento)

    if not nombre or not apellido or not dni:
        return (
            mensaje("Nombre, apellido y DNI son obligatorios.", "error"),
            tabla_socios(),
            panel_estadisticas(),
        )

    if not dni.isdigit():
        return (
            mensaje("El DNI debe contener solamente números.", "error"),
            tabla_socios(),
            panel_estadisticas(),
        )

    if buscar_por_dni(dni):
        return (
            mensaje("Ya existe un socio con ese DNI.", "error"),
            tabla_socios(),
            panel_estadisticas(),
        )

    if not fecha_valida(vencimiento):
        return (
            mensaje("Usá una fecha válida con formato AAAA-MM-DD.", "error"),
            tabla_socios(),
            panel_estadisticas(),
        )

    try:
        precio = float(precio)
        if precio <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return (
            mensaje("El precio debe ser mayor que cero.", "error"),
            tabla_socios(),
            panel_estadisticas(),
        )

    nuevo_socio = {
        "nombre": nombre,
        "apellido": apellido,
        "dni": dni,
        "telefono": telefono,
        "plan": plan,
        "precio": precio,
        "fecha_vencimiento": vencimiento,
        "cuota_pagada": False,
        "historial_pagos": [],
    }

    with BLOQUEO:
        socios.append(nuevo_socio)
        guardar_socios()

    return (
        mensaje(f"{nombre} {apellido} fue registrado correctamente."),
        tabla_socios(),
        panel_estadisticas(),
    )


def filtrar_socios(busqueda):
    return tabla_socios(busqueda)


def gestionar_cuota(dni, accion, nueva_fecha, monto):
    socio = buscar_por_dni(dni)

    if socio is None:
        return (
            mensaje("No se encontró un socio con ese DNI.", "error"),
            tabla_socios(),
            panel_estadisticas(),
        )

    accion = limpiar(accion)

    with BLOQUEO:
        if accion == "Marcar pagada":
            socio["cuota_pagada"] = True
            texto = "La cuota fue marcada como pagada."

        elif accion == "Marcar pendiente":
            socio["cuota_pagada"] = False
            texto = "La cuota fue marcada como pendiente."

        elif accion == "Renovar y registrar pago":
            nueva_fecha = limpiar(nueva_fecha)

            if not fecha_valida(nueva_fecha):
                return (
                    mensaje("Ingresá el nuevo vencimiento como AAAA-MM-DD.", "error"),
                    tabla_socios(),
                    panel_estadisticas(),
                )

            try:
                monto_final = float(monto)
                if monto_final <= 0:
                    raise ValueError
            except (TypeError, ValueError):
                monto_final = float(socio["precio"])

            pago = {
                "fecha_pago": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "monto": monto_final,
                "plan": socio["plan"],
                "nuevo_vencimiento": nueva_fecha,
            }

            socio["historial_pagos"].append(pago)
            socio["fecha_vencimiento"] = nueva_fecha
            socio["cuota_pagada"] = True
            texto = f"Renovación guardada por {dinero(monto_final)}."

        else:
            return (
                mensaje("Seleccioná una acción válida.", "error"),
                tabla_socios(),
                panel_estadisticas(),
            )

        guardar_socios()

    return (
        mensaje(texto),
        tabla_socios(),
        panel_estadisticas(),
    )


def ver_historial(dni):
    socio = buscar_por_dni(dni)

    if socio is None:
        return """
        <div class="vacio">
            <h3>Socio no encontrado</h3>
            <p>Revisá el DNI ingresado.</p>
        </div>
        """

    pagos = socio["historial_pagos"]

    if not pagos:
        return f"""
        <div class="vacio">
            <h3>{html.escape(socio["nombre"])} no tiene pagos registrados</h3>
            <p>Usá la sección Cuotas para registrar una renovación.</p>
        </div>
        """

    filas = []
    total = 0.0

    for indice, pago in enumerate(reversed(pagos), start=1):
        try:
            monto_pago = float(pago.get("monto", 0))
        except (TypeError, ValueError):
            monto_pago = 0

        total += monto_pago

        filas.append(
            f"""
            <tr>
                <td>{indice}</td>
                <td>{html.escape(str(pago.get("fecha_pago", "-")))}</td>
                <td>{html.escape(str(pago.get("plan", socio["plan"])))}</td>
                <td>{dinero(monto_pago)}</td>
                <td>{html.escape(str(pago.get("nuevo_vencimiento", "-")))}</td>
            </tr>
            """
        )

    return f"""
    <div class="historial-titulo">
        <h3>{html.escape(socio["apellido"])}, {html.escape(socio["nombre"])}</h3>
        <p>Total histórico: <strong>{dinero(total)}</strong></p>
    </div>

    <div class="tabla-scroll">
        <table class="tabla-gym">
            <thead>
                <tr>
                    <th>#</th>
                    <th>Fecha del pago</th>
                    <th>Plan</th>
                    <th>Monto</th>
                    <th>Nuevo vencimiento</th>
                </tr>
            </thead>
            <tbody>
                {''.join(filas)}
            </tbody>
        </table>
    </div>
    """


def eliminar_socio(dni, confirmar):
    socio = buscar_por_dni(dni)

    if socio is None:
        return (
            mensaje("No se encontró un socio con ese DNI.", "error"),
            tabla_socios(),
            panel_estadisticas(),
        )

    if not confirmar:
        return (
            mensaje("Marcá la confirmación antes de eliminar.", "error"),
            tabla_socios(),
            panel_estadisticas(),
        )

    nombre_completo = f'{socio["nombre"]} {socio["apellido"]}'

    with BLOQUEO:
        socios.remove(socio)
        guardar_socios()

    return (
        mensaje(f"{nombre_completo} fue eliminado."),
        tabla_socios(),
        panel_estadisticas(),
    )


def exportar_csv():
    columnas = [
        "nombre",
        "apellido",
        "dni",
        "telefono",
        "plan",
        "precio",
        "fecha_vencimiento",
        "estado",
        "cantidad_pagos",
        "total_pagado",
    ]

    with ARCHIVO_EXPORTACION.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=columnas)
        escritor.writeheader()

        for socio in socios:
            total = 0.0

            for pago in socio["historial_pagos"]:
                try:
                    total += float(pago.get("monto", 0))
                except (TypeError, ValueError):
                    continue

            escritor.writerow(
                {
                    "nombre": socio["nombre"],
                    "apellido": socio["apellido"],
                    "dni": socio["dni"],
                    "telefono": socio["telefono"],
                    "plan": socio["plan"],
                    "precio": socio["precio"],
                    "fecha_vencimiento": socio["fecha_vencimiento"],
                    "estado": estado_cuota(socio),
                    "cantidad_pagos": len(socio["historial_pagos"]),
                    "total_pagado": total,
                }
            )

    return str(ARCHIVO_EXPORTACION)


# =========================================================
# INTERFAZ WEB
# =========================================================

CSS = """
.gradio-container {
    max-width: 1200px !important;
    margin: auto !important;
}

footer {
    display: none !important;
}

.panel-bienvenida {
    padding: 22px 4px 10px;
}

.panel-bienvenida h1 {
    margin: 0;
    font-size: 48px;
    letter-spacing: -2px;
}

.panel-bienvenida p {
    opacity: .75;
}

.sobrelinea {
    margin-bottom: 4px !important;
    color: #8fd400;
    font-size: 12px;
    font-weight: 800;
    letter-spacing: 2px;
}

.tarjetas {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 14px;
    margin: 18px 0 24px;
}

.tarjeta {
    padding: 19px;
    border: 1px solid rgba(127, 127, 127, .25);
    border-radius: 15px;
    background: rgba(127, 127, 127, .08);
}

.tarjeta span,
.tarjeta small {
    display: block;
    opacity: .7;
}

.tarjeta strong {
    display: block;
    margin-top: 7px;
    font-size: 30px;
}

.tarjeta-ancha {
    grid-column: span 2;
}

.dato-texto {
    font-size: 21px !important;
}

.tabla-scroll {
    overflow-x: auto;
    border: 1px solid rgba(127, 127, 127, .2);
    border-radius: 14px;
}

.tabla-gym {
    width: 100%;
    border-collapse: collapse;
}

.tabla-gym th,
.tabla-gym td {
    padding: 14px 16px;
    border-bottom: 1px solid rgba(127, 127, 127, .15);
    text-align: left;
    white-space: nowrap;
}

.tabla-gym th {
    font-size: 12px;
    letter-spacing: .7px;
    opacity: .65;
    text-transform: uppercase;
}

.tabla-gym td small {
    display: block;
    margin-top: 4px;
    opacity: .6;
}

.estado {
    display: inline-block;
    padding: 5px 9px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 800;
}

.estado-pagada {
    color: #8fd400;
    background: rgba(143, 212, 0, .14);
}

.estado-pendiente {
    color: #e9ae19;
    background: rgba(233, 174, 25, .14);
}

.estado-vencida {
    color: #ef6262;
    background: rgba(239, 98, 98, .14);
}

.vacio {
    padding: 42px 20px;
    text-align: center;
    opacity: .75;
}

.historial-titulo {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 20px;
    margin-bottom: 12px;
}

@media (max-width: 800px) {
    .tarjetas {
        grid-template-columns: repeat(2, 1fr);
    }

    .tarjeta-ancha {
        grid-column: span 2;
    }

    .panel-bienvenida h1 {
        font-size: 38px;
    }
}
"""

with gr.Blocks(
    title="GymManager",
    theme=gr.themes.Soft(
        primary_hue="lime",
        secondary_hue="gray",
        neutral_hue="slate",
    ),
    css=CSS,
) as demo:
    gr.Markdown("# 🏋️ GymManager Web")

    with gr.Tab("Panel"):
        panel = gr.HTML(panel_estadisticas())
        boton_actualizar_panel = gr.Button("Actualizar estadísticas")
        boton_actualizar_panel.click(
            panel_estadisticas,
            outputs=panel,
        )

    with gr.Tab("Registrar socio"):
        with gr.Row():
            nombre = gr.Textbox(label="Nombre")
            apellido = gr.Textbox(label="Apellido")

        with gr.Row():
            dni = gr.Textbox(label="DNI")
            telefono = gr.Textbox(label="Teléfono")

        with gr.Row():
            plan = gr.Dropdown(
                choices=[
                    "Musculación",
                    "Musculación y clases",
                    "Pase libre",
                    "Plan estudiante",
                ],
                value="Musculación",
                label="Plan",
            )
            precio = gr.Number(
                label="Precio mensual",
                minimum=1,
                value=35000,
            )
            vencimiento = gr.Textbox(
                label="Vencimiento",
                placeholder="AAAA-MM-DD",
                value=date.today().isoformat(),
            )

        boton_registrar = gr.Button(
            "Registrar socio",
            variant="primary",
        )
        resultado_registro = gr.Markdown()

    with gr.Tab("Socios"):
        with gr.Row():
            busqueda = gr.Textbox(
                label="Buscar",
                placeholder="Nombre, apellido, DNI o plan",
                scale=4,
            )
            boton_buscar = gr.Button("Buscar", scale=1)
            boton_refrescar = gr.Button("Mostrar todos", scale=1)

        listado = gr.HTML(tabla_socios())

        boton_buscar.click(
            filtrar_socios,
            inputs=busqueda,
            outputs=listado,
        )
        busqueda.submit(
            filtrar_socios,
            inputs=busqueda,
            outputs=listado,
        )
        boton_refrescar.click(
            tabla_socios,
            outputs=listado,
        )

    with gr.Tab("Cuotas"):
        dni_cuota = gr.Textbox(
            label="DNI del socio",
            placeholder="Ingresá el DNI",
        )
        accion_cuota = gr.Dropdown(
            choices=[
                "Marcar pagada",
                "Marcar pendiente",
                "Renovar y registrar pago",
            ],
            value="Renovar y registrar pago",
            label="Acción",
        )

        with gr.Row():
            nueva_fecha = gr.Textbox(
                label="Nuevo vencimiento",
                placeholder="AAAA-MM-DD",
            )
            monto = gr.Number(
                label="Monto pagado",
                minimum=0,
                info="Si queda vacío, se usa el precio del plan.",
            )

        boton_cuota = gr.Button(
            "Guardar cambio",
            variant="primary",
        )
        resultado_cuota = gr.Markdown()

    with gr.Tab("Historial"):
        with gr.Row():
            dni_historial = gr.Textbox(
                label="DNI del socio",
                placeholder="Ingresá el DNI",
                scale=4,
            )
            boton_historial = gr.Button(
                "Ver historial",
                scale=1,
            )

        historial = gr.HTML(
            """
            <div class="vacio">
                <h3>Historial de pagos</h3>
                <p>Ingresá un DNI para consultar sus movimientos.</p>
            </div>
            """
        )

        boton_historial.click(
            ver_historial,
            inputs=dni_historial,
            outputs=historial,
        )
        dni_historial.submit(
            ver_historial,
            inputs=dni_historial,
            outputs=historial,
        )

    with gr.Tab("Eliminar"):
        dni_eliminar = gr.Textbox(
            label="DNI del socio",
            placeholder="Ingresá el DNI",
        )
        confirmar_eliminar = gr.Checkbox(
            label="Confirmo que deseo eliminar al socio y su historial",
        )
        boton_eliminar = gr.Button(
            "Eliminar socio",
            variant="stop",
        )
        resultado_eliminar = gr.Markdown()

    with gr.Tab("Exportar"):
        gr.Markdown(
            """
            Descargá un archivo CSV con los socios, estados,
            vencimientos y totales históricos.
            """
        )
        boton_exportar = gr.Button("Preparar archivo CSV")
        archivo_csv = gr.File(label="Archivo listo")
        boton_exportar.click(
            exportar_csv,
            outputs=archivo_csv,
        )

    boton_registrar.click(
        registrar_socio,
        inputs=[
            nombre,
            apellido,
            dni,
            telefono,
            plan,
            precio,
            vencimiento,
        ],
        outputs=[
            resultado_registro,
            listado,
            panel,
        ],
    )

    boton_cuota.click(
        gestionar_cuota,
        inputs=[
            dni_cuota,
            accion_cuota,
            nueva_fecha,
            monto,
        ],
        outputs=[
            resultado_cuota,
            listado,
            panel,
        ],
    )

    boton_eliminar.click(
        eliminar_socio,
        inputs=[
            dni_eliminar,
            confirmar_eliminar,
        ],
        outputs=[
            resultado_eliminar,
            listado,
            panel,
        ],
    )

    demo.load(
        panel_estadisticas,
        outputs=panel,
    )
    demo.load(
        tabla_socios,
        outputs=listado,
    )


if EN_COLAB:
    print("Usuario:", USUARIO_WEB)
    print("Abrí el enlace público que aparecerá abajo.")
else:
    print("Abrí http://127.0.0.1:7860 en tu navegador.")

autenticacion = (USUARIO_WEB, CLAVE_WEB) if CLAVE_WEB else None

demo.launch(
    share=EN_COLAB,
    debug=EN_COLAB,
    auth=autenticacion,
    show_error=True,
)
