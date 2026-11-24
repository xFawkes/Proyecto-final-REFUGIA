/* =========================================================
   REFUGIA — Moderación del foro (admin/foro.html)
   ---------------------------------------------------------
     Listar            → GET    /api/foro/publicaciones?moderacion=true&revision=pendiente
     Ver denuncias     → GET    /api/foro/publicaciones/<id>?moderacion=true
     Aprobar           → PUT    /api/foro/publicaciones/<id>  {"verificacion": "confirmada", "oculta": false}
     Ocultar / mostrar → PUT    /api/foro/publicaciones/<id>  {"oculta": true | false}
     Eliminar          → DELETE /api/foro/publicaciones/<id>
     Eliminar respuesta→ DELETE /api/foro/respuestas/<id>
   Requiere ../js/api.js y que la API esté corriendo:  python main.py
   ========================================================= */
(() => {
  "use strict";

  const POR_PAGINA = 10;
  const $ = (selector, raiz = document) => raiz.querySelector(selector);
  const contenedor = $("#moderacion");
  const estado = $("#moderacion-estado");
  const botonMas = $("#moderacion-mas");
  const aviso = $("#aviso");
  const dialogo = $("#dialogo-confirmar");
  const fecha = new Intl.DateTimeFormat("es-CO", { day: "2-digit", month: "2-digit", year: "numeric" });
  const fechaHora = new Intl.DateTimeFormat("es-CO", { dateStyle: "medium", timeStyle: "short" });

  let mostradas = 0;

  function crear(etiqueta, clase, texto) {
    const elemento = document.createElement(etiqueta);
    if (clase) elemento.className = clase;
    if (texto !== undefined) elemento.textContent = texto;
    return elemento;
  }

  function boton(texto, clase, etiqueta, accion) {
    const b = crear("button", `boton ${clase}`, texto);
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

  function confirmar(titulo, texto) {
    $("#dialogo-titulo").textContent = titulo;
    $("#dialogo-texto").textContent = texto;
    dialogo.returnValue = "";
    dialogo.showModal();
    return new Promise((resolver) =>
      dialogo.addEventListener("close", () => resolver(dialogo.returnValue === "confirmar"), { once: true })
    );
  }

  // ---------------- Tarjeta de cada publicación ----------------
  function etiquetaEstado(p) {
    if (p.oculta) return crear("span", "etiqueta etiqueta--oculta", "Oculta");
    return crear("span", `etiqueta etiqueta--${p.verificacion}`, p.verificacion_nombre);
  }

  function tarjeta(p) {
    const articulo = crear("article", "publicacion");
    articulo.setAttribute("aria-labelledby", `mod-${p.id_publicacion}`);
    const titulo = crear("h2", "publicacion__titulo", p.titulo);
    titulo.id = `mod-${p.id_publicacion}`;
    const cabecera = crear("div", "publicacion__cabecera");
    cabecera.append(etiquetaEstado(p));
    if (p.denuncias_pendientes) cabecera.append(crear("span", "etiqueta etiqueta--denuncia", `${p.denuncias_pendientes} ${p.denuncias_pendientes === 1 ? "denuncia" : "denuncias"} por revisar`));

    const meta = crear("p", "publicacion__datos", `${p.autor} · ${p.categoria_nombre}${p.ubicacion ? ` · ${p.ubicacion}` : ""}`);
    const texto = crear("p", "publicacion__texto", p.contenido);
    const datos = crear("p", "publicacion__datos");
    datos.append(
      crear("span", "", `VALIDACIÓN: ${p.validaciones}`),
      crear("span", "", `DENUNCIAS: ${p.denuncias_pendientes}`),
      crear("span", "", `RESPUESTAS: ${p.total_respuestas}`),
      crear("span", "", fecha.format(new Date(p.creado_en)))
    );
    articulo.append(titulo, cabecera, meta, texto, datos);

    // Detalle (denuncias y respuestas) se carga al pedirlo
    const extra = crear("div", "publicacion__extra");
    extra.id = `extra-${p.id_publicacion}`;
    extra.hidden = true;

    const acciones = crear("div", "publicacion__acciones");
    const nombre = `"${p.titulo}"`;
    const necesitaAprobar = p.verificacion !== "confirmada" || p.denuncias_pendientes > 0 || p.oculta;
    if (necesitaAprobar) {
      acciones.append(boton("Aprobar", "boton--aprobar", `Aprobar ${nombre}`, () =>
        moderar(p, { verificacion: "confirmada", oculta: false }, `Publicación aprobada: ${nombre}. Sus denuncias quedaron revisadas.`)
      ));
    }
    acciones.append(boton(p.oculta ? "Mostrar" : "Ocultar", "boton--secundario", `${p.oculta ? "Mostrar" : "Ocultar"} ${nombre}`, () =>
      moderar(p, { oculta: !p.oculta }, p.oculta ? `Publicación visible otra vez: ${nombre}.` : `Publicación oculta: ${nombre}. Ya no aparece en el foro.`)
    ));
    const verDetalle = boton(p.denuncias_pendientes ? "Ver denuncias y respuestas" : "Ver respuestas", "boton--secundario", null, () => alternarDetalle(p, verDetalle, extra));
    verDetalle.setAttribute("aria-expanded", "false");
    verDetalle.setAttribute("aria-controls", extra.id);
    acciones.append(verDetalle);
    acciones.append(boton("Eliminar", "boton--eliminar", `Eliminar ${nombre}`, () => eliminar(p)));

    articulo.append(acciones, extra);
    return articulo;
  }

  async function alternarDetalle(p, disparador, extra) {
    const abrir = extra.hidden;
    extra.hidden = !abrir;
    disparador.setAttribute("aria-expanded", String(abrir));
    if (!abrir) return;
    extra.replaceChildren(crear("p", "publicacion__datos", "Cargando…"));
    try {
      const completa = await RefugiaAPI.obtener(`/api/foro/publicaciones/${p.id_publicacion}`, { moderacion: true });
      pintarDetalle(completa, extra);
    } catch (error) {
      extra.replaceChildren(crear("p", "publicacion__datos", error.message));
    }
  }

  function pintarDetalle(p, extra) {
    extra.replaceChildren();
    const denuncias = p.denuncias.filter((d) => !d.revisada);
    if (denuncias.length) {
      extra.append(crear("h3", "publicacion__subtitulo", "Denuncias por revisar"));
      const lista = crear("ul", "publicacion__lista");
      denuncias.forEach((d) => lista.append(crear("li", "", `${d.motivo_nombre}${d.detalle ? `: ${d.detalle}` : ""} (${fechaHora.format(new Date(d.creado_en))})`)));
      extra.append(lista);
    }
    extra.append(crear("h3", "publicacion__subtitulo", `Respuestas (${p.respuestas.length})`));
    if (!p.respuestas.length) extra.append(crear("p", "publicacion__datos", "Sin respuestas."));
    const lista = crear("ul", "publicacion__lista publicacion__lista--respuestas");
    p.respuestas.forEach((r) => {
      const item = crear("li", "publicacion__respuesta");
      const texto = crear("div");
      texto.append(crear("strong", "", r.autor), crear("p", "", r.contenido));
      item.append(texto, boton("Eliminar", "boton--eliminar boton--pequeno", `Eliminar la respuesta de ${r.autor}`, async () => {
        const ok = await confirmar("¿Eliminar esta respuesta?", `"${r.contenido.slice(0, 120)}" de ${r.autor} se borrará.`);
        if (!ok) return;
        try {
          await RefugiaAPI.eliminar(`/api/foro/respuestas/${r.id_respuesta}`);
          mostrarAviso(`Respuesta de ${r.autor} eliminada.`);
          await cargar();
        } catch (error) {
          mostrarAviso(error.message, "error");
        }
      }));
      lista.append(item);
    });
    extra.append(lista);
  }

  // ---------------- Acciones ----------------
  async function moderar(p, cambios, mensaje) {
    try {
      await RefugiaAPI.actualizar(`/api/foro/publicaciones/${p.id_publicacion}`, cambios);
      mostrarAviso(mensaje);
      await cargar();
    } catch (error) {
      mostrarAviso(error.message, "error");
    }
  }

  async function eliminar(p) {
    const ok = await confirmar("¿Eliminar esta publicación?", `"${p.titulo}" se borrará con sus ${p.total_respuestas} respuestas y sus denuncias. Esta acción no se puede deshacer.`);
    if (!ok) return;
    try {
      await RefugiaAPI.eliminar(`/api/foro/publicaciones/${p.id_publicacion}`);
      mostrarAviso(`Publicación eliminada: "${p.titulo}".`);
      await cargar();
    } catch (error) {
      mostrarAviso(error.message, "error");
    }
  }

  // ---------------- Listado ----------------
  async function cargar({ agregar = false } = {}) {
    const offset = agregar ? mostradas : 0;
    botonMas.disabled = true;
    try {
      const r = await RefugiaAPI.obtener("/api/foro/publicaciones", {
        moderacion: true,
        revision: $("#filtro-revision").value,
        q: $("#filtro-q").value.trim(),
        limite: POR_PAGINA,
        offset,
      });
      if (!agregar) {
        contenedor.replaceChildren();
        mostradas = 0;
      }
      r.resultados.forEach((p) => contenedor.append(tarjeta(p)));
      mostradas += r.resultados.length;
      const filtro = $("#filtro-revision").value;
      estado.textContent = r.total
        ? `${r.total} ${r.total === 1 ? "publicación" : "publicaciones"}${filtro === "pendiente" ? " por revisar" : ""}.`
        : filtro === "pendiente" ? "¡Todo al día! No hay publicaciones por revisar." : "No hay publicaciones con este filtro.";
      estado.classList.remove("moderacion__estado--error");
      botonMas.hidden = mostradas >= r.total;
    } catch (error) {
      estado.textContent = `No se pudieron cargar las publicaciones. ${error.message}`;
      estado.classList.add("moderacion__estado--error");
    } finally {
      botonMas.disabled = false;
    }
  }

  $("#filtros").addEventListener("submit", (e) => {
    e.preventDefault();
    cargar();
  });
  $("#filtro-revision").addEventListener("change", () => cargar());
  botonMas.addEventListener("click", () => cargar({ agregar: true }));

  cargar();
})();
