/* =========================================================
   REFUGIA — Voluntariados (consume GET /api/voluntariados)
   ---------------------------------------------------------
   Requiere js/api.js y que la API esté corriendo:  python main.py
   Los voluntariados se administran en admin/voluntariados.html.
   ========================================================= */
(() => {
  "use strict";

  const POR_PAGINA = 8;

  const $ = (selector) => document.querySelector(selector);
  const grid = $("#voluntariados-grid");
  const estado = $("#voluntariados-estado");
  const botonMas = $("#voluntariados-mas");
  const formulario = $("#voluntariados-busqueda");
  const campoBusqueda = $("#voluntariados-q");
  const campoModalidad = $("#voluntariados-modalidad");

  let mostrados = 0;
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

  function tarjeta(voluntariado) {
    const articulo = crear("article", "voluntariado");
    const idTitulo = `voluntariado-${voluntariado.id_voluntariado}`;
    articulo.setAttribute("aria-labelledby", idTitulo);

    const cuerpo = crear("div", "voluntariado__cuerpo");
    const titulo = crear("h2", "voluntariado__titulo", voluntariado.actividad);
    titulo.id = idTitulo;
    cuerpo.append(titulo);
    cuerpo.append(crear("p", "voluntariado__organizacion", `Organiza: ${voluntariado.organizacion}`));

    const etiquetas = crear("p", "voluntariado__etiquetas");
    etiquetas.append(crear("span", "voluntariado__etiqueta", voluntariado.modalidad_nombre));
    if (voluntariado.ubicacion) etiquetas.append(crear("span", "voluntariado__etiqueta", voluntariado.ubicacion));
    cuerpo.append(etiquetas);

    cuerpo.append(crear("p", "", voluntariado.descripcion));

    // Requisitos: desplegable, uno por línea
    if (voluntariado.requisitos) {
      const detalles = crear("details", "voluntariado__requisitos");
      detalles.append(crear("summary", "", "Requisitos"));
      const lista = crear("ul");
      voluntariado.requisitos
        .split("\n")
        .map((linea) => linea.replace(/^[-•*]\s*/, "").trim())
        .filter(Boolean)
        .forEach((linea) => lista.append(crear("li", "", linea)));
      detalles.append(lista);
      cuerpo.append(detalles);
    }

    if (voluntariado.enlace) {
      const enlace = crear("a", "voluntariado__enlace", "Da click aquí para ir a la página");
      enlace.href = voluntariado.enlace;
      enlace.target = "_blank";
      enlace.rel = "noopener noreferrer";
      // Para lectores de pantalla: a dónde lleva el enlace (empieza con el texto visible)
      enlace.setAttribute("aria-label", `Da click aquí para ir a la página de inscripción de "${voluntariado.actividad}" (se abre en otra pestaña)`);
      cuerpo.append(enlace);
    }

    articulo.append(cuerpo);
    if (voluntariado.imagen) {
      const imagen = crear("img", "voluntariado__imagen");
      imagen.src = RefugiaAPI.recurso(voluntariado.imagen);
      imagen.alt = voluntariado.imagen_alt || "";
      imagen.loading = "lazy";
      imagen.decoding = "async";
      articulo.append(imagen);
    } else {
      articulo.classList.add("voluntariado--sin-imagen");
    }
    return articulo;
  }

  // ---------------- Carga desde la API ----------------
  function hayFiltros() {
    return Boolean(campoBusqueda.value.trim() || campoModalidad.value);
  }

  function mostrarEstado(texto, esError = false) {
    estado.textContent = texto;
    estado.hidden = !texto;
    estado.classList.toggle("voluntariados__estado--error", esError);
  }

  async function cargar({ agregar = false } = {}) {
    const numero = ++peticionActual;
    const offset = agregar ? mostrados : 0;
    botonMas.disabled = true;
    if (!agregar) mostrarEstado("Cargando voluntariados…");

    try {
      const respuesta = await RefugiaAPI.obtener("/api/voluntariados", {
        q: campoBusqueda.value.trim(),
        modalidad: campoModalidad.value,
        limite: POR_PAGINA,
        offset,
      });
      if (numero !== peticionActual) return;

      if (!agregar) {
        grid.replaceChildren();
        mostrados = 0;
      }
      total = respuesta.total;
      respuesta.resultados.forEach((voluntariado) => grid.append(tarjeta(voluntariado)));
      mostrados += respuesta.resultados.length;

      if (total === 0) {
        mostrarEstado(hayFiltros() ? "No hay voluntariados que coincidan con la búsqueda." : "En este momento no hay voluntariados activos.");
      } else {
        mostrarEstado("");
      }
      if (!agregar && hayFiltros()) {
        window.Accesibilidad?.anunciar?.(`${total} ${total === 1 ? "voluntariado encontrado" : "voluntariados encontrados"}.`);
      }
    } catch (error) {
      if (numero !== peticionActual) return;
      mostrarEstado(`No se pudieron cargar los voluntariados. ${error.message}`, true);
    } finally {
      if (numero === peticionActual) {
        botonMas.hidden = mostrados >= total;
        botonMas.disabled = false;
      }
    }
  }

  // ---------------- Eventos ----------------
  formulario.addEventListener("submit", (evento) => {
    evento.preventDefault();
    cargar();
  });
  campoModalidad.addEventListener("change", () => cargar());
  campoBusqueda.addEventListener("search", () => cargar()); // la "x" del campo
  botonMas.addEventListener("click", () => cargar({ agregar: true }));

  cargar();
})();
