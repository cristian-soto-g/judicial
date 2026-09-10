# Protección de datos: decisiones de diseño y riesgos que subsisten

Este documento explica por qué la aplicación está construida como está, y
—más importante— qué riesgos no elimina. Un anonimizador que se presente como
infalible es peligroso justamente porque induce a confiar sin revisar.

---

## 1. El documento no sale del equipo

- El servidor escucha únicamente en `127.0.0.1`, la interfaz de bucle local.
- Además, la aplicación **rechaza con un error 403 toda petición dirigida a un
  anfitrión distinto** de `127.0.0.1` o `localhost`. La restricción es
  redundante respecto de la anterior, y esa redundancia es intencional: cubre
  el caso de que la aplicación quede accidentalmente expuesta detrás de un
  reenvío de puertos o de un contenedor mal configurado.
- No hay llamadas a servicios externos en tiempo de ejecución. La interfaz no
  carga tipografías, hojas de estilo ni bibliotecas desde internet: todo el
  código se sirve desde el propio equipo.
- No hay telemetría, registro de uso ni analítica de ninguna especie.

## 2. Las sesiones viven solo en memoria

El texto del documento **no se escribe en disco en ningún momento**. Se
mantiene en la memoria del proceso mientras la aplicación está abierta y se
pierde al cerrarla. La aplicación en que este trabajo se basa contemplaba una
persistencia opcional en SQLite; aquí se eliminó por completo.

Consecuencia práctica: si cierra la aplicación a mitad del trabajo, deberá
volver a cargar el documento. Es un costo aceptado a cambio de que no queden
restos del contenido en el equipo.

Las respuestas HTTP llevan `Cache-Control: no-store`, de modo que el navegador
tampoco conserve copias del contenido.

## 3. El mapa de reversión

Es el archivo más sensible de todo el flujo: concentra la totalidad de los
datos personales del documento junto con la clave para reubicarlos en él.

**Cómo se protege**

- Cifrado con **AES-256-GCM**, que aporta confidencialidad y autenticación: un
  archivo alterado no se descifra, falla de manera explícita en lugar de
  devolver datos corruptos.
- Clave derivada con **scrypt** (N = 2¹⁶, r = 8, p = 1), que exige alrededor de
  64 MB de memoria por intento y encarece de manera considerable un ataque por
  fuerza bruta sobre la frase de paso.
- Sal y nonce aleatorios en cada operación: dos mapas del mismo documento no
  son comparables entre sí.
- Los parámetros públicos viajan como datos autenticados adicionales, de suerte
  que tampoco puedan manipularse.
- Se descarga como **archivo separado** del documento anonimizado, para que
  este último pueda compartirse sin arrastrar consigo la información que
  permite deshacer la anonimización.

**La frase de paso no se guarda en ninguna parte.** Ni en el equipo, ni en la
sesión, ni en el archivo. La interfaz la borra apenas se usa. Es una decisión
de diseño y no una omisión: si la pierde, la reversión es imposible. Anótela en
un lugar seguro y distinto de donde guarde el mapa.

**Qué restituye exactamente la reversión**

Cuando durante la revisión se confirma una identidad —varias formas de nombrar
a la misma persona pasan a compartir una sola sustitución—, el mapa registra la
forma más completa como canónica y anota las demás como variantes. La reversión
restituye entonces la forma canónica en todas las apariciones.

Dicho de otro modo: el documento restituido vuelve a identificar a las mismas
personas, pero no reproduce el original carácter por carácter. Si necesita una
restitución literal, no confirme identidades y conserve cada variante como una
detección propia.

La aplicación sí rechaza generar el mapa cuando personas **distintas** comparten
una etiqueta, que es lo que ocurre con los modos de etiquetado genérico y de
iniciales. Ahí la reversión sería imposible y entregar un mapa parcial induciría
a error.

**Riesgos que subsisten**

- Si el mapa y el documento anonimizado se comparten juntos, la anonimización
  no protege nada. Guárdelos separados.
- La seguridad del cifrado no supera a la de la frase de paso. Una frase larga
  y memorable protege mejor que una contraseña corta y compleja.
- Un mapa cifrado no deja de ser un tratamiento de datos personales. Aplíquele
  los mismos plazos de conservación y las mismas medidas que a cualquier otro
  archivo con datos sensibles.

## 4. La tabla de equivalencias en CSV

Contiene los datos originales **en claro, sin cifrar**. Está pensada para el
control interno del trabajo —verificar qué se reemplazó y con qué— y la
aplicación lo advierte de manera expresa en la pantalla de exportación.

No debe compartirse junto con el documento anonimizado. Si necesita conservar
la posibilidad de revertir, use el mapa cifrado.

## 5. Seudonimización, no anonimización irreversible

Conviene ser preciso con los términos, porque tienen consecuencias jurídicas.

Cuando se genera el mapa de reversión, lo que la aplicación produce es una
**seudonimización**: existe información adicional que permite reidentificar a
las personas. Un dato seudonimizado sigue siendo un dato personal y sigue
sometido al régimen de protección correspondiente.

Solo si **no** se genera el mapa —o si este se destruye de manera efectiva— el
resultado se aproxima a una anonimización. Y aun entonces con reservas: un
documento judicial puede permitir la reidentificación por el relato mismo de
los hechos, sin necesidad de ningún identificador directo. Una combinación de
fecha, comuna, profesión y circunstancias singulares puede señalar a una
persona con tanta precisión como su RUT.

Ninguna herramienta automática resuelve ese problema. La revisión del relato,
y no solo de los identificadores, sigue siendo responsabilidad de quien
publica.

## 6. Lo que la herramienta no hace

- **No lee documentos escaneados.** No incluye reconocimiento óptico de
  caracteres. Un PDF sin capa de texto se rechaza con un mensaje explícito, y
  si solo algunas páginas carecen de texto se advierte cuáles quedaron fuera
  del análisis. La advertencia es deliberada: procesar un escaneo en silencio
  produciría un documento en apariencia anonimizado y en realidad intacto, que
  es el peor resultado posible.
- **No lee metadatos ni contenido oculto.** Un `.docx` puede llevar autor,
  comentarios, control de cambios y texto oculto con datos personales. La
  aplicación extrae el texto visible, las tablas, los encabezados y los pies de
  página, pero no inspecciona el resto. Los formatos de exportación son
  documentos nuevos y no arrastran los metadatos del original; el más seguro en
  ese sentido es el texto plano.
- **No detecta todo.** Es una herramienta de asistencia. La revisión humana
  previa a la exportación no es opcional.

## 7. Recomendaciones de uso

1. Revise siempre la vista previa completa antes de exportar. La aplicación
   privilegia detectar de más precisamente para que la revisión sea de
   descarte y no de búsqueda.
2. Lea el documento exportado una vez más, ya sin la herramienta a la vista.
3. Preste atención a los datos que ninguna regla puede capturar: circunstancias
   singulares del relato, fechas combinadas con lugares, profesiones poco
   frecuentes, vínculos familiares.
4. Guarde el mapa de reversión separado del documento y con una frase de paso
   que no reutilice.
5. Cierre la aplicación cuando termine: con ello se descarta el contenido de la
   memoria.
