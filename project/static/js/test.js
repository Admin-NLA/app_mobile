document.addEventListener('DOMContentLoaded', () => {
    const csrfToken = generateCsrfToken();
    document.getElementById('csrf-token').value = csrfToken;
});

function generateCsrfToken() {
    return 'csrf_' + Math.random().toString(36).substring(2,15) + Math.random().toString(36).substring(2,15);
}

const loginForm = document.getElementById('login-form');
loginForm.addEventListener('submit', (e) => {
    
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const csrfToken = document.getElementById('csrf-token').value;


    if (!username || !password) {
        alert('Por favor, llena todos los campos');
        return;
    }

    const hashedPassword = sha256(password);

    const formData = {
        username: username,
        password: hashedPassword,
        csrfToken: csrfToken,
    };
    
    message = document.getElementById('message');
    message.textContent = "Processing...";
    message.style.color = "blue";

    fetch(loginForm.action, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
    })
        .then((response) => response.json())
        .then((data) => {
            message.textContent = "Inicio de Sesión correcto";
            message.style.color = "green";
        })
        .catch(() => {
            message.textContent = "Ocurrió un error al procesar su solicitud";
            message.style.color = "red";
        });
});

async function sha256(message) {
    const msgBuffer = new TextEncoder().encode(message);
    const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map((b) => b.toString(16).padStart(2, '0')).join('');
}