/* Interfaz del Anonimizador Judicial Chile.
 *
 * Basada en la interfaz del Anonimizador Judicial de IALAB — Facultad de
 * Derecho, UBA (Apache 2.0). Reescrita para las nueve categorías chilenas, el
 * flujo de reversibilidad y el registro lingüístico de este proyecto.
 *
 * No se cargan bibliotecas externas: todo el código se ejecuta en el navegador
 * del propio equipo y ninguna función realiza peticiones fuera de él.
 */
'use strict';

/* ------------------------------------------------------------------ */
/* Constantes                                                          */
/* ------------------------------------------------------------------ */

const CATEGORIAS = [
  { clave: 'PERSONA',      nombre: 'Personas',                 color: '#9f3343' },
  { clave: 'RUT',          nombre: 'RUT/Cédula de identidad',  color: '#8a4a19' },
  { clave: 'ORGANIZACION', nombre: 'Organizaciones',           color: '#4a1e78' },
  { clave: 'EMAIL',        nombre: 'Emails',                   color: '#256c5b' },
  { clave: 'TELEFONO',     nombre: 'Teléfonos',                color: '#24647a' },
  { clave: 'DOMICILIO',    nombre: 'Domicilios',               color: '#7a476d' },
  { clave: 'PATENTE',      nombre: 'Patentes',                 color: '#5a3d6e' },
  { clave: 'OTRO',         nombre: 'Otros sensibles',          color: '#445a84' },
  { clave: 'CAUSA',        nombre: 'Número de causa',          color: '#0b2545' }
];

const MAPA_CATEGORIAS = Object.fromEntries(CATEGORIAS.map((c) => [c.clave, c]));

const estado = {
  sessionId: null,
  nombreDocumento: '',
  textoOriginal: '',
  textoAnonimizado: '',
  detecciones: [],
  grupos: [],
  estadisticas: {},
  resaltados: [],
  modoVista: 'original',
  seleccion: null,
  coincidencias: [],
  analizando: false
};

/* ------------------------------------------------------------------ */
/* Utilidades                                                          */
/* ------------------------------------------------------------------ */

const $ = (id) => document.getElementById(id);

function escapar(texto) {
  return String(texto)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

/* Normalización que conserva la longitud del texto: cada carácter se sustituye
 * por su forma base en minúscula. Es indispensable para que las posiciones
 * calculadas en la búsqueda coincidan con las del documento original. */
function aplanar(texto) {
  return Array.from(texto)
    .map((c) => (c.normalize('NFD')[0] || c).toLowerCase())
    .join('');
}

let temporizadorNotificacion = null;
function notificar(mensaje, tipo = '') {
  const caja = $('notificacion');
  caja.textContent = mensaje;
  caja.className = `notificacion visible ${tipo}`;
  clearTimeout(temporizadorNotificacion);
  temporizadorNotificacion = setTimeout(() => {
    caja.className = 'notificacion';
  }, tipo === 'error' ? 9000 : 5000);
}

async function pedir(url, opciones = {}) {
  const respuesta = await fetch(url, opciones);
  if (!respuesta.ok) {
    let detalle = `Error ${respuesta.status}`;
    try {
      const cuerpo = await respuesta.json();
      if (cuerpo && cuerpo.detail) {
        detalle = Array.isArray(cuerpo.detail)
          ? cuerpo.detail.map((d) => d.msg || d).join('; ')
          : cuerpo.detail;
      }
    } catch (_) { /* la respuesta no era JSON */ }
    throw new Error(detalle);
  }
  return respuesta;
}

async function pedirJson(url, opciones) {
  return (await pedir(url, opciones)).json();
}

async function descargar(url, opciones, nombrePorDefecto) {
  const respuesta = await pedir(url, opciones);
  const blob = await respuesta.blob();
  const cabecera = respuesta.headers.get('Content-Disposition') || '';
  let nombre = nombrePorDefecto;
  const coincidencia = /filename\*=UTF-8''([^;]+)/i.exec(cabecera);
  if (coincidencia) {
    try { nombre = decodeURIComponent(coincidencia[1]); } catch (_) { /* se conserva el nombre por defecto */ }
  }
  const enlace = document.createElement('a');
  enlace.href = URL.createObjectURL(blob);
  enlace.download = nombre;
  document.body.appendChild(enlace);
  enlace.click();
  document.body.removeChild(enlace);
  setTimeout(() => URL.revokeObjectURL(enlace.href), 1000);
}

function opcionesCategoria(selector, incluirTodas = false) {
  const elemento = typeof selector === 'string' ? $(selector) : selector;
  if (!elemento) return;
  const partes = incluirTodas ? ['<option value="">Todas las categorías</option>'] : [];
  CATEGORIAS.forEach((c) => partes.push(`<option value="${c.clave}">${escapar(c.nombre)}</option>`));
  elemento.innerHTML = partes.join('');
}

/* ------------------------------------------------------------------ */
/* Navegación entre etapas                                             */
/* ------------------------------------------------------------------ */

const PANELES = {
  1: ['panelCarga'],
  2: ['panelConfiguracion'],
  3: ['areaTrabajo', 'filaEstadisticas'],
  4: ['panelExportacion'],
  5: ['panelReversion']
};

function irAPaso(numero) {
  document.querySelectorAll('.paso').forEach((boton) => {
    boton.classList.toggle('activo', Number(boton.dataset.paso) === numero);
  });

  const visibles = new Set(PANELES[numero] || []);
  Object.values(PANELES).flat().forEach((id) => {
    const panel = $(id);
    if (!panel) return;
    if (id === 'filaEstadisticas') {
      panel.hidden = !visibles.has(id) || !estado.detecciones.length;
    } else {
      panel.hidden = !visibles.has(id);
    }
  });

  if (numero === 4) prepararEditor();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

/* ------------------------------------------------------------------ */
/* Paso 1: carga del documento                                         */
/* ------------------------------------------------------------------ */

async function cargarArchivo(archivo) {
  if (!archivo) return;

  const zona = $('zonaCarga');
  zona.classList.add('activa');
  $('infoArchivo').innerHTML = 'Leyendo el documento…';

  const formulario = new FormData();
  formulario.append('file', archivo);

  try {
    const datos = await pedirJson('/api/cargar', { method: 'POST', body: formulario });

    estado.sessionId = datos.session_id;
    estado.nombreDocumento = datos.doc_name;
    estado.detecciones = [];
    estado.grupos = [];

    let informe =
      `<strong>${escapar(archivo.name)}</strong> — ` +
      `${datos.char_count.toLocaleString('es-CL')} caracteres, ` +
      `${datos.paragraph_count.toLocaleString('es-CL')} párrafos.`;
    if (datos.aviso) {
      informe += `<div class="aviso aviso-alerta" style="margin-top:.6rem"><strong>Advertencia</strong>${escapar(datos.aviso)}</div>`;
    }
    $('infoArchivo').innerHTML = informe;

    $('botonAnalizar').disabled = false;
    notificar('Documento cargado. Configure el análisis y continúe.', 'exito');
    irAPaso(2);
  } catch (error) {
    $('infoArchivo').innerHTML =
      `<div class="aviso aviso-error"><strong>No se pudo cargar el archivo</strong>${escapar(error.message)}</div>`;
    notificar(error.message, 'error');
  } finally {
    zona.classList.remove('activa');
  }
}

/* ------------------------------------------------------------------ */
/* Paso 2: análisis                                                    */
/* ------------------------------------------------------------------ */

function categoriasSeleccionadas() {
  return Array.from(document.querySelectorAll('#casillasCategorias input:checked'))
    .map((casilla) => casilla.dataset.cat);
}

async function analizar() {
  if (!estado.sessionId || estado.analizando) return;

  const categorias = categoriasSeleccionadas();
  if (!categorias.length) {
    notificar('Seleccione al menos una categoría para detectar.', 'error');
    return;
  }

  estado.analizando = true;
  $('cargadorAnalisis').classList.add('visible');
  $('botonAnalizar').disabled = true;
  $('botonDetener').hidden = false;

  try {
    const datos = await pedirJson('/api/analizar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: estado.sessionId,
        label_mode: document.querySelector('input[name="modo"]:checked').value,
        sensibilidad: $('selectorSensibilidad').value,
        enabled_categories: categorias
      })
    });

    estado.detecciones = datos.detections;
    estado.grupos = datos.clusters;
    estado.estadisticas = datos.stats;

    await cargarVistaPrevia();
    dibujarEstadisticas();
    dibujarDetecciones();
    dibujarGrupos();

    $('areaTrabajo').hidden = false;
    irAPaso(3);

    const total = datos.stats.TOTAL || 0;
    notificar(
      total
        ? `Se detectaron ${total} datos distintos. Revíselos antes de exportar.`
        : 'No se detectaron datos personales. Revise la vista previa y agregue los que falten a mano.',
      total ? 'exito' : ''
    );
  } catch (error) {
    notificar(error.message, 'error');
  } finally {
    estado.analizando = false;
    $('cargadorAnalisis').classList.remove('visible');
    $('botonAnalizar').disabled = false;
    $('botonDetener').hidden = true;
  }
}

async function detenerAnalisis() {
  if (!estado.sessionId) return;
  try {
    await pedir('/api/analizar/cancelar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: estado.sessionId })
    });
    notificar('Se solicitó la interrupción del análisis.');
  } catch (error) {
    notificar(error.message, 'error');
  }
}

/* ------------------------------------------------------------------ */
/* Paso 3: vista previa y revisión                                     */
/* ------------------------------------------------------------------ */

async function cargarVistaPrevia() {
  const datos = await pedirJson(
    `/api/vista-previa?session_id=${encodeURIComponent(estado.sessionId)}&modo=original`
  );
  estado.textoOriginal = datos.texto;
  estado.resaltados = datos.resaltados || [];
  dibujarVista();
}

function dibujarVista() {
  const contenedor = $('vistaDocumento');

  if (estado.modoVista === 'anonimizado') {
    contenedor.innerHTML = escapar(estado.textoAnonimizado || '');
    return;
  }

  const texto = estado.textoOriginal;
  const rangos = [...estado.resaltados].sort((a, b) => a.start - b.start);

  const partes = [];
  let cursor = 0;
  rangos.forEach((rango) => {
    if (rango.start < cursor) return;
    partes.push(escapar(texto.slice(cursor, rango.start)));
    const color = (MAPA_CATEGORIAS[rango.cat] || {}).color || '#666';
    const nombre = (MAPA_CATEGORIAS[rango.cat] || {}).nombre || rango.cat;
    partes.push(
      `<span class="resaltado" style="--c:${color}" title="${escapar(nombre)} → ${escapar(rango.placeholder)}">` +
      `${escapar(texto.slice(rango.start, rango.end))}</span>`
    );
    cursor = rango.end;
  });
  partes.push(escapar(texto.slice(cursor)));

  contenedor.innerHTML = partes.join('');
}

function dibujarEstadisticas() {
  const fila = $('filaEstadisticas');
  const tarjetas = [
    `<div class="estadistica" style="--c:var(--azul-profundo)">
       <div class="estadistica-valor">${estado.estadisticas.TOTAL || 0}</div>
       <div class="estadistica-nombre">Datos distintos</div></div>`,
    `<div class="estadistica" style="--c:var(--verde)">
       <div class="estadistica-valor">${estado.estadisticas.OCURRENCIAS || 0}</div>
       <div class="estadistica-nombre">Ocurrencias</div></div>`
  ];

  CATEGORIAS.forEach((categoria) => {
    const cantidad = estado.estadisticas[categoria.clave] || 0;
    if (!cantidad) return;
    tarjetas.push(
      `<div class="estadistica" style="--c:${categoria.color}">
         <div class="estadistica-valor">${cantidad}</div>
         <div class="estadistica-nombre">${escapar(categoria.nombre)}</div></div>`
    );
  });

  fila.innerHTML = tarjetas.join('');
  fila.hidden = false;
}

function deteccionesVisibles() {
  const filtro = aplanar($('filtroDetecciones').value.trim());
  const categoria = $('filtroCategoria').value;
  return estado.detecciones.filter((deteccion) => {
    if (categoria && deteccion.cat !== categoria) return false;
    if (!filtro) return true;
    return (
      aplanar(deteccion.original).includes(filtro) ||
      aplanar(deteccion.placeholder).includes(filtro)
    );
  });
}

function dibujarDetecciones() {
  const cuerpo = $('cuerpoDetecciones');
  const visibles = deteccionesVisibles();

  $('contadorDetecciones').textContent = estado.detecciones.length;

  if (!visibles.length) {
    cuerpo.innerHTML =
      '<tr><td colspan="6" class="sin-resultados">No hay detecciones que mostrar. ' +
      'Puede agregar datos a mano seleccionándolos en la vista previa.</td></tr>';
    return;
  }

  cuerpo.innerHTML = visibles.map((deteccion) => {
    const categoria = MAPA_CATEGORIAS[deteccion.cat] || { color: '#666', nombre: deteccion.cat };
    const opciones = CATEGORIAS.map((c) =>
      `<option value="${c.clave}" ${c.clave === deteccion.cat ? 'selected' : ''}>${escapar(c.nombre)}</option>`
    ).join('');

    return `
      <tr class="${deteccion.enabled ? '' : 'desactivada'}" data-id="${deteccion.id}">
        <td><input type="checkbox" data-accion="alternar" ${deteccion.enabled ? 'checked' : ''}
             title="Incluir en la exportación"></td>
        <td>
          <span class="punto" style="--c:${categoria.color}"></span>
          <select class="campo" data-accion="tipo">${opciones}</select>
        </td>
        <td class="celda-original">${escapar(deteccion.original)}
          ${deteccion.user_added ? '<span class="fuente">agregado a mano</span>' : ''}</td>
        <td><input class="campo" data-accion="sustitucion" value="${escapar(deteccion.placeholder)}"></td>
        <td>${deteccion.positions.length}</td>
        <td><button class="boton-quitar" data-accion="quitar" title="Quitar esta detección">✕</button></td>
      </tr>`;
  }).join('');
}

function dibujarGrupos() {
  const lista = $('listaGrupos');
  $('contadorGrupos').textContent = estado.grupos.length;

  if (!estado.grupos.length) {
    lista.innerHTML =
      '<p class="sin-resultados">No se sugirieron identidades. Ocurre cuando ' +
      'cada dato aparece siempre escrito de la misma forma.</p>';
    return;
  }

  lista.innerHTML = estado.grupos.map((grupo) => {
    const categoria = MAPA_CATEGORIAS[grupo.cat] || { nombre: grupo.cat, color: '#666' };
    const confirmado = grupo.status === 'confirmado';
    const variantes = grupo.surfaces.map((superficie) =>
      `<span class="variante">${escapar(superficie)}
         <button data-accion="quitar-variante" data-grupo="${escapar(grupo.cluster_id)}"
                 data-variante="${escapar(superficie)}" title="Separar esta variante del grupo">✕</button>
       </span>`
    ).join('');

    return `
      <div class="grupo ${confirmado ? 'grupo-confirmado' : ''}">
        <div class="grupo-cabecera">
          <span class="grupo-titulo">
            <span class="punto" style="--c:${categoria.color}"></span> ${escapar(categoria.nombre)}
            ${confirmado ? `— ${escapar(grupo.placeholder || '')}` : ''}
          </span>
          <span class="grupo-confianza confianza-${grupo.confidence}">confianza ${grupo.confidence}</span>
        </div>
        <div class="grupo-variantes">${variantes}</div>
        ${confirmado ? '' :
          `<button class="boton boton-pequeno boton-contorno" data-accion="confirmar-grupo"
                   data-grupo="${escapar(grupo.cluster_id)}">Confirmar como una sola identidad</button>`}
      </div>`;
  }).join('');
}

/* ---------- Acciones sobre la tabla ---------- */

async function modificarDeteccion(id, cambios) {
  try {
    const datos = await pedirJson(`/api/detecciones/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: estado.sessionId, ...cambios })
    });
    estado.detecciones = datos.detecciones;
    estado.grupos = datos.grupos;
    await refrescar();
  } catch (error) {
    notificar(error.message, 'error');
    await refrescar();
  }
}

async function quitarDeteccion(id) {
  try {
    const datos = await pedirJson(
      `/api/detecciones/${id}?session_id=${encodeURIComponent(estado.sessionId)}`,
      { method: 'DELETE' }
    );
    estado.detecciones = datos.detecciones;
    estado.grupos = datos.grupos;
    await refrescar();
    notificar('Detección quitada.');
  } catch (error) {
    notificar(error.message, 'error');
  }
}

async function confirmarGrupo(clusterId) {
  try {
    const datos = await pedirJson(
      `/api/grupos/${encodeURIComponent(clusterId)}/confirmar?session_id=${encodeURIComponent(estado.sessionId)}`,
      { method: 'POST' }
    );
    estado.detecciones = datos.detections;
    estado.grupos = estado.grupos.map((g) => (g.cluster_id === clusterId ? datos.cluster : g));
    await refrescar();
    notificar('Grupo confirmado: todas sus variantes comparten una sustitución.', 'exito');
  } catch (error) {
    notificar(error.message, 'error');
  }
}

async function quitarVariante(clusterId, variante) {
  try {
    const datos = await pedirJson(
      `/api/grupos/${encodeURIComponent(clusterId)}/quitar-variante?session_id=${encodeURIComponent(estado.sessionId)}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ surface: variante })
      }
    );
    estado.grupos = datos.grupos;
    estado.detecciones = datos.detecciones;
    await refrescar();
    notificar('La variante se separó del grupo.');
  } catch (error) {
    notificar(error.message, 'error');
  }
}

async function refrescar() {
  const datos = await pedirJson(
    `/api/vista-previa?session_id=${encodeURIComponent(estado.sessionId)}&modo=original`
  );
  estado.textoOriginal = datos.texto;
  estado.resaltados = datos.resaltados || [];

  const conteos = {};
  let ocurrencias = 0;
  estado.detecciones.forEach((deteccion) => {
    if (!deteccion.enabled) return;
    conteos[deteccion.cat] = (conteos[deteccion.cat] || 0) + 1;
    ocurrencias += deteccion.positions.length;
  });
  estado.estadisticas = { ...conteos, TOTAL: estado.detecciones.length, OCURRENCIAS: ocurrencias };

  dibujarVista();
  dibujarEstadisticas();
  dibujarDetecciones();
  dibujarGrupos();
}

/* ---------- Selección manual sobre la vista previa ---------- */

function desplazamientoEnVista(nodo, desplazamiento) {
  const contenedor = $('vistaDocumento');
  const recorrido = document.createTreeWalker(contenedor, NodeFilter.SHOW_TEXT);
  let total = 0;
  let actual = recorrido.nextNode();
  while (actual) {
    if (actual === nodo) return total + desplazamiento;
    total += actual.textContent.length;
    actual = recorrido.nextNode();
  }
  return -1;
}

function manejarSeleccion() {
  if (estado.modoVista !== 'original') return;

  const seleccion = window.getSelection();
  if (!seleccion || seleccion.isCollapsed) {
    $('barraSeleccion').hidden = true;
    estado.seleccion = null;
    return;
  }

  const rango = seleccion.getRangeAt(0);
  const contenedor = $('vistaDocumento');
  if (!contenedor.contains(rango.commonAncestorContainer)) return;

  const inicio = desplazamientoEnVista(rango.startContainer, rango.startOffset);
  const fin = desplazamientoEnVista(rango.endContainer, rango.endOffset);
  const texto = seleccion.toString().trim();

  if (inicio < 0 || fin <= inicio || texto.length < 2) {
    $('barraSeleccion').hidden = true;
    estado.seleccion = null;
    return;
  }

  estado.seleccion = { inicio, fin, texto };
  $('fragmentoSeleccion').textContent = texto.length > 40 ? `${texto.slice(0, 40)}…` : texto;
  $('barraSeleccion').hidden = false;
}

async function anonimizarSeleccion() {
  if (!estado.seleccion) return;
  const { inicio, fin, texto } = estado.seleccion;

  try {
    const datos = await pedirJson('/api/detecciones/manual', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: estado.sessionId,
        cat: $('categoriaSeleccion').value,
        start: inicio,
        end: fin,
        original: texto
      })
    });
    estado.detecciones = datos.detecciones;
    await refrescar();
    $('barraSeleccion').hidden = true;
    estado.seleccion = null;
    window.getSelection().removeAllRanges();
    notificar('Dato agregado. Se anonimizarán todas sus apariciones.', 'exito');
  } catch (error) {
    notificar(error.message, 'error');
  }
}

/* ---------- Buscador ---------- */

function buscarEnDocumento() {
  const consulta = $('campoBusqueda').value.trim();
  const conteo = $('conteoBusqueda');

  if (consulta.length < 2) {
    estado.coincidencias = [];
    conteo.textContent = '0 coincidencias';
    $('anonimizarBusqueda').disabled = true;
    dibujarVista();
    return;
  }

  const textoPlano = aplanar(estado.textoOriginal);
  const consultaPlana = aplanar(consulta);
  const coincidencias = [];

  let desde = textoPlano.indexOf(consultaPlana);
  while (desde !== -1) {
    coincidencias.push({ start: desde, end: desde + consultaPlana.length });
    desde = textoPlano.indexOf(consultaPlana, desde + consultaPlana.length);
  }

  estado.coincidencias = coincidencias;
  conteo.textContent = coincidencias.length === 1
    ? '1 coincidencia'
    : `${coincidencias.length} coincidencias`;
  $('anonimizarBusqueda').disabled = coincidencias.length === 0;

  if (estado.modoVista === 'original') resaltarCoincidencias();
}

function resaltarCoincidencias() {
  const contenedor = $('vistaDocumento');
  const texto = estado.textoOriginal;
  const partes = [];
  let cursor = 0;

  estado.coincidencias.forEach((coincidencia) => {
    partes.push(escapar(texto.slice(cursor, coincidencia.start)));
    partes.push(`<mark class="marca-busqueda">${escapar(texto.slice(coincidencia.start, coincidencia.end))}</mark>`);
    cursor = coincidencia.end;
  });
  partes.push(escapar(texto.slice(cursor)));
  contenedor.innerHTML = partes.join('');
}

async function anonimizarCoincidencias() {
  if (!estado.coincidencias.length) return;
  const consulta = $('campoBusqueda').value.trim();

  try {
    const datos = await pedirJson('/api/detecciones/buscar-y-anonimizar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: estado.sessionId,
        cat: $('categoriaBusqueda').value,
        original: consulta,
        positions: estado.coincidencias.map((c) => ({ start: c.start, end: c.end, raw: '' }))
      })
    });
    estado.detecciones = datos.detecciones;
    estado.coincidencias = [];
    $('campoBusqueda').value = '';
    $('conteoBusqueda').textContent = '0 coincidencias';
    $('anonimizarBusqueda').disabled = true;
    await refrescar();
    notificar(`Se anonimizaron todas las apariciones de «${consulta}».`, 'exito');
  } catch (error) {
    notificar(error.message, 'error');
  }
}

/* ------------------------------------------------------------------ */
/* Paso 4: exportación                                                 */
/* ------------------------------------------------------------------ */

async function prepararEditor() {
  if (!estado.sessionId || !estado.detecciones.length) return;
  try {
    const datos = await pedirJson('/api/exportar/vista-previa', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: estado.sessionId })
    });
    estado.textoAnonimizado = datos.text;
    $('editorTexto').value = datos.text;
  } catch (error) {
    notificar(error.message, 'error');
  }
}

function opcionesFormato() {
  return {
    font_name: $('fmtFuente').value,
    font_size_pt: Number($('fmtTamano').value),
    line_spacing: Number($('fmtInterlineado').value),
    margin_cm: Number($('fmtMargen').value),
    margin_top_bottom_cm: 2.5,
    alignment: $('fmtAlineacion').value
  };
}

async function exportar(formato) {
  if (!estado.sessionId) return;
  const cuerpo = {
    session_id: estado.sessionId,
    text: $('editorTexto').value,
    format: opcionesFormato()
  };

  try {
    await descargar(
      `/api/exportar/${formato}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cuerpo)
      },
      `${estado.nombreDocumento}_anonimizado.${formato}`
    );
    notificar('Documento exportado. Revíselo una vez más antes de compartirlo.', 'exito');
  } catch (error) {
    notificar(error.message, 'error');
  }
}

async function exportarEquivalencias() {
  try {
    await descargar(
      '/api/exportar/csv',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: estado.sessionId })
      },
      `${estado.nombreDocumento}_equivalencias.csv`
    );
    notificar('Tabla descargada. Recuerde que contiene los datos originales sin cifrar.', '');
  } catch (error) {
    notificar(error.message, 'error');
  }
}

/* ------------------------------------------------------------------ */
/* Paso 5: reversibilidad                                              */
/* ------------------------------------------------------------------ */

async function generarMapa() {
  const frase = $('fraseMapa').value;
  const confirmacion = $('fraseMapaConfirmar').value;
  const informe = $('estadoMapa');

  if (frase !== confirmacion) {
    notificar('Las dos frases de paso no coinciden.', 'error');
    return;
  }
  if (frase.length < 12) {
    notificar('La frase de paso debe tener al menos 12 caracteres.', 'error');
    return;
  }
  if (!estado.sessionId) {
    notificar('Cargue y analice un documento antes de generar el mapa.', 'error');
    return;
  }

  try {
    await descargar(
      '/api/reversion/mapa',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: estado.sessionId,
          passphrase: frase,
          nota: $('notaMapa').value
        })
      },
      `${estado.nombreDocumento}.anonmap`
    );

    // La frase se borra de la interfaz apenas se usa: no debe quedar visible
    // ni recuperable desde el navegador.
    $('fraseMapa').value = '';
    $('fraseMapaConfirmar').value = '';
    informe.textContent =
      'Mapa descargado. Guárdelo en un lugar distinto del documento anonimizado. ' +
      'La frase de paso no quedó registrada en ninguna parte.';
    notificar('Mapa de reversión descargado y cifrado.', 'exito');
  } catch (error) {
    informe.textContent = '';
    notificar(error.message, 'error');
  }
}

async function revertir() {
  const archivoMapa = $('archivoMapa').files[0];
  const archivoDocumento = $('archivoAnonimizado').files[0];
  const textoPegado = $('textoAnonimizado').value.trim();
  const frase = $('fraseRevertir').value;

  if (!archivoMapa) { notificar('Adjunte el archivo del mapa.', 'error'); return; }
  if (!frase) { notificar('Escriba la frase de paso del mapa.', 'error'); return; }
  if (!archivoDocumento && !textoPegado) {
    notificar('Adjunte el documento anonimizado o pegue su texto.', 'error');
    return;
  }

  const formulario = new FormData();
  formulario.append('mapa', archivoMapa);
  formulario.append('passphrase', frase);
  formulario.append('texto', textoPegado);
  if (archivoDocumento) formulario.append('documento', archivoDocumento);

  try {
    const datos = await pedirJson('/api/reversion/revertir', { method: 'POST', body: formulario });

    $('textoRevertido').value = datos.texto;
    $('resultadoReversion').hidden = false;
    $('fraseRevertir').value = '';

    let resumen = `Se restituyeron ${datos.reemplazos} ocurrencias.`;
    if (datos.sin_coincidencia.length) {
      resumen +=
        ` Atención: ${datos.sin_coincidencia.length} etiquetas del mapa no aparecen ` +
        'en el documento. Verifique que el mapa corresponda a este documento.';
    }
    $('resumenReversion').textContent = resumen;
    notificar('Documento restituido.', 'exito');
  } catch (error) {
    notificar(error.message, 'error');
  }
}

async function descargarRevertido(formato) {
  const texto = $('textoRevertido').value;
  if (!texto) return;

  const formulario = new FormData();
  formulario.append('formato', formato);
  formulario.append('nombre', estado.nombreDocumento || 'documento');
  formulario.append('texto', texto);

  try {
    await descargar('/api/reversion/descargar', { method: 'POST', body: formulario },
      `documento_restituido.${formato}`);
  } catch (error) {
    notificar(error.message, 'error');
  }
}

/* ------------------------------------------------------------------ */
/* Reinicio                                                            */
/* ------------------------------------------------------------------ */

async function reiniciar() {
  if (!confirm('¿Desea empezar de nuevo? Se descartará el documento cargado y todas las detecciones.')) {
    return;
  }
  if (estado.sessionId) {
    try {
      await pedir(`/api/sesion/${encodeURIComponent(estado.sessionId)}`, { method: 'DELETE' });
    } catch (_) { /* la sesión ya podía no existir */ }
  }
  window.location.reload();
}

/* ------------------------------------------------------------------ */
/* Conexión de eventos                                                 */
/* ------------------------------------------------------------------ */

function conectarEventos() {
  // Carga
  const zona = $('zonaCarga');
  zona.addEventListener('click', () => $('entradaArchivo').click());
  zona.addEventListener('keydown', (evento) => {
    if (evento.key === 'Enter' || evento.key === ' ') { evento.preventDefault(); $('entradaArchivo').click(); }
  });
  ['dragenter', 'dragover'].forEach((nombre) =>
    zona.addEventListener(nombre, (evento) => { evento.preventDefault(); zona.classList.add('activa'); }));
  ['dragleave', 'drop'].forEach((nombre) =>
    zona.addEventListener(nombre, (evento) => { evento.preventDefault(); zona.classList.remove('activa'); }));
  zona.addEventListener('drop', (evento) => cargarArchivo(evento.dataTransfer.files[0]));
  $('entradaArchivo').addEventListener('change', (evento) => cargarArchivo(evento.target.files[0]));

  // Configuración
  document.querySelectorAll('input[name="modo"]').forEach((radio) => {
    radio.addEventListener('change', () => {
      document.querySelectorAll('.opcion-radio').forEach((opcion) =>
        opcion.classList.toggle('seleccionada', opcion.querySelector('input').checked));
    });
  });
  $('botonAnalizar').addEventListener('click', analizar);
  $('botonDetener').addEventListener('click', detenerAnalisis);

  // Navegación
  document.querySelectorAll('.paso').forEach((boton) => {
    boton.addEventListener('click', () => {
      const paso = Number(boton.dataset.paso);
      if (paso >= 3 && !estado.detecciones.length && paso !== 5) {
        notificar('Primero cargue y analice un documento.', 'error');
        return;
      }
      irAPaso(paso);
    });
  });

  // Vista previa
  $('verOriginal').addEventListener('click', () => {
    estado.modoVista = 'original';
    $('verOriginal').classList.add('activo');
    $('verAnonimizado').classList.remove('activo');
    dibujarVista();
  });
  $('verAnonimizado').addEventListener('click', async () => {
    estado.modoVista = 'anonimizado';
    $('verAnonimizado').classList.add('activo');
    $('verOriginal').classList.remove('activo');
    $('barraSeleccion').hidden = true;
    await prepararEditor();
    dibujarVista();
  });

  $('vistaDocumento').addEventListener('mouseup', () => setTimeout(manejarSeleccion, 10));
  $('anonimizarSeleccion').addEventListener('click', anonimizarSeleccion);
  $('cancelarSeleccion').addEventListener('click', () => {
    $('barraSeleccion').hidden = true;
    estado.seleccion = null;
    window.getSelection().removeAllRanges();
  });

  // Buscador
  $('abrirBuscador').addEventListener('click', () => {
    const barra = $('barraBusqueda');
    barra.hidden = !barra.hidden;
    if (!barra.hidden) $('campoBusqueda').focus();
  });
  $('cerrarBuscador').addEventListener('click', () => {
    $('barraBusqueda').hidden = true;
    $('campoBusqueda').value = '';
    estado.coincidencias = [];
    dibujarVista();
  });
  $('campoBusqueda').addEventListener('input', buscarEnDocumento);
  $('anonimizarBusqueda').addEventListener('click', anonimizarCoincidencias);

  // Tabla de detecciones
  $('cuerpoDetecciones').addEventListener('change', (evento) => {
    const fila = evento.target.closest('tr');
    if (!fila) return;
    const id = Number(fila.dataset.id);
    const accion = evento.target.dataset.accion;
    if (accion === 'alternar') modificarDeteccion(id, { enabled: evento.target.checked });
    if (accion === 'tipo') modificarDeteccion(id, { cat: evento.target.value });
    if (accion === 'sustitucion') modificarDeteccion(id, { placeholder: evento.target.value });
  });
  $('cuerpoDetecciones').addEventListener('click', (evento) => {
    if (evento.target.dataset.accion !== 'quitar') return;
    const fila = evento.target.closest('tr');
    if (fila) quitarDeteccion(Number(fila.dataset.id));
  });
  $('filtroDetecciones').addEventListener('input', dibujarDetecciones);
  $('filtroCategoria').addEventListener('change', dibujarDetecciones);

  // Pestañas
  document.querySelectorAll('.pestana').forEach((pestana) => {
    pestana.addEventListener('click', () => {
      document.querySelectorAll('.pestana').forEach((p) => p.classList.remove('activa'));
      pestana.classList.add('activa');
      const destino = pestana.dataset.pestana;
      $('panelDetecciones').hidden = destino !== 'detecciones';
      $('panelDetecciones').classList.toggle('activo', destino === 'detecciones');
      $('panelGrupos').hidden = destino !== 'grupos';
      $('panelGrupos').classList.toggle('activo', destino === 'grupos');
    });
  });

  // Grupos
  $('listaGrupos').addEventListener('click', (evento) => {
    const accion = evento.target.dataset.accion;
    if (accion === 'confirmar-grupo') confirmarGrupo(evento.target.dataset.grupo);
    if (accion === 'quitar-variante') {
      quitarVariante(evento.target.dataset.grupo, evento.target.dataset.variante);
    }
  });

  // Exportación
  $('exportarDocx').addEventListener('click', () => exportar('docx'));
  $('exportarPdf').addEventListener('click', () => exportar('pdf'));
  $('exportarTxt').addEventListener('click', () => exportar('txt'));
  $('exportarCsv').addEventListener('click', exportarEquivalencias);
  $('reiniciar').addEventListener('click', reiniciar);

  // Reversibilidad
  $('generarMapa').addEventListener('click', generarMapa);
  $('botonRevertir').addEventListener('click', revertir);
  $('descargarRevertidoDocx').addEventListener('click', () => descargarRevertido('docx'));
  $('descargarRevertidoTxt').addEventListener('click', () => descargarRevertido('txt'));
}

/* ------------------------------------------------------------------ */
/* Arranque                                                            */
/* ------------------------------------------------------------------ */

async function comprobarEstado() {
  try {
    const datos = await pedirJson('/estado');
    const capa = (datos.capas_lenguaje_natural || {}).spacy || {};
    const insignia = $('insigniaEstado');

    if (capa.disponible) {
      insignia.textContent = 'Motor local activo · con modelo de lenguaje';
      insignia.className = 'insignia insignia-ok';
    } else {
      insignia.textContent = 'Motor local activo · solo reglas';
      insignia.className = 'insignia insignia-local';
      insignia.title =
        'La capa opcional de lenguaje natural no está instalada. La detección ' +
        'por reglas funciona igual; instalarla mejora el reconocimiento de ' +
        'nombres poco frecuentes.';
    }
    $('pieVersion').textContent = `${datos.aplicacion} versión ${datos.version}`;
  } catch (_) {
    const insignia = $('insigniaEstado');
    insignia.textContent = 'No se pudo contactar al motor local';
    insignia.className = 'insignia insignia-alerta';
  }
}

document.addEventListener('DOMContentLoaded', () => {
  opcionesCategoria('categoriaSeleccion');
  opcionesCategoria('categoriaBusqueda');
  opcionesCategoria('filtroCategoria', true);
  conectarEventos();
  comprobarEstado();
});
