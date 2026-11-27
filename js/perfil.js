/* =========================================================
   REFUGIA — Mi perfil (perfil.html)
   ---------------------------------------------------------
   Usa la sesión (js/sesion.js) y la API de usuarios (js/api.js):
     GET /api/sesion                 → datos de quien inició sesión
     PUT /api/usuarios/yo            → guardar nombre, correo, número y locación
     PUT /api/usuarios/yo/contrasena → cambiar la contraseña
   ========================================================= */
(function () {
  "use strict";

  const $ = (selector) => document.querySelector(selector);
  const casilla = $("#modo-edicion");
  const formPerfil = $("#form-perfil");
  const formClave = $("#form-contrasena");
  const estadoPerfil = $("#estado-perfil");
  const estadoClave = $("#estado-contrasena");
  const CAMPOS = ["nombre", "correo", "telefono", "ubicacion"];
  let usuario = null;

  // ---------------- Utilidades ----------------
  function limpiarErrores(form, estado) {
    form.querySelectorAll("[aria-invalid]").forEach((c) => c.removeAttribute("aria-invalid"));
    form.querySelectorAll(".usuario__error").forEach((p) => (p.textContent = ""));
    estado.textContent = "";
    estado.classList.remove("usuario__estado--error");
  }

  function mostrarErrores(form, estado, detalles, mensaje) {
    let primero = null;
    for (const [campo, mensajes] of Object.entries(detalles || {})) {
      const input = form.elements[campo];
      const parrafo = document.getElementById(`error-${campo}`);
      if (!input || !parrafo) continue;
      input.setAttribute("aria-invalid", "true");
      parrafo.textContent = Array.isArray(mensajes) ? mensajes.join(" ") : mensajes;
      primero ??= input;
    }
    if (mensaje) {
      estado.textContent = mensaje;
      estado.classList.add("usuario__estado--error");
    }
    primero?.focus();
  }

  function mostrarEstado(estado, texto) {
    estado.textContent = texto;
    window.Accesibilidad?.anunciar?.(texto);
  }

  // ---------------- Datos del perfil ----------------
  function pintar() {
    $("#usuario-id").textContent = `@${usuario.nombre_usuario}`;
    $("#usuario-rol").textContent = usuario.rol_nombre;
    for (const campo of CAMPOS) formPerfil.elements[campo].value = usuario[campo] ?? "";
    document.title = `REFUGIA | Mi perfil (@${usuario.nombre_usuario})`;
  }

  function modoEdicion(activo) {
    casilla.checked = activo;
    for (const campo of CAMPOS) formPerfil.elements[campo].readOnly = !activo;
    if (activo) formPerfil.elements.nombre.focus();
  }

  // El lápiz (casilla #modo-edicion) activa la edición
  casilla.addEventListener("change", () => {
    limpiarErrores(formPerfil, estadoPerfil);
    if (!casilla.checked && usuario) pintar(); // al salir sin guardar se restauran los datos
    modoEdicion(casilla.checked);
  });

  $("#btn-cancelar-perfil").addEventListener("click", () => {
    limpiarErrores(formPerfil, estadoPerfil);
    pintar();
    modoEdicion(false);
    casilla.focus();
  });

  formPerfil.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    if (!casilla.checked) return;
    limpiarErrores(formPerfil, estadoPerfil);
    const datos = {};
    for (const campo of CAMPOS) datos[campo] = formPerfil.elements[campo].value.trim();
    if (!datos.correo) {
      mostrarErrores(formPerfil, estadoPerfil, { correo: "El correo es obligatorio." });
      return;
    }

    const guardar = document.querySelector('button[form="form-perfil"]');
    guardar.disabled = true;
    try {
      usuario = await RefugiaAPI.actualizar("/api/usuarios/yo", datos);
      pintar();
      modoEdicion(false);
      casilla.focus();
      mostrarEstado(estadoPerfil, "Tus datos se guardaron.");
      // El nombre del menú de usuario también cambia
      document.querySelectorAll("[data-sesion-nombre]").forEach((e) => (e.textContent = usuario.nombre_visible));
    } catch (error) {
      if (error.estado === 401) return location.replace(RefugiaSesion.urlIniciarSesion());
      mostrarErrores(formPerfil, estadoPerfil, error.detalles, error.detalles ? "" : error.message);
    } finally {
      guardar.disabled = false;
    }
  });

  // ---------------- Cambiar contraseña ----------------
  formClave.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    limpiarErrores(formClave, estadoClave);
    const actual = formClave.elements.actual.value;
    const nueva = formClave.elements.nueva.value;
    const confirmar = formClave.elements.confirmar.value;

    const errores = {};
    if (!actual) errores.actual = "Escribe tu contraseña actual.";
    if (nueva.length < 8 || !/\p{L}/u.test(nueva) || !/\d/.test(nueva)) {
      errores.nueva = "Mínimo 8 caracteres, con letras y números.";
    }
    if (confirmar !== nueva) errores.confirmar = "No coincide con la nueva contraseña.";
    if (Object.keys(errores).length) {
      mostrarErrores(formClave, estadoClave, errores);
      return;
    }

    const boton = formClave.querySelector('button[type="submit"]');
    boton.disabled = true;
    try {
      const r = await RefugiaAPI.actualizar("/api/usuarios/yo/contrasena", { actual, nueva });
      formClave.reset();
      mostrarEstado(estadoClave, r.mensaje);
    } catch (error) {
      if (error.estado === 401) return location.replace(RefugiaSesion.urlIniciarSesion());
      mostrarErrores(formClave, estadoClave, error.detalles, error.detalles ? "" : error.message);
    } finally {
      boton.disabled = false;
    }
  });

  // ---------------- Inicio ----------------
  RefugiaSesion.listo.then((u) => {
    if (!u) return; // js/sesion.js ya lleva a iniciar-sesion.html
    usuario = u;
    pintar();
    modoEdicion(false);
  });
})();
