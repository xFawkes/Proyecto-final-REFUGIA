/* =========================================================
   REFUGIA — Panel de administración (admin/inicio.html)
   ---------------------------------------------------------
   1. Llena los números del resumen con el "total" que responde la API.
      Uso:  <strong data-api-total="/api/noticias?publicada=false">000</strong>
      (las APIs de listado responden { "total": …, "resultados": [...] })
   2. Llena la tabla "Tareas pendientes" con las publicaciones del foro por revisar
      (GET /api/foro/publicaciones?moderacion=true&revision=pendiente).
   Requiere ../js/api.js
   ========================================================= */
(() => {
  "use strict";

  document.querySelectorAll("[data-api-total]").forEach(async (elemento) => {
    const [ruta, consulta = ""] = elemento.dataset.apiTotal.split("?");
    const parametros = Object.fromEntries(new URLSearchParams(consulta));
    try {
      const respuesta = await RefugiaAPI.obtener(ruta, { ...parametros, limite: 1 });
      elemento.textContent = respuesta.total;
    } catch {
      elemento.textContent = "—";
      elemento.title = "No se pudo consultar la API";
    }
  });

  // ---------------- Tareas pendientes ----------------
  const tabla = document.querySelector("#tareas-pendientes");
  if (!tabla) return;
  const fecha = new Intl.DateTimeFormat("es-CO", { day: "2-digit", month: "2-digit", year: "numeric" });

  function celda(texto) {
    const td = document.createElement("td");
    td.textContent = texto;
    return td;
  }

  function filaMensaje(texto) {
    const fila = document.createElement("tr");
    const td = celda(texto);
    td.colSpan = 4;
    fila.append(td);
    return fila;
  }

  function detalle(p) {
    if (p.oculta) return `Oculta por denuncias: ${p.titulo}`;
    if (p.denuncias_pendientes) return `${p.denuncias_pendientes} ${p.denuncias_pendientes === 1 ? "denuncia" : "denuncias"}: ${p.titulo}`;
    return `Publicación sin confirmar: ${p.titulo}`;
  }

  RefugiaAPI.obtener("/api/foro/publicaciones", { moderacion: true, revision: "pendiente", limite: 5 })
    .then((r) => {
      if (!r.resultados.length) return tabla.replaceChildren(filaMensaje("No hay tareas pendientes."));
      tabla.replaceChildren(...r.resultados.map((p) => {
        const fila = document.createElement("tr");
        const accion = document.createElement("td");
        const enlace = document.createElement("a");
        enlace.href = "foro.html";
        enlace.className = "tareas__accion";
        enlace.textContent = "Revisar";
        enlace.setAttribute("aria-label", `Revisar en el foro: ${p.titulo}`);
        accion.append(enlace);
        fila.append(celda("Foro"), celda(detalle(p)), celda(fecha.format(new Date(p.creado_en))), accion);
        return fila;
      }));
    })
    .catch(() => tabla.replaceChildren(filaMensaje("No se pudieron cargar las tareas.")));
})();
