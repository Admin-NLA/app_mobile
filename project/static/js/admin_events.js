const eventsBody = document.getElementById("eventsBody");

function badgeClassFor(event) {
    if (event.manual_status === true) return "appt-badge appt-badge--completed";
    if (event.manual_status === false) return "appt-badge appt-badge--not-completed";
    return "appt-badge appt-badge--pending";
}

function renderEvents(events) {
    eventsBody.innerHTML = "";

    events.forEach((event) => {
        const row = eventsBody.insertRow();

        row.insertCell().textContent = `${event.location} ${event.year}`;
        row.insertCell().textContent = event.start_date;
        row.insertCell().textContent = event.end_date;

        const statusCell = row.insertCell();
        statusCell.innerHTML = `<span class="${badgeClassFor(event)}">${event.manual_label}</span>`;

        const activeCell = row.insertCell();
        activeCell.textContent = event.is_effective_active ? "Sí" : "No";

        const actionsCell = row.insertCell();

        const activateBtn = document.createElement("button");
        activateBtn.className = "btn btn-sm btn-dark me-1";
        activateBtn.textContent = "Forzar Activo";
        activateBtn.disabled = event.manual_status === true;
        activateBtn.addEventListener("click", () => confirmAndSetStatus(event, "activate"));

        const disableBtn = document.createElement("button");
        disableBtn.className = "btn btn-sm btn-outline-danger me-1";
        disableBtn.textContent = "Deshabilitar";
        disableBtn.disabled = event.manual_status === false;
        disableBtn.addEventListener("click", () => confirmAndSetStatus(event, "disable"));

        const autoBtn = document.createElement("button");
        autoBtn.className = "btn btn-sm btn-outline-secondary";
        autoBtn.textContent = "Automático";
        autoBtn.disabled = event.manual_status === null;
        autoBtn.addEventListener("click", () => confirmAndSetStatus(event, "auto"));

        actionsCell.appendChild(activateBtn);
        actionsCell.appendChild(disableBtn);
        actionsCell.appendChild(autoBtn);
    });
}

async function confirmAndSetStatus(event, action) {
    const eventName = `${event.location} ${event.year}`;
    const actionText = {
        activate: `forzar "${eventName}" como el evento activo (y quitar el forzado de cualquier otro)`,
        disable: `deshabilitar "${eventName}" (nunca se elegirá automáticamente)`,
        auto: `regresar "${eventName}" a modo automático`,
    }[action];

    const confirmResult = await Swal.fire({
        theme: "dark",
        title: "¿Confirmas este cambio?",
        text: `Vas a ${actionText}.`,
        icon: "warning",
        showCancelButton: true,
        confirmButtonText: "Sí, confirmar",
        cancelButtonText: "Cancelar",
        confirmButtonColor: "#212E57",
    });

    if (!confirmResult.isConfirmed) return;

    const response = await fetch("/admin/events/set-status", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ event_id: event.event_id, action }),
    });

    const result = await response.json().catch(() => ({}));

    if (!response.ok || !result.success) {
        await Swal.fire({
            theme: "dark",
            title: "<strong>ERROR</strong>",
            text: result.message || "No se pudo actualizar el estado",
            icon: "error",
        });
        return;
    }

    await Swal.fire({
        theme: "dark",
        title: "<strong>ÉXITO</strong>",
        text: result.message,
        icon: "success",
    });

    loadEvents();
}

function loadEvents() {
    fetch("/admin/events/list")
        .then((response) => response.json())
        .then((data) => renderEvents(data.events || []));
}

loadEvents();