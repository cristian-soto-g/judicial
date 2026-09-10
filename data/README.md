# Catálogos de apoyo a la detección

Esta carpeta contiene los diccionarios que asisten al motor de detección. Se
generan con `python scripts/generar_diccionarios.py`, de modo que su contenido
es reproducible y auditable.

| Archivo | Contenido |
|---|---|
| `dictionaries/nombres.json` | Nombres de pila de uso corriente en Chile. |
| `dictionaries/apellidos.json` | Apellidos, con cobertura deliberada de distintos orígenes. |
| `dictionaries/formulas_judiciales.json` | Vocabulario forense chileno que no designa personas. |

## Composición de los catálogos y control de sesgo

Los diccionarios son la principal fuente de sesgo de un motor de este tipo: un
apellido ausente del catálogo se detecta peor que uno presente, de manera que
la anonimización termina protegiendo menos a quienes llevan apellidos poco
representados. Por eso la selección **no sigue la frecuencia estadística**, que
reproduciría ese desequilibrio, sino que cubre de forma pareja los orígenes
presentes en Chile: castellano, mapuche, y los habituales entre las
comunidades haitiana, venezolana, colombiana, peruana y boliviana, además de
los de origen europeo, árabe y asiático.

Ninguna palabra puede figurar a la vez como nombre de persona y como
vocabulario forense. Esa regla, que el generador aplica de manera automática,
corrige un error nada evidente: varias comunas chilenas llevan nombres de
persona —Pedro Aguirre Cerda, San Miguel, San Joaquín, San Ramón, San
Bernardo—, y al descomponerlas en palabras sueltas se colaban «pedro»,
«miguel», «joaquín», «ramón» y «bernardo» entre las fórmulas. El efecto era
silencioso y grave: cualquier persona llamada así quedaba sin detectar.

## La detección no depende solo del catálogo

Conviene subrayarlo porque es la garantía de fondo frente al sesgo: las reglas
de contexto del motor —tratamiento de cortesía, rol procesal, RUT contiguo,
encabezado «APELLIDOS, Nombres»— **no consultan el diccionario**. Un apellido
ausente del catálogo se detecta igualmente cuando el texto lo presenta como
persona. El catálogo solo interviene cuando el nombre aparece sin ninguna
señal de contexto.

Las pruebas de `tests/test_sesgo.py` verifican ambas cosas: que las reglas de
contexto funcionen por igual para todos los orígenes, incluidos apellidos
inventados que no figuran en ningún catálogo, y que la detección apoyada en el
diccionario no quede por debajo en ningún grupo.

## Ampliar los catálogos

Para agregar apellidos, edite las listas de `scripts/generar_diccionarios.py`
y vuelva a ejecutarlo. Si al ampliar el catálogo la prueba de paridad falla en
algún grupo, corresponde reforzar ese grupo antes de dar por buena la versión.

## Datos

Estos archivos contienen únicamente nombres y apellidos de uso público. El
proyecto no distribuye documentos judiciales reales ni sesiones de uso.
