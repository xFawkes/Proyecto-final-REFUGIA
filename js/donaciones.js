/* =========================================================
   REFUGIA — Donaciones con pasarela de pagos SIMULADA
   ---------------------------------------------------------
     Organizaciones → GET  /api/organizaciones
     Datos de prueba → GET /api/donaciones/pasarela
     1. Donar        → POST /api/donaciones                    (queda "pendiente")
     2. Pagar        → POST /api/donaciones/<referencia>/pago  ("aprobada" o "rechazada")
     3. Comprobante  → la respuesta del paso 2
   No se cobra dinero real. Requiere js/api.js y  python main.py
   ========================================================= */
(() => {
  "use strict";

  const $ = (selector, raiz = document) => raiz.querySelector(selector);
  const listaOrganizaciones = $("#organizaciones-lista");
  const estadoOrganizaciones = $("#organizaciones-estado");
  const formDonacion = $("#form-donacion");
  const selectDestino = $("#donacion-destino");
  const campoOtro = $("#monto-otro");
  const errorDonacion = $("#donacion-error");
  const btnDonar = $("#btn-donar");
  const contenedorPasarela = $("#pasarela-pagos");

  const pesos = new Intl.NumberFormat("es-CO", { style: "currency", currency: "COP", maximumFractionDigits: 0 });
  const fechaHora = new Intl.DateTimeFormat("es-CO", { dateStyle: "long", timeStyle: "short" });

  let infoPasarela = null; // medios de pago y datos de prueba (GET /api/donaciones/pasarela)
  let donacionActual = null;

  function crear(etiqueta, clase, texto) {
    const elemento = document.createElement(etiqueta);
    if (clase) elemento.className = clase;
    if (texto !== undefined) elemento.textContent = texto;
    return elemento;
  }

  // =========================================================
  // Organizaciones (columna izquierda)
  // =========================================================
  function tarjetaOrganizacion(org) {
    const articulo = crear("article", "tarjeta-ong");
    if (org.imagen) {
      const imagen = crear("img", "tarjeta-ong__imagen");
      imagen.src = RefugiaAPI.recurso(org.imagen);
      imagen.alt = org.imagen_alt || "";
      imagen.loading = "lazy";
      articulo.append(imagen);
    } else {
      articulo.classList.add("tarjeta-ong--sin-imagen");
    }

    const cuerpo = crear("div", "tarjeta-ong__cuerpo");
    cuerpo.append(crear("h2", "tarjeta-ong__nombre", org.nombre));
    cuerpo.append(crear("p", "", org.descripcion));
    if (org.impacto) cuerpo.append(crear("p", "", `Tu donación ayuda a: ${org.impacto}`));

    const acciones = crear("div", "tarjeta-ong__acciones");
    const donar = crear("button", "tarjeta-ong__donar", "Donar a esta organización");
    donar.type = "button";
    donar.setAttribute("aria-label", `Donar a esta organización: ${org.nombre}`);
    donar.addEventListener("click", () => elegirOrganizacion(org.id_organizacion));
    acciones.append(donar);

    if (org.enlace) {
      const enlace = crear("a", "tarjeta-ong__enlace", "Da click aquí para ir a la página");
      enlace.href = org.enlace;
      enlace.target = "_blank";
      enlace.rel = "noopener noreferrer";
      enlace.setAttribute("aria-label", `Da click aquí para ir a la página de ${org.nombre} (se abre en otra pestaña)`);
      acciones.append(enlace);
    }
    cuerpo.append(acciones);
    articulo.append(cuerpo);
    return articulo;
  }

  function elegirOrganizacion(id) {
    if (formDonacion.hidden) cerrarPasarela();
    selectDestino.value = String(id);
    formDonacion.scrollIntoView({ behavior: "smooth", block: "start" });
    const nombre = selectDestino.selectedOptions[0]?.textContent;
    window.Accesibilidad?.anunciar?.(`Donarás a ${nombre}. Elige el monto.`);
    formDonacion.querySelector('input[name="monto"]')?.focus({ preventScroll: true });
  }

  async function cargarOrganizaciones() {
    try {
      const organizaciones = await RefugiaAPI.obtener("/api/organizaciones");
      listaOrganizaciones.replaceChildren(...organizaciones.map(tarjetaOrganizacion));
      organizaciones.forEach((org) => {
        const opcion = crear("option", "", org.nombre);
        opcion.value = org.id_organizacion;
        selectDestino.append(opcion);
      });
      estadoOrganizaciones.hidden = organizaciones.length > 0;
      estadoOrganizaciones.textContent = organizaciones.length ? "" : "Pronto publicaremos las organizaciones aliadas.";
    } catch (error) {
      estadoOrganizaciones.textContent = `No se pudieron cargar las organizaciones. ${error.message}`;
      estadoOrganizaciones.classList.add("organizaciones__estado--error");
    }
  }

  // =========================================================
  // Paso 1: formulario de donación
  // =========================================================
  // Monto: o un botón sugerido o el campo "otro monto" (no los dos)
  campoOtro.addEventListener("input", () => {
    if (campoOtro.value) formDonacion.querySelectorAll('input[name="monto"]').forEach((r) => (r.checked = false));
  });
  formDonacion.querySelectorAll('input[name="monto"]').forEach((radio) =>
    radio.addEventListener("change", () => (campoOtro.value = ""))
  );

  function leerMonto() {
    const elegido = formDonacion.querySelector('input[name="monto"]:checked');
    return elegido ? Number(elegido.value) : Number(campoOtro.value || 0);
  }

  function mostrarErrorDonacion(texto, campo) {
    errorDonacion.textContent = texto;
    formDonacion.querySelectorAll("[aria-invalid]").forEach((c) => c.removeAttribute("aria-invalid"));
    if (campo) {
      campo.setAttribute("aria-invalid", "true");
      campo.focus();
    }
  }

  formDonacion.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    const monto = leerMonto();
    const nombre = $("#donacion-nombre").value.trim();
    const correo = $("#donacion-correo").value.trim();

    if (!monto) return mostrarErrorDonacion("Elige un monto o escribe otro valor.", formDonacion.querySelector('input[name="monto"]'));
    if (monto < 10000) return mostrarErrorDonacion("El monto mínimo es COP $10.000.", campoOtro);
    if (monto > 20000000) return mostrarErrorDonacion("El monto máximo es COP $20.000.000.", campoOtro);
    if (nombre.length < 2) return mostrarErrorDonacion("Escribe tu nombre.", $("#donacion-nombre"));
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(correo)) return mostrarErrorDonacion("Escribe un correo válido.", $("#donacion-correo"));
    mostrarErrorDonacion("");

    btnDonar.disabled = true;
    try {
      donacionActual = await RefugiaAPI.crear("/api/donaciones", {
        monto,
        frecuencia: formDonacion.querySelector('input[name="frecuencia"]:checked').value,
        id_organizacion: selectDestino.value ? Number(selectDestino.value) : null,
        nombre_donante: nombre,
        correo,
      });
      await abrirPasarela();
    } catch (error) {
      const detalle = error.detalles ? Object.values(error.detalles).flat().join(" ") : "";
      mostrarErrorDonacion(`${error.message} ${detalle}`.trim());
    } finally {
      btnDonar.disabled = false;
    }
  });

  // =========================================================
  // Paso 2: pasarela de pagos simulada
  // =========================================================
  function llenarCampos(raiz, donacion) {
    raiz.querySelectorAll("[data-campo]").forEach((elemento) => {
      const campo = elemento.dataset.campo;
      if (!(campo in donacion)) return;
      let valor = donacion[campo];
      if (campo === "monto") valor = pesos.format(valor);
      if (campo === "pagado_en" && valor) valor = fechaHora.format(new Date(valor));
      if (campo === "frecuencia_nombre" && donacion.frecuencia === "mensual") valor += " (simulada: solo se registra este pago)";
      elemento.textContent = valor ?? "—";
    });
    raiz.querySelectorAll("[data-si]").forEach((fila) => (fila.hidden = !donacion[fila.dataset.si]));
  }

  async function abrirPasarela() {
    infoPasarela ??= await RefugiaAPI.obtener("/api/donaciones/pasarela");
    const vista = $("#plantilla-pasarela").content.cloneNode(true);
    llenarCampos(vista, donacionActual);
    $(".pasarela__boton--pagar", vista).textContent = `Pagar ${pesos.format(donacionActual.monto)}`;

    // Bancos de prueba
    const selectBanco = $("#pago-banco", vista);
    infoPasarela.bancos_prueba.forEach((banco) => {
      const opcion = crear("option", "", banco.nombre);
      opcion.value = banco.clave;
      selectBanco.append(opcion);
    });

    // Lista de datos de prueba con botón para usarlos
    const lista = $('[data-lista="pruebas"]', vista);
    infoPasarela.tarjetas_prueba.forEach((t) =>
      lista.append(itemPrueba(`Tarjeta ${t.franquicia} ${t.numero} → ${t.resultado}`, { metodo: "tarjeta", numero: t.numero }))
    );
    infoPasarela.bancos_prueba.forEach((b) =>
      lista.append(itemPrueba(`Transferencia: ${b.nombre}`, { metodo: "transferencia", banco: b.clave }))
    );
    infoPasarela.billeteras_prueba.forEach((b) =>
      lista.append(itemPrueba(`Billetera ${b.celular} → ${b.resultado}`, { metodo: "billetera", celular: b.celular }))
    );

    contenedorPasarela.replaceChildren(vista);
    const formPago = $("#form-pago");
    formPago.addEventListener("change", (e) => e.target.name === "metodo" && mostrarMetodo(e.target.value));
    formPago.addEventListener("submit", pagar);
    $('[data-accion="cancelar"]', formPago).addEventListener("click", cerrarPasarela);
    $("#tarjeta-numero").addEventListener("input", formatearNumero);
    $("#tarjeta-vencimiento").addEventListener("input", formatearVencimiento);

    formDonacion.hidden = true;
    $("#pasarela-titulo").focus();
  }

  function itemPrueba(texto, datos) {
    const item = crear("li");
    item.append(crear("span", "", texto));
    const usar = crear("button", "pasarela__usar", "Usar");
    usar.type = "button";
    usar.setAttribute("aria-label", `Usar ${texto}`);
    usar.addEventListener("click", () => usarDatosPrueba(datos));
    item.append(usar);
    return item;
  }

  function usarDatosPrueba(datos) {
    $(`#metodo-${datos.metodo}`).checked = true;
    mostrarMetodo(datos.metodo);
    if (datos.metodo === "tarjeta") {
      $("#tarjeta-titular").value ||= $("#donacion-nombre").value.trim();
      $("#tarjeta-numero").value = datos.numero;
      $("#tarjeta-vencimiento").value = "12/30";
      $("#tarjeta-cvv").value = "123";
    } else if (datos.metodo === "transferencia") {
      $("#pago-banco").value = datos.banco;
    } else {
      $("#pago-celular").value = datos.celular;
    }
    $(".pasarela__boton--pagar").focus();
  }

  function mostrarMetodo(metodo) {
    document.querySelectorAll("#form-pago [data-metodo]").forEach((bloque) => (bloque.hidden = bloque.dataset.metodo !== metodo));
  }

  function formatearNumero(evento) {
    const digitos = evento.target.value.replace(/\D/g, "").slice(0, 19);
    evento.target.value = digitos.replace(/(\d{4})(?=\d)/g, "$1 ");
  }

  function formatearVencimiento(evento) {
    const digitos = evento.target.value.replace(/\D/g, "").slice(0, 4);
    evento.target.value = digitos.length > 2 ? `${digitos.slice(0, 2)}/${digitos.slice(2)}` : digitos;
  }

  function limpiarErroresPago() {
    document.querySelectorAll("#form-pago .pasarela__error-campo").forEach((p) => (p.textContent = ""));
    document.querySelectorAll("#form-pago [aria-invalid]").forEach((c) => c.removeAttribute("aria-invalid"));
    $('#form-pago [data-campo="error"]').textContent = "";
  }

  // Muestra los errores de la API junto a cada campo ({"tarjeta": {"numero": [...]}} → #error-tarjeta-numero)
  function mostrarErroresPago(detalles, prefijo = "") {
    let primero = null;
    for (const [campo, mensajes] of Object.entries(detalles || {})) {
      if (!Array.isArray(mensajes) && typeof mensajes === "object") {
        primero ??= mostrarErroresPago(mensajes, `${campo}-`);
        continue;
      }
      const id = `${prefijo}${campo}`;
      const parrafo = $(`#error-${id}`);
      const entrada = $(`#${id}`) || $(`#pago-${campo}`);
      if (parrafo) parrafo.textContent = [].concat(mensajes).join(" ");
      else $('#form-pago [data-campo="error"]').textContent = [].concat(mensajes).join(" ");
      if (entrada) {
        entrada.setAttribute("aria-invalid", "true");
        primero ??= entrada;
      }
    }
    return primero;
  }

  function leerPago() {
    const metodo = $('#form-pago input[name="metodo"]:checked').value;
    if (metodo === "tarjeta") {
      return {
        metodo,
        tarjeta: {
          titular: $("#tarjeta-titular").value.trim(),
          numero: $("#tarjeta-numero").value,
          vencimiento: $("#tarjeta-vencimiento").value.trim(),
          cvv: $("#tarjeta-cvv").value.trim(),
        },
      };
    }
    if (metodo === "transferencia") return { metodo, banco: $("#pago-banco").value };
    return { metodo, celular: $("#pago-celular").value.trim() };
  }

  async function pagar(evento) {
    evento.preventDefault();
    limpiarErroresPago();
    const botones = evento.target.querySelectorAll("button");
    const pagarBoton = $(".pasarela__boton--pagar");
    botones.forEach((b) => (b.disabled = true));
    pagarBoton.textContent = "Procesando pago…";
    try {
      donacionActual = await RefugiaAPI.crear(`/api/donaciones/${donacionActual.referencia}/pago`, leerPago());
      mostrarComprobante();
    } catch (error) {
      const primero = mostrarErroresPago(error.detalles);
      if (!error.detalles) $('#form-pago [data-campo="error"]').textContent = error.message;
      else if (!primero) $('#form-pago [data-campo="error"]').textContent ||= error.message;
      primero?.focus();
      botones.forEach((b) => (b.disabled = false));
      pagarBoton.textContent = `Pagar ${pesos.format(donacionActual.monto)}`;
    }
  }

  // =========================================================
  // Paso 3: comprobante
  // =========================================================
  function mostrarComprobante() {
    const aprobada = donacionActual.estado === "aprobada";
    const vista = $("#plantilla-comprobante").content.cloneNode(true);
    const tarjeta = $(".pasarela__comprobante", vista);
    tarjeta.classList.add(aprobada ? "pasarela__comprobante--aprobada" : "pasarela__comprobante--rechazada");
    $(".pasarela__icono", vista).classList.add(aprobada ? "bi-check-circle-fill" : "bi-x-circle-fill");
    $(".pasarela__titulo", vista).textContent = aprobada
      ? `¡Gracias, ${donacionActual.nombre_donante}! Tu donación fue aprobada`
      : "Tu pago fue rechazado";
    llenarCampos(vista, donacionActual);

    const acciones = $("[data-acciones]", vista);
    if (aprobada) {
      acciones.append(botonAccion("Hacer otra donación", "pasarela__boton--pagar", () => cerrarPasarela({ reiniciar: true })));
    } else {
      acciones.append(botonAccion("Intentar con otro medio de pago", "pasarela__boton--pagar", abrirPasarela));
      acciones.append(botonAccion("Cancelar", "pasarela__boton--secundario", () => cerrarPasarela()));
    }
    contenedorPasarela.replaceChildren(vista);
    $("#comprobante-titulo").focus();
  }

  function botonAccion(texto, clase, accion) {
    const boton = crear("button", `pasarela__boton ${clase}`, texto);
    boton.type = "button";
    boton.addEventListener("click", accion);
    return boton;
  }

  function cerrarPasarela({ reiniciar = false } = {}) {
    contenedorPasarela.replaceChildren();
    formDonacion.hidden = false;
    if (reiniciar) {
      formDonacion.reset();
      donacionActual = null;
    }
    btnDonar.focus();
  }

  cargarOrganizaciones();
})();
