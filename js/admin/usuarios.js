/* =========================================================
   REFUGIA — Administración de usuarios (admin/usuarios.html)
   ---------------------------------------------------------
     Listar           → GET    /api/usuarios?q=…&rol=…&activo=…
     Cambiar rol      → PUT    /api/usuarios/<id>  {"rol": "administrador" | "usuario"}
     Activar/desact.  → PUT    /api/usuarios/<id>  {"activo": true | false}
     Contraseña temp. → POST   /api/usuarios/<id>/contrasena-temporal
     Eliminar         → DELETE /api/usuarios/<id>
   Las cuentas nuevas se crean desde registro.html (POST /api/usuarios).
   Requiere ../js/api.js, ../js/sesion.js y que la API esté corriendo:  python main.py
   ========================================================= */
(() => {
  "use strict";

  const POR_PAGINA = 20;
  const $ = (selector) => document.querySelector(selector);
  const aviso = $("#aviso");
  const dialogo = $("#dialogo-confirmar");
  const fechaCorta = new Intl.DateTimeFormat("es-CO", { dateStyle: "medium", timeStyle: "short" });
  let yo = null; // el administrador que tiene la sesión iniciada

  function crear(etiqueta, clase, texto) {
    const elemento = document.createElement(etiqueta);
    if (clase) elemento.className = clase;
    if (texto !== undefined) elemento.textContent = texto;
    return elemento;
  }

  function boton(texto, clase, etiqueta, accion) {
    const b = crear("button", `formulario__boton ${clase}`, texto);
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

  // Confirmación con <dialog>: devuelve una promesa que se resuelve en true o false
  function confirmar(titulo, texto, textoBoton) {
    $("#dialogo-titulo").textContent = titulo;
    $("#dialogo-texto").textContent = texto;
    $("#dialogo-confirmar-boton").textContent = textoBoton;
    dialogo.returnValue = "";
    dialogo.showModal();
    return new Promise((resolver) =>
      dialogo.addEventListener("close", () => resolver(dialogo.returnValue === "confirmar"), { once: true })
    );
  }

  // =========================================================
  // Resumen (tres consultas que solo piden el total)
  // =========================================================
  async function cargarResumen() {
    const total = (filtros) => RefugiaAPI.obtener("/api/usuarios", { ...filtros, limite: 1 }).then((r) => r.total);
    try {
      const [todas, admins, inactivas] = await Promise.all([
        total({}), total({ rol: "administrador" }), total({ activo: false }),
      ]);
      $("#resumen-total").textContent = todas;
      $("#resumen-admin").textContent = admins;
      $("#resumen-inactivas").textContent = inactivas;
    } catch (error) {
      mostrarAviso(`No se pudo cargar el resumen. ${error.message}`, "error");
    }
  }

  // =========================================================
  // Tabla de cuentas
  // =========================================================
  const tabla = $("#tabla-usuarios");
  const estadoLista = $("#usuarios-estado");
  const botonMas = $("#usuarios-mas");
  let mostradas = 0;

  function filaUsuario(u) {
    const esYo = u.id_usuario === yo?.id_usuario;
    const fila = crear("tr");

    const usuario = crear("td");
    const nombre = crear("span", "tabla__referencia", `@${u.nombre_usuario}`);
    usuario.append(nombre);
    if (esYo) usuario.append(" ", crear("span", "tabla__tu", "(tú)"));
    if (u.nombre) usuario.append(crear("span", "tabla__secundario", u.nombre));
    fila.append(usuario);

    const correo = crear("td");
    correo.append(crear("span", "", u.correo));
    if (u.telefono) correo.append(crear("span", "tabla__secundario", u.telefono));
    fila.append(correo);

    const rol = crear("td");
    rol.append(crear("span", `sello sello--${u.rol}`, u.rol_nombre));
    fila.append(rol);

    const estado = crear("td");
    estado.append(crear("span", `sello ${u.activo ? "sello--activa" : "sello--inactiva"}`, u.activo ? "Activa" : "Desactivada"));
    fila.append(estado);

    fila.append(crear("td", "", u.ultimo_acceso ? fechaCorta.format(new Date(u.ultimo_acceso)) : "Nunca"));

    const acciones = crear("td");
    const contenedor = crear("div", "tabla__acciones");
    if (!esYo) {
      // Tu propia cuenta no se puede degradar, desactivar ni eliminar (el panel quedaría sin acceso)
      contenedor.append(u.rol === "administrador"
        ? boton("Quitar admin", "formulario__boton--secundario", `Quitar el rol de administrador a ${u.nombre_usuario}`, () => cambiarRol(u, "usuario"))
        : boton("Hacer admin", "formulario__boton--secundario", `Hacer administrador a ${u.nombre_usuario}`, () => cambiarRol(u, "administrador")));
      contenedor.append(u.activo
        ? boton("Desactivar", "formulario__boton--secundario", `Desactivar la cuenta de ${u.nombre_usuario}`, () => cambiarActivo(u, false))
        : boton("Activar", "formulario__boton--aprobar", `Activar la cuenta de ${u.nombre_usuario}`, () => cambiarActivo(u, true)));
    }
    contenedor.append(boton("Contraseña temporal", "formulario__boton--secundario",
      `Generar una contraseña temporal para ${u.nombre_usuario}`, () => contrasenaTemporal(u)));
    if (!esYo) {
      contenedor.append(boton("Eliminar", "formulario__boton--eliminar", `Eliminar la cuenta de ${u.nombre_usuario}`, () => eliminar(u)));
    }
    acciones.append(contenedor);
    fila.append(acciones);
    return fila;
  }

  async function cargarUsuarios({ agregar = false } = {}) {
    const offset = agregar ? mostradas : 0;
    botonMas.disabled = true;
    try {
      const r = await RefugiaAPI.obtener("/api/usuarios", {
        q: $("#filtro-q").value.trim(),
        rol: $("#filtro-rol").value,
        activo: $("#filtro-activo").value,
        limite: POR_PAGINA,
        offset,
      });
      if (!agregar) {
        tabla.replaceChildren();
        mostradas = 0;
      }
      r.resultados.forEach((u) => tabla.append(filaUsuario(u)));
      mostradas += r.resultados.length;
      estadoLista.textContent = r.total
        ? `${r.total} ${r.total === 1 ? "cuenta" : "cuentas"}.`
        : "No hay cuentas con este filtro.";
      botonMas.hidden = mostradas >= r.total;
    } catch (error) {
      estadoLista.textContent = `No se pudieron cargar las cuentas. ${error.message}`;
    } finally {
      botonMas.disabled = false;
    }
  }

  async function recargar(mensaje) {
    if (mensaje) mostrarAviso(mensaje);
    await Promise.all([cargarUsuarios(), cargarResumen()]);
  }

  // =========================================================
  // Acciones
  // =========================================================
  async function cambiarRol(u, rol) {
    const haciaAdmin = rol === "administrador";
    const ok = await confirmar(
      haciaAdmin ? "¿Hacer administrador?" : "¿Quitar el rol de administrador?",
      haciaAdmin
        ? `@${u.nombre_usuario} podrá entrar a este panel y crear, editar o borrar contenido.`
        : `@${u.nombre_usuario} ya no podrá entrar al panel de administración.`,
      haciaAdmin ? "Hacer administrador" : "Quitar rol"
    );
    if (!ok) return;
    try {
      await RefugiaAPI.actualizar(`/api/usuarios/${u.id_usuario}`, { rol });
      await recargar(`@${u.nombre_usuario} ahora es ${haciaAdmin ? "administrador" : "usuario"}.`);
    } catch (error) {
      mostrarAviso(`No se pudo cambiar el rol. ${error.message}`, "error");
    }
  }

  async function cambiarActivo(u, activo) {
    if (!activo) {
      const ok = await confirmar("¿Desactivar la cuenta?",
        `@${u.nombre_usuario} no podrá iniciar sesión y se cerrará su sesión abierta. Puedes volver a activarla después.`,
        "Desactivar");
      if (!ok) return;
    }
    try {
      await RefugiaAPI.actualizar(`/api/usuarios/${u.id_usuario}`, { activo });
      await recargar(`La cuenta de @${u.nombre_usuario} quedó ${activo ? "activa" : "desactivada"}.`);
    } catch (error) {
      mostrarAviso(`No se pudo cambiar el estado. ${error.message}`, "error");
    }
  }

  const dialogoTemporal = $("#dialogo-temporal");
  const claveTemporal = $("#temporal-clave");

  async function contrasenaTemporal(u) {
    const ok = await confirmar("¿Generar una contraseña temporal?",
      `La contraseña actual de @${u.nombre_usuario} dejará de servir y se cerrarán sus sesiones abiertas.`,
      "Generar");
    if (!ok) return;
    try {
      const r = await RefugiaAPI.crear(`/api/usuarios/${u.id_usuario}/contrasena-temporal`, {});
      $("#temporal-texto").textContent = r.mensaje;
      claveTemporal.textContent = r.contrasena_temporal;
      $("#btn-copiar-temporal").textContent = "Copiar";
      dialogoTemporal.showModal();
      dialogoTemporal.addEventListener("close", () => (claveTemporal.textContent = ""), { once: true });
    } catch (error) {
      mostrarAviso(`No se pudo generar la contraseña. ${error.message}`, "error");
    }
  }

  $("#btn-copiar-temporal").addEventListener("click", async (evento) => {
    try {
      await navigator.clipboard.writeText(claveTemporal.textContent);
      evento.currentTarget.textContent = "Copiada";
    } catch {
      evento.currentTarget.textContent = "Selecciónala y cópiala";
    }
  });

  async function eliminar(u) {
    const ok = await confirmar("¿Eliminar la cuenta?",
      `Se borrará @${u.nombre_usuario}. Sus publicaciones del foro se conservan con su nombre. Esta acción no se puede deshacer.`,
      "Eliminar");
    if (!ok) return;
    try {
      await RefugiaAPI.eliminar(`/api/usuarios/${u.id_usuario}`);
      await recargar(`Se eliminó la cuenta @${u.nombre_usuario}.`);
    } catch (error) {
      mostrarAviso(`No se pudo eliminar. ${error.message}`, "error");
    }
  }

  // =========================================================
  // Inicio
  // =========================================================
  $("#filtros-usuarios").addEventListener("submit", (evento) => {
    evento.preventDefault();
    cargarUsuarios();
  });
  ["#filtro-rol", "#filtro-activo"].forEach((s) => $(s).addEventListener("change", () => cargarUsuarios()));
  botonMas.addEventListener("click", () => cargarUsuarios({ agregar: true }));

  RefugiaSesion.listo.then((usuario) => {
    if (usuario?.rol !== "administrador") return; // js/sesion.js lleva a iniciar sesión
    yo = usuario;
    recargar();
  });
})();
