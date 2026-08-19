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

    fetch(url, {
        method: 'GET',
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        },
    }).then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok ' + response.statusText);
        }
        return response.json();
    })
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
        }).catch(error => {
            var icons = actions.getElementsByClassName('fa-sync');
            while (icons.length > 0) { icons[0].remove(); };

            var icon = document.createElement('i');
            icon.className = 'fa-solid fa-skull-crossbones';
            actions.appendChild(icon);

            console.warn('There was a problem with the GET request: ' + error.message);
        });
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

    fetch(url, {
        method: 'POST',
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok ' + response.statusText);
            }
            return response.json();
        })
        .then(data => {
            form.querySelector('.muuid').value = data["uuid"];

            var icons = actions.getElementsByClassName('fa-sync');
            while (icons.length > 0) { icons[0].remove(); };

            var icon = document.createElement('i');
            icon.className = 'fa-solid fa-database';
            actions.appendChild(icon);

            console.info('POST successful: ' + JSON.stringify(data));
        })
        .catch(error => {
            var icons = actions.getElementsByClassName('fa-sync');
            while (icons.length > 0) { icons[0].remove(); };

            var icon = document.createElement('i');
            icon.className = 'fa-solid fa-skull-crossbones';
            actions.appendChild(icon);

            console.warn('There was a problem with the POST request: ' + error.message);
        });

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
    var forms = document.querySelectorAll('form[id^="ins"]');
    forms.forEach(function (form) {
        updateGeoEconMenuForm(form.id);
    });
});