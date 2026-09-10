# Control de sesgos en la detección

## Por qué importa aquí

Un anonimizador que reconozca peor unos apellidos que otros no comete un error
técnico neutro: protege de manera desigual, y lo hace precisamente en
perjuicio de quienes ya están menos representados. Si el motor detecta
«González» y no «Huenchullán», el resultado es que las personas mapuche
aparecen identificadas en documentos donde las demás no lo están.

En materia judicial el efecto se agrava, porque quienes comparecen ante los
tribunales no son una muestra representativa de la población.

## De dónde viene el sesgo

La fuente principal es el diccionario. Un motor que decida «esto es un nombre»
consultando un catálogo detectará bien lo que el catálogo contiene y mal lo que
no. Y todo catálogo construido por frecuencia estadística reproduce la
distribución de la población mayoritaria.

La segunda fuente, menos evidente, es el vocabulario que se declara «no es un
nombre». Si esa lista incluye por error palabras que sí son nombres de persona,
esas personas quedan sistemáticamente sin detectar.

## Qué hace esta aplicación al respecto

### 1. Las reglas de contexto no consultan el diccionario

Es la garantía de fondo. Cuando el texto presenta a alguien como persona —con
un tratamiento de cortesía, con un rol procesal, junto a un RUT, en un
encabezado «APELLIDOS, Nombres»— la detección opera **sin mirar el catálogo**.

Un apellido que no figura en ningún diccionario se detecta exactamente igual
que el más frecuente de Chile, siempre que el contexto lo identifique como
persona. Y en un escrito judicial el contexto casi siempre está: las personas
se individualizan.

El catálogo solo interviene en el caso residual de un nombre que aparece sin
ninguna señal de contexto.

### 2. El catálogo se compone por cobertura, no por frecuencia

La selección de apellidos cubre de manera deliberada los distintos orígenes
presentes en Chile —castellano, mapuche, y los habituales entre las comunidades
haitiana, venezolana, colombiana, peruana y boliviana, además de los de origen
europeo, árabe y asiático— sin seguir su frecuencia relativa.

### 3. Ninguna palabra puede ser a la vez nombre y fórmula forense

El generador de catálogos resta del vocabulario forense toda palabra que
aparezca en los catálogos de nombres o apellidos.

Esa regla corrige un defecto que el desarrollo de esta versión encontró y que
ilustra bien lo silencioso que puede ser un sesgo. Varias comunas chilenas
llevan nombres de persona: Pedro Aguirre Cerda, San Miguel, San Joaquín, San
Ramón, San Bernardo. Al descomponer esos nombres en palabras sueltas para el
catálogo de fórmulas, se colaban «pedro», «miguel», «joaquín», «ramón» y
«bernardo». El resultado era que **cualquier persona llamada así quedaba sin
detectar** cuando su nombre aparecía sin contexto explícito. No lo advirtió una
revisión del código, sino la prueba de paridad.

### 4. La sensibilidad exhaustiva es la predeterminada

Detectar de más y descartar en la revisión distribuye el error de manera más
pareja que detectar de menos. Un falso positivo cuesta un clic; un dato no
detectado se publica.

## Cómo se verifica

`tests/test_sesgo.py` mide la paridad, no la calidad general:

1. **Paridad por contexto.** Cinco grupos de apellidos —castellano, mapuche,
   haitiano, andino y asiático— se insertan en cuatro plantillas con contexto
   explícito. Todos deben detectarse en todas.
2. **Apellidos fuera de catálogo.** Cuatro nombres inventados, ausentes de todo
   diccionario, deben detectarse igualmente por contexto. Es la prueba directa
   de que la protección no depende del catálogo.
3. **Paridad por catálogo.** Sin contexto, se mide la tasa de detección de cada
   grupo. La prueba falla si algún grupo queda por debajo de los demás, e
   indica en el mensaje cuál es y qué corresponde hacer.
4. **Cobertura del catálogo.** Se comprueba que haya apellidos de cada origen.

La prueba de paridad **debe seguir pasando** al modificar el motor o los
catálogos. Si falla, corresponde reforzar el grupo más débil antes de dar por
buena la versión: no es una prueba informativa, es una condición de entrega.

## Límites que subsisten

- Los cinco grupos evaluados no agotan la diversidad de apellidos en Chile.
  La prueba detecta desequilibrios groseros, no diferencias finas.
- La paridad se mide sobre plantillas construidas, no sobre documentos reales.
  Un corpus real permitiría medir mejor, pero no puede incorporarse a un
  repositorio público sin comprometer datos personales.
- El sesgo de género no está evaluado. Los tratamientos y roles procesales
  contemplan las formas femeninas y masculinas de manera simétrica, pero eso no
  se ha medido.
- La capa opcional de lenguaje natural aporta sus propios sesgos, heredados de
  los datos con que se entrenó el modelo. Al ser opcional y complementaria, no
  altera la garantía de fondo, que descansa en las reglas de contexto. Conviene
  señalar, eso sí, que su contribución va en la dirección correcta: reconoce
  nombres sin contexto y con apellidos ausentes del catálogo, que es
  precisamente el caso residual donde la detección por reglas resulta más
  desigual. Durante el desarrollo esa contribución estuvo anulada, porque el
  filtro de calidad le exigía al modelo el mismo respaldo del diccionario que a
  las reglas y descartaba justamente los nombres que solo él encontraba.

## Cómo ampliar los catálogos

Edite las listas de `scripts/generar_diccionarios.py` y vuelva a ejecutarlo:

```bash
python scripts/generar_diccionarios.py
python -m pytest tests/test_sesgo.py
```
