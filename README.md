# Anonimizador Judicial Chile

Aplicación web de **uso personal** para anonimizar documentos judiciales
chilenos, con **procesamiento íntegramente local**: el documento no sale del
equipo en ningún momento.

> Esta aplicación está **basada en el Anonimizador Judicial de IALAB** —
> Laboratorio de Innovación e Inteligencia Artificial, Facultad de Derecho,
> Universidad de Buenos Aires—, distribuido bajo licencia Apache 2.0. La
> presente es una obra derivada, adaptada al ordenamiento chileno y a un
> registro de español latinoamericano neutro. **No está afiliada a IALAB ni
> cuenta con su patrocinio o aval.** Véase el archivo [NOTICE](NOTICE) para el
> detalle de las modificaciones introducidas.

---

## Qué hace

1. **Carga** un documento en texto plano (`.txt`), Word (`.docx`) o PDF con
   texto seleccionable.
2. **Detecta** las nueve categorías de datos personales que se indican más
   abajo, mediante reglas determinísticas y validación estructural.
3. **Permite revisar**: corregir el tipo, editar la sustitución, descartar
   falsos positivos, agrupar las variantes de un mismo nombre y agregar a mano
   lo que el motor no haya detectado.
4. **Exporta** el documento anonimizado a Word, PDF o texto plano.
5. **Permite revertir** la anonimización mediante un mapa de correspondencias
   cifrado, que se descarga por separado del documento.

## Entidades que detecta

La aplicación detecta **únicamente** estas nueve categorías. La lista es
cerrada de manera deliberada: cada categoría adicional amplía la superficie de
falsos positivos y diluye la atención de quien revisa.

| Categoría | Qué comprende |
|---|---|
| **Personas** | Nombres de personas naturales. |
| **RUT/Cédula de identidad** | RUT y RUN, con verificación del dígito verificador por módulo 11. |
| **Organizaciones** | Empresas (S.A., SpA, Ltda., E.I.R.L.), instituciones y organismos públicos. |
| **Emails** | Direcciones de correo electrónico. |
| **Teléfonos** | Numeración chilena fija y móvil, con o sin prefijo +56. |
| **Domicilios** | Direcciones, con vía, numeración, complemento y comuna. |
| **Patentes** | Placas patente únicas, en sus formatos vigente e histórico. |
| **Otros sensibles** | NUE, pasaporte, número de serie de cédula, cuentas bancarias, IMEI, licencia de conducir, ficha clínica, fecha de nacimiento, dirección IP, entre otros. |
| **Número de causa** | RIT, RUC y ROL, incluidos los prefijos por materia. |

El detalle de cada categoría, con los formatos reconocidos y sus límites, está
en [docs/ENTIDADES.md](docs/ENTIDADES.md).

## Instalación y uso

### Descarga lista para usar (recomendada)

En la sección **[Releases](https://github.com/cristian-soto-g/judicial/releases)**
del repositorio hay un paquete para Windows y otro para macOS. No requieren
instalar Python, ni permisos de administrador, ni instalación alguna:
se descomprimen y se abren con un doble clic. Para desinstalar, se borra la
carpeta.

En Windows, doble clic en `INICIAR.bat`. En macOS, clic derecho sobre
`INICIAR.sh` y elegir Abrir; los detalles están en
[docs/INSTALACION_MAC.md](docs/INSTALACION_MAC.md).

La primera vez el sistema advertirá que el programa no está firmado. Es lo
esperable: firmar un ejecutable exige un certificado comercial de pago. En
Windows, presione «Más información» y luego «Ejecutar de todas formas»; en
macOS, use el clic derecho descrito arriba.

Cada archivo viene con su suma de verificación SHA-256 para comprobar la
descarga.

El paquete no incluye la capa opcional de lenguaje natural, por la licencia
GPL-3.0 del modelo. La detección funciona sin ella.

### Desde el código fuente

Requiere **Python 3.11 o superior**.

**En macOS**: instale Python desde
[python.org](https://www.python.org/downloads/macos/), descargue y descomprima
el proyecto, y haga doble clic en **`INICIAR.command`**. La guía completa está
en [docs/INSTALACION_MAC.md](docs/INSTALACION_MAC.md).

**En Windows**: descargue y descomprima el proyecto, y haga doble clic en
**`INICIAR.bat`**.

**En Linux**: ejecute `./INICIAR.sh` desde una terminal.

Los tres lanzadores hacen lo mismo: comprueban la versión de Python, crean el
entorno virtual la primera vez, instalan las dependencias y abren la aplicación
en el navegador, en <http://127.0.0.1:8799>.

Si prefiere hacerlo a mano:

```bash
git clone --branch claude/anonimizador-personal-local-ziqd1w \
  https://github.com/cristian-soto-g/judicial.git
cd judicial
python3 -m venv .venv
source .venv/bin/activate          # en Windows: .venv\Scripts\activate
pip install -r requirements.txt
python scripts/run_dev.py
```

Para comprobar que el entorno esté completo:

```bash
python scripts/verificar_entorno.py
```

### Capa opcional de lenguaje natural

La detección funciona de manera autónoma con reglas y diccionarios. De forma
opcional puede añadirse una capa de reconocimiento de entidades con spaCy, que
mejora el hallazgo de nombres y organizaciones no previstos por las reglas:

```bash
pip install -r requirements-nlp.txt
python -m spacy download es_core_news_md
```

Advertencia de licencia: el modelo `es_core_news_md` se distribuye bajo GPL-3.0
y no forma parte de este repositorio.

Qué aporta en concreto: reconoce nombres que ninguna regla puede alcanzar,
porque aparecen sin tratamiento, sin rol procesal y sin RUT contiguo, y con
apellidos ausentes del catálogo. La aplicación no le vuelve a exigir el
respaldo del diccionario —hacerlo la dejaría sin utilidad—, salvo en el nivel
de sensibilidad «Precisa», donde se le aplican los mismos requisitos que a las
reglas para que ese ajuste diga la verdad.

Las pruebas de `tests/test_capa_lenguaje.py` verifican su aporte y se omiten
solas cuando la capa no está instalada.

## Privacidad

- El procesamiento ocurre por completo en el equipo, en `127.0.0.1`. La
  aplicación **rechaza las peticiones dirigidas a cualquier otro anfitrión**,
  de modo que no quede expuesta por accidente en una red compartida.
- No hay llamadas a servicios externos ni registro de uso de ninguna especie.
- Las sesiones viven **solo en memoria**. El texto del documento no se escribe
  en disco y se pierde al cerrar la aplicación.
- El mapa de reversión se cifra con AES-256-GCM y una clave derivada por
  scrypt. **La frase de paso no se guarda en ninguna parte**: si se pierde, la
  reversión es imposible.

El razonamiento completo, con los riesgos que subsisten, está en
[docs/PRIVACIDAD.md](docs/PRIVACIDAD.md).

## Control de sesgos

Un anonimizador que reconozca peor unos apellidos que otros protege de manera
desigual, y lo hace en perjuicio de quienes ya están menos representados. El
motor aborda ese riesgo por dos vías:

- Las reglas de contexto —tratamiento de cortesía, rol procesal, RUT contiguo,
  encabezado «APELLIDOS, Nombres»— **no consultan el diccionario**, de modo que
  un apellido ausente del catálogo se detecta igual que uno frecuente.
- El catálogo de apellidos cubre de forma deliberada los distintos orígenes
  presentes en Chile, sin seguir su frecuencia estadística.

Las pruebas de `tests/test_sesgo.py` verifican esa paridad y fallan si algún
grupo queda por debajo. El desarrollo de esta versión encontró por esa vía un
defecto real: nombres de pila chilenos habituales —Pedro, Miguel, Joaquín,
Ramón, Bernardo— estaban clasificados como vocabulario forense por provenir de
nombres de comunas, y las personas así llamadas quedaban sin detectar.

El detalle está en [docs/SESGOS.md](docs/SESGOS.md).

## Límites que conviene tener presentes

- **No incluye reconocimiento óptico de caracteres.** Un PDF escaneado será
  rechazado; si solo algunas páginas lo están, se advierte cuáles quedaron
  fuera del análisis.
- **La detección automática no es completa.** Es una herramienta de asistencia:
  la revisión humana previa a la exportación no es opcional.
- **La reversibilidad exige el modo de etiquetado «Categorizado».** Los modos
  genérico y de iniciales asignan una misma etiqueta a varias personas, de
  suerte que la reversión sería ambigua; la aplicación lo rechaza antes que
  entregar un mapa engañoso.
- **La tabla de equivalencias en CSV no está cifrada.** Contiene los datos
  originales en claro y sirve para el control interno del trabajo: no debe
  compartirse junto con el documento anonimizado.

## Pruebas

```bash
pip install -r requirements-dev.txt
python -m pytest
```

## Desarrollo

```
app/
  detection/    motor de detección chileno, filtros de calidad y validadores
  resolution/   agrupación de las variantes de un mismo dato
  anonymize/    generación de etiquetas y aplicación de sustituciones
  reversal/     mapa de correspondencias cifrado y restitución
  extraction/   lectura de texto plano, Word y PDF
  export/       exportación a Word, PDF, texto y CSV
  api/          rutas HTTP
frontend/       interfaz web, sin dependencias externas
data/           catálogos de nombres, apellidos y vocabulario forense
```

Los catálogos se regeneran con `python scripts/generar_diccionarios.py`.

La construcción y publicación del paquete portable están documentadas en
[docs/EMPAQUETADO.md](docs/EMPAQUETADO.md).

## Licencia

Código de la aplicación: **Apache 2.0** (véase [LICENSE](LICENSE)).

Obra original: **Anonimizador Judicial**, IALAB — Facultad de Derecho,
Universidad de Buenos Aires, Apache 2.0. Las marcas, nombres y logotipos de
IALAB no están cubiertos por esa licencia y no se utilizan aquí como
identificación del producto: se los menciona solo para describir el origen del
trabajo, uso que la propia licencia permite en su Sección 6.
