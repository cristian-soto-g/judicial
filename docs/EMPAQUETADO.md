# Construcción y publicación del paquete portable

El paquete portable permite usar la aplicación sin instalar Python ni
dependencia alguna: se descarga, se descomprime y se abre con un doble clic.

## Cómo obtener el paquete ya construido

En la sección **Releases** del repositorio, cada versión publicada trae el
archivo comprimido para Windows y para macOS, junto con su suma de
verificación.

## Cómo publicar una versión nueva

Cree y empuje una etiqueta que comience con `v`:

```bash
git tag v1.0.1
git push origin v1.0.1
```

Eso pone en marcha el flujo `.github/workflows/paquete.yml`, que en los equipos
de GitHub ejecuta las pruebas, construye el paquete para Windows y para macOS,
lo verifica, calcula su suma SHA-256 y reúne todo en una versión.

**La versión se crea en borrador.** Solo la ve quien administra el
repositorio. Revísela, descargue los paquetes si quiere comprobarlos, y
publíquela con un clic desde la sección Releases cuando esté conforme.
Mientras siga en borrador puede eliminarse sin que haya quedado rastro
público. La decisión es deliberada: publicar una versión es un acto que queda
expuesto de forma permanente, y conviene que lo tome una persona.

Para probar el proceso sin publicar nada, entre a la pestaña **Actions**, elija
el flujo «Paquete portable» y presione **Run workflow**. El resultado queda
como artefacto descargable durante catorce días, sin crear una versión pública.

La compilación tiene que ocurrir en los equipos de GitHub porque un ejecutable
de Windows solo puede construirse en Windows, y uno de macOS solo en macOS: las
herramientas de empaquetado no compilan de un sistema operativo a otro.

## Cómo construirlo en su propio equipo

```bash
pip install -r requirements-build.txt
python scripts/construir_paquete.py
python scripts/probar_paquete.py
```

El resultado queda en `dist/`. El paquete construido corresponde al sistema
operativo desde el que se ejecuta.

## Decisiones de empaquetado

**Distribución en carpeta, no en archivo único.** PyInstaller admite generar un
solo ejecutable, pero ese formato se descomprime entero en la carpeta temporal
del sistema cada vez que se abre, dejando allí una copia completa del programa.
Para una herramienta que trata información sensible, la distribución en carpeta
es preferible: no escribe nada fuera de donde el usuario la puso.

**Con ventana de consola.** La ventana muestra el estado de la aplicación y es
el modo de cerrarla. Sin ella, el usuario no tendría señal alguna durante los
segundos que tarda en levantar, ni forma evidente de detenerla.

**Sin el modelo de lenguaje.** La capa opcional de reconocimiento de entidades
usa un modelo que se distribuye bajo licencia GPL-3.0. Incorporarlo al paquete
sometería toda la distribución a esa licencia, de modo que queda fuera. La
detección determinística funciona sin él, y quien lo quiera puede añadirlo
ejecutando la aplicación desde el código fuente.

También se excluye una tipografía de demostración que reportlab trae entre sus
datos, igualmente bajo GPL y que la aplicación nunca utiliza. Así la
distribución queda compuesta solo por componentes de licencia permisiva.

**Bibliotecas excluidas por tamaño.** `pdfplumber` declara `numpy` y
`pypdfium2` para su modo de inspección visual, que dibuja las páginas como
imágenes. La aplicación solo extrae texto y nunca lo usa; excluirlas reduce el
paquete de 186 a 106 MB. `Pillow`, en cambio, no puede excluirse: `reportlab`
lo importa al cargarse, de modo que sin él no habría exportación a PDF.

Esa distinción no se dedujo leyendo las dependencias declaradas, sino
ejecutando la prueba de humo contra el paquete construido. Es la razón de que
esa prueba exista.

## La prueba de humo

`scripts/probar_paquete.py` levanta el ejecutable tal como lo hará el usuario y
recorre contra él el flujo completo: carga de los tres formatos admitidos,
análisis, exportación, generación del mapa cifrado y reversión. Verifica además
que el documento exportado no conserve ninguno de los datos que debía
anonimizar.

Distingue un paquete que arranca de uno que sirve. Durante el desarrollo
detectó dos fallas que la aplicación no presenta al ejecutarse desde el código
fuente:

1. **La lectura de documentos Word fallaba.** `python-docx` localiza sus
   plantillas XML con una ruta que sube un nivel desde su propio módulo:
   `docx/parts/../templates/default-header.xml`. El sistema operativo exige que
   todos los tramos de esa ruta existan, y en una distribución de PyInstaller
   `docx/parts/` no llega a materializarse, porque los módulos viven
   comprimidos dentro del programa. La solución es el marcador de
   `scripts/empaquetado/`, que fuerza la creación de ese directorio.

2. **Faltaban archivos de datos.** `python-docx`, `reportlab` y `pdfminer` leen
   del disco plantillas, tipografías y tablas de codificación que no son
   módulos, de modo que el análisis de importaciones no los alcanza.

Ambas fallas comparten un rasgo: el paquete arrancaba sin errores y fallaba
recién al procesar el primer archivo del usuario.
