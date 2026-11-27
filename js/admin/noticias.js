/* =========================================================
   REFUGIA — Administración de noticias (CRUD completo)
   ---------------------------------------------------------
     Listar      → GET    /api/noticias?incluir_ocultas=true
     Crear       → POST   /api/noticias
     Editar      → PUT    /api/noticias/<id>
     Aprobar     → PUT    /api/noticias/<id>  {"publicada": true}
     Eliminar    → DELETE /api/noticias/<id>
     Imagen      → POST   /api/noticias/imagen  (multipart)
   Requiere ../js/api.js y que la API esté corriendo:  python main.py
   ========================================================= */
(() => {
  "use strict";

  const RUTA = "/api/noticias";
  const CAMPOS = ["titulo", "fuente", "fecha_publicacion", "enlace", "verificacion", "imagen_alt", "contenido"];

  const $ = (selector) => document.querySelector(selector);
  const formulario = $("#formulario-noticia");
  const tituloFormulario = $("#titulo-formulario");
  const aviso = $("#aviso");
  const btnAprobar = $("#btn-aprobar");
  const btnBorrador = $("#btn-borrador");
  const btnEliminar = $("#btn-eliminar");
  const btnCancelar = $("#btn-cancelar");
  const archivoImagen = $("#archivo-imagen");
  const vistaImagen = $("#imagen-vista");
  const imagenPrevia = $("#imagen-previa");
  const btnQuitarImagen = $("#btn-quitar-imagen");
  const listado = $("#listado");
  const listadoEstado = $("#listado-estado");
  const filtroEstado = $("#filtro-estado");
  const dialogo = $("#dialogo-eliminar");

  let noticias = [];          // las del listado
  let editando = null;        // noticia que se está editando (null = creando una nueva)
  let imagenActual = null;    // ruta guardada en la base de datos ("img/…")
  let urlVistaPrevia = null;  // vista previa local del archivo elegido

  // ---------------- Utilidades ----------------
  function crear(etiqueta, clase, texto) {
    const elemento = document.createElement(etiqueta);
    if (clase) elemento.className = clase;
    if (texto !== undefined) elemento.textContent = texto;
    return elemento;
  }

  function mostrarAviso(texto, tipo = "exito") {
    aviso.textContent = texto;
    aviso.className = `aviso aviso--${tipo}`;
    aviso.hidden = false;
    aviso.setAttribute("role", tipo === "error" ? "alert" : "status");
  }

  function hoy() {
    const ahora = new Date();
    return new Date(ahora.getTime() - ahora.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
  }

  function ocupado(si) {
    formulario.querySelectorAll("button").forEach((boton) => (boton.disabled = si));
    formulario.setAttribute("aria-busy", String(si));
  }

  // ---------------- Errores por campo ----------------
  function limpiarErrores() {
    formulario.querySelectorAll(".formulario__error").forEach((p) => (p.textContent = ""));
    formulario.querySelectorAll("[aria-invalid]").forEach((campo) => campo.removeAttribute("aria-invalid"));
  }

  function mostrarErrores(detalles) {
    let primero = null;
    for (const [campo, mensajes] of Object.entries(detalles || {})) {
      const parrafo = $(`#error-${campo}`);
      const entrada = campo === "imagen" ? archivoImagen : $(`#${campo}`);
      const texto = Array.isArray(mensajes) ? mensajes.join(" ") : Object.values(mensajes).flat().join(" ");
      if (parrafo) parrafo.textContent = texto;
      if (entrada) {
        entrada.setAttribute("aria-invalid", "true");
        primero ??= entrada;
      }
    }
    primero?.focus();
  }

  // Revisión rápida en el navegador; la API vuelve a validar todo
  function validarEnNavegador(datos) {
    const errores = {};
    if (datos.titulo.length < 5) errores.titulo = ["Escribe un título de al menos 5 caracteres."];
    if (datos.fuente.length < 2) errores.fuente = ["Escribe la fuente de la noticia."];
    if (datos.contenido.length < 10) errores.contenido = ["Escribe el contenido (al menos 10 caracteres)."];
    if (datos.enlace && !/^https?:\/\/\S+$/i.test(datos.enlace)) errores.enlace = ["Debe empezar por http:// o https://."];
    const hayImagen = archivoImagen.files.length > 0 || imagenActual;
    if (hayImagen && !datos.imagen_alt) errores.imagen_alt = ["Describe la imagen: es obligatorio cuando hay imagen."];
    return errores;
  }

  // ---------------- Imagen ----------------
  function mostrarVistaPrevia(src) {
    if (src) {
      imagenPrevia.src = src;
      vistaImagen.hidden = false;
    } else {
      imagenPrevia.src = "data:,";
      vistaImagen.hidden = true;
    }
  }

  function liberarVistaLocal() {
    if (urlVistaPrevia) URL.revokeObjectURL(urlVistaPrevia);
    urlVistaPrevia = null;
  }

  archivoImagen.addEventListener("change", () => {
    liberarVistaLocal();
    const archivo = archivoImagen.files[0];
    $("#error-imagen").textContent = "";
    if (!archivo) {
      mostrarVistaPrevia(imagenActual ? RefugiaAPI.recurso(imagenActual) : "");
      return;
    }
    if (archivo.size > 5 * 1024 * 1024) {
      $("#error-imagen").textContent = "La imagen pesa más de 5 MB.";
      archivoImagen.value = "";
      return;
    }
    urlVistaPrevia = URL.createObjectURL(archivo);
    mostrarVistaPrevia(urlVistaPrevia);
  });

  btnQuitarImagen.addEventListener("click", () => {
    archivoImagen.value = "";
    liberarVistaLocal();
    imagenActual = null;
    mostrarVistaPrevia("");
    archivoImagen.focus();
  });

  // ---------------- Formulario: crear y editar ----------------
  function modoCrear() {
    editando = null;
    formulario.reset();
    limpiarErrores();
    liberarVistaLocal();
    imagenActual = null;
    mostrarVistaPrevia("");
    $("#fecha_publicacion").value = hoy();
    tituloFormulario.textContent = "Nueva noticia";
    btnAprobar.textContent = "Aprobar";
    btnBorrador.textContent = "Guardar borrador";
    btnEliminar.hidden = true;
    btnCancelar.hidden = true;
  }

  function modoEditar(noticia) {
    modoCrear();
    editando = noticia;
    for (const campo of CAMPOS) $(`#${campo}`).value = noticia[campo] ?? "";
    $("#destacada").checked = noticia.destacada;
    imagenActual = noticia.imagen;
    mostrarVistaPrevia(imagenActual ? RefugiaAPI.recurso(imagenActual) : "");

    tituloFormulario.textContent = `Editando: ${noticia.titulo}`;
    btnAprobar.textContent = noticia.publicada ? "Guardar cambios" : "Aprobar";
    btnBorrador.textContent = noticia.publicada ? "Pasar a borrador" : "Guardar borrador";
    btnEliminar.hidden = false;
    btnCancelar.hidden = false;
    formulario.scrollIntoView({ behavior: "smooth", block: "start" });
    $("#titulo").focus({ preventScroll: true });
  }

  function leerFormulario() {
    const datos = {};
    for (const campo of CAMPOS) datos[campo] = $(`#${campo}`).value.trim();
    datos.destacada = $("#destacada").checked;
    if (!datos.fecha_publicacion) delete datos.fecha_publicacion; // la API pone la de hoy
    return datos;
  }

  formulario.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    limpiarErrores();
    const publicar = evento.submitter?.value !== "borrador";
    const datos = leerFormulario();
    datos.publicada = publicar;

    const errores = validarEnNavegador(datos);
    if (Object.keys(errores).length) {
      mostrarErrores(errores);
      mostrarAviso("Revisa los campos marcados.", "error");
      return;
    }

    ocupado(true);
    try {
      // 1. Si se eligió una imagen nueva, primero se sube y la API devuelve su ruta
      if (archivoImagen.files.length) {
        const subida = await RefugiaAPI.subirArchivo(`${RUTA}/imagen`, "imagen", archivoImagen.files[0]);
        imagenActual = subida.imagen;
      }
      datos.imagen = imagenActual || null;

      // 2. POST (nueva) o PUT (edición)
      const guardada = editando
        ? await RefugiaAPI.actualizar(`${RUTA}/${editando.id_noticia}`, datos)
        : await RefugiaAPI.crear(RUTA, datos);

      const accion = editando ? "actualizada" : "creada";
      mostrarAviso(`Noticia ${accion} ${guardada.publicada ? "y publicada" : "como borrador"}: "${guardada.titulo}".`);
      modoCrear();
      await cargarListado();
    } catch (error) {
      if (error.detalles) mostrarErrores(error.detalles);
      mostrarAviso(error.message, "error");
    } finally {
      ocupado(false);
    }
  });

  btnCancelar.addEventListener("click", () => {
    modoCrear();
    mostrarAviso("Edición cancelada.", "info");
  });

  btnEliminar.addEventListener("click", () => editando && pedirConfirmacion(editando));

  // ---------------- Eliminar (con confirmación) ----------------
  function pedirConfirmacion(noticia) {
    $("#dialogo-texto").textContent = `"${noticia.titulo}" se borrará de la base de datos. Esta acción no se puede deshacer.`;
    dialogo.returnValue = "";
    dialogo.dataset.id = noticia.id_noticia;
    dialogo.showModal();
  }

  dialogo.addEventListener("close", async () => {
    if (dialogo.returnValue !== "eliminar") return;
    const id = Number(dialogo.dataset.id);
    try {
      const eliminada = await RefugiaAPI.eliminar(`${RUTA}/${id}`);
      if (editando?.id_noticia === id) modoCrear();
      mostrarAviso(`Noticia eliminada: "${eliminada.titulo}".`);
      await cargarListado();
    } catch (error) {
      mostrarAviso(error.message, "error");
    }
  });

  // ---------------- Aprobar / pasar a borrador desde el listado ----------------
  async function cambiarPublicacion(noticia) {
    try {
      const guardada = await RefugiaAPI.actualizar(`${RUTA}/${noticia.id_noticia}`, { publicada: !noticia.publicada });
      mostrarAviso(guardada.publicada ? `Noticia aprobada y publicada: "${guardada.titulo}".` : `Noticia pasada a borrador: "${guardada.titulo}".`);
      await cargarListado();
    } catch (error) {
      mostrarAviso(error.message, "error");
    }
  }

  // ---------------- Listado ----------------
  function filaNoticia(noticia) {
    const fila = crear("li", "listado__fila");

    if (noticia.imagen) {
      const miniatura = crear("img", "listado__miniatura");
      miniatura.src = RefugiaAPI.recurso(noticia.imagen);
      miniatura.alt = ""; // decorativa: el título ya describe la noticia
      miniatura.loading = "lazy";
      fila.append(miniatura);
    } else {
      fila.append(crear("div", "listado__miniatura listado__miniatura--vacia"));
    }

    const info = crear("div", "listado__info");
    info.append(crear("h3", "listado__titulo", noticia.titulo));
    info.append(crear("p", "listado__meta", `${noticia.fuente} · ${RefugiaAPI.formatearFecha(noticia.fecha_publicacion)}`));
    const sellos = crear("p", "listado__sellos");
    sellos.append(crear("span", `sello ${noticia.publicada ? "sello--publicada" : "sello--borrador"}`, noticia.publicada ? "Publicada" : "Borrador"));
    sellos.append(crear("span", "sello", noticia.verificacion_nombre));
    if (noticia.destacada) sellos.append(crear("span", "sello sello--destacada", "Destacada"));
    info.append(sellos);

    const acciones = crear("div", "listado__acciones");
    const nombre = `"${noticia.titulo}"`;

    const editar = crear("button", "formulario__boton formulario__boton--secundario", "Editar");
    editar.type = "button";
    editar.setAttribute("aria-label", `Editar ${nombre}`);
    editar.addEventListener("click", () => modoEditar(noticia));

    const publicar = crear("button", `formulario__boton ${noticia.publicada ? "formulario__boton--secundario" : "formulario__boton--aprobar"}`, noticia.publicada ? "Ocultar" : "Aprobar");
    publicar.type = "button";
    // La etiqueta empieza con el texto visible (así la reconocen también los programas de control por voz)
    publicar.setAttribute("aria-label", `${noticia.publicada ? "Ocultar (pasar a borrador)" : "Aprobar y publicar"} ${nombre}`);
    publicar.addEventListener("click", () => cambiarPublicacion(noticia));

    const eliminar = crear("button", "formulario__boton formulario__boton--eliminar", "Eliminar");
    eliminar.type = "button";
    eliminar.setAttribute("aria-label", `Eliminar ${nombre}`);
    eliminar.addEventListener("click", () => pedirConfirmacion(noticia));

    acciones.append(editar, publicar, eliminar);
    fila.append(info, acciones);
    return fila;
  }

  async function cargarListado() {
    const estado = filtroEstado.value;
    const parametros = estado ? { publicada: estado, limite: 100 } : { incluir_ocultas: true, limite: 100 };
    try {
      const respuesta = await RefugiaAPI.obtener(RUTA, parametros);
      noticias = respuesta.resultados;
      listado.replaceChildren(...noticias.map(filaNoticia));
      listadoEstado.textContent = noticias.length
        ? `${respuesta.total} ${respuesta.total === 1 ? "noticia" : "noticias"}.`
        : "No hay noticias con este filtro.";
      listadoEstado.classList.remove("listado__estado--error");
    } catch (error) {
      listado.replaceChildren();
      listadoEstado.textContent = `No se pudieron cargar las noticias. ${error.message}`;
      listadoEstado.classList.add("listado__estado--error");
    }
  }

  filtroEstado.addEventListener("change", cargarListado);

  modoCrear();
  cargarListado();
})();
