/* =========================================================
   REFUGIA — Administración de voluntariados (CRUD completo)
   ---------------------------------------------------------
     Listar          → GET    /api/voluntariados?estado=todos
     Crear (Aprobar) → POST   /api/voluntariados
     Editar          → PUT    /api/voluntariados/<id>
     Cerrar/Reabrir  → PUT    /api/voluntariados/<id>  {"estado": "cerrado" | "activo"}
     Eliminar        → DELETE /api/voluntariados/<id>
     Imagen          → POST   /api/voluntariados/imagen  (multipart)
   Requiere ../js/api.js y que la API esté corriendo:  python main.py
   ========================================================= */
(() => {
  "use strict";

  const RUTA = "/api/voluntariados";
  const CAMPOS = ["actividad", "organizacion", "descripcion", "requisitos", "modalidad", "ubicacion", "enlace", "imagen_alt"];

  const $ = (selector) => document.querySelector(selector);
  const formulario = $("#formulario-voluntariado");
  const tituloFormulario = $("#titulo-formulario");
  const aviso = $("#aviso");
  const estadoActual = $("#estado-actual");
  const btnAprobar = $("#btn-aprobar");
  const btnCancelar = $("#btn-cancelar");
  const btnEstado = $("#btn-estado");
  const btnEliminar = $("#btn-eliminar");
  const campoModalidad = $("#modalidad");
  const marcaUbicacion = $("#ubicacion-obligatoria");
  const archivoImagen = $("#archivo-imagen");
  const vistaImagen = $("#imagen-vista");
  const imagenPrevia = $("#imagen-previa");
  const btnQuitarImagen = $("#btn-quitar-imagen");
  const listado = $("#listado");
  const listadoEstado = $("#listado-estado");
  const filtroEstado = $("#filtro-estado");
  const dialogo = $("#dialogo-eliminar");

  let editando = null;        // voluntariado que se está editando (null = creando uno nuevo)
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

  function ocupado(si) {
    formulario.querySelectorAll("button").forEach((boton) => (boton.disabled = si));
    formulario.setAttribute("aria-busy", String(si));
  }

  // La ubicación es obligatoria salvo en los voluntariados virtuales
  function actualizarUbicacionObligatoria() {
    const obligatoria = campoModalidad.value !== "virtual";
    marcaUbicacion.hidden = !obligatoria;
    $("#ubicacion").required = obligatoria;
  }
  campoModalidad.addEventListener("change", actualizarUbicacionObligatoria);

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
    if (datos.actividad.length < 5) errores.actividad = ["Escribe el nombre de la actividad (al menos 5 caracteres)."];
    if (datos.organizacion.length < 2) errores.organizacion = ["Escribe la organización responsable."];
    if (datos.descripcion.length < 10) errores.descripcion = ["Escribe la descripción (al menos 10 caracteres)."];
    if (datos.modalidad !== "virtual" && !datos.ubicacion) errores.ubicacion = ["Indica dónde se realiza (obligatorio si no es virtual)."];
    if (datos.enlace && !/^https?:\/\/\S+$/i.test(datos.enlace)) errores.enlace = ["Debe empezar por http:// o https://."];
    const hayImagen = archivoImagen.files.length > 0 || imagenActual;
    if (hayImagen && !datos.imagen_alt) errores.imagen_alt = ["Describe la imagen: es obligatorio cuando hay imagen."];
    return errores;
  }

  // ---------------- Imagen ----------------
  function mostrarVistaPrevia(src) {
    imagenPrevia.src = src || "data:,";
    vistaImagen.hidden = !src;
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
    actualizarUbicacionObligatoria();
    tituloFormulario.textContent = "Publicar voluntariado";
    btnAprobar.textContent = "Aprobar";
    estadoActual.hidden = true;
    btnEstado.hidden = true;
    btnEliminar.hidden = true;
  }

  function modoEditar(voluntariado) {
    modoCrear();
    editando = voluntariado;
    for (const campo of CAMPOS) $(`#${campo}`).value = voluntariado[campo] ?? "";
    actualizarUbicacionObligatoria();
    imagenActual = voluntariado.imagen;
    mostrarVistaPrevia(imagenActual ? RefugiaAPI.recurso(imagenActual) : "");

    const activo = voluntariado.estado === "activo";
    tituloFormulario.textContent = `Revisando: ${voluntariado.actividad}`;
    btnAprobar.textContent = "Guardar cambios";
    estadoActual.textContent = activo
      ? "Estado: activo (se muestra en la página de voluntariados)."
      : "Estado: cerrado (no se muestra en la página de voluntariados).";
    estadoActual.hidden = false;
    btnEstado.textContent = activo ? "Cerrar voluntariado" : "Reabrir voluntariado";
    btnEstado.hidden = false;
    btnEliminar.hidden = false;
    formulario.closest("section").scrollIntoView({ behavior: "smooth", block: "start" });
    $("#actividad").focus({ preventScroll: true });
  }

  function leerFormulario() {
    const datos = {};
    for (const campo of CAMPOS) datos[campo] = $(`#${campo}`).value.trim();
    return datos;
  }

  formulario.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    limpiarErrores();
    const datos = leerFormulario();

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

      // 2. POST (nuevo, queda activo) o PUT (edición)
      const guardado = editando
        ? await RefugiaAPI.actualizar(`${RUTA}/${editando.id_voluntariado}`, datos)
        : await RefugiaAPI.crear(RUTA, { ...datos, estado: "activo" });

      mostrarAviso(editando
        ? `Cambios guardados: "${guardado.actividad}".`
        : `Voluntariado aprobado y publicado: "${guardado.actividad}".`);
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
    const estabaEditando = Boolean(editando);
    modoCrear();
    if (estabaEditando) mostrarAviso("Edición cancelada.", "info");
  });

  // ---------------- Cerrar / reabrir ----------------
  btnEstado.addEventListener("click", async () => {
    if (!editando) return;
    const nuevoEstado = editando.estado === "activo" ? "cerrado" : "activo";
    ocupado(true);
    try {
      const guardado = await RefugiaAPI.actualizar(`${RUTA}/${editando.id_voluntariado}`, { estado: nuevoEstado });
      mostrarAviso(nuevoEstado === "cerrado"
        ? `Voluntariado cerrado: "${guardado.actividad}". Ya no aparece en la página.`
        : `Voluntariado reabierto: "${guardado.actividad}". Ya aparece en la página.`);
      modoCrear();
      await cargarListado();
    } catch (error) {
      mostrarAviso(error.message, "error");
    } finally {
      ocupado(false);
    }
  });

  // ---------------- Eliminar (con confirmación) ----------------
  btnEliminar.addEventListener("click", () => {
    if (!editando) return;
    $("#dialogo-texto").textContent = `"${editando.actividad}" se borrará de la base de datos. Esta acción no se puede deshacer. Si solo ya no recibe voluntarios, mejor ciérralo.`;
    dialogo.returnValue = "";
    dialogo.showModal();
  });

  dialogo.addEventListener("close", async () => {
    if (dialogo.returnValue !== "eliminar" || !editando) return;
    try {
      const eliminado = await RefugiaAPI.eliminar(`${RUTA}/${editando.id_voluntariado}`);
      mostrarAviso(`Voluntariado eliminado: "${eliminado.actividad}".`);
      modoCrear();
      await cargarListado();
    } catch (error) {
      mostrarAviso(error.message, "error");
    }
  });

  // ---------------- Listado (tabla) ----------------
  function filaVoluntariado(voluntariado) {
    const fila = crear("tr");
    fila.append(crear("td", "tareas__celda--negrita", voluntariado.actividad));
    fila.append(crear("td", "tareas__celda--negrita", voluntariado.organizacion));

    const celdaEstado = crear("td", "tareas__celda--centro");
    celdaEstado.append(crear("span", `tareas__estado tareas__estado--${voluntariado.estado}`, voluntariado.estado_nombre));
    fila.append(celdaEstado);

    const celdaAccion = crear("td", "tareas__celda--centro");
    const revisar = crear("button", "tareas__boton", "Revisar");
    revisar.type = "button";
    revisar.setAttribute("aria-label", `Revisar "${voluntariado.actividad}"`);
    revisar.addEventListener("click", () => modoEditar(voluntariado));
    celdaAccion.append(revisar);
    fila.append(celdaAccion);
    return fila;
  }

  async function cargarListado() {
    try {
      const respuesta = await RefugiaAPI.obtener(RUTA, { estado: filtroEstado.value, limite: 100 });
      listado.replaceChildren(...respuesta.resultados.map(filaVoluntariado));
      listadoEstado.textContent = respuesta.total
        ? `${respuesta.total} ${respuesta.total === 1 ? "voluntariado" : "voluntariados"}.`
        : "No hay voluntariados con este filtro.";
      listadoEstado.classList.remove("tareas__resumen--error");
    } catch (error) {
      listado.replaceChildren();
      listadoEstado.textContent = `No se pudieron cargar los voluntariados. ${error.message}`;
      listadoEstado.classList.add("tareas__resumen--error");
    }
  }

  filtroEstado.addEventListener("change", cargarListado);

  modoCrear();
  cargarListado();
})();
