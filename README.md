# 🏋️ GymManager

Aplicación web desarrollada en Python para administrar socios, cuotas y pagos de un gimnasio.

## Funciones

- Registro y búsqueda de socios.
- Plan, precio y fecha de vencimiento.
- Estados de cuota: pagada, pendiente o vencida.
- Renovación y registro de pagos.
- Historial individual por socio.
- Panel con estadísticas.
- Exportación de datos a CSV.
- Persistencia en Google Drive cuando se ejecuta en Colab.
- Persistencia local en la carpeta `data` cuando se ejecuta en una computadora.

## Tecnologías

- Python
- Gradio
- JSON
- Google Colab

## Probar en Google Colab

1. Subir `GymManager_Web_Colab.ipynb` a Google Colab.
2. Elegir **Entorno de ejecución → Ejecutar todas**.
3. Aceptar el acceso a Google Drive.
4. Crear una contraseña cuando el cuaderno la solicite.
5. Abrir el enlace público generado por Gradio.

## Ejecutar localmente

```bash
python -m venv .venv
```

En Windows:

```bash
.venv\Scripts\activate
```

Instalar dependencias:

```bash
pip install -r requirements.txt
```

Ejecutar:

```bash
python app.py
```

Abrir en el navegador:

```text
http://127.0.0.1:7860
```

Para activar usuario y contraseña localmente, se pueden definir las variables de entorno `GYM_USER` y `GYM_PASSWORD`.

## Privacidad

El archivo con socios y pagos no se incluye en GitHub. La configuración de `.gitignore` evita subir archivos JSON, CSV, variables de entorno y contenidos de la carpeta `data`.

No se deben publicar nombres, DNI, teléfonos, pagos ni contraseñas reales.

## Próximas mejoras

- Migración de JSON a PostgreSQL.
- Edición de datos de socios.
- Roles de usuario.
- Reportes mensuales.
- Despliegue permanente.
- Pruebas automáticas.

## Autor

**Joaquín Mancilla**  
Estudiante de programación.
