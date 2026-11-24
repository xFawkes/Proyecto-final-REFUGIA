/* =========================================================
   REFUGIA — Noticias (consume GET /api/noticias)
   ---------------------------------------------------------
   Requiere js/api.js y que la API esté corriendo:  python main.py
   Las noticias se administran en admin/noticias.html.
   ========================================================= */
(() => {
  "use strict";

  const POR_PAGINA = 9;

  const $ = (selector) => document.querySelector(selector);
  const destacada = $("#noticias-destacada");
  const grid = $("#noticias-grid");
  const estado = $("#noticias-estado");
  const botonMas = $("#noticias-mas");
  const formulario = $("#noticias-busqueda");
  const campoBusqueda = $("#noticias-q");
  const campoVerificacion = $("#noticias-verificacion");

  let mostradas = 0;
  let total = 0;
  let peticionActual = 0; // evita que una respuesta vieja pise a una nueva

  // ---------------- Construcción de las tarjetas ----------------
  // Se usa textContent (no innerHTML) para que el texto de la base de datos nunca se interprete como HTML.
  function crear(etiqueta, clase, texto) {
    const elemento = document.createElement(etiqueta);
    if (clase) elemento.className = clase;
    if (texto !== undefined) elemento.textContent = texto;
    return elemento;
  }

  function tarjeta(noticia, esDestacada) {
    const articulo = crear("article", esDestacada ? "noticia noticia--destacada" : "noticia");
    articulo.setAttribute("aria-labelledby", `noticia-${noticia.id_noticia}`);

    const figura = crear("div", "noticia__figura");
    if (noticia.imagen) {
      const imagen = crear("img");
      imagen.src = RefugiaAPI.recurso(noticia.imagen);
      imagen.alt = noticia.imagen_alt || "";
      imagen.loading = esDestacada ? "eager" : "lazy";
      imagen.decoding = "async";
      figura.append(imagen);
    }
    const titulo = crear("h2", "noticia__titulo", noticia.titulo);
    titulo.id = `noticia-${noticia.id_noticia}`;
    figura.append(titulo);

    const cuerpo = crear("div", "noticia__cuerpo");
    const meta = crear("p", "noticia__meta");
    const fecha = crear("time", "", RefugiaAPI.formatearFecha(noticia.fecha_publicacion));
    fecha.dateTime = noticia.fecha_publicacion;
    const sello = crear("span", `noticia__sello noticia__sello--${noticia.verificacion}`, noticia.verificacion_nombre);
    meta.append(`${noticia.fuente} · `, fecha, " ", sello);
    cuerpo.append(meta);

    // Los párrafos se separan con una línea en blanco
    noticia.contenido
      .split(/\n\s*\n/)
      .map((parrafo) => parrafo.trim())
      .filter(Boolean)
      .forEach((parrafo) => cuerpo.append(crear("p", "", parrafo)));

    if (noticia.enlace) {
      const enlace = crear("a", "noticia__enlace", "Da click aquí para ir a la página");
      enlace.href = noticia.enlace;
      enlace.target = "_blank";
      enlace.rel = "noopener noreferrer";
      // Para lectores de pantalla: a dónde lleva el enlace
      enlace.setAttribute("aria-label", `Leer "${noticia.titulo}" en ${noticia.fuente} (se abre en otra pestaña)`);
      cuerpo.append(enlace);
    }

    articulo.append(figura, cuerpo);
    return articulo;
  }

  // ---------------- Carga desde la API ----------------
  function parametros(offset) {
    return {
      q: campoBusqueda.value.trim(),
      verificacion: campoVerificacion.value,
      limite: POR_PAGINA,
      offset,
    };
  }

  function mostrarEstado(texto, esError = false) {
    estado.textContent = texto;
    estado.hidden = !texto;
    estado.classList.toggle("noticias__estado--error", esError);
  }

  async function cargar({ agregar = false } = {}) {
    const numero = ++peticionActual;
    const offset = agregar ? mostradas : 0;
    botonMas.disabled = true;
    if (!agregar) mostrarEstado("Cargando noticias…");

    try {
      const respuesta = await RefugiaAPI.obtener("/api/noticias", parametros(offset));
      if (numero !== peticionActual) return;

      if (!agregar) {
        destacada.replaceChildren();
        grid.replaceChildren();
        mostradas = 0;
      }
      total = respuesta.total;

      respuesta.resultados.forEach((noticia, i) => {
        // La primera va arriba en grande (la API pone primero la destacada; si no hay, la más reciente)
        if (!agregar && i === 0) destacada.append(tarjeta(noticia, true));
        else grid.append(tarjeta(noticia, false));
      });
      mostradas += respuesta.resultados.length;

      if (total === 0) {
        const hayFiltros = campoBusqueda.value.trim() || campoVerificacion.value;
        mostrarEstado(hayFiltros ? "No hay noticias que coincidan con la búsqueda." : "Todavía no hay noticias publicadas.");
      } else {
        mostrarEstado("");
      }
      if (!agregar && (campoBusqueda.value.trim() || campoVerificacion.value)) {
        window.Accesibilidad?.anunciar?.(`${total} ${total === 1 ? "noticia encontrada" : "noticias encontradas"}.`);
      }
    } catch (error) {
      if (numero !== peticionActual) return;
      mostrarEstado(`No se pudieron cargar las noticias. ${error.message}`, true);
    } finally {
      if (numero === peticionActual) {
        botonMas.hidden = mostradas >= total;
        botonMas.disabled = false;
      }
    }
  }

  // ---------------- Eventos ----------------
  formulario.addEventListener("submit", (evento) => {
    evento.preventDefault();
    cargar();
  });
  campoVerificacion.addEventListener("change", () => cargar());
  // Si se borra la búsqueda (con la "x" del campo), se vuelve a mostrar todo
  campoBusqueda.addEventListener("search", () => cargar());
  botonMas.addEventListener("click", () => cargar({ agregar: true }));

  cargar();
})();
