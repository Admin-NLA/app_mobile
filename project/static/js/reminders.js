const REMINDER_MINUTES = 5;
const CHECK_INTERVAL_MS = 30000;
const NOTIFIED_KEY_PREFIX = "cmc_reminder_notified_";
const DISMISSED_BANNER_KEY = "cmc_reminder_banner_dismissed";

let upcomingAppointments = [];

function parseAppointmentDateTime(appt) {
    const [year, month, day] = appt.date.split("-").map(Number);
    const [hours, minutes] = appt.hour.split(":").map(Number);
    return new Date(year, month - 1, day, hours, minutes, 0, 0);
}

function showInPageBubble(title, body) {
    const bubble = document.createElement("div");
    bubble.className = "reminder-bubble";
    bubble.innerHTML = `<strong>${title}</strong><br>${body}`;
    document.body.appendChild(bubble);

    setTimeout(() => {
        bubble.classList.add("reminder-bubble--hide");
        setTimeout(() => bubble.remove(), 500);
    }, 8000);
}

function fireReminder(appt) {
    const title = "Tu cita está por comenzar";
    const body = `Reunión con ${appt.contact_name} a las ${appt.hour}`;

    if ("Notification" in window && Notification.permission === "granted") {
        new Notification(title, { body });
    }

    showInPageBubble(title, body);
}

function checkUpcomingAppointments() {
    const now = new Date();

    upcomingAppointments.forEach((appt) => {
        const apptTime = parseAppointmentDateTime(appt);
        const diffMinutes = (apptTime - now) / 60000;
        const notifiedKey = `${NOTIFIED_KEY_PREFIX}${appt.appointment_id}`;

        if (diffMinutes > 0 && diffMinutes <= REMINDER_MINUTES && !sessionStorage.getItem(notifiedKey)) {
            fireReminder(appt);
            sessionStorage.setItem(notifiedKey, "1");
        }
    });
}

function loadAppointments() {
    fetch("/exhibitor-appointments")
        .then((response) => response.json())
        .then((data) => {
            upcomingAppointments = data.appointments || [];
        });
}

function setupNotificationBanner() {
    if (!("Notification" in window)) return;
    if (Notification.permission !== "default") return;
    if (localStorage.getItem(DISMISSED_BANNER_KEY)) return;

    const banner = document.createElement("div");
    banner.className = "reminder-banner";
    banner.innerHTML = `
        <span>¿Activar notificaciones para avisos de citas próximas?</span>
        <button type="button" class="btn btn-sm btn-dark" id="reminderEnableBtn">Activar</button>
        <button type="button" class="btn btn-sm btn-outline-secondary" id="reminderDismissBtn">Ahora no</button>
    `;
    document.body.appendChild(banner);

    document.getElementById("reminderEnableBtn").addEventListener("click", () => {
        Notification.requestPermission().finally(() => banner.remove());
    });

    document.getElementById("reminderDismissBtn").addEventListener("click", () => {
        localStorage.setItem(DISMISSED_BANNER_KEY, "1");
        banner.remove();
    });
}

setupNotificationBanner();
loadAppointments();
setInterval(checkUpcomingAppointments, CHECK_INTERVAL_MS);

if (typeof io !== "undefined") {
    const reminderSocket = io();
    reminderSocket.on("records_update", () => {
        loadAppointments();
    });
}