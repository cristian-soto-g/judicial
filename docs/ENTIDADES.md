# Las nueve categorías de detección

La aplicación detecta únicamente las categorías que se detallan a continuación.
La lista es cerrada de manera deliberada: cada categoría adicional amplía la
superficie de falsos positivos y diluye la atención de quien revisa, que es el
recurso más escaso de todo el proceso.

Cada categoría puede activarse o desactivarse antes del análisis, y cualquier
detección puede corregirse o descartarse después.

---

## 1. Personas

Nombres de personas naturales.

**Reglas de contexto** (no consultan el diccionario y operan con cualquier
apellido, frecuente o no):

- Tratamiento de cortesía o profesional: «don», «doña», «Sr.», «Sra.», «Dr.»,
  «abogado», «juez», «fiscal», «defensor», «perito», grados de Carabineros y de
  la Policía de Investigaciones.
- Rol procesal: imputado, acusado, condenado, víctima, ofendido, denunciante,
  querellante, testigo, perito, demandante, demandado, recurrente, adolescente,
  alimentante, entre otros.
- Nombre inmediatamente anterior a un RUT o a una cédula de identidad.
- Fórmulas de presentación: «de nombre», «individualizado como», «responde al
  nombre de».
- Apellido aislado que sigue a un tratamiento o a un rol procesal («la señora
  Painemal ratificó»), que es como los escritos chilenos nombran a una persona
  después de individualizarla.

**Reglas apoyadas en el catálogo** (para nombres sin ninguna señal de contexto):

- Encabezado judicial «APELLIDOS, Nombres».
- Nombre con inicial intermedia: «Juan P. Muñoz».
- Secuencias capitalizadas o en versales con al menos una palabra en el
  catálogo de nombres o apellidos.

**Precauciones.** No se unen dos personas enlazadas por «y». Se descartan las
frases narrativas, las fórmulas forenses y las denominaciones administrativas
que no vienen ancladas por un nombre de pila.

**Menciones parciales.** Cuando el documento individualiza a alguien con su
nombre completo y después lo nombra solo por su apellido, ambas menciones
quedan cubiertas por una única sustitución. Es un punto donde un anonimizador
falla de manera silenciosa: si las menciones posteriores no se reemplazan, el
documento parece anonimizado sin estarlo.

---

## 2. RUT/Cédula de identidad

RUT y RUN de personas naturales y jurídicas.

- **Con rótulo** («RUT», «RUN», «cédula de identidad», «C.I.», «rol único
  tributario»): se acepta el número aunque el dígito verificador no calce,
  porque un RUT mal transcrito sigue identificando a una persona.
- **Sin rótulo**: se exige que el dígito verificador calce según el algoritmo
  módulo 11, lo que evita confundirlo con cualquier otra cifra del expediente.
- Se admiten los formatos `12.345.678-5`, `12345678-5` y sus variantes con
  espacios; el verificador `K` se acepta en mayúscula y en minúscula.
- Las cifras en contexto monetario se descartan.

Se anonimiza el número, no el rótulo: el documento sigue diciendo «cédula de
identidad N° [RUT_1]».

---

## 3. Organizaciones

Empresas, instituciones y organismos públicos, en una sola categoría.

- **Por sufijo societario**: S.A., SpA, Ltda., Limitada, E.I.R.L., S.C.M.,
  cooperativas, corporaciones, fundaciones y asociaciones gremiales.
- **Por encabezado institucional**: juzgados, tribunales, cortes, fiscalías,
  defensorías, ministerios, municipalidades, delegaciones presidenciales,
  Carabineros, Policía de Investigaciones, Gendarmería, Registro Civil,
  Servicio Médico Legal, hospitales, clínicas, CESFAM, universidades, liceos,
  colegios, bancos e isapres.
- **Por sigla**: SII, PDI, SML, SENDA, SENAME, IPS, FONASA, OS7, LABOCAR, CDE,
  entre otras.
- **Tribunales con ordinal**: «4° Tribunal de Juicio Oral en lo Penal de
  Santiago», «8° Juzgado de Garantía de Santiago».

El nombre de una organización no cruza un punto ni un salto de línea, de modo
que la detección no invade el considerando siguiente.

**Consideración práctica.** Muchos usuarios prefieren conservar la
individualización del tribunal y de los intervinientes institucionales, que no
son datos personales. La categoría puede desactivarse por completo antes del
análisis, o pueden descartarse filas concretas en la revisión.

---

## 4. Emails

Direcciones de correo electrónico en su forma habitual, incluidas las que el
extractor de PDF separa con un espacio alrededor de la arroba.

---

## 5. Teléfonos

Numeración chilena de nueve dígitos.

- Con prefijo internacional: `+56 9 8765 4321`, `+56987654321`.
- Numeración nacional con separadores: `9 8765 4321`, `22 234 5678`.
- Con rótulo: «teléfono», «fono», «celular», «contacto», «WhatsApp».
- Nueve dígitos seguidos que comienzan con 9, solo en sensibilidad exhaustiva
  por su ambigüedad.

Se valida que el primer dígito corresponda a la numeración chilena —9 para
móviles, 2 a 7 para la red fija— y se descartan las secuencias de relleno.

---

## 6. Domicilios

Direcciones con vía, numeración, complemento y comuna.

- **Vías**: calle, avenida, pasaje, camino, ruta, callejón, costanera,
  alameda, carretera, plaza.
- **Complementos**: departamento, oficina, casa, block, torre, piso, villa,
  población, condominio, parcela, sitio, lote, manzana, kilómetro, sector,
  fundo, loteo.
- **Anclas narrativas**: «domiciliado en», «con domicilio en», «sito en»,
  «ubicado en», «reside en», «vive en».
- **Comuna**: «comuna de X».

El nombre de la vía debe comenzar con mayúscula o con un número. Ese criterio
sustituye a la lista de palabras prohibidas que usaba la aplicación original:
en Chile las vías que empiezan por artículo —Los Aromos, Las Rosas, El Bosque—
son numerosísimas, y una lista de ese tipo las eliminaría todas.

La captura se recorta en el punto donde el texto deja de ser una dirección y
comienza el relato, de modo que la detección no arrastre media oración.

---

## 7. Patentes

Placas patente únicas de vehículos.

- **Formato vigente** (desde 2007): cuatro letras y dos dígitos, `BBBB12`. Las
  letras provienen de un alfabeto restringido que excluye las vocales y las
  letras M, N y Q. Ese formato es lo bastante específico como para detectarse
  sin rótulo.
- **Motocicletas**: tres letras y dos dígitos.
- **Formato anterior** (1985-2007): dos letras y cuatro dígitos, `AB1234`.
- **Con rótulo** («patente», «placa patente», «PPU»): se acepta un patrón más
  amplio, porque el rótulo aporta la evidencia que de otro modo debería aportar
  el formato.

Se descartan las citas normativas que calzan con el patrón antiguo («Ley 471»).

---

## 8. Otros sensibles

Datos identificatorios que no encajan en las categorías anteriores:

- **NUE** (Número Único de Evidencia) de la cadena de custodia.
- Pasaporte y número de serie de la cédula.
- Cuentas corrientes, vista, de ahorro y cuenta RUT.
- Números de tarjeta.
- IMEI.
- Licencia de conducir.
- Ficha clínica o médica.
- Parte policial y número de denuncia.
- Folio.
- Fecha de nacimiento, cuando aparece explícitamente rotulada.
- Dirección IP, URL y nombre de usuario de redes sociales.

Las cifras en contexto monetario se descartan.

---

## 9. Número de causa

Identificadores de causa en las tres nomenclaturas chilenas:

- **RIT**: `RIT N° 145-2024`, `RIT O-1234-2023`, con los prefijos por materia.
- **RUC**: `RUC 2300456789-1`. Se verifica la estructura —dos dígitos de año,
  ocho de serie y verificador— pero **no** el dígito verificador: el algoritmo
  con que se calcula no está publicado de manera oficial y verificable, y
  rechazar un RUC legítimo por una suposición equivocada dejaría un dato
  identificatorio sin anonimizar.
- **ROL**: `Rol N° 12.345-2023`, `Rol Ingreso Corte N° 5678-2024`.
- Rótulos genéricos: «causa», «expediente», «carpeta investigativa», «Ingreso
  Corte».

Se anonimiza el número, no el rótulo: el documento sigue diciendo
«RIT N° [CAUSA_1]».

---

## Sensibilidad de la detección

Tres niveles regulan el equilibrio entre detectar de más y detectar de menos:

| Nivel | Comportamiento |
|---|---|
| **Exhaustiva** (predeterminado) | Incorpora las reglas más ambiguas: teléfonos de nueve dígitos sin separadores, identificadores de causa sin rótulo y apellidos sueltos tras un rol procesal aunque no figuren en el catálogo. |
| **Equilibrada** | Omite esas tres reglas y conserva todo lo demás. |
| **Precisa** | Omite además lo que se reconoce solo por su forma, sin rótulo que lo respalde. |

En el nivel **preciso**, en concreto:

- Los nombres detectados sin ninguna señal de contexto deben traer **a la vez**
  un nombre de pila y un apellido presentes en el catálogo, en lugar de
  cualquiera de los dos. Las reglas de contexto no cambian: siguen operando sin
  consultar el diccionario, de modo que este endurecimiento no introduce sesgo
  por origen del apellido.
- Los domicilios deben incluir numeración. Sin ella, la captura suele ser el
  nombre de un lugar y no el domicilio de nadie.
- De las patentes sin rótulo solo se admite el formato vigente de cuatro letras
  y dos dígitos, que es inequívoco.
- De «Otros sensibles» se descartan los patrones sin rótulo —dirección IP,
  número de tarjeta y nombre de usuario—, que son los más expuestos a coincidir
  por azar con una cifra del escrito.

El nivel exhaustivo es el predeterminado por una razón de fondo: un falso
positivo se descarta con un clic en la pantalla de revisión, mientras que un
dato no detectado se publica.

Cuando la capa opcional de lenguaje natural está instalada, el nivel preciso le
aplica los mismos requisitos que a las reglas. De lo contrario el ajuste no
diría la verdad: la interfaz ofrecería menos falsos positivos y el modelo
seguiría proponiendo los suyos.
