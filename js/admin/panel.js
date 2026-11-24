/* =========================================================
   REFUGIA — Panel de administración (admin/inicio.html)
   ---------------------------------------------------------
   Llena los números del resumen con el "total" que responde la API.
   Uso:  <strong data-api-total="/api/noticias?publicada=false">000</strong>
   (las APIs de listado responden { "total": …, "resultados": [...] })
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
})();
