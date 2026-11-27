/* =========================================================
   REFUGIA — Iniciar sesión y Registro
   (iniciar-sesion.html y registro.html)
   ---------------------------------------------------------
   Usa la API de usuarios (js/api.js):
     POST /api/sesion     → iniciar sesión  {usuario, contrasena}
     POST /api/usuarios   → crear cuenta    {nombre_usuario, correo, contrasena}
     GET  /api/sesion     → ¿ya había una sesión iniciada?

   Después de entrar:
     • Administrador → admin/inicio.html (panel)
     • Usuario       → inicio.html
     • Si se llegó desde una página que pedía sesión (?siguiente=perfil.html),
       se vuelve a esa página.
   ========================================================= */
(function () {
  "use strict";

  const $ = (selector) => document.querySelector(selector);
  const formLogin = $("#form-iniciar-sesion");
  const formRegistro = $("#form-registro");
  const form = formLogin || formRegistro;
  if (!form) return;

  const alerta = $("#alerta-acceso");
  const aviso = $("#aviso-acceso");
  const boton = form.querySelector('button[type="submit"]');

  // ---------------- A dónde ir después ----------------
  const parametros = new URLSearchParams(location.search);

  /** ?siguiente=… solo si es una página de este mismo sitio (nunca otro dominio). */
  function paginaSiguiente() {
    const valor = parametros.get("siguiente") || "";
    if (!valor || /^[a-z][a-z0-9+.-]*:|^\/\/|\\/i.test(valor)) return null;
    const url = new URL(valor.replace(/^\/+/, ""), new URL(".", location.href));
    return url.origin === location.origin && url.pathname.endsWith(".html") ? url : null;
  }

  const siguiente = paginaSiguiente();
  const siguienteEsAdmin = Boolean(siguiente && /\/admin\//.test(siguiente.pathname));

  function destino(usuario, redireccion) {
    if (siguiente && (!siguienteEsAdmin || usuario.rol === "administrador")) return siguiente.href;
    return redireccion || (usuario.rol === "administrador" ? "admin/inicio.html" : "inicio.html");
  }

  // El enlace "Regístrate" / "Inicia sesión" conserva a dónde se quería ir
  const enlaceOtra = $("#enlace-otra-pagina");
  if (enlaceOtra && siguiente && !siguienteEsAdmin) {
    enlaceOtra.href += `?siguiente=${encodeURIComponent(parametros.get("siguiente"))}`;
  }

  function mostrarAviso(texto) {
    aviso.textContent = texto;
    aviso.hidden = false;
  }

  // ---------------- Errores ----------------
  function limpiarErrores() {
    alerta.textContent = "";
    form.querySelectorAll("[aria-invalid]").forEach((campo) => campo.removeAttribute("aria-invalid"));
    form.querySelectorAll(".acceso__error-campo").forEach((p) => (p.textContent = ""));
  }

  function errorCampo(nombre, mensaje) {
    const campo = form.elements[nombre];
    const parrafo = document.getElementById(`error-${nombre}`);
    if (!campo || !parrafo) return false;
    campo.setAttribute("aria-invalid", "true");
    parrafo.textContent = mensaje;
    return true;
  }

  function mostrarErrores(errores, general) {
    let primero = null;
    for (const [nombre, mensajes] of Object.entries(errores || {})) {
      const mensaje = Array.isArray(mensajes) ? mensajes.join(" ") : String(mensajes);
      if (errorCampo(nombre, mensaje)) primero ??= form.elements[nombre];
      else general = `${general || ""} ${mensaje}`.trim();
    }
    if (general) alerta.textContent = general;
    (primero || boton).focus();
    if (primero) window.Accesibilidad?.anunciar?.("Revisa los campos marcados.");
  }

  // ---------------- Validación en el navegador (la API vuelve a validar) ----------------
  const PATRON_USUARIO = /^[a-z0-9][a-z0-9._-]{2,29}$/;
  const PATRON_CORREO = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  function validarLogin(datos) {
    const errores = {};
    if (!datos.usuario) errores.usuario = "Escribe tu nombre de usuario o tu correo.";
    if (!datos.contrasena) errores.contrasena = "Escribe tu contraseña.";
    return errores;
  }

  function validarRegistro(datos) {
    const errores = {};
    if (!PATRON_USUARIO.test(datos.nombre_usuario)) {
      errores.nombre_usuario = datos.nombre_usuario
        ? "Usa de 3 a 30 caracteres: letras sin tilde, números, punto, guion o guion bajo."
        : "Escribe un nombre de usuario.";
    }
    if (!PATRON_CORREO.test(datos.correo)) {
      errores.correo = datos.correo ? "Escribe un correo válido, por ejemplo nombre@correo.com." : "Escribe tu correo electrónico.";
    }
    const c = datos.contrasena;
    if (!c) errores.contrasena = "Escribe una contraseña.";
    else if (c.length < 8 || !/\p{L}/u.test(c) || !/\d/.test(c)) {
      errores.contrasena = "La contraseña debe tener mínimo 8 caracteres, con letras y números.";
    }
    return errores;
  }

  function leerDatos() {
    if (formLogin) {
      return { usuario: form.elements.usuario.value.trim(), contrasena: form.elements.contrasena.value };
    }
    return {
      nombre_usuario: form.elements.nombre_usuario.value.trim().toLowerCase(),
      correo: form.elements.correo.value.trim(),
      contrasena: form.elements.contrasena.value,
    };
  }

  // ---------------- Enviar ----------------
  form.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    limpiarErrores();
    const datos = leerDatos();
    const errores = formLogin ? validarLogin(datos) : validarRegistro(datos);
    if (Object.keys(errores).length) {
      mostrarErrores(errores);
      return;
    }

    const textoBoton = boton.textContent;
    boton.disabled = true;
    boton.textContent = formLogin ? "Entrando…" : "Creando cuenta…";
    try {
      const respuesta = await RefugiaAPI.crear(formLogin ? "/api/sesion" : "/api/usuarios", datos);
      window.Accesibilidad?.anunciar?.(respuesta.mensaje);
      location.assign(destino(respuesta.usuario, respuesta.redireccion));
    } catch (error) {
      boton.disabled = false;
      boton.textContent = textoBoton;
      if (formLogin && error.estado === 401) form.elements.contrasena.value = "";
      mostrarErrores(error.detalles, error.detalles ? "" : error.message);
    }
  });

  // ---------------- ¿Olvidaste tus datos? ----------------
  const dialogo = $("#dialogo-olvide");
  $("#btn-olvide")?.addEventListener("click", () => dialogo?.showModal());

  // ---------------- ¿Ya había una sesión iniciada? ----------------
  async function revisarSesion() {
    if (siguienteEsAdmin) {
      mostrarAviso("Esta sección es solo para administradores. Inicia sesión con una cuenta de administrador.");
    } else if (siguiente) {
      mostrarAviso("Inicia sesión para continuar.");
    }
    try {
      const { usuario } = await RefugiaAPI.obtener("/api/sesion");
      if (!usuario) return;
      if (siguienteEsAdmin && usuario.rol !== "administrador") {
        mostrarAviso(`Iniciaste sesión como ${usuario.nombre_usuario}, que no es administrador. Entra con una cuenta de administrador.`);
        return;
      }
      location.replace(destino(usuario)); // ya tenía sesión: no hace falta volver a entrar
    } catch {
      /* sin conexión con la API: el error se mostrará al enviar el formulario */
    }
  }

  revisarSesion();
})();
