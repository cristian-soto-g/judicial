# Instalación en macOS

**Conviene decirlo de entrada: todavía no existe una descarga empaquetada.** No
hay un archivo `.app` ni un instalador `.dmg`. Lo que se descarga es el código
fuente, y un archivo de arranque se encarga del resto con un doble clic.

La preparación toma unos minutos la primera vez. Después, abrir la aplicación
es inmediato.

Funciona igual en Mac con procesador Apple Silicon (M1 a M4) y en los Mac Intel.

---

## Paso 1. Instalar Python

macOS incluye una versión de Python demasiado antigua para esta aplicación, de
modo que hay que instalar una actual. Se necesita **Python 3.11 o superior**.

Para saber si ya tiene una, abra la aplicación **Terminal** (búsquela con
Spotlight, tecla ⌘ + barra espaciadora) y escriba:

```
python3 --version
```

Si responde 3.11 o un número mayor, ya está listo y puede saltar al paso 2. Si
responde 3.9 o 3.10, o si no responde nada, instale Python por cualquiera de
estas dos vías:

**Opción A — instalador oficial (la más simple).** Entre a
<https://www.python.org/downloads/macos/>, descargue la última versión estable
y ejecute el instalador como cualquier otro programa.

**Opción B — Homebrew**, si ya lo usa:

```
brew install python@3.12
```

---

## Paso 2. Descargar la aplicación

Abra este enlace, que descargará un archivo comprimido:

<https://github.com/cristian-soto-g/judicial/archive/refs/heads/claude/anonimizador-personal-local-ziqd1w.zip>

Descomprímalo con doble clic. Quedará una carpeta llamada
`judicial-claude-anonimizador-personal-local-ziqd1w`. Muévala donde le resulte
cómodo: la carpeta Documentos o el escritorio, por ejemplo. La aplicación
funciona desde donde esté.

Si prefiere la terminal:

```
git clone --branch claude/anonimizador-personal-local-ziqd1w \
  https://github.com/cristian-soto-g/judicial.git
```

---

## Paso 3. Abrir la aplicación

Dentro de la carpeta encontrará el archivo **`INICIAR.command`**. Haga doble
clic sobre él.

Se abrirá una ventana de Terminal que mostrará el avance. La primera vez dirá
«Primera ejecución: preparando el entorno» y tardará algunos minutos, porque
está descargando las bibliotecas que la aplicación necesita. Cuando termine, su
navegador se abrirá solo en la aplicación.

**Si macOS bloquea el archivo.** Es lo habitual con cualquier archivo
descargado de internet. Aparecerá un aviso que dice que proviene de un
desarrollador no identificado. Para autorizarlo una sola vez:

1. Haga **clic derecho** sobre `INICIAR.command` (o Control + clic).
2. Elija **Abrir** en el menú.
3. En el aviso que aparece, confirme con **Abrir**.

Desde entonces el doble clic funcionará sin preguntar. Si el aviso persiste,
abra la Terminal, escriba `xattr -dr com.apple.quarantine ` —con el espacio
final—, arrastre la carpeta de la aplicación sobre la ventana de Terminal y
presione Intro.

**Si dice «permiso denegado».** El archivo perdió su marca de ejecutable al
descomprimirse. En la Terminal escriba `chmod +x ` —con el espacio final—,
arrastre `INICIAR.command` sobre la ventana y presione Intro.

---

## Uso diario

- **Para abrirla**: doble clic en `INICIAR.command`.
- **Para cerrarla**: presione Control + C en la ventana de Terminal, o
  simplemente cierre esa ventana. Al hacerlo se descarta de la memoria el
  documento que estaba procesando.
- **La aplicación no se conecta a internet** mientras trabaja. Puede
  desconectar el equipo de la red y seguirá funcionando igual. Solo necesita
  conexión la primera vez, para descargar las bibliotecas.

---

## Mejorar la detección de nombres (opcional)

La aplicación funciona sin esto. Si desea que reconozca además nombres poco
frecuentes que aparecen sin ninguna señal de contexto, abra la Terminal, sitúe
el cursor en la carpeta de la aplicación y ejecute:

```
./.venv/bin/python -m pip install -r requirements-nlp.txt
./.venv/bin/python -m spacy download es_core_news_md
```

Son unos 45 MB de descarga. Al volver a abrir la aplicación, la etiqueta
superior dirá «con modelo de lenguaje».

Advertencia de licencia: ese modelo se distribuye bajo GPL-3.0 y no forma parte
de este repositorio.

---

## Actualizar a una versión posterior

Descargue de nuevo el archivo comprimido y reemplace la carpeta. Conserve, si
la creó, la subcarpeta `.venv` para no repetir la preparación; si la borra, la
aplicación la volverá a crear en el siguiente arranque.

---

## Si prefiere una aplicación empaquetada

Es posible construir un `.app` de macOS que se abra como cualquier otro
programa, sin Terminal ni instalación previa de Python. Requiere compilarlo en
un Mac —las herramientas de empaquetado no permiten hacerlo desde otro sistema
operativo—, sea en su propio equipo o mediante un servicio de compilación
automática. Si le interesa, puede pedirse.
