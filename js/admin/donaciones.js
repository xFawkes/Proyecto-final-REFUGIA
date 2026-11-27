/* =========================================================
   REFUGIA — Administración de donaciones
   ---------------------------------------------------------
   Donaciones (pasarela simulada):
     Resumen   → GET    /api/donaciones/resumen
     Listar    → GET    /api/donaciones?estado=…&q=…
     Anular    → PUT    /api/donaciones/<referencia>  {"estado": "anulada"}
     Eliminar  → DELETE /api/donaciones/<referencia>  (solo pendientes, rechazadas o anuladas)
   Organizaciones (CRUD completo):
     GET / POST / PUT / DELETE  /api/organizaciones   e imagen: POST /api/organizaciones/imagen
   Requiere ../js/api.js y que la API esté corriendo:  python main.py
   ========================================================= */
(() => {
  "use strict";

  const POR_PAGINA = 20;
  const CAMPOS = ["nombre", "enlace", "descripcion", "impacto", "imagen_alt"];

  const $ = (selector) => document.querySelector(selector);
  const aviso = $("#aviso");
  const dialogo = $("#dialogo-confirmar");
  const pesos = new Intl.NumberFormat("es-CO", { style: "currency", currency: "COP", maximumFractionDigits: 0 });
  const fechaCorta = new Intl.DateTimeFormat("es-CO", { dateStyle: "medium", timeStyle: "short" });

  function crear(etiqueta, clase, texto) {
    const elemento = document.createElement(etiqueta);
    if (clase) elemento.className = clase;
    if (texto !== undefined) elemento.textContent = texto;
    return elemento;
  }

  function boton(texto, clase, etiqueta, accion) {
    const b = crear("button", `formulario__boton ${clase}`, texto);
    b.type = "button";
    if (etiqueta) b.setAttribute("aria-label", etiqueta);
    b.addEventListener("click", accion);
    return b;
  }

  function mostrarAviso(texto, tipo = "exito") {
    aviso.textContent = texto;
    aviso.className = `aviso aviso--${tipo}`;
    aviso.hidden = false;
    aviso.setAttribute("role", tipo === "error" ? "alert" : "status");
  }

  // Confirmación con <dialog>: devuelve una promesa que se resuelve en true o false
  function confirmar(titulo, texto, textoBoton) {
    $("#dialogo-titulo").textContent = titulo;
    $("#dialogo-texto").textContent = texto;
    $("#dialogo-confirmar-boton").textContent = textoBoton;
    dialogo.returnValue = "";
    dialogo.showModal();
    return new Promise((resolver) =>
      dialogo.addEventListener("close", () => resolver(dialogo.returnValue === "confirmar"), { once: true })
    );
  }

  // =========================================================
  // Resumen
  // =========================================================
  async function cargarResumen() {
    try {
      const r = await RefugiaAPI.obtener("/api/donaciones/resumen");
      const c = r.cantidad_por_estado;
      $("#resumen-total").textContent = pesos.format(r.total_recaudado);
      $("#resumen-aprobadas").textContent = c.aprobada;
      $("#resumen-pendientes").textContent = c.pendiente + c.rechazada;
      $("#resumen-detalle").textContent = `${c.pendiente} pendientes, ${c.rechazada} rechazadas y ${c.anulada} anuladas`;
      $("#resumen-destinos").replaceChildren(
        ...r.por_destino.map((d) => crear("li", "", `${d.destino}: ${pesos.format(d.total)} (${d.cantidad})`))
      );
    } catch (error) {
      mostrarAviso(`No se pudo cargar el resumen. ${error.message}`, "error");
    }
  }

  // =========================================================
  // Donaciones
  // =========================================================
  const tabla = $("#tabla-donaciones");
  const estadoDonaciones = $("#donaciones-estado");
  const botonMas = $("#donaciones-mas");
  let mostradas = 0;

  function filaDonacion(d) {
    const fila = crear("tr");

    const ref = crear("td");
    ref.append(crear("span", "tabla__referencia", d.referencia));
    ref.append(crear("span", "tabla__secundario", fechaCorta.format(new Date(d.creado_en))));
    fila.append(ref);

    const donante = crear("td");
    donante.append(crear("span", "", d.nombre_donante));
    donante.append(crear("span", "tabla__secundario", d.correo));
    fila.append(donante);

    const destino = crear("td");
    destino.append(crear("span", "", d.destino));
    if (d.detalle_pago) destino.append(crear("span", "tabla__secundario", d.detalle_pago));
    fila.append(destino);

    const monto = crear("td", "tabla__monto", pesos.format(d.monto));
    if (d.frecuencia === "mensual") monto.append(crear("span", "tabla__secundario", "Mensual"));
    fila.append(monto);

    const estado = crear("td");
    estado.append(crear("span", `sello sello--${d.estado}`, d.estado_nombre));
    fila.append(estado);

    const accion = crear("td");
    if (d.estado === "aprobada") {
      accion.append(boton("Anular", "formulario__boton--secundario", `Anular la donación ${d.referencia}`, () => anular(d)));
    } else {
      accion.append(boton("Eliminar", "formulario__boton--eliminar", `Eliminar la donación ${d.referencia}`, () => eliminarDonacion(d)));
    }
    fila.append(accion);
    return fila;
  }

  async function cargarDonaciones({ agregar = false } = {}) {
    const offset = agregar ? mostradas : 0;
    botonMas.disabled = true;
    try {
      const r = await RefugiaAPI.obtener("/api/donaciones", {
        q: $("#filtro-q").value.trim(),
        estado: $("#filtro-estado").value,
        limite: POR_PAGINA,
        offset,
      });
      if (!agregar) {
        tabla.replaceChildren();
        mostradas = 0;
      }
      r.resultados.forEach((d) => tabla.append(filaDonacion(d)));
      mostradas += r.resultados.length;
      estadoDonaciones.textContent = r.total
        ? `${r.total} ${r.total === 1 ? "donación" : "donaciones"}.`
        : "No hay donaciones con este filtro. Haz una donación de prueba en la página de donaciones.";
      estadoDonaciones.classList.remove("listado__estado--error");
      botonMas.hidden = mostradas >= r.total;
    } catch (error) {
      estadoDonaciones.textContent = `No se pudieron cargar las donaciones. ${error.message}`;
      estadoDonaciones.classList.add("listado__estado--error");
    } finally {
      botonMas.disabled = false;
    }
  }

  async function anular(d) {
    const ok = await confirmar(
      "¿Anular esta donación?",
      `${d.referencia} — ${pesos.format(d.monto)} de ${d.nombre_donante}. En una pasarela real esto sería un reembolso. Dejará de sumar en lo recaudado.`,
      "Anular"
    );
    if (!ok) return;
    try {
      await RefugiaAPI.actualizar(`/api/donaciones/${d.referencia}`, { estado: "anulada", nota: "Anulada desde el panel" });
      mostrarAviso(`Donación ${d.referencia} anulada.`);
      await Promise.all([cargarResumen(), cargarDonaciones()]);
    } catch (error) {
      mostrarAviso(error.message, "error");
    }
  }

  async function eliminarDonacion(d) {
    const ok = await confirmar(
      "¿Eliminar esta donación?",
      `${d.referencia} (${d.estado_nombre.toLowerCase()}) se borrará de la base de datos.`,
      "Eliminar"
    );
    if (!ok) return;
    try {
      await RefugiaAPI.eliminar(`/api/donaciones/${d.referencia}`);
      mostrarAviso(`Donación ${d.referencia} eliminada.`);
      await Promise.all([cargarResumen(), cargarDonaciones()]);
    } catch (error) {
      mostrarAviso(error.message, "error");
    }
  }

  $("#filtros-donaciones").addEventListener("submit", (e) => {
    e.preventDefault();
    cargarDonaciones();
  });
  $("#filtro-estado").addEventListener("change", () => cargarDonaciones());
  botonMas.addEventListener("click", () => cargarDonaciones({ agregar: true }));

  // =========================================================
  // Organizaciones (CRUD)
  // =========================================================
  const formulario = $("#formulario-organizacion");
  const archivoImagen = $("#archivo-imagen");
  const vistaImagen = $("#imagen-vista");
  const imagenPrevia = $("#imagen-previa");
  const lista = $("#lista-organizaciones");
  let editando = null;
  let imagenActual = null;
  let urlVistaPrevia = null;

  function limpiarErrores() {
    formulario.querySelectorAll(".formulario__error").forEach((p) => (p.textContent = ""));
    formulario.querySelectorAll("[aria-invalid]").forEach((c) => c.removeAttribute("aria-invalid"));
  }

  function mostrarErrores(detalles) {
    let primero = null;
    for (const [campo, mensajes] of Object.entries(detalles || {})) {
      const entrada = campo === "imagen" ? archivoImagen : $(`#${campo}`);
      const parrafo = $(`#error-${campo}`);
      if (parrafo) parrafo.textContent = [].concat(mensajes).join(" ");
      if (entrada) {
        entrada.setAttribute("aria-invalid", "true");
        primero ??= entrada;
      }
    }
    primero?.focus();
  }

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
    if (!archivo) return mostrarVistaPrevia(imagenActual ? RefugiaAPI.recurso(imagenActual) : "");
    if (archivo.size > 5 * 1024 * 1024) {
      $("#error-imagen").textContent = "La imagen pesa más de 5 MB.";
      archivoImagen.value = "";
      return;
    }
    urlVistaPrevia = URL.createObjectURL(archivo);
    mostrarVistaPrevia(urlVistaPrevia);
  });

  $("#btn-quitar-imagen").addEventListener("click", () => {
    archivoImagen.value = "";
    liberarVistaLocal();
    imagenActual = null;
    mostrarVistaPrevia("");
    archivoImagen.focus();
  });

  function modoCrear() {
    editando = null;
    formulario.reset();
    limpiarErrores();
    liberarVistaLocal();
    imagenActual = null;
    mostrarVistaPrevia("");
    $("#titulo-formulario").textContent = "Nueva organización";
    $("#btn-guardar").textContent = "Aprobar";
    $("#btn-cancelar").hidden = true;
  }

  function modoEditar(org) {
    modoCrear();
    editando = org;
    for (const campo of CAMPOS) $(`#${campo}`).value = org[campo] ?? "";
    $("#activa").checked = org.activa;
    imagenActual = org.imagen;
    mostrarVistaPrevia(imagenActual ? RefugiaAPI.recurso(imagenActual) : "");
    $("#titulo-formulario").textContent = `Editando: ${org.nombre}`;
    $("#btn-guardar").textContent = "Guardar cambios";
    $("#btn-cancelar").hidden = false;
    formulario.closest("section").scrollIntoView({ behavior: "smooth", block: "start" });
    $("#nombre").focus({ preventScroll: true });
  }

  formulario.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    limpiarErrores();
    const datos = {};
    for (const campo of CAMPOS) datos[campo] = $(`#${campo}`).value.trim();
    datos.activa = $("#activa").checked;

    const errores = {};
    if (datos.nombre.length < 2) errores.nombre = ["Escribe el nombre de la organización."];
    if (datos.descripcion.length < 10) errores.descripcion = ["Escribe la descripción (al menos 10 caracteres)."];
    if (datos.enlace && !/^https?:\/\/\S+$/i.test(datos.enlace)) errores.enlace = ["Debe empezar por http:// o https://."];
    if ((archivoImagen.files.length || imagenActual) && !datos.imagen_alt) errores.imagen_alt = ["Describe la imagen: es obligatorio cuando hay imagen."];
    if (Object.keys(errores).length) {
      mostrarErrores(errores);
      return mostrarAviso("Revisa los campos marcados.", "error");
    }

    formulario.querySelectorAll("button").forEach((b) => (b.disabled = true));
    try {
      if (archivoImagen.files.length) {
        imagenActual = (await RefugiaAPI.subirArchivo("/api/organizaciones/imagen", "imagen", archivoImagen.files[0])).imagen;
      }
      datos.imagen = imagenActual || null;
      const guardada = editando
        ? await RefugiaAPI.actualizar(`/api/organizaciones/${editando.id_organizacion}`, datos)
        : await RefugiaAPI.crear("/api/organizaciones", datos);
      mostrarAviso(editando ? `Cambios guardados: "${guardada.nombre}".` : `Organización creada: "${guardada.nombre}".`);
      modoCrear();
      await cargarOrganizaciones();
    } catch (error) {
      if (error.detalles) mostrarErrores(error.detalles);
      mostrarAviso(error.message, "error");
    } finally {
      formulario.querySelectorAll("button").forEach((b) => (b.disabled = false));
    }
  });

  $("#btn-cancelar").addEventListener("click", () => {
    modoCrear();
    mostrarAviso("Edición cancelada.", "info");
  });

  function filaOrganizacion(org) {
    const fila = crear("li", "listado__fila");
    if (org.imagen) {
      const miniatura = crear("img", "listado__miniatura");
      miniatura.src = RefugiaAPI.recurso(org.imagen);
      miniatura.alt = "";
      fila.append(miniatura);
    } else {
      fila.append(crear("div", "listado__miniatura listado__miniatura--vacia"));
    }
    const info = crear("div", "listado__info");
    info.append(crear("h3", "listado__titulo", org.nombre));
    info.append(crear("p", "listado__meta", org.enlace || "Sin página oficial"));
    const sellos = crear("p", "listado__sellos");
    sellos.append(crear("span", `sello ${org.activa ? "sello--publicada" : "sello--inactiva"}`, org.activa ? "Activa" : "Inactiva"));
    info.append(sellos);

    const acciones = crear("div", "listado__acciones");
    const nombre = `"${org.nombre}"`;
    acciones.append(boton("Editar", "formulario__boton--secundario", `Editar ${nombre}`, () => modoEditar(org)));
    acciones.append(boton(
      org.activa ? "Desactivar" : "Activar",
      org.activa ? "formulario__boton--secundario" : "formulario__boton--aprobar",
      `${org.activa ? "Desactivar" : "Activar"} ${nombre}`,
      () => cambiarActiva(org)
    ));
    acciones.append(boton("Eliminar", "formulario__boton--eliminar", `Eliminar ${nombre}`, () => eliminarOrganizacion(org)));
    fila.append(info, acciones);
    return fila;
  }

  async function cambiarActiva(org) {
    try {
      const guardada = await RefugiaAPI.actualizar(`/api/organizaciones/${org.id_organizacion}`, { activa: !org.activa });
      mostrarAviso(guardada.activa
        ? `"${guardada.nombre}" ya aparece en la página de donaciones.`
        : `"${guardada.nombre}" ya no aparece en la página ni recibe donaciones.`);
      await cargarOrganizaciones();
    } catch (error) {
      mostrarAviso(error.message, "error");
    }
  }

  async function eliminarOrganizacion(org) {
    const ok = await confirmar(
      "¿Eliminar esta organización?",
      `"${org.nombre}" se borrará. Sus donaciones se conservan con el nombre guardado. Si solo quieres ocultarla, mejor desactívala.`,
      "Eliminar"
    );
    if (!ok) return;
    try {
      const eliminada = await RefugiaAPI.eliminar(`/api/organizaciones/${org.id_organizacion}`);
      if (editando?.id_organizacion === org.id_organizacion) modoCrear();
      mostrarAviso(`Organización eliminada: "${eliminada.nombre}".`);
      await cargarOrganizaciones();
    } catch (error) {
      mostrarAviso(error.message, "error");
    }
  }

  async function cargarOrganizaciones() {
    try {
      const organizaciones = await RefugiaAPI.obtener("/api/organizaciones", { incluir_inactivas: true });
      lista.replaceChildren(...organizaciones.map(filaOrganizacion));
      $("#organizaciones-estado").textContent = organizaciones.length
        ? `${organizaciones.length} ${organizaciones.length === 1 ? "organización" : "organizaciones"}.`
        : "No hay organizaciones registradas.";
    } catch (error) {
      $("#organizaciones-estado").textContent = `No se pudieron cargar las organizaciones. ${error.message}`;
    }
  }

  modoCrear();
  cargarResumen();
  cargarDonaciones();
  cargarOrganizaciones();
})();
