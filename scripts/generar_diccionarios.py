# -*- coding: utf-8 -*-
"""Genera los catálogos de nombres, apellidos y vocabulario forense.

Ejecutar desde la raíz del proyecto:

    python scripts/generar_diccionarios.py

Criterio de composición de los catálogos. La selección de apellidos no busca
representar su frecuencia estadística en Chile, sino cubrir de manera pareja
los distintos orígenes presentes en el país: castellano, mapuche, y los
habituales entre las comunidades migrantes haitiana, venezolana, colombiana,
peruana y boliviana, además de los de origen europeo, árabe y asiático. Un
catálogo construido por frecuencia protegería mejor a quienes llevan apellidos
comunes y peor a todos los demás, que es exactamente el sesgo que se quiere
evitar.

El catálogo de fórmulas recoge el vocabulario forense chileno que aparece
capitalizado en los escritos y que el detector podría confundir con nombres
propios.
"""
import json
import unicodedata
from pathlib import Path

DEST = Path("data/dictionaries")


def norm(s):
    s = s.strip().lower()
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return s


NOMBRES_CHILE = """
Maria Jose Juan Carlos Ana Luis Pedro Jorge Francisco Patricia Claudia Marcela Andrea Paula
Cristian Cristina Rodrigo Alejandro Alejandra Fernando Fernanda Sebastian Sebastiana Camila
Matias Martina Benjamin Florencia Vicente Valentina Agustin Agustina Tomas Antonia Joaquin
Josefa Diego Isidora Maximiliano Catalina Nicolas Emilia Gabriel Sofia Lucas Amanda Vicenta
Bastian Javiera Ignacio Constanza Felipe Daniela Pablo Carolina Mauricio Veronica Ricardo
Sandra Hector Rosa Manuel Margarita Victor Gloria Roberto Ximena Sergio Cecilia Eduardo
Monica Raul Silvia Oscar Elizabeth Marcelo Jacqueline Alberto Nancy Hernan Eliana Guillermo
Ruth Rene Ines Mario Teresa Enrique Isabel Gonzalo Lorena Cristobal Karen Ramon Mercedes
Arturo Angelica Gustavo Pamela Alfredo Viviana Miguel Marisol Rafael Loreto Ernesto Solange
Cristopher Nicole Jonathan Katherine Bryan Yasna Kevin Denisse Alexis Fabiola Franco Estefania
Ivan Roxana Nelson Erika Rolando Mariela Osvaldo Jessica Segundo Berta Juana Amalia Elena
Clara Olga Dominga Filomena Adriana Bernardita Paz Trinidad Renata Antonella Anais Belen
Millaray Ayelen Rayen Antu Lientur Nahuel Kalfu Elisa Amaru Kurruf Aylin Newen Likan Pehuen
Rayun Lemu Antinao Huenu Melipal Mankeo
Jean Marie Pierre Wisly Frantz Emmanuel Mackenson Woodly Jephte Guerline Rosemene Islande
Fabiola Kettelie Widlyn Wilner Jonas Dieuseul Jimmy Ricardo Roseline Mirlande Nadege Jesula
Yorman Yeison Deivi Wilmer Yusmary Anyelo Keiber Jhoan Jhonny Maikel Yulimar Dayana Yubisay
Jhonatan Darwin Franyer Endry Neiber Yorley Yorbin Yaneth Yajaira Yesenia Yohana
Wilson Edwin Elmer Percy Nilda Zenobia Justina Basilia Eulogio Hipolito Marcelino Feliciana
Santusa Bernardino Gregoria Julia Hilda Rufino Sabina Esperanza Ceferino Isidoro
Ling Wei Jun Mei Hui Yan Xiu Chen Kim Min Ji Soo Hyun Ahmed Fatima Hassan Layla Karim Nadia
Giovanni Marco Antonella Luigi Franco Paolo Hans Klaus Erika Ingrid Helmut Gerardo Werner
"""

APELLIDOS_CHILE = """
Gonzalez Munoz Rojas Diaz Perez Soto Contreras Silva Martinez Sepulveda Morales Rodriguez
Lopez Fuentes Hernandez Torres Araya Flores Espinoza Valenzuela Castillo Tapia Reyes
Gutierrez Castro Vargas Alvarez Vasquez Sanchez Fernandez Ramirez Carrasco Gomez Cortes
Herrera Nunez Jara Vergara Rivera Figueroa Riquelme Bravo Miranda Orellana Vera Salazar
Campos Sandoval Guzman Molina Ortiz Garrido Vega Olivares Escobar Yanez Cardenas Pena
Aguilera Navarro Alarcon Godoy Ruiz Pino Saavedra Pizarro Leiva Zuniga Salinas Henriquez
Ortega Toro Bustos Rios Poblete Maldonado Palma Caceres Farias Villegas Aravena Parra
Paredes Medina Lagos Barrera Cabrera Acuna Avila Suarez Aguirre Rivas Cespedes Donoso
Chavez Ibanez Mella Concha Mora Bustamante Correa Pacheco Valdes Cifuentes Arriagada
Alvarado Osorio Retamal Vidal Marin Ampuero Barria Oyarzun Aguayo Barrientos Carcamo
Millan Sanhueza Neira Beltran Quiroz Verdugo Ovalle Urrutia Valdivia Villarroel Zamora
Sotomayor Quezada Duran Rebolledo Pavez Meza Riveros Valdebenito Gallardo Cuevas Roa
Munita Errazuriz Larrain Undurraga Vial Matte Edwards Amunategui Irarrazaval Valdivieso
Echeverria Prieto Montt Balmaceda Alessandri Frei Aylwin Lavin Piñera Bachelet Boric
Yarur Said Sabag Toha Chahuan Awad Zalaquett Hales Kast Elgueta Nazal Hirmas Musalem
Schmidt Muller Hott Kuschel Winkler Bianchi Rossi Ferrada Doren Grillo Bertoni Cerda
Huenchullan Huenchuman Huenchumilla Curihual Curinao Curiqueo Painemal Painen Painecura
Catrileo Catrilaf Catrileu Millaqueo Millapan Millanao Nahuelpan Nahuel Nahuelhual
Calfucura Calfuqueo Calfulaf Lemunao Antileo Antinao Antilef Anticura Huaiquil Huaiquilaf
Marileo Marilaf Mariman Maripan Quilaqueo Quilapan Llanquileo Llancapan Lincopan Linconir
Colipan Coliqueo Colihuinca Cayuqueo Cayupan Namuncura Melillan Melinir Melinao Melivilu
Trecananco Huenteo Huentelaf Huentemil Huenupe Loncon Lonconao Paillalef Paillan Paillacar
Canio Canulaf Currio Huichacura Huirimilla Levicoy Levinao Lefiman Manquel Manquepillan
Neculman Pichun Pilquiman Pranao Quintreman Raiman Reuque Tranamil Treuquil Nancucheo
Nanco Curiche Huenchunir Painevilo Quidel Rapiman Aillapan Chihuailaf Cheuquelaf Conuepan
Epunan Hueche Panguilef Relmucao Tripailaf Quintupil Antihuala Huenupil Marifil Coliman
Pierre Jean Joseph Charles Louis Baptiste Dorvil Cadet Desir Alexis Michel Etienne Francois
Toussaint Casimir Laguerre Noel Augustin Elie Cherry Vilsaint Beauvoir Delva Mompoint
Sanon Volcy Estime Jeune Morisset Bellevue Guerrier Lafleur Sylvain Philippe Gabriel
Antoine Raymond Simon Julien Lamothe Isidore Excellent Fenelon Sainvil Charlot Denis
Delice Metellus Registre Ulysse Voltaire Zamor Saintilus Previlon Dessalines Exantus
Quispe Mamani Condori Huaman Apaza Choque Ticona Cusi Vilca Callisaya Poma Chura Colque
Aduviri Yupanqui Anco Sucasaire Ccama Layme Calcina Coaquira Larico Machaca Nina Paucar
Sarmiento Tito Turpo Yucra Zapana Ayma Catacora Chipana Copa Cutipa Huanca Limachi
Mosquera Palacios Renteria Cordoba Asprilla Valencia Caicedo Perea Ibarguen Murillo
Angulo Riascos Arboleda Bonilla Hurtado Obregon Gaviria Restrepo Ospina Zapata Betancur
Bolivar Blanco Colmenares Aponte Quintero Marquez Rondon Sivira Urdaneta Chirinos
Zambrano Pinango Gil Rangel Villalobos Duarte Guedez Andrade Escalona Piña
Chan Lam Wong Kim Lee Zhang Wang Liu Chen Yang Huang Zhao Wu Zhou Xu Sun Zhu Guo Lin Gao
Luo Zheng Nakamura Tanaka Yamamoto Suzuki Kato Sato Park Choi Jung Kang Cho
Smith Johnson Brown Taylor Wilson Anderson Thomas Jackson White Harris Clark Lewis Walker
Rossi Russo Ferrari Esposito Bianchi Romano Colombo Ricci Marino Greco Bruno Gallo Conti
Schneider Fischer Weber Meyer Wagner Becker Hoffmann Schulz Koch Bauer Richter Klein
Silva Santos Oliveira Souza Pereira Costa Carvalho Almeida Nascimento Lima Araujo Ribeiro
"""

# Palabras que aparecen capitalizadas en escritos judiciales chilenos y que el
# detector de personas podria confundir con nombres propios.
FORMULAS_JUDICIALES = """
vistos considerando considerandos resuelvo resuelve teniendo presente notifiquese archivese
registrese cumplase comuniquese devuelvase autos autoriza certifica proveido resolucion
sentencia veredicto audiencia acta comparendo querella querellante requerimiento demanda
demandante demandado acusacion formalizacion sobreseimiento suspension condicional
procedimiento abreviado simplificado monitorio ordinario reforma recurso nulidad apelacion
casacion queja amparo proteccion cautelar cautelares prision preventiva libertad vigilada
remision reclusion presidio multa comiso agravante atenuante irreprochable conducta anterior
delito cuasidelito falta crimen simple consumado frustrado tentativa autor complice encubridor
homicidio parricidio femicidio robo hurto lesiones amenazas estafa receptacion trafico
microtrafico estupefacientes ebriedad violacion abuso sexual incendio danos usurpacion
desacato maltrato violencia intrafamiliar alimentos tuicion cuidado personal relacion directa
regular divorcio nulidad matrimonio adopcion susceptibilidad medida proteccion internacion
juez jueza jueces ministro ministra ministros fiscal fiscales defensor defensora defensoria
secretario secretaria abogado abogada procurador receptor perito peritos testigo testigos
imputado imputada victima ofendido denunciante querellado condenado absuelto sentenciado
policia carabineros investigaciones gendarmeria funcionario funcionarios profesional
tribunal tribunales juzgado juzgados corte cortes suprema apelaciones garantia oral penal
civil familia laboral cobranza previsional letras competencia comun
articulo articulos codigo procesal penal civil trabajo ley leyes decreto reglamento
numero numeral inciso letra parrafo titulo libro capitulo folio foja fojas
enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre
lunes martes miercoles jueves viernes sabado domingo
region regional metropolitana provincia provincial comuna comunal nacional ciudad
santiago valparaiso concepcion temuco antofagasta iquique arica copiapo serena rancagua
talca chillan valdivia osorno puerto montt coyhaique punta arenas calama quilpue
providencia nunoa maipu florida puente alto pintana granja cisterna reina condes barnechea
recoleta independencia conchali huechuraba quilicura renca cerrillos estacion central
pedro aguirre cerda san miguel joaquin ramon bernardo lo espejo prado macul penalolen
vitacura quinta normal cerro navia bosque
estado republica chile chileno chilena chilenos chilenas nacion gobierno ministerio
servicio instituto direccion departamento unidad seccion oficina
declaracion declaraciones hechos hecho pruebas prueba antecedentes antecedente informe
oficio parte denuncia atestado constancia fotografia video registro grabacion
manifiesta senala declara expresa indica agrega refiere sostiene afirma reconoce niega
solicita pide requiere ordena dispone decreta ratifica confirma revoca rechaza acoge
primero segundo tercero cuarto quinto sexto septimo octavo noveno decimo undecimo
"""


def to_list(bloque):
    palabras = {norm(p) for p in bloque.split() if len(p.strip()) > 1}
    return sorted(palabras)


DEST.mkdir(parents=True, exist_ok=True)
nombres = to_list(NOMBRES_CHILE)
apellidos = to_list(APELLIDOS_CHILE)

# Ninguna palabra que sea un nombre de pila o un apellido puede figurar a la vez
# como vocabulario forense. Varias comunas chilenas llevan nombres de persona
# —Pedro Aguirre Cerda, San Miguel, San Joaquín, San Ramón, San Bernardo—, de
# modo que al descomponerlas en palabras sueltas se colaban "pedro", "miguel",
# "joaquin", "ramon" y "bernardo" en el catálogo de fórmulas. El efecto era
# grave y silencioso: cualquier persona llamada así quedaba sin detectar.
formulas = [p for p in to_list(FORMULAS_JUDICIALES) if p not in set(nombres) | set(apellidos)]

(DEST / "nombres.json").write_text(
    json.dumps(nombres, ensure_ascii=False, indent=0), encoding="utf-8"
)
(DEST / "apellidos.json").write_text(
    json.dumps(apellidos, ensure_ascii=False, indent=0), encoding="utf-8"
)
(DEST / "formulas_judiciales.json").write_text(
    json.dumps(formulas, ensure_ascii=False, indent=0), encoding="utf-8"
)

print("nombres:", len(nombres))
print("apellidos:", len(apellidos))
print("formulas:", len(formulas))
print("solapamiento nombres/apellidos:", len(set(nombres) & set(apellidos)))
print("solapamiento formulas/personas:", len(set(formulas) & (set(nombres) | set(apellidos))))
