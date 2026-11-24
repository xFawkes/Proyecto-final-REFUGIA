/* =========================================================
   REFUGIA — Cliente de la API (reutilizable en todas las páginas)
   ---------------------------------------------------------
   Cómo usarlo (antes del JavaScript de la página):
     <script src="js/api.js" defer></script>          (páginas de la raíz)
     <script src="../js/api.js" defer></script>       (páginas de admin/)

   Funciones (window.RefugiaAPI):
     obtener(ruta, parametros)   → GET     ej. obtener("/api/noticias", { q: "sismo" })
     crear(ruta, datos)          → POST    (envía JSON)
     actualizar(ruta, datos)     → PUT     (envía JSON)
     eliminar(ruta)              → DELETE
     subirArchivo(ruta, campo, archivo) → POST multipart (imágenes)
     recurso(ruta)               → URL de una imagen guardada como "img/…"
     formatearFecha("2026-10-20") → "20 de octubre de 2026"

   Si la API responde con error, la promesa falla con un Error que trae:
     error.message  → mensaje para mostrar
     error.detalles → { campo: ["mensaje"] } cuando los datos no son válidos (400)
     error.estado   → código HTTP (0 si no hubo conexión)
   ========================================================= */
(function () {
  "use strict";

  // Con Live Server (puerto 5500) la API está en el 5000; si la página la sirve Flask, es la misma dirección.
  const BASE =
    window.REFUGIA_API_BASE ??
    (["5500", "5501"].includes(location.port) ? "http://127.0.0.1:5000" : "");

  function construirUrl(ruta, parametros) {
    const url = new URL(BASE + ruta, location.origin);
    for (const [clave, valor] of Object.entries(parametros || {})) {
      if (valor === undefined || valor === null || valor === "") continue;
      (Array.isArray(valor) ? valor : [valor]).forEach((v) => url.searchParams.append(clave, v));
    }
    return url;
  }

  async function pedir(metodo, ruta, { parametros, datos, formulario } = {}) {
    const opciones = { method: metodo, headers: { Accept: "application/json" } };
    if (datos !== undefined) {
      opciones.headers["Content-Type"] = "application/json";
      opciones.body = JSON.stringify(datos);
    } else if (formulario) {
      opciones.body = formulario; // el navegador pone el Content-Type multipart
    }

    let respuesta;
    try {
      respuesta = await fetch(construirUrl(ruta, parametros), opciones);
    } catch {
      const error = new Error("No hay conexión con el servidor. ¿Está corriendo python main.py?");
      error.estado = 0;
      throw error;
    }

    const cuerpo = await respuesta.json().catch(() => null);
    if (!respuesta.ok) {
      const error = new Error(cuerpo?.error || `La API respondió ${respuesta.status}.`);
      error.estado = respuesta.status;
      error.detalles = cuerpo?.detalles || null;
      throw error;
    }
    return cuerpo;
  }

  function recurso(ruta) {
    if (!ruta) return "";
    if (/^https?:\/\//i.test(ruta)) return ruta;
    return construirUrl("/" + ruta.replace(/^\/+/, "")).href;
  }

  const formatoFecha = new Intl.DateTimeFormat("es-CO", { day: "numeric", month: "long", year: "numeric" });

  function formatearFecha(texto) {
    if (!texto) return "";
    const [anio, mes, dia] = texto.slice(0, 10).split("-").map(Number);
    return formatoFecha.format(new Date(anio, mes - 1, dia));
  }

  window.RefugiaAPI = {
    BASE,
    obtener: (ruta, parametros) => pedir("GET", ruta, { parametros }),
    crear: (ruta, datos) => pedir("POST", ruta, { datos }),
    actualizar: (ruta, datos) => pedir("PUT", ruta, { datos }),
    eliminar: (ruta) => pedir("DELETE", ruta),
    subirArchivo(ruta, campo, archivo) {
      const formulario = new FormData();
      formulario.append(campo, archivo);
      return pedir("POST", ruta, { formulario });
    },
    recurso,
    formatearFecha,
  };
})();
