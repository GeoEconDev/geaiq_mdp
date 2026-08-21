// Base de la API contra la que este reporte escribe el menú (ui/tmenu).
//
// Estaba hardcodeada a 'https://geoecon-api-dev-699125245692.us-central1.run.app/api/v1',
// el Cloud Run de la era GCP. Ese servicio hoy devuelve 503 "Service is disabled"
// — verificado el 2026-08-19 desde la laptop Y desde el VPS, así que no es un corte
// de red nuestro: está deshabilitado. Con esa URL, cada submit del formulario del
// reporte iba a un servicio muerto y la fila nunca llegaba a ui.t_menu.
//
// La migración a api.geaiq.com quedó a medio hacer: el lado Python ya está
// migrado (menu.py usa GEAIQ_API_URL con default https://api.geaiq.com) y este
// estático se quedó atrás. Se toma el valor que el reporte inyecta en
// window.GEAIQ_API_BASE, y si no está se cae al mismo default que el Python.
const endpoint_base = (
    (typeof window !== 'undefined' && window.GEAIQ_API_BASE)
    || 'https://api.geaiq.com/api/v1'
).replace(/\/+$/, '')

// --- Autenticación del browser ----------------------------------------------
//
// `/api/v1/ui` está detrás de `require_any_auth`, así que este fetch necesita
// mandar `Authorization: Bearer`. El JS original fue escrito contra una API SIN
// auth y no mandaba nada: cada submit se comía un 403 y la fila nunca llegaba a
// `ui.t_menu`.
//
// De dónde sale el token, y por qué NO va embebido en el reporte: los reportes
// se sirven PÚBLICOS, sin token (`redirect_router` no lleva `require_any_auth`),
// así que hornear una credencial en el HTML sería publicarla. Pero el reporte se
// sirve desde el MISMO ORIGEN que el admin (`static.py` sirve los HTML directo
// desde el dominio de la API justamente para eso), y el admin guarda su token de
// OAuth2 en `localStorage` de ese origen. O sea: la credencial es la del curador
// logueado y vive en SU browser, no en el documento.
//
// Verificado el 2026-08-20: `https://api.geaiq.com/admin.html` → 200 y
// `https://api.geaiq.com/reports/menu/ok/menu.md` → 200. Mismo host.
const TOKEN_KEY = 'gq_tok'
const REFRESH_KEY = 'gq_refresh'
const ADMIN_URL = '/admin.html'

function readStorage(key) {
    try {
        return localStorage.getItem(key)
    } catch (e) {
        // localStorage puede tirar en contextos con cookies de terceros bloqueadas.
        console.warn('No se pudo leer localStorage: ' + e.message)
        return null
    }
}

class AuthError extends Error { }

// Renueva el access token con el refresh. La forma de la llamada es la MISMA que
// usa el admin (`admin.html::_doRefresh`): POST /auth/oauth2/refresh con el
// refresh_token como form-urlencoded — no `/auth/token`, que es el login local.
async function refreshAccessToken() {
    const refresh = readStorage(REFRESH_KEY)
    if (!refresh || refresh === 'null') return null
    try {
        const r = await fetch(endpoint_base + '/auth/oauth2/refresh', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams({ refresh_token: refresh }),
        })
        if (!r.ok) return null
        const d = await r.json()
        if (!d.access_token) return null
        try {
            localStorage.setItem(TOKEN_KEY, d.access_token)
            if (d.refresh_token) localStorage.setItem(REFRESH_KEY, d.refresh_token)
        } catch (e) { /* sesión efímera: el token sirve igual para esta request */ }
        return d.access_token
    } catch (e) {
        return null
    }
}

// fetch con Authorization. Un 401/403 se reintenta UNA vez con el token renovado;
// si sigue fallando es sesión vencida y se dice con esas palabras, no con un
// "Network response was not ok" que manda a mirar la red.
async function apiFetch(url, options = {}) {
    let token = readStorage(TOKEN_KEY)
    if (!token) {
        throw new AuthError('No hay sesión: abrí ' + ADMIN_URL + ', logueate y recargá este reporte.')
    }
    const call = (tok) => fetch(url, {
        ...options,
        headers: { ...(options.headers || {}), 'Authorization': 'Bearer ' + tok },
    })

    let response = await call(token)
    if (response.status === 401 || response.status === 403) {
        const renewed = await refreshAccessToken()
        if (renewed) response = await call(renewed)
    }
    if (response.status === 401 || response.status === 403) {
        throw new AuthError('Sesión vencida o sin permiso: volvé a loguearte en ' + ADMIN_URL + ' y recargá este reporte.')
    }
    if (!response.ok) {
        throw new Error('Network response was not ok ' + response.statusText)
    }
    return response
}

// El aviso va ARRIBA y en el documento, no en la consola: si el curador no ve
// por qué no escribe, va a apretar los botones igual y a creer que guardó.
function showAuthBanner(message) {
    let banner = document.getElementById('geaiq-auth-banner')
    if (!banner) {
        banner = document.createElement('div')
        banner.id = 'geaiq-auth-banner'
        banner.style.cssText = 'position:sticky;top:0;z-index:9999;background:#fdecea;'
            + 'border:1px solid #d93025;color:#a50e0e;padding:.6em 1em;margin:0 0 1em 0;'
            + 'border-radius:4px;font-weight:600;'
        document.body.insertBefore(banner, document.body.firstChild)
    }
    banner.innerHTML = message
        + ' <a href="' + ADMIN_URL + '" target="_blank" rel="noopener">Abrir el admin</a>'
}

function reportError(actions, error) {
    var icons = actions.getElementsByClassName('fa-sync')
    while (icons.length > 0) { icons[0].remove() }

    var icon = document.createElement('i')
    icon.className = 'fa-solid fa-skull-crossbones'
    icon.title = error.message
    actions.appendChild(icon)

    if (error instanceof AuthError) {
        showAuthBanner(error.message)
    }
    console.warn('Falló la request: ' + error.message)
}

function updateGeoEconMenuForm(formId) {
    const form = document.getElementById(formId);
    const actions = form.previousElementSibling;
    const uuid = form.querySelector('.muuid').value;
    if (uuid !== '') {
        return;
    }

    const data = {
        slug: form.querySelector('.slug').value,
        country: form.querySelector('.country').value,
        scale: form.querySelector('.scale').value,
        period: form.querySelector('.period').value,
        topic: form.querySelector('.topic').value,
        indicator_1: form.querySelector('.indicator_1').value,
        indicator_2: form.querySelector('.indicator_2').value,
        indicator_3: form.querySelector('.indicator_3').value,
        indicator_4: form.querySelector('.indicator_4').value,
        indicator_5: form.querySelector('.indicator_5').value,
    };

    const url = new URL(endpoint_base + '/ui/tmenu' + (uuid ? '/' + uuid : ''));
    Object.keys(data).forEach(key => url.searchParams.append(key, data[key]));

    var icon = document.createElement('i');
    icon.className = 'fa-solid fa-sync fa-spin';
    actions.appendChild(icon);

    apiFetch(url, {
        method: 'GET',
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        },
    }).then(response => response.json())
        .then(data => {
            var icons = actions.getElementsByClassName('fa-sync');
            while (icons.length > 0) { icons[0].remove(); };

            data['items'].forEach(function (item) {
                var icon = document.createElement('i');
                icon.className = 'fa-solid fa-database';
                actions.appendChild(icon);
            });

            if (data["total"] == 1) {
                form.querySelector('.muuid').value = data['items'][0]['uuid'];
                console.info('GET successful: ' + JSON.stringify(data));
            } else if (data["total"] > 1) {
                console.warn('Multiple responses on GET request: ' + JSON.stringify(data));
            } else {
                console.info('No responses on GET request: ' + JSON.stringify(data));
            }
        }).catch(error => reportError(actions, error));
}

function postToGeoEcon(formId) {
    const form = document.getElementById(formId);
    const actions = form.previousElementSibling;
    const data = {
        slug: form.querySelector('.slug').value,
        country: form.querySelector('.country').value,
        scale: form.querySelector('.scale').value,
        period: form.querySelector('.period').value,
        topic: form.querySelector('.topic').value,
        indicator_1: form.querySelector('.indicator_1').value,
        indicator_2: form.querySelector('.indicator_2').value,
        indicator_3: form.querySelector('.indicator_3').value,
        indicator_4: form.querySelector('.indicator_4').value,
        indicator_5: form.querySelector('.indicator_5').value,
        description: form.querySelector('.description').value,
        resume: form.querySelector('.resume').value
    };

    const uuid = form.querySelector('.muuid').value;
    const url = endpoint_base + '/ui/tmenu' + (uuid ? '/' + uuid : '');

    var icon = document.createElement('i');
    icon.className = 'fa-solid fa-sync fa-spin';
    actions.appendChild(icon);

    apiFetch(url, {
        method: 'POST',
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
        .then(response => response.json())
        .then(data => {
            form.querySelector('.muuid').value = data["uuid"];

            var icons = actions.getElementsByClassName('fa-sync');
            while (icons.length > 0) { icons[0].remove(); };

            var icon = document.createElement('i');
            icon.className = 'fa-solid fa-database';
            actions.appendChild(icon);

            console.info('POST successful: ' + JSON.stringify(data));
        })
        .catch(error => reportError(actions, error));

}

function FillResumes(resume) {
    document.querySelectorAll("textarea.resume").forEach(ta => { ta.text = resume; });
}

function ClickAllButtons() {
    document.querySelectorAll("button").forEach(b => { b.click() });
}

function toggleForm(formId) {
    var formInputDiv = document.querySelector(`#${formId} .form_input`);
    if (formInputDiv.style.display === "none" || formInputDiv.style.display === "") {
        formInputDiv.style.display = "block";
    } else {
        formInputDiv.style.display = "none";
    }
}

document.addEventListener('DOMContentLoaded', function () {
    // El aviso va ANTES de que el curador apriete nada: sin sesión, cada
    // "Agregar/Actualizar Menú" es un 403 y la fila no entra al catálogo.
    if (!readStorage(TOKEN_KEY)) {
        showAuthBanner('No hay sesión iniciada: los botones de este reporte NO van a escribir en el catálogo.')
    }
    var forms = document.querySelectorAll('form[id^="ins"]');
    forms.forEach(function (form) {
        updateGeoEconMenuForm(form.id);
    });
});