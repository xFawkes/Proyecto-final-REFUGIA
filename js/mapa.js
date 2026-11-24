/* =========================================================
   REFUGIA — Mapa de puntos de ayuda (Leaflet + OpenStreetMap + API FastAPI)
   ---------------------------------------------------------
   Requiere que la API esté corriendo:  uvicorn api.main:app --reload
   Leaflet se carga desde el CDN en mapa.html. No necesita API key.
   ========================================================= */
(() => {
  "use strict";

  // ---------------- Configuración ----------------
  // Si la página se abre con Live Server (puerto 5500) la API está en el 8000.
  // Si se abre desde la misma API (http://localhost:8000/mapa.html) se usa la misma dirección.
  const API_BASE =
    window.REFUGIA_API_BASE ??
    (["5500", "5501"].includes(location.port) ? "http://localhost:8000" : "");

  const BOGOTA = { lat: 4.65, lng: -74.1 };
  const IMAGEN_POR_DEFECTO = "img/mapa/centro-acopio.png";

  // Color e ícono (Bootstrap Icons) de cada tipo de lugar
  const ESTILO_TIPO = {
    albergue: { color: "#1C5568", icono: "bi-house-heart-fill" },
    centro_salud: { color: "#2E7D32", icono: "bi-heart-pulse-fill" },
    hospital: { color: "#B3261E", icono: "bi-hospital-fill" },
    centro_acopio: { color: "#E8BA63", icono: "bi-box-seam-fill", oscuro: true },
    otro: { color: "#694E1C", icono: "bi-info-circle-fill" },
  };

  // Imagen por tipo cuando el punto no trae una propia (cámbialas por las tuyas)
  const IMAGEN_POR_TIPO = {
    albergue: IMAGEN_POR_DEFECTO,
    centro_salud: IMAGEN_POR_DEFECTO,
    hospital: IMAGEN_POR_DEFECTO,
    centro_acopio: IMAGEN_POR_DEFECTO,
    otro: IMAGEN_POR_DEFECTO,
  };

  const CLAVE_GUARDADOS = "refugia:guardados";
  const MAX_SUGERENCIAS = 8;

  // ---------------- Estado ----------------
  const estado = {
    mapa: null,
    marcadores: new Map(), // id -> { marcador, punto }
    puntos: [],
    total: 0,
    totalGeneral: 0,
    seleccionado: null,
    ubicacion: null,
    marcadorUsuario: null,
    peticion: 0,
    activo: -1, // índice de la sugerencia resaltada con el teclado
  };

  // ---------------- Utilidades ----------------
  const $ = (selector) => document.querySelector(selector);
  const $$ = (selector) => [...document.querySelectorAll(selector)];

  const esc = (texto) =>
    String(texto ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

  const anunciar = (texto, opciones) => window.Accesibilidad?.anunciar(texto, opciones);

  function debounce(fn, ms) {
    let t;
    return (...args) => {
      clearTimeout(t);
      t = setTimeout(() => fn(...args), ms);
    };
  }

  function formatearDistancia(km) {
    if (km == null) return "";
    return km < 1 ? `${Math.round(km * 1000)} m` : `${km.toLocaleString("es-CO", { maximumFractionDigits: 1 })} km`;
  }

  function soloDigitos(telefono) {
    return String(telefono || "").replace(/\D/g, "");
  }

  async function api(ruta, parametros) {
    const url = new URL(API_BASE + ruta, location.href);
    if (parametros) url.search = parametros.toString();
    const respuesta = await fetch(url);
    if (!respuesta.ok) throw new Error(`La API respondió ${respuesta.status}`);
    return respuesta.json();
  }

  // ---------------- Guardados (en este navegador) ----------------
  function leerGuardados() {
    try {
      return JSON.parse(localStorage.getItem(CLAVE_GUARDADOS) || "[]");
    } catch {
      return [];
    }
  }

  function escribirGuardados(ids) {
    try {
      localStorage.setItem(CLAVE_GUARDADOS, JSON.stringify(ids));
    } catch {
      anunciar("No se pudo guardar: el navegador bloquea el almacenamiento.");
    }
  }

  const estaGuardado = (id) => leerGuardados().includes(id);

  // =========================================================
  // Filtros
  // =========================================================
  function construirParametros() {
    const p = new URLSearchParams();
    const q = $("#busqueda").value.trim();
    if (q) p.set("q", q);

    $$("#filtro-tipos input:checked").forEach((i) => p.append("tipo", i.value));
    $$("#filtro-servicios input:checked").forEach((i) => p.append("servicio", i.value));
    $$('input[name="verificacion"]:checked').forEach((i) => p.append("verificacion", i.value));

    if ($("#filtro-abierto").checked) p.set("abierto_ahora", "true");
    if ($("#filtro-cupos").checked) p.set("con_cupos", "true");
    if ($("#filtro-gratuito").checked) p.set("gratuito", "true");
    if ($("#filtro-confianza").value) p.set("confianza_min", $("#filtro-confianza").value);
    if ($("#filtro-guardados").checked) p.set("ids", leerGuardados().join(","));

    if (estado.ubicacion) {
      p.set("lat", estado.ubicacion.lat);
      p.set("lng", estado.ubicacion.lng);
      if ($("#filtro-cerca").checked) p.set("radio_km", $("#filtro-radio").value);
    }
    p.set("limite", "500");
    return p;
  }

  function contarFiltrosActivos() {
    let n = $$("#filtros-busqueda input[type=checkbox]:checked").length;
    if ($("#filtro-confianza").value) n++;
    return n;
  }

  async function actualizar({ ajustarVista = false } = {}) {
    const id = ++estado.peticion;
    let datos;
    try {
      datos = await api("/api/puntos", construirParametros());
    } catch (error) {
      console.error(error);
      anunciar("No se pudo conectar con el servidor de REFUGIA. Revisa que la API esté encendida.");
      return;
    }
    if (id !== estado.peticion) return; // llegó una respuesta más nueva

    estado.puntos = datos.resultados;
    estado.total = datos.total;

    pintarMarcadores();
    pintarSugerencias();
    pintarResumen();
    if (ajustarVista) ajustarMapa();
  }

  function pintarResumen() {
    const n = estado.total;
    const texto = n === 1 ? "1 lugar encontrado" : `${n} lugares encontrados`;
    $("#filtros-resumen").textContent =
      estado.totalGeneral ? `Mostrando ${n} de ${estado.totalGeneral} lugares` : texto;
    $("#estado-busqueda").textContent = texto;

    const activos = contarFiltrosActivos();
    const contador = $("#filtros-contador");
    contador.hidden = activos === 0;
    contador.textContent = activos;
    $("#btn-filtros").setAttribute(
      "aria-label",
      activos ? `Mostrar filtros (${activos} activos)` : "Mostrar filtros"
    );
  }

  async function cargarCatalogos() {
    const [tipos, servicios] = await Promise.all([api("/api/tipos"), api("/api/servicios")]);
    estado.totalGeneral = tipos.reduce((suma, t) => suma + t.total, 0);

    $("#filtro-tipos").innerHTML = tipos
      .map((t) => {
        const e = ESTILO_TIPO[t.clave];
        return `<label class="chip" style="--color:${e.color}${e.oscuro ? ";--texto:#694E1C" : ""}">
            <input type="checkbox" value="${esc(t.clave)}">
            <i class="bi ${e.icono}" aria-hidden="true"></i>
            <span>${esc(t.plural)} <span class="chip__total">(${t.total})</span></span>
          </label>`;
      })
      .join("");

    $("#filtro-servicios").innerHTML = servicios
      .map((s) => `<label class="chip chip--servicio"><input type="checkbox" value="${esc(s.clave)}"><span>${esc(s.nombre)}</span></label>`)
      .join("");

    $("#leyenda").innerHTML = tipos
      .map((t) => {
        const e = ESTILO_TIPO[t.clave];
        return `<li class="leyenda__item"><span class="leyenda__icono" style="--color:${e.color}${e.oscuro ? ";--icono:#694E1C" : ""}">
            <i class="bi ${e.icono}" aria-hidden="true"></i></span>${esc(t.plural)}</li>`;
      })
      .join("");
  }

  function limpiarFiltros() {
    $$("#filtros-busqueda input[type=checkbox]").forEach((i) => (i.checked = false));
    $("#filtro-confianza").value = "";
    $("#filtro-radio").value = "5";
    actualizar({ ajustarVista: true });
    anunciar("Filtros eliminados");
  }

  // =========================================================
  // Panel de filtros y lista de sugerencias
  // =========================================================
  function abrirFiltros(abrir) {
    $("#filtros-busqueda").hidden = !abrir;
    $("#btn-filtros").setAttribute("aria-expanded", String(abrir));
    if (abrir) cerrarSugerencias();
    actualizarFormaBuscador();
  }

  function actualizarFormaBuscador() {
    const abierto = !$("#filtros-busqueda").hidden || !$("#resultados-busqueda").hidden;
    $("#form-busqueda").classList.toggle("buscador--abierto", abierto);
  }

  function pintarSugerencias() {
    const lista = $("#resultados-busqueda");
    const q = $("#busqueda").value.trim();
    if (!q || document.activeElement !== $("#busqueda")) {
      cerrarSugerencias();
      return;
    }

    estado.activo = -1;
    $("#busqueda").removeAttribute("aria-activedescendant");

    if (!estado.puntos.length) {
      lista.innerHTML = `<li class="resultado resultado--vacio" role="option" aria-disabled="true">
          No encontramos lugares para «${esc(q)}». Prueba con otra palabra o revisa los filtros.</li>`;
    } else {
      lista.innerHTML = estado.puntos
        .slice(0, MAX_SUGERENCIAS)
        .map((p, i) => {
          const e = ESTILO_TIPO[p.tipo];
          const detalles = [
            p.tipo_nombre,
            p.barrio || p.localidad,
            p.distancia_km != null ? formatearDistancia(p.distancia_km) : null,
            p.abierto_ahora ? "Abierto" : "Cerrado",
          ].filter(Boolean);
          return `<li class="resultado" role="option" id="sugerencia-${i}" data-id="${p.id}" aria-selected="false">
              <span class="resultado__icono" style="--color:${e.color}${e.oscuro ? ";--icono:#694E1C" : ""}">
                <i class="bi ${e.icono}" aria-hidden="true"></i></span>
              <span class="resultado__texto">
                <span class="resultado__nombre">${esc(p.nombre)}</span>
                <span class="resultado__detalle">${esc(detalles.join(" · "))}</span>
              </span>
            </li>`;
        })
        .join("");
      if (estado.total > MAX_SUGERENCIAS) {
        lista.insertAdjacentHTML(
          "beforeend",
          `<li class="resultado resultado--nota" role="presentation">Y ${estado.total - MAX_SUGERENCIAS} más en el mapa</li>`
        );
      }
    }
    lista.hidden = false;
    $("#busqueda").setAttribute("aria-expanded", "true");
    $("#filtros-busqueda").hidden = true;
    $("#btn-filtros").setAttribute("aria-expanded", "false");
    actualizarFormaBuscador();
  }

  function cerrarSugerencias() {
    $("#resultados-busqueda").hidden = true;
    $("#busqueda").setAttribute("aria-expanded", "false");
    $("#busqueda").removeAttribute("aria-activedescendant");
    estado.activo = -1;
    actualizarFormaBuscador();
  }

  function moverActivo(paso) {
    const opciones = $$("#resultados-busqueda .resultado[data-id]");
    if (!opciones.length) return;
    estado.activo = (estado.activo + paso + opciones.length) % opciones.length;
    opciones.forEach((o, i) => o.setAttribute("aria-selected", String(i === estado.activo)));
    const activa = opciones[estado.activo];
    $("#busqueda").setAttribute("aria-activedescendant", activa.id);
    activa.scrollIntoView({ block: "nearest" });
  }

  // =========================================================
  // Mapa (Leaflet + OpenStreetMap)
  // =========================================================
  function mostrarMensajeMapa(texto) {
    let mensaje = $("#mapa-mensaje");
    if (!mensaje) {
      mensaje = document.createElement("p");
      mensaje.id = "mapa-mensaje";
      mensaje.className = "mapa__placeholder";
      $("#mapa").append(mensaje);
    }
    mensaje.textContent = texto;
  }

  function iniciarMapa() {
    if (!window.L) {
      mostrarMensajeMapa("No se pudo cargar el mapa (¿sin conexión?). Puedes seguir usando el buscador y los filtros.");
      return;
    }
    $("#mapa-mensaje")?.remove();

    estado.mapa = L.map("mapa", { zoomControl: false }).setView([BOGOTA.lat, BOGOTA.lng], 11);

    // Teselas de OpenStreetMap: la atribución es obligatoria
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(estado.mapa);
    estado.mapa.attributionControl.setPrefix(
      '<a href="https://leafletjs.com" title="Librería de mapas">Leaflet</a>'
    );

    agregarControlCercaDeMi();
    L.control.zoom({ position: "bottomright", zoomInTitle: "Acercar", zoomOutTitle: "Alejar" }).addTo(estado.mapa);

    pintarMarcadores();
    pintarUsuario();
    ajustarMapa();
  }

  function crearIcono(punto) {
    const e = ESTILO_TIPO[punto.tipo];
    const icono = e.oscuro ? ";--icono:#694E1C" : "";
    return L.divIcon({
      className: "marcador-contenedor",
      html: `<div class="marcador" style="--color:${e.color}${icono}"><i class="bi ${e.icono}" aria-hidden="true"></i></div>`,
      iconSize: [0, 0], // el tamaño lo da el CSS; la punta queda sobre el lugar
      iconAnchor: [0, 0],
    });
  }

  function pintarMarcadores() {
    if (!estado.mapa) return;

    // El lugar seleccionado se sigue mostrando aunque los filtros lo oculten
    const visibles = new Map(estado.puntos.map((p) => [p.id, p]));
    if (estado.seleccionado && !visibles.has(estado.seleccionado.id)) {
      visibles.set(estado.seleccionado.id, estado.seleccionado);
    }

    for (const [id, registro] of estado.marcadores) {
      if (!visibles.has(id)) {
        registro.marcador.remove();
        estado.marcadores.delete(id);
      }
    }

    for (const [id, punto] of visibles) {
      const existente = estado.marcadores.get(id);
      if (existente) {
        existente.punto = punto;
        continue;
      }
      // keyboard: true -> el marcador se alcanza con Tab y se abre con Enter
      const marcador = L.marker([punto.lat, punto.lng], {
        icon: crearIcono(punto),
        title: `${punto.nombre} (${punto.tipo_nombre})`,
        alt: `${punto.nombre} (${punto.tipo_nombre})`,
        keyboard: true,
        riseOnHover: true,
      })
        .on("click", () => seleccionar(id, { origen: "mapa" }))
        // Leaflet solo abre con Enter los marcadores con popup: aquí se hace a mano
        .on("keypress", (e) => {
          if (e.originalEvent.key === "Enter" || e.originalEvent.key === " ") {
            e.originalEvent.preventDefault();
            seleccionar(id, { origen: "mapa" });
          }
        })
        .addTo(estado.mapa);
      estado.marcadores.set(id, { marcador, punto });
    }
    if (estado.seleccionado) resaltarMarcador(estado.seleccionado.id, true);
  }

  function resaltarMarcador(id, resaltar) {
    for (const [otroId, r] of estado.marcadores) {
      const activo = resaltar && otroId === id;
      r.marcador.getElement()?.querySelector(".marcador")?.classList.toggle("marcador--seleccionado", activo);
      r.marcador.setZIndexOffset(activo ? 1000 : 0);
    }
  }

  function ajustarMapa() {
    if (!estado.mapa) return;
    const puntos = estado.puntos.map((p) => ({ lat: p.lat, lng: p.lng }));
    if (estado.ubicacion && $("#filtro-cerca").checked) puntos.push(estado.ubicacion);
    if (!puntos.length) return;
    if (puntos.length === 1) {
      estado.mapa.setView(puntos[0], 15);
      return;
    }
    estado.mapa.fitBounds(L.latLngBounds(puntos), { padding: [60, 60], maxZoom: 16 });
  }

  // =========================================================
  // Cerca de mí
  // =========================================================
  function agregarControlCercaDeMi() {
    const Control = L.Control.extend({
      options: { position: "bottomright" },
      onAdd() {
        const boton = L.DomUtil.create("button", "mapa__control");
        boton.type = "button";
        boton.id = "btn-cerca-de-mi";
        boton.setAttribute("aria-label", "Mostrar lugares cerca de mí");
        boton.title = "Cerca de mí";
        boton.innerHTML = '<i class="bi bi-crosshair" aria-hidden="true"></i>';
        L.DomEvent.disableClickPropagation(boton); // que el clic no mueva el mapa
        L.DomEvent.on(boton, "click", () => activarCercaDeMi());
        return boton;
      },
    });
    new Control().addTo(estado.mapa);
  }

  function obtenerUbicacion() {
    return new Promise((resolve, reject) => {
      if (!navigator.geolocation) {
        reject({ code: 0 });
        return;
      }
      navigator.geolocation.getCurrentPosition(
        (pos) => resolve({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
        reject,
        { enableHighAccuracy: true, timeout: 12000, maximumAge: 60000 }
      );
    });
  }

  async function activarCercaDeMi() {
    const casilla = $("#filtro-cerca");
    casilla.checked = true;
    anunciar("Buscando tu ubicación…");
    try {
      estado.ubicacion = await obtenerUbicacion();
    } catch (error) {
      casilla.checked = false;
      const mensajes = {
        0: "Tu navegador no permite obtener la ubicación.",
        1: "No diste permiso para usar tu ubicación. Puedes activarlo en la configuración del navegador.",
        2: "No fue posible determinar tu ubicación.",
        3: "Se agotó el tiempo para obtener tu ubicación. Intenta de nuevo.",
      };
      anunciar(mensajes[error.code] || mensajes[2]);
      return;
    }
    pintarUsuario();
    await actualizar({ ajustarVista: true });
    const radio = $("#filtro-radio").value;
    anunciar(
      estado.total
        ? `${estado.total} ${estado.total === 1 ? "lugar" : "lugares"} a menos de ${radio} km de ti`
        : `No hay lugares a menos de ${radio} km. Prueba con una distancia mayor.`
    );
    if (estado.seleccionado) seleccionar(estado.seleccionado.id, { origen: "silencioso" });
  }

  function pintarUsuario() {
    if (!estado.mapa || !estado.ubicacion) return;
    const posicion = [estado.ubicacion.lat, estado.ubicacion.lng];
    if (!estado.marcadorUsuario) {
      estado.marcadorUsuario = L.marker(posicion, {
        icon: L.divIcon({ className: "marcador-contenedor", html: '<div class="marcador-usuario"></div>', iconSize: [0, 0] }),
        title: "Tu ubicación",
        alt: "Tu ubicación",
        interactive: false,
        keyboard: false,
        zIndexOffset: 2000,
      }).addTo(estado.mapa);
    } else {
      estado.marcadorUsuario.setLatLng(posicion);
    }
  }

  // =========================================================
  // Panel de detalle
  // =========================================================
  async function seleccionar(id, { origen = "lista" } = {}) {
    const p = new URLSearchParams();
    if (estado.ubicacion) {
      p.set("lat", estado.ubicacion.lat);
      p.set("lng", estado.ubicacion.lng);
    }
    let punto;
    try {
      punto = await api(`/api/puntos/${id}`, p);
    } catch (error) {
      console.error(error);
      anunciar("No se pudo cargar la información de este lugar.");
      return;
    }
    estado.seleccionado = punto;
    pintarDetalle(punto);
    pintarMarcadores(); // por si el lugar no estaba entre los filtrados
    resaltarMarcador(punto.id, true);

    if (estado.mapa && origen !== "silencioso") {
      estado.mapa.setView([punto.lat, punto.lng], Math.max(estado.mapa.getZoom(), 15));
    }

    const url = new URL(location.href);
    url.searchParams.set("punto", punto.id);
    history.replaceState(null, "", url);

    if (origen === "lista" || origen === "mapa") {
      const titulo = $("#detalle-titulo");
      const pantallaPequena = window.matchMedia("(max-width: 900px)").matches;
      titulo.focus({ preventScroll: !pantallaPequena });
      if (pantallaPequena) $("#detalle-ubicacion").scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  function pintarEstrellas(valor) {
    let html = "";
    for (let i = 1; i <= 5; i++) {
      const clase = valor >= i - 0.25 ? "bi-star-fill" : valor >= i - 0.75 ? "bi-star-half" : "bi-star";
      html += `<i class="bi ${clase}" aria-hidden="true"></i>`;
    }
    return html;
  }

  function pintarDetalle(p) {
    $("#detalle-vacio").hidden = true;
    $("#detalle-ficha").hidden = false;

    const imagen = $("#detalle-imagen");
    imagen.src = p.imagen || IMAGEN_POR_TIPO[p.tipo] || IMAGEN_POR_DEFECTO;
    imagen.alt = `Foto de ${p.nombre}`;

    const e = ESTILO_TIPO[p.tipo];
    const tipo = $("#detalle-tipo");
    tipo.textContent = p.tipo_nombre;
    tipo.style.setProperty("--color", e.color);
    tipo.classList.toggle("etiqueta--oscura", Boolean(e.oscuro));

    const verificacion = $("#detalle-verificacion");
    verificacion.textContent = p.verificacion_nombre;
    verificacion.dataset.nivel = p.verificacion;

    $("#detalle-titulo").textContent = p.nombre;

    const puntaje = p.confianza.toFixed(1);
    $("#detalle-estrellas").innerHTML = pintarEstrellas(p.confianza);
    $("#detalle-estrellas").setAttribute("aria-label", `Calificación: ${puntaje} de 5`);
    $("#detalle-puntaje").textContent = puntaje;

    $("#detalle-descripcion").textContent = p.descripcion || "";
    $("#detalle-descripcion").hidden = !p.descripcion;

    const zona = [p.barrio, p.localidad].filter(Boolean).join(", ");
    $("#detalle-direccion").textContent = zona ? `${p.direccion} (${zona})` : p.direccion;
    const distancia = $("#detalle-distancia");
    distancia.hidden = p.distancia_km == null;
    distancia.textContent = p.distancia_km != null ? `· a ${formatearDistancia(p.distancia_km)} de ti` : "";

    $("#detalle-horario").textContent = p.horario_texto;
    const abierto = $("#detalle-abierto");
    abierto.textContent = p.abierto_ahora ? "Abierto ahora" : "Cerrado ahora";
    abierto.classList.toggle("estado-apertura--abierto", p.abierto_ahora);

    const itemCupos = $("#detalle-item-cupos");
    itemCupos.hidden = p.cupos_disponibles == null;
    if (p.cupos_disponibles != null) {
      const cupos = $("#detalle-cupos");
      cupos.textContent =
        p.cupos_disponibles > 0
          ? `${p.cupos_disponibles} disponibles de ${p.capacidad}`
          : `Sin cupos disponibles (capacidad: ${p.capacidad})`;
      cupos.classList.toggle("detalle__valor--alerta", p.cupos_disponibles === 0);
    }

    $("#detalle-costo").textContent = p.gratuito ? "No" : p.costo_detalle || "Sí";

    const telefono = $("#detalle-telefono");
    if (p.telefono) {
      telefono.href = `tel:+57${soloDigitos(p.telefono)}`;
      telefono.textContent = p.telefono;
    } else {
      telefono.removeAttribute("href");
      telefono.textContent = "No disponible";
    }

    const web = $("#detalle-web");
    if (p.sitio_web) {
      web.href = p.sitio_web;
      web.target = "_blank";
      web.rel = "noopener noreferrer";
      web.textContent = p.sitio_web.replace(/^https?:\/\//, "").replace(/\/$/, "");
    } else {
      web.removeAttribute("href");
      web.removeAttribute("target");
      web.textContent = "No disponible";
    }

    $("#detalle-item-servicios").hidden = !p.servicios.length;
    $("#detalle-servicios").innerHTML = p.servicios.map((s) => `<li>${esc(s.nombre)}</li>`).join("");

    $("#detalle-fuente").textContent = p.fuente || "No informada";
    const fecha = new Date(p.actualizado_en);
    const actualizado = $("#detalle-actualizado");
    actualizado.dateTime = p.actualizado_en;
    actualizado.textContent = isNaN(fecha)
      ? p.actualizado_en
      : fecha.toLocaleString("es-CO", { dateStyle: "medium", timeStyle: "short" });

    pintarBotonGuardar();
    pintarBotonContactar();
    cerrarMenuContacto();
  }

  /** Texto que se lee con el botón "Leer en voz alta" en esta página. */
  function textoParaLeer() {
    const p = estado.seleccionado;
    if (!p) {
      return `Mapa de puntos de ayuda. Hay ${estado.total} lugares en el mapa. ` +
        "Usa el buscador para encontrar albergues, centros de salud, hospitales o centros de acopio, " +
        "y selecciona un lugar para escuchar su información.";
    }
    const partes = [
      `${p.nombre}. ${p.tipo_nombre}. ${p.verificacion_nombre}.`,
      `Índice de confianza: ${p.confianza.toFixed(1).replace(".", ",")} de 5.`,
      p.descripcion,
      `Dirección: ${p.direccion}${p.barrio ? ", barrio " + p.barrio : ""}.`,
      p.distancia_km != null ? `Está a ${formatearDistancia(p.distancia_km)} de ti.` : "",
      `Horario: ${p.horario_texto} ${p.abierto_ahora ? "Ahora está abierto." : "Ahora está cerrado."}`,
      p.cupos_disponibles != null
        ? p.cupos_disponibles > 0 ? `Tiene ${p.cupos_disponibles} cupos disponibles.` : "No tiene cupos disponibles."
        : "",
      p.gratuito ? "La ayuda no tiene costo." : `Costo: ${p.costo_detalle || "con costo"}.`,
      p.telefono ? `Teléfono: ${p.telefono}.` : "",
      p.servicios.length ? `Servicios: ${p.servicios.map((s) => s.nombre).join(", ")}.` : "",
    ];
    return partes.filter(Boolean).join(" ");
  }

  // =========================================================
  // Acciones: Cómo llegar, Guardar, Contactar, Compartir
  // =========================================================
  function comoLlegar() {
    const p = estado.seleccionado;
    if (!p) return;
    const url = new URL("https://www.google.com/maps/dir/");
    url.searchParams.set("api", "1");
    url.searchParams.set("destination", `${p.lat},${p.lng}`);
    if (estado.ubicacion) url.searchParams.set("origin", `${estado.ubicacion.lat},${estado.ubicacion.lng}`);
    window.open(url, "_blank", "noopener");
  }

  function pintarBotonGuardar() {
    const guardado = estado.seleccionado && estaGuardado(estado.seleccionado.id);
    const boton = $("#accion-guardar");
    boton.setAttribute("aria-pressed", String(Boolean(guardado)));
    boton.querySelector(".accion__texto").textContent = guardado ? "Guardado" : "Guardar";
    const icono = boton.querySelector("i");
    icono.className = `bi ${guardado ? "bi-bookmark-check-fill" : "bi-bookmark"}`;
  }

  function alternarGuardado() {
    const p = estado.seleccionado;
    if (!p) return;
    const ids = leerGuardados();
    const guardado = ids.includes(p.id);
    escribirGuardados(guardado ? ids.filter((i) => i !== p.id) : [...ids, p.id]);
    pintarBotonGuardar();
    anunciar(guardado ? `${p.nombre} se quitó de tus lugares guardados` : `${p.nombre} se guardó en tus lugares`);
    if ($("#filtro-guardados").checked) actualizar();
  }

  function canalesDeContacto(p) {
    const canales = [];
    if (p.telefono) {
      canales.push({ texto: "Llamar", etiqueta: `Llamar al ${p.telefono}`, icono: "bi-telephone-fill", url: `tel:+57${soloDigitos(p.telefono)}` });
    }
    if (p.whatsapp) {
      const mensaje = `Hola, encontré "${p.nombre}" en REFUGIA y quisiera más información.`;
      canales.push({
        texto: "WhatsApp",
        etiqueta: "Escribir por WhatsApp (se abre en otra pestaña)",
        icono: "bi-whatsapp",
        url: `https://wa.me/57${soloDigitos(p.whatsapp)}?text=${encodeURIComponent(mensaje)}`,
        nuevaPestana: true,
      });
    }
    if (p.correo) {
      const asunto = `Consulta desde REFUGIA: ${p.nombre}`;
      canales.push({ texto: "Correo", etiqueta: `Enviar correo a ${p.correo}`, icono: "bi-envelope-fill", url: `mailto:${p.correo}?subject=${encodeURIComponent(asunto)}` });
    }
    return canales;
  }

  function pintarBotonContactar() {
    const sinCanales = !canalesDeContacto(estado.seleccionado).length;
    const boton = $("#accion-contactar");
    boton.setAttribute("aria-disabled", String(sinCanales));
    boton.classList.toggle("accion--deshabilitada", sinCanales);
  }

  function cerrarMenuContacto() {
    $("#menu-contacto").hidden = true;
    $("#accion-contactar").setAttribute("aria-expanded", "false");
  }

  function contactar() {
    const p = estado.seleccionado;
    if (!p) return;
    const canales = canalesDeContacto(p);
    if (!canales.length) {
      anunciar("Este lugar no tiene canales de contacto registrados.");
      return;
    }
    if (canales.length === 1) {
      abrirCanal(canales[0]);
      return;
    }
    const menu = $("#menu-contacto");
    if (!menu.hidden) {
      cerrarMenuContacto();
      return;
    }
    menu.innerHTML = canales
      .map(
        (c) => `<li><a class="menu-contacto__opcion" href="${esc(c.url)}" aria-label="${esc(c.etiqueta)}"${c.nuevaPestana ? ' target="_blank" rel="noopener noreferrer"' : ""}>
            <i class="bi ${c.icono}" aria-hidden="true"></i> ${esc(c.texto)}</a></li>`
      )
      .join("");
    menu.hidden = false;
    $("#accion-contactar").setAttribute("aria-expanded", "true");
    menu.querySelector("a")?.focus();
  }

  function abrirCanal(canal) {
    if (canal.nuevaPestana) window.open(canal.url, "_blank", "noopener");
    else location.href = canal.url;
  }

  async function compartir() {
    const p = estado.seleccionado;
    if (!p) return;
    const url = new URL(location.href);
    url.search = "";
    url.hash = "";
    url.searchParams.set("punto", p.id);
    const datos = {
      title: `${p.nombre} | REFUGIA`,
      text: `${p.nombre} (${p.tipo_nombre}) — ${p.direccion}. ${p.horario_texto}`,
      url: url.toString(),
    };

    if (navigator.share) {
      try {
        await navigator.share(datos);
        return;
      } catch (error) {
        if (error.name === "AbortError") return; // el usuario canceló
      }
    }
    try {
      await navigator.clipboard.writeText(datos.url);
      anunciar("Enlace copiado. Ya puedes pegarlo en un mensaje.");
    } catch {
      anunciar(`Copia este enlace: ${datos.url}`);
    }
  }

  // =========================================================
  // Eventos
  // =========================================================
  function enlazarEventos() {
    const entrada = $("#busqueda");
    const buscarConRetraso = debounce(() => actualizar(), 250);

    entrada.addEventListener("input", () => {
      buscarConRetraso();
      if (!entrada.value.trim()) cerrarSugerencias();
    });
    entrada.addEventListener("focus", () => {
      if (entrada.value.trim()) pintarSugerencias();
    });
    entrada.addEventListener("keydown", (e) => {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        if ($("#resultados-busqueda").hidden) pintarSugerencias();
        moverActivo(1);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        moverActivo(-1);
      } else if (e.key === "Escape") {
        cerrarSugerencias();
      }
    });

    // Enter: abre la sugerencia resaltada o la primera
    $("#form-busqueda").addEventListener("submit", async (e) => {
      e.preventDefault();
      const opciones = $$("#resultados-busqueda .resultado[data-id]");
      const elegida = opciones[estado.activo] || null;
      if (elegida) {
        cerrarSugerencias();
        seleccionar(Number(elegida.dataset.id));
        return;
      }
      await actualizar({ ajustarVista: true });
      cerrarSugerencias();
      if (estado.puntos.length === 1) seleccionar(estado.puntos[0].id);
      else anunciar(estado.total ? `${estado.total} lugares en el mapa` : "No se encontraron lugares");
    });

    $("#resultados-busqueda").addEventListener("click", (e) => {
      const opcion = e.target.closest(".resultado[data-id]");
      if (!opcion) return;
      cerrarSugerencias();
      seleccionar(Number(opcion.dataset.id));
    });
    // Evita que el input pierda el foco antes del clic en una sugerencia
    $("#resultados-busqueda").addEventListener("mousedown", (e) => e.preventDefault());

    $("#btn-filtros").addEventListener("click", () => abrirFiltros($("#filtros-busqueda").hidden));

    $("#filtros-busqueda").addEventListener("change", (e) => {
      if (e.target.id === "filtro-cerca") {
        if (e.target.checked && !estado.ubicacion) {
          activarCercaDeMi();
          return;
        }
      }
      if (e.target.id === "filtro-radio" && !$("#filtro-cerca").checked) return;
      actualizar({ ajustarVista: true });
    });
    $("#btn-limpiar-filtros").addEventListener("click", limpiarFiltros);

    // Cerrar paneles con Escape o al hacer clic fuera
    document.addEventListener("keydown", (e) => {
      if (e.key !== "Escape") return;
      if (!$("#filtros-busqueda").hidden) {
        abrirFiltros(false);
        $("#btn-filtros").focus();
      }
      if (!$("#menu-contacto").hidden) {
        cerrarMenuContacto();
        $("#accion-contactar").focus();
      }
    });
    document.addEventListener("click", (e) => {
      if (!e.target.closest("#form-busqueda")) {
        if (!$("#filtros-busqueda").hidden) abrirFiltros(false);
        cerrarSugerencias();
      }
      if (!e.target.closest(".accion-contenedor")) cerrarMenuContacto();
    });

    $("#accion-como-llegar").addEventListener("click", comoLlegar);
    $("#accion-guardar").addEventListener("click", alternarGuardado);
    $("#accion-contactar").addEventListener("click", contactar);
    $("#accion-compartir").addEventListener("click", compartir);

    window.Accesibilidad?.definirLectura(textoParaLeer);
  }

  // =========================================================
  // Inicio
  // =========================================================
  async function iniciar() {
    enlazarEventos();
    iniciarMapa(); // no se espera: la búsqueda funciona aunque el mapa tarde o falle

    try {
      await cargarCatalogos();
    } catch (error) {
      console.error(error);
      anunciar("No se pudo conectar con el servidor de REFUGIA. Revisa que la API esté encendida.");
      return;
    }
    await actualizar({ ajustarVista: true });

    // Enlace compartido: mapa.html?punto=12
    const idCompartido = Number(new URLSearchParams(location.search).get("punto"));
    if (idCompartido) seleccionar(idCompartido, { origen: "inicio" });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", iniciar);
  else iniciar();
})();
