# Visor y Geocodificador Escolar Interactivo

Esta aplicación Streamlit permite visualizar la ubicación de alumnos y un colegio en un mapa interactivo. Ofrece dos modos principales de funcionamiento:

1.  **Visualización Directa:** Si el archivo Excel subido ya contiene columnas de latitud y longitud (nombradas `LATITUD`/`LONGITUD` o `LATITUD_GEO`/`LONGITUD_GEO`), la aplicación las utilizará para mostrar los puntos directamente en el mapa.
2.  **Geocodificación:** Si el archivo Excel no contiene coordenadas pero sí una columna de dirección (calle y número) y una de comuna, la aplicación utilizará la API de Geocodificación de Google para obtener las coordenadas y luego mostrarlas en el mapa.

Adicionalmente, la aplicación marca de forma distintiva la ubicación del "COLEGIO TENIENTE DAGOBERTO GODOY".

## Características Principales

*   Carga de datos desde archivos Excel (`.xlsx`, `.xls`).
*   Detección automática de columnas de coordenadas existentes.
*   Geocodificación de direcciones usando Google Geocoding API (requiere API Key).
*   Visualización de alumnos en un mapa Folium, coloreados por "Desc Grado".
*   Marcador distintivo para la ubicación del colegio.
*   Filtro interactivo para mostrar alumnos por "Desc Grado".
*   Leyenda de colores para los cursos.
*   Tabla de datos filtrados.
*   Opción para descargar los datos procesados (con coordenadas geocodificadas si aplica) en formato Excel.

## Configuración y Ejecución Local

### Prerrequisitos

*   Python 3.8 o superior.
*   `pip` (manejador de paquetes de Python).
*   Una clave de API de Google Geocoding (si se va a usar la funcionalidad de geocodificación).

### Pasos de Instalación

1.  **Clonar el Repositorio (si está en GitHub):**
    ```bash
    git clone https://github.com/TU_USUARIO/TU_REPOSITORIO.git
    cd TU_REPOSITORIO
    ```

2.  **Crear y Activar un Entorno Virtual:**
    Es altamente recomendado usar un entorno virtual.
    ```bash
    python -m venv venv
    # En Windows:
    # venv\Scripts\activate.bat
    # En macOS/Linux:
    source venv/bin/activate
    ```

3.  **Instalar Dependencias:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configurar la API Key de Google (Obligatorio para Geocodificación):**
    *   Crea una carpeta llamada `.streamlit` en la raíz del proyecto si no existe.
    *   Dentro de `.streamlit`, crea un archivo llamado `secrets.toml`.
    *   Añade tu clave de API de Google al archivo `secrets.toml` con el siguiente formato:
        ```toml
        GOOGLE_API_KEY = "TU_API_KEY_DE_GOOGLE_VA_AQUI"
        ```
        **Importante:** El archivo `.streamlit/secrets.toml` está incluido en `.gitignore` y no debe ser subido a repositorios públicos.

### Ejecutar la Aplicación

Con el entorno virtual activado y las dependencias instaladas:
```bash
streamlit run app.py
