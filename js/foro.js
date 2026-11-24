/* =========================================================
   REFUGIA — Foro (consume /api/foro)
   ---------------------------------------------------------
     Listado        → GET  /api/foro/publicaciones?q=…&categoria=…
     Detalle        → GET  /api/foro/publicaciones/<id>      (foro.html?publicacion=<id>)
     Publicar       → POST /api/foro/publicaciones
     Responder      → POST /api/foro/publicaciones/<id>/respuestas
     Confirmar      → POST /api/foro/publicaciones/<id>/validar
     Denunciar      → POST /api/foro/publicaciones/<id>/denuncias
   La moderación se hace en admin/foro.html.
   Requiere js/api.js y que la API esté corriendo:  python main.py
   ========================================================= */
(() => {
  "use strict";

  const POR_PAGINA = 10;
  const CLAVE_VALIDADAS = "refugia:foro:validadas";
  const CLAVE_DENUNCIADAS = "refugia:foro:denunciadas";

  const $ = (selector, raiz = document) => raiz.querySelector(selector);
  const listado = $("#foro-listado");
  const lista = $("#foro-lista");
  const estado = $("#foro-estado");
  const botonMas = $("#foro-mas");
  const detalle = $("#foro-detalle");
  const panelNueva = $("#foro-nueva");
  const btnNueva = $("#btn-nueva");
  const formNueva = $("#form-nueva");
  const campoBusqueda = $("#buscar-foro");
  const filtroCategoria = $("#filtro-categoria");

  const fechaCorta = new Intl.DateTimeFormat("es-CO", { day: "2-digit", month: "2-digit", year: "numeric" });
  const fechaLarga = new Intl.DateTimeFormat("es-CO", { dateStyle: "long", timeStyle: "short" });

  let catalogos = null;
  let mostradas = 0;
  let total = 0;
  let peticionActual = 0;

  // ---------------- Utilidades ----------------
  function crear(etiqueta, clase, texto) {
    const elemento = document.createElement(etiqueta);
    if (clase) elemento.className = clase;
    if (texto !== undefined) elemento.textContent = texto;
    return elemento;
  }

  function parrafos(texto) {
    return texto.split(/\n\s*\n|\n/).map((p) => p.trim()).filter(Boolean).map((p) => crear("p", "", p));
  }

  function iniciales(nombre) {
    // Solo palabras que empiezan por letra: "Carlos (ejemplo)" → "CE"
    const palabras = nombre.match(/\p{L}[\p{L}'-]*/gu) || ["?"];
    return palabras.slice(0, 2).map((p) => p[0]).join("").toUpperCase();
  }

  function leerLista(clave) {
    try {
      return JSON.parse(localStorage.getItem(clave) || "[]");
    } catch {
      return [];
    }
  }

  function agregarALista(clave, id) {
    try {
      localStorage.setItem(clave, JSON.stringify([...new Set([...leerLista(clave), id])]));
    } catch {
      /* sin almacenamiento: solo dura en esta página */
    }
  }

  function anunciar(texto) {
    window.Accesibilidad?.anunciar?.(texto);
  }

  function sello(publicacion) {
    return crear("span", `foro__sello foro__sello--${publicacion.verificacion}`, publicacion.verificacion_nombre);
  }

  // ---------------- Errores de formularios ----------------
  function limpiarErrores(form) {
    form.querySelectorAll(".foro__error-campo").forEach((p) => (p.textContent = ""));
    form.querySelectorAll("[aria-invalid]").forEach((c) => c.removeAttribute("aria-invalid"));
    const general = $(".foro__error", form);
    if (general) general.textContent = "";
  }

  function mostrarErrores(form, prefijo, detalles, mensajeGeneral) {
    let primero = null;
    for (const [campo, mensajes] of Object.entries(detalles || {})) {
      const entrada = $(`#${prefijo}-${campo}`, form);
      const parrafo = $(`#error-${prefijo}-${campo}`, form);
      if (parrafo) parrafo.textContent = [].concat(mensajes).join(" ");
      if (entrada) {
        entrada.setAttribute("aria-invalid", "true");
        primero ??= entrada;
      }
    }
    if (mensajeGeneral && !primero) {
      let general = $(".foro__error", form);
      if (!general) {
        general = crear("p", "foro__error");
        general.setAttribute("role", "alert");
        form.prepend(general);
      }
      general.textContent = mensajeGeneral;
    }
    primero?.focus();
  }

  function validarRequeridos(form, prefijo, reglas) {
    const errores = {};
    for (const [campo, minimo, mensaje] of reglas) {
      if ($(`#${prefijo}-${campo}`, form).value.trim().length < minimo) errores[campo] = [mensaje];
    }
    return errores;
  }

  // =========================================================
  // Listado
  // =========================================================
  function filaPublicacion(p) {
    const fila = crear("article", "fila");
    fila.setAttribute("aria-labelledby", `publicacion-${p.id_publicacion}`);

    const celdaAvatar = crear("div", "celda-avatar");
    const avatar = crear("div", "avatar", iniciales(p.autor));
    avatar.setAttribute("aria-hidden", "true");
    const texto = crear("div", "texto");
    const titulo = crear("h2");
    const enlace = crear("a", "", p.titulo);
    enlace.id = `publicacion-${p.id_publicacion}`;
    enlace.href = `foro.html?publicacion=${p.id_publicacion}`;
    enlace.addEventListener("click", (evento) => {
      evento.preventDefault();
      abrirDetalle(p.id_publicacion, { guardarHistorial: true });
    });
    titulo.append(enlace);
    const resumen = p.contenido.length > 180 ? `${p.contenido.slice(0, 180).trim()}…` : p.contenido;
    const meta = crear("p", "foro__meta");
    meta.append(`Por ${p.autor}${p.ubicacion ? ` · ${p.ubicacion}` : ""} `, sello(p));
    texto.append(titulo, crear("p", "", resumen), meta);
    celdaAvatar.append(avatar, texto);
    fila.append(celdaAvatar);

    // Columnas "Temas", "Mensajes" y "Fechas" (con su nombre oculto para lectores de pantalla)
    const datos = [
      ["Temas", "Tema", p.categoria_nombre],
      ["Mensajes", "Mensajes", p.total_respuestas],
      ["Fecha", "Última actividad", fechaCorta.format(new Date(p.ultima_actividad))],
    ];
    for (const [etiqueta, leido, valor] of datos) {
      const celda = crear("div", etiqueta === "Temas" ? "celda dato dato--tema" : "celda dato");
      celda.dataset.etiqueta = etiqueta;
      celda.append(crear("span", "sr-only", `${leido}: `), String(valor));
      fila.append(celda);
    }
    return fila;
  }

  async function cargarListado({ agregar = false } = {}) {
    const numero = ++peticionActual;
    const offset = agregar ? mostradas : 0;
    botonMas.disabled = true;
    if (!agregar) {
      estado.hidden = false;
      estado.textContent = "Cargando publicaciones…";
    }
    try {
      const r = await RefugiaAPI.obtener("/api/foro/publicaciones", {
        q: campoBusqueda.value.trim(),
        categoria: filtroCategoria.value,
        limite: POR_PAGINA,
        offset,
      });
      if (numero !== peticionActual) return;
      if (!agregar) {
        lista.replaceChildren();
        mostradas = 0;
      }
      total = r.total;
      r.resultados.forEach((p) => lista.append(filaPublicacion(p)));
      mostradas += r.resultados.length;

      const hayFiltros = campoBusqueda.value.trim() || filtroCategoria.value;
      estado.hidden = total > 0;
      estado.textContent = total ? "" : hayFiltros ? "No hay publicaciones que coincidan con la búsqueda." : "Todavía no hay publicaciones. ¡Crea la primera!";
      estado.classList.remove("foro__estado--error");
      if (!agregar && hayFiltros) anunciar(`${total} ${total === 1 ? "publicación encontrada" : "publicaciones encontradas"}.`);
    } catch (error) {
      if (numero !== peticionActual) return;
      estado.hidden = false;
      estado.textContent = `No se pudieron cargar las publicaciones. ${error.message}`;
      estado.classList.add("foro__estado--error");
    } finally {
      if (numero === peticionActual) {
        botonMas.hidden = mostradas >= total;
        botonMas.disabled = false;
      }
    }
  }

  // =========================================================
  // Detalle de una publicación
  // =========================================================
  function mostrarListado() {
    detalle.hidden = true;
    detalle.replaceChildren();
    listado.hidden = false;
  }

  async function abrirDetalle(id, { guardarHistorial = false } = {}) {
    if (guardarHistorial) history.pushState({ publicacion: id }, "", `foro.html?publicacion=${id}`);
    cerrarNueva();
    listado.hidden = true;
    detalle.hidden = false;
    detalle.replaceChildren(crear("p", "foro__estado", "Cargando publicación…"));
    try {
      const p = await RefugiaAPI.obtener(`/api/foro/publicaciones/${id}`);
      pintarDetalle(p);
      $("#detalle-titulo").focus();
      document.title = `REFUGIA | ${p.titulo}`;
    } catch (error) {
      detalle.replaceChildren(botonVolver(), crear("p", "foro__estado foro__estado--error",
        error.estado === 404 ? "Esta publicación no existe o fue retirada por moderación." : `No se pudo cargar la publicación. ${error.message}`));
    }
  }

  function botonVolver() {
    const volver = crear("a", "foro__volver", "← Volver al foro");
    volver.href = "foro.html";
    volver.addEventListener("click", (evento) => {
      evento.preventDefault();
      history.pushState({}, "", "foro.html");
      volverAlListado();
    });
    return volver;
  }

  function volverAlListado() {
    document.title = "REFUGIA | Foro";
    mostrarListado();
    cargarListado();
    campoBusqueda.focus();
  }

  function pintarDetalle(p) {
    const articulo = crear("article", "foro__articulo");
    const etiquetas = crear("p", "foro__etiquetas");
    etiquetas.append(crear("span", "foro__sello foro__sello--categoria", p.categoria_nombre), sello(p));
    const titulo = crear("h2", "foro__titulo-detalle", p.titulo);
    titulo.id = "detalle-titulo";
    titulo.tabIndex = -1;
    const meta = crear("p", "foro__meta", `Por ${p.autor}${p.ubicacion ? ` · ${p.ubicacion}` : ""} · ${fechaLarga.format(new Date(p.creado_en))}`);
    const cuerpo = crear("div", "foro__contenido");
    cuerpo.append(...parrafos(p.contenido));
    if (p.verificacion === "sin_confirmar") {
      cuerpo.append(crear("p", "foro__aviso", "Esta información aún no ha sido confirmada por un moderador. Verifícala con fuentes oficiales antes de actuar."));
    }
    articulo.append(etiquetas, titulo, meta, cuerpo, accionesDetalle(p));

    const respuestas = crear("section", "foro__respuestas");
    respuestas.setAttribute("aria-labelledby", "titulo-respuestas");
    const tituloRespuestas = crear("h3", "foro__subtitulo", `Respuestas (${p.respuestas.length})`);
    tituloRespuestas.id = "titulo-respuestas";
    const listaRespuestas = crear("ol", "foro__lista-respuestas");
    p.respuestas.forEach((r) => listaRespuestas.append(itemRespuesta(r)));
    if (!p.respuestas.length) listaRespuestas.append(crear("li", "foro__sin-respuestas", "Todavía no hay respuestas. Sé la primera persona en responder."));
    respuestas.append(tituloRespuestas, listaRespuestas, formularioRespuesta(p, listaRespuestas, tituloRespuestas));

    detalle.replaceChildren(botonVolver(), articulo, respuestas);
  }

  function itemRespuesta(r) {
    const item = crear("li", "foro__respuesta");
    const cabecera = crear("p", "foro__meta");
    cabecera.append(crear("strong", "", r.autor), ` · ${fechaLarga.format(new Date(r.creado_en))}`);
    item.append(cabecera, ...parrafos(r.contenido));
    return item;
  }

  // ---------------- Confirmar y denunciar ----------------
  function accionesDetalle(p) {
    const contenedor = crear("div", "foro__interaccion");
    const acciones = crear("div", "foro__acciones");

    const yaValidada = leerLista(CLAVE_VALIDADAS).includes(p.id_publicacion);
    const validar = crear("button", "foro__boton foro__boton--principal");
    validar.type = "button";
    const pintarValidar = (n, hecha) => {
      validar.textContent = hecha ? `Confirmaste esta información (${n})` : `Confirmo esta información (${n})`;
      validar.disabled = hecha;
    };
    pintarValidar(p.validaciones, yaValidada);
    validar.addEventListener("click", async () => {
      validar.disabled = true;
      try {
        const r = await RefugiaAPI.crear(`/api/foro/publicaciones/${p.id_publicacion}/validar`, {});
        agregarALista(CLAVE_VALIDADAS, p.id_publicacion);
        pintarValidar(r.validaciones, true);
        anunciar("Gracias por confirmar la información.");
      } catch (error) {
        validar.disabled = false;
        anunciar(error.message);
      }
    });

    const yaDenunciada = leerLista(CLAVE_DENUNCIADAS).includes(p.id_publicacion);
    const denunciar = crear("button", "foro__boton", yaDenunciada ? "Ya la denunciaste" : "Denunciar");
    denunciar.type = "button";
    denunciar.disabled = yaDenunciada;
    denunciar.setAttribute("aria-expanded", "false");
    const formDenuncia = formularioDenuncia(p, denunciar);
    denunciar.setAttribute("aria-controls", formDenuncia.id);
    denunciar.addEventListener("click", () => {
      const abrir = formDenuncia.hidden;
      formDenuncia.hidden = !abrir;
      denunciar.setAttribute("aria-expanded", String(abrir));
      if (abrir) $("select", formDenuncia).focus();
    });

    acciones.append(validar, denunciar);
    contenedor.append(acciones, formDenuncia);
    return contenedor;
  }

  function formularioDenuncia(p, botonDenunciar) {
    const form = crear("form", "foro__formulario foro__formulario--denuncia");
    form.id = "form-denuncia";
    form.hidden = true;
    form.noValidate = true;
    form.innerHTML = `
      <div class="foro__campo">
        <label for="denuncia-motivo">Motivo de la denuncia</label>
        <select id="denuncia-motivo"></select>
      </div>
      <div class="foro__campo foro__campo--ancho">
        <label for="denuncia-detalle">Detalle (opcional)</label>
        <textarea id="denuncia-detalle" rows="2" maxlength="300"></textarea>
      </div>
      <div class="foro__acciones">
        <button type="submit" class="foro__boton foro__boton--peligro">Enviar denuncia</button>
        <button type="button" class="foro__boton" data-accion="cancelar">Cancelar</button>
      </div>`;
    catalogos.motivos_denuncia.forEach((m) => {
      const opcion = crear("option", "", m.nombre);
      opcion.value = m.clave;
      $("#denuncia-motivo", form).append(opcion);
    });
    $('[data-accion="cancelar"]', form).addEventListener("click", () => {
      form.hidden = true;
      botonDenunciar.setAttribute("aria-expanded", "false");
      botonDenunciar.focus();
    });
    form.addEventListener("submit", async (evento) => {
      evento.preventDefault();
      limpiarErrores(form);
      form.querySelectorAll("button").forEach((b) => (b.disabled = true));
      try {
        const r = await RefugiaAPI.crear(`/api/foro/publicaciones/${p.id_publicacion}/denuncias`, {
          motivo: $("#denuncia-motivo", form).value,
          detalle: $("#denuncia-detalle", form).value.trim(),
        });
        agregarALista(CLAVE_DENUNCIADAS, p.id_publicacion);
        const gracias = crear("p", "foro__confirmacion", r.publicacion_oculta
          ? "Gracias. Con tu denuncia, la publicación quedó oculta hasta que un moderador la revise."
          : "Gracias. Un moderador revisará la publicación.");
        gracias.setAttribute("role", "status");
        form.replaceWith(gracias);
        botonDenunciar.textContent = "Ya la denunciaste";
        botonDenunciar.disabled = true;
        botonDenunciar.removeAttribute("aria-controls"); // el formulario ya no existe
        botonDenunciar.removeAttribute("aria-expanded");
      } catch (error) {
        mostrarErrores(form, "denuncia", error.detalles, error.message);
        form.querySelectorAll("button").forEach((b) => (b.disabled = false));
      }
    });
    return form;
  }

  // ---------------- Responder ----------------
  function formularioRespuesta(p, listaRespuestas, tituloRespuestas) {
    const form = crear("form", "foro__formulario foro__formulario--respuesta");
    form.noValidate = true;
    form.setAttribute("aria-labelledby", "titulo-responder");
    form.innerHTML = `
      <h3 class="foro__subtitulo foro__campo--ancho" id="titulo-responder">Responder</h3>
      <div class="foro__campo foro__campo--ancho">
        <label for="respuesta-contenido">Tu mensaje *</label>
        <textarea id="respuesta-contenido" rows="3" maxlength="2000" required aria-describedby="error-respuesta-contenido"></textarea>
        <p class="foro__error-campo" id="error-respuesta-contenido"></p>
      </div>
      <div class="foro__campo">
        <label for="respuesta-autor">Tu nombre *</label>
        <input type="text" id="respuesta-autor" maxlength="80" autocomplete="name" required aria-describedby="error-respuesta-autor">
        <p class="foro__error-campo" id="error-respuesta-autor"></p>
      </div>
      <div class="foro__acciones">
        <button type="submit" class="foro__boton foro__boton--principal">Publicar respuesta</button>
      </div>`;
    form.addEventListener("submit", async (evento) => {
      evento.preventDefault();
      limpiarErrores(form);
      const errores = validarRequeridos(form, "respuesta", [
        ["contenido", 2, "Escribe tu mensaje."],
        ["autor", 2, "Escribe tu nombre."],
      ]);
      if (Object.keys(errores).length) return mostrarErrores(form, "respuesta", errores);
      const boton = $('button[type="submit"]', form);
      boton.disabled = true;
      try {
        const r = await RefugiaAPI.crear(`/api/foro/publicaciones/${p.id_publicacion}/respuestas`, {
          autor: $("#respuesta-autor", form).value.trim(),
          contenido: $("#respuesta-contenido", form).value.trim(),
        });
        $(".foro__sin-respuestas", listaRespuestas)?.remove();
        listaRespuestas.append(itemRespuesta(r));
        tituloRespuestas.textContent = `Respuestas (${listaRespuestas.children.length})`;
        $("#respuesta-contenido", form).value = "";
        anunciar("Tu respuesta fue publicada.");
      } catch (error) {
        mostrarErrores(form, "respuesta", error.detalles, error.message);
      } finally {
        boton.disabled = false;
      }
    });
    return form;
  }

  // =========================================================
  // Nueva publicación
  // =========================================================
  function abrirNueva() {
    if (!detalle.hidden) {
      history.pushState({}, "", "foro.html");
      mostrarListado();
    }
    panelNueva.hidden = false;
    btnNueva.setAttribute("aria-expanded", "true");
    $("#nueva-titulo").focus();
  }

  function cerrarNueva() {
    panelNueva.hidden = true;
    btnNueva.setAttribute("aria-expanded", "false");
  }

  btnNueva.addEventListener("click", () => (panelNueva.hidden ? abrirNueva() : cerrarNueva()));
  $("#btn-cancelar-nueva").addEventListener("click", () => {
    formNueva.reset();
    limpiarErrores(formNueva);
    cerrarNueva();
    btnNueva.focus();
  });

  formNueva.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    limpiarErrores(formNueva);
    const errores = validarRequeridos(formNueva, "nueva", [
      ["titulo", 5, "Escribe un título de al menos 5 caracteres."],
      ["contenido", 10, "Escribe tu mensaje (al menos 10 caracteres)."],
      ["autor", 2, "Escribe tu nombre."],
    ]);
    if (Object.keys(errores).length) return mostrarErrores(formNueva, "nueva", errores);

    const boton = $('button[type="submit"]', formNueva);
    boton.disabled = true;
    try {
      const nueva = await RefugiaAPI.crear("/api/foro/publicaciones", {
        titulo: $("#nueva-titulo").value.trim(),
        categoria: $("#nueva-categoria").value,
        ubicacion: $("#nueva-ubicacion").value.trim(),
        contenido: $("#nueva-contenido").value.trim(),
        autor: $("#nueva-autor").value.trim(),
      });
      formNueva.reset();
      cerrarNueva();
      anunciar("Tu publicación fue creada. Aparece como sin confirmar hasta que la revise un moderador.");
      abrirDetalle(nueva.id_publicacion, { guardarHistorial: true });
    } catch (error) {
      mostrarErrores(formNueva, "nueva", error.detalles, error.message);
    } finally {
      boton.disabled = false;
    }
  });

  // =========================================================
  // Búsqueda, filtros y navegación
  // =========================================================
  $("#form-busqueda").addEventListener("submit", (evento) => {
    evento.preventDefault();
    if (!detalle.hidden) {
      history.pushState({}, "", "foro.html");
      mostrarListado();
    }
    cargarListado();
  });
  campoBusqueda.addEventListener("search", () => cargarListado()); // la "x" del campo
  filtroCategoria.addEventListener("change", () => cargarListado());
  botonMas.addEventListener("click", () => cargarListado({ agregar: true }));

  // Botones atrás/adelante del navegador
  window.addEventListener("popstate", () => mostrarSegunUrl());

  function mostrarSegunUrl() {
    const id = Number(new URLSearchParams(location.search).get("publicacion"));
    if (id) {
      abrirDetalle(id);
    } else {
      document.title = "REFUGIA | Foro";
      mostrarListado();
      cargarListado();
    }
  }

  async function iniciar() {
    try {
      catalogos = await RefugiaAPI.obtener("/api/foro/catalogos");
      for (const categoria of catalogos.categorias) {
        for (const select of [filtroCategoria, $("#nueva-categoria")]) {
          const opcion = crear("option", "", categoria.nombre);
          opcion.value = categoria.clave;
          select.append(opcion);
        }
      }
      $("#nueva-categoria").value = "general";
    } catch (error) {
      estado.textContent = `No se pudo conectar con el foro. ${error.message}`;
      estado.classList.add("foro__estado--error");
      return;
    }
    mostrarSegunUrl();
  }

  iniciar();
})();
