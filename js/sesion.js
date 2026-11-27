/* =========================================================
   REFUGIA — Sesión del usuario (reutilizable en todas las páginas)
   ---------------------------------------------------------
   Cómo usarlo (después de js/api.js):
     <script src="js/api.js" defer></script>
     <script src="js/sesion.js" defer></script>            (páginas de la raíz)
     <script src="../js/sesion.js" defer></script>         (páginas de admin/)

   Qué hace:
     • Llena el menú de usuario con el nombre de quien inició sesión:
         [data-sesion-nombre]   → nombre        [data-sesion-detalle] → @usuario · rol
     • Muestra u oculta elementos según la sesión:
         data-sesion-ver="invitado"  → solo sin sesión (Iniciar sesión, Registrarse)
         data-sesion-ver="sesion"    → solo con sesión (Mi perfil, Cerrar sesión)
         data-sesion-ver="admin"     → solo administradores (Panel de administración)
     • Protege la página: <body data-requiere="sesion"> o <body data-requiere="admin">
       lleva a iniciar-sesion.html si no se cumple (con Live Server; si la página la sirve
       Flask, el servidor ya lo revisó antes de entregarla).
     • Cierra la sesión: cualquier enlace o botón con data-cerrar-sesion.

   API pública (window.RefugiaSesion):
     listo     → promesa con el usuario (o null si no inició sesión)
     usuario   → el usuario actual (después de "listo")
     cerrar()  → cierra la sesión y lleva al inicio
     urlIniciarSesion() → iniciar-sesion.html?siguiente=<esta página>
   ========================================================= */
(function () {
  "use strict";

  // Carpeta raíz del sitio (este archivo está en js/): sirve igual desde admin/ que desde la raíz
  const RAIZ = new URL("../", document.currentScript.src);

  function urlIniciarSesion() {
    const pagina = location.href.startsWith(RAIZ.href) ? location.href.slice(RAIZ.href.length) : "";
    const url = new URL("iniciar-sesion.html", RAIZ);
    if (pagina && !/^(iniciar-sesion|registro)\.html/.test(pagina)) url.searchParams.set("siguiente", pagina);
    return url.href;
  }

  function pintar(usuario) {
    const esAdmin = usuario?.rol === "administrador";
    document.querySelectorAll("[data-sesion-ver]").forEach((elemento) => {
      const ver = elemento.dataset.sesionVer;
      elemento.hidden = !(ver === "invitado" ? !usuario : ver === "sesion" ? Boolean(usuario) : esAdmin);
    });
    document.querySelectorAll("[data-sesion-nombre]").forEach((elemento) => {
      elemento.textContent = usuario ? usuario.nombre_visible : "Invitado";
    });
    document.querySelectorAll("[data-sesion-detalle]").forEach((elemento) => {
      elemento.textContent = usuario ? `@${usuario.nombre_usuario} · ${usuario.rol_nombre}` : "Inicia sesión para participar";
    });
    // "Iniciar sesión" vuelve a esta misma página después de entrar
    document.querySelectorAll('[data-sesion-ver="invitado"] a[href$="iniciar-sesion.html"]').forEach((enlace) => {
      enlace.href = urlIniciarSesion();
    });
  }

  async function cerrar(destino = new URL("inicio.html", RAIZ).href) {
    try {
      await RefugiaAPI.eliminar("/api/sesion");
    } catch {
      /* si no hay conexión igual se sale de la página */
    }
    location.assign(destino);
  }

  // Cerrar sesión desde cualquier enlace o botón con data-cerrar-sesion
  document.addEventListener("click", (evento) => {
    const elemento = evento.target.closest("[data-cerrar-sesion]");
    if (!elemento) return;
    evento.preventDefault();
    cerrar(elemento.href || undefined);
  });

  const listo = RefugiaAPI.obtener("/api/sesion")
    .then(({ usuario }) => usuario)
    .catch(() => null) // sin conexión con la API: se trata como invitado
    .then((usuario) => {
      window.RefugiaSesion.usuario = usuario;
      pintar(usuario);
      const requiere = document.body.dataset.requiere;
      if ((requiere === "sesion" && !usuario) || (requiere === "admin" && usuario?.rol !== "administrador")) {
        location.replace(urlIniciarSesion());
      }
      return usuario;
    });

  window.RefugiaSesion = { listo, usuario: null, cerrar, urlIniciarSesion };
})();
