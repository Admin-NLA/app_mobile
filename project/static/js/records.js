const recordsContainer = document.getElementById("recordsContainer");
const activeEventLabel = document.getElementById("activeEventLabel");
let records;
let eventName;
let c_user;
let canEditRecords = false;
const notesChangedMap = {};
const pendingRemoteRecordIds = new Set();
let recordsStream = null;
let streamRetryTimeout = null;
const expandedRecordIds = new Set();

function toggleExportButton(activeEvent) {
    const div = document.getElementById("topDiv");
    const exportButton = document.getElementById("exportBtn");

    if (activeEvent) {
        if (!exportButton) {
            const btn = document.createElement("button");
            btn.id = "exportBtn";
            btn.textContent = "Exportar Contactos";
            btn.onclick = exportRecords;
            btn.className = "btn btn-sm btn-success";
            div.appendChild(btn);
        }
    } else {
        if (exportButton) {
            exportButton.remove();
        }
    }
}

function updateEventLabel(eventData) {
    if (!activeEventLabel) return;
    if (eventData) {
        eventName = `${eventData.location} ${eventData.year}`;
        const modeLabel = eventData.is_editable_window
            ? `<span class="badge bg-success ms-2">Modo edición</span>`
            : `<span class="badge bg-secondary ms-2">Modo consulta</span>`;
        activeEventLabel.innerHTML = `<strong>${eventData.total_records} Registros</strong> para: <strong>${eventName}</strong> <span class="small">(${eventData.start_date} – ${eventData.end_date})</span> ${modeLabel}`;
        toggleExportButton(true);
    } else {
        activeEventLabel.textContent = "No hay evento activo para la fecha de hoy.";
        toggleExportButton(false);
    }
}

function renderRecords() {
    if (!recordsContainer) return;

    recordsContainer.innerHTML = "";
    Object.keys(notesChangedMap).forEach((key) => {
        delete notesChangedMap[key];
    });

    const visibleRecordIds = new Set();

    (records || []).forEach((record) => {
        visibleRecordIds.add(record.e_scan_id);

        const card = document.createElement("div");
        card.className = "record-card";

        const header = document.createElement("div");
        header.className = "d-flex justify-content-between align-items-start gap-2";

        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "btn btn-sm btn-outline-primary";
        btn.textContent = "+";

        const nameBlock = document.createElement("div");
        nameBlock.className = "text-start flex-grow-1 mx-2";
        nameBlock.innerHTML = `
            <p class="mb-0 fw-medium">${record.scanned_a_last_name} ${record.scanned_a_name}</p>
            <p class="mb-0 text-secondary" style="font-size:0.85rem;">${record.scanned_a_email || "N/A"}</p>
        `;

        const scheduleBtn = document.createElement("button");
        scheduleBtn.type = "button";
        scheduleBtn.id = `scheduleBtn${record.e_scan_id}`;
        scheduleBtn.className = "btn btn-sm btn-dark";
        scheduleBtn.textContent = record.appointment ? "Ver Cita" : "Agendar Cita";

        header.appendChild(btn);
        header.appendChild(nameBlock);
        if (window.innerWidth > 768) {
            header.appendChild(scheduleBtn);
        }
        card.appendChild(header);

        const details = document.createElement("div");
        details.className = "d-none mt-3";
        details.innerHTML = `
            <div class="container-fluid d-flex flex-column flex-md-row text-start">
                <div class="container d-flex flex-column justify-content-center mb-3 fs-5">
                    <span><strong>Día:</strong> ${record.day}</span>
                    <span><strong>Nombre:</strong> ${record.scanned_a_last_name} ${record.scanned_a_name}</span>
                    <span><strong>Teléfono:</strong> ${record.scanned_a_phone || "N/A"}</span>
                    <span><strong>Empresa:</strong> ${record.scanned_a_company || "N/A"}</span>
                    <span><strong>Escaneado por:</strong> ${record.scanned_by_rep_name || record.scanned_by_login || "Sin registrar"}</span>
                    <span class="fw-bold mt-3 mb-2">Estado de la Cita:</span>
                    <div id="appointmentStatus${record.e_scan_id}">
                        <span></span>
                    </div>
                    <div class="form-check">
                        <input class="form-check-input check-yes" type="radio" name="apptStatus${record.e_scan_id}" 
                            id="appointmentCompletedRadio${record.e_scan_id}" value="completed" disabled>
                        <label class="form-check-label" for="appointmentCompletedRadio${record.e_scan_id}">Marcar Cita como Completada</label>
                    </div>
                    <div class="form-check">
                        <input class="form-check-input check-no" type="radio" name="apptStatus${record.e_scan_id}" 
                            id="appointmentNoCompletedRadio${record.e_scan_id}" value="not_completed" disabled>
                        <label class="form-check-label" for="appointmentNoCompletedRadio${record.e_scan_id}">Marcar Cita como No Completada</label>
                    </div>
                </div>
                <div class="container d-flex flex-column justify-content-center mb-3">
                    <span class="mb-2"><strong>Notas:</strong></span>
                    <textarea class="form-control border-dark" rows="10" id="notesText${record.e_scan_id}">${record.notes || ""}</textarea>
                </div>
            </div>
            <div class="container-fluid d-flex flex-column flex-md-row text-start">
                <div class="container d-flex flex-column justify-content-center mb-3 order-2 order-md-1" id="scheduleContainer${record.e_scan_id}">
                </div>
                <div class="container d-flex flex-column justify-content-center mb-3 order-1 order-md-2">
                    <button disabled class="btn btn-sm btn-dark" id="saveBtn${record.e_scan_id}" 
                    onclick="updateNotes(${record.e_scan_id}, document.getElementById('notesText${record.e_scan_id}').value)">Guardar</button>
                </div>
            </div>
        `;
        card.appendChild(details);
        recordsContainer.appendChild(card);

        if (window.innerWidth < 768) {
            details.querySelector(`#scheduleContainer${record.e_scan_id}`).appendChild(scheduleBtn);
        }

        const notesTA = document.getElementById(`notesText${record.e_scan_id}`);
        const saveBtn = document.getElementById(`saveBtn${record.e_scan_id}`);

        notesTA.addEventListener("input", () => {
            if (notesTA.value.trim() !== (record.notes || "")) {
                saveBtn.disabled = false;
                notesChangedMap[record.e_scan_id] = true;
            } else {
                saveBtn.disabled = true;
                notesChangedMap[record.e_scan_id] = false;
            }
        });

        btn.addEventListener("click", () => {
            const isHidden = details.classList.contains("d-none");
            details.classList.toggle("d-none", !isHidden);
            btn.textContent = isHidden ? "−" : "+";
            if (isHidden) {
                expandedRecordIds.add(record.e_scan_id);
            } else {
                expandedRecordIds.delete(record.e_scan_id);
            }
        });

        if (expandedRecordIds.has(record.e_scan_id)) {
            details.classList.remove("d-none");
            btn.textContent = "−";
        }

        const apptStatusText = document.getElementById(`appointmentStatus${record.e_scan_id}`);
        const apptCompletedRadio = document.getElementById(`appointmentCompletedRadio${record.e_scan_id}`);
        const apptNoCompletedRadio = document.getElementById(`appointmentNoCompletedRadio${record.e_scan_id}`);
        let statusText, statusTextClass;

        scheduleBtn.addEventListener("click", async () => {
            if (!canEditRecords && !record.appointment) {
                await Swal.fire({
                    theme: "dark",
                    title: "<strong>AVISO</strong>",
                    text: "Evento Finalizado. Sólo puedes consultar y exportar contactos.",
                    icon: "info"
                });
                return;
            }
            const scheduleResult = await Swal.fire({
                theme: "dark",
                title: `<strong>${record.appointment ? "Actualizar Cita" : "Agendar Cita"}</strong>`,
                html: `
                    <div style="display:flex; flex-direction:column; gap:10px; width:100%">
                        <label for="appointmentDate">Fecha:</label>
                        <input id="appointmentDate" type="date" class="swal2-input"
                            value="${record.appointment ? record.appointment.date : ''}">
                        <label for="appointmentHour">Hora:</label>
                        <input id="appointmentHour" type="time" class="swal2-input"
                            value="${record.appointment ? record.appointment.hour : ''}">
                        <label for="appointmentDescription">Descripción:</label>
                        <textarea id="appointmentDescription" class="swal2-textarea">${record.appointment ? record.appointment.description.trim() : ''}</textarea>
                    </div>
                `,
                focusConfirm: false,
                showCancelButton: true,
                showDenyButton: Boolean(record.appointment),
                confirmButtonText: record.appointment ? "Actualizar Cita" : "Guardar Cita",
                denyButtonText: "Descargar Cita",
                confirmButtonColor: "#4caf50",
                cancelButtonText: "Cancelar",
                preDeny: () => {
                    if (!record.appointment) {
                        Swal.showValidationMessage("No hay cita guardada");
                        return false;
                    }
                    return true;
                },
                preConfirm: () => {
                    const date = document.getElementById('appointmentDate').value;
                    const hour = document.getElementById('appointmentHour').value;
                    const description = document.getElementById('appointmentDescription')?.value ?? "";
                    if (!date || !hour) {
                        Swal.showValidationMessage('Escoge una fecha y hora');
                        return false;
                    }
                    return { date, hour, description };
                },
            });

            if (scheduleResult.isConfirmed) {
                if (!canEditRecords) {
                    await Swal.fire({
                        theme: "dark",
                        title: "<strong>AVISO</strong>",
                        text: "Evento Finalizado. Sólo puedes consultar y exportar contactos.",
                        icon: "info"
                    });
                    return;
                }
                const { date, hour, description } = scheduleResult.value;

                const schedulePayload = {
                    e_scan_id: record.e_scan_id,
                    appointment_id: record.appointment ? record.appointment.appointment_id : 0,
                    date: date,
                    hour: hour,
                    description: description
                };

                const response = await fetch("/add-or-update-appointment", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(schedulePayload)
                });
                const responseData = await response.json().catch(() => ({}));

                if (!response.ok) {
                    await Swal.fire({
                        theme: "dark",
                        title: "<strong>ERROR</strong>",
                        text: "No se pudo guardar la cita",
                        icon: "error"
                    });
                    return;
                }

                record.appointment = responseData.appointment;
                scheduleBtn.textContent = "Ver Cita";

                [statusText, statusTextClass] = changeApptDisplayedStatus(record.appointment);
                apptStatusText.querySelector('span').textContent = statusText;
                apptStatusText.className = statusTextClass;
                apptCompletedRadio.disabled = false;
                apptNoCompletedRadio.disabled = false;

                await Swal.fire({
                    theme: "dark",
                    title: "<strong>ÉXITO</strong>",
                    text: responseData.message || "Cita guardada",
                    icon: "success"
                });

            } else if (scheduleResult.isDenied) {
                downloadAndShareAppointment(record);
            }
        });

        if (!record.appointment) {
            statusText = "Cita no Agendada";
            statusTextClass = "appt-badge appt-badge--none";
        } else {
            apptCompletedRadio.disabled = false;
            apptNoCompletedRadio.disabled = false;
            [statusText, statusTextClass] = changeApptDisplayedStatus(record.appointment);
        }

        saveBtn.disabled = true;

        apptStatusText.querySelector('span').textContent = statusText;
        apptStatusText.className = statusTextClass;

        document.querySelectorAll(`input[name="apptStatus${record.e_scan_id}"]`)
            .forEach(radio => {
                radio.addEventListener("focus", function () {
                    this.dataset.waschecked = this.checked;
                });
                radio.addEventListener("change", async function () {
                    if (this.checked) {
                        const ok = await updateAppointmentStatus(this, record);
                        if (!ok) {
                            const radios = document.querySelectorAll(`input[name="apptStatus${record.e_scan_id}"][value="${this.value}"]`);
                            radios.forEach(r => r.checked = false);
                            const prev = Array.from(radios).find(r => r.dataset.waschecked === "true");
                            if (prev) prev.checked = true;
                        }
                    }
                });
            });

    });

    [...expandedRecordIds].forEach((recordId) => {
        if (!visibleRecordIds.has(recordId)) {
            expandedRecordIds.delete(recordId);
        }
    });
}

async function updateNotes(e_scan_id, notes) {
    if (!canEditRecords) {
        await Swal.fire({
            theme: "dark",
            title: "<strong>AVISO</strong>",
            text: "Evento Finalizado. Sólo puedes consultar y exportar contactos.",
            icon: "info"
        });
        return;
    }
    if (!notesChangedMap[e_scan_id]) {
        await Swal.fire({
            theme: "dark",
            title: "<strong>CUIDADO</strong>",
            text: "No se actualizaron las notas. Acción no permitida",
            icon: "warning"
        });
        return;
    }
    const updatePayload = {
        e_scan_id: e_scan_id,
        notes: notes || ''
    };
    const response = await fetch("/update-exhibitor-record-notes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updatePayload)
    });

    const updateData = await response.json().catch(() => ({}));

    if (!response.ok || !updateData.success) {
        await Swal.fire({
            theme: "dark",
            title: "<strong>ERROR</strong>",
            text: updateData.message || "No se pudieron actualizar las notas",
            icon: "error"
        });
        return;
    }

    await Swal.fire({
        theme: "dark",
        title: "<strong>ÉXITO</strong>",
        text: updateData.message || "Notas actualizadas",
        icon: "success"
    });

    const record = (records || []).find(r => r.e_scan_id === e_scan_id);
    if (record) {
        record.notes = updatePayload.notes;
    }
    notesChangedMap[e_scan_id] = false;

    document.getElementById(`saveBtn${e_scan_id}`).disabled = true;

    if (pendingRemoteRecordIds.has(e_scan_id)) {
        pendingRemoteRecordIds.delete(e_scan_id);
        loadRecords();
    }
}

function loadRecords() {
    fetch("/exhibitor-records", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({}),
    })
        .then((response) => response.json())
        .then((data) => {
            c_user = data.current_user;
            canEditRecords = Boolean(data.is_editable_window);
            updateEventLabel(data.event);
            records = data.records;
            renderRecords();
            if (data.event && data.event.is_editable_window && !recordsStream) {
                startRecordsStream();
            }
        });
}

function insertNewRecord(record) {
    records.push(record);
    renderRecords();
}

function updateSingleRecord(updatedRecord) {
    const index = records.findIndex(r => r.e_scan_id === updatedRecord.e_scan_id);

    if (index === -1) return;

    records[index] = updatedRecord;
    renderRecords();
}

function hasPendingLocalChanges() {
    return Object.values(notesChangedMap).some(Boolean);
}

function hasPendingNotesForRecord(eScanId) {
    return Boolean(notesChangedMap[eScanId]);
}

function startRecordsStream() {
    if (recordsStream) return;

    recordsStream = io({
        transports: ["websocket"]
    });

    recordsStream.on("connect", () => {
        if (!hasPendingLocalChanges()) {
            loadRecords();
        }
    });

    recordsStream.on("records_update", (payload) => {
        if (!payload) return;

        if (payload.type === "record_created") {
            insertNewRecord(payload.record);
            return;
        }

        if (payload.type === "record_updated") {
            const record = payload.record;

            if (hasPendingNotesForRecord(record.e_scan_id)) {
                pendingRemoteRecordIds.add(record.e_scan_id);
                return;
            }

            updateSingleRecord(record);
        }
    });

    recordsStream.on("disconnect", () => {
        recordsStream = null;

        if (!streamRetryTimeout) {
            streamRetryTimeout = setTimeout(() => {
                streamRetryTimeout = null;
                startRecordsStream();
            }, 3000);
        }
    });
}

window.addEventListener("beforeunload", () => {
    if (recordsStream) {
        recordsStream.close();
        recordsStream = null;
    }
    if (streamRetryTimeout) {
        clearTimeout(streamRetryTimeout);
        streamRetryTimeout = null;
    }
});

async function exportRecords() {

    if (!records || records.length === 0) {
        await Swal.fire({
            theme: "dark",
            title: "<strong>AVISO</strong>",
            text: "No hay registros para exportar",
            icon: "info"
        });
        return;
    }

    fetch("/export-records")
        .then(async response => {
            if (!response.ok) {
                const err = await response.json().catch(() => ({}));

                await Swal.fire({
                    theme: "dark",
                    title: "<strong>ERROR</strong>",
                    text: err.error || "Ocurrió un error al exportar",
                    icon: "error"
                });
                return;
            }
            return response.blob();
        })
        .then(blob => {
            const downloadUrl = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = downloadUrl;
            a.download = `Contactos CMC ${eventName}`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(downloadUrl);

            Swal.fire({
                theme: "dark",
                title: "<strong>ÉXITO</strong>",
                text: "Descarga completada exitosamente",
                icon: "success"
            });
        })
        .catch(err => {
            Swal.fire({
                theme: "dark",
                title: "<strong>ERROR</strong>",
                text: "Descarga fallida " + err.message,
                icon: "error"
            });
        });
}

async function downloadAndShareAppointment(record) {

    const dateStr = record.appointment.date.replace(/-/g, "");
    const hourStr = record.appointment.hour.replace(":", "") + "00";

    const icsContent = `BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//CMC//ES
BEGIN:VEVENT
UID:${record.appointment.appointment_id}-cmc-app
DTSTAMP:${dateStr}T${hourStr}
DTSTART:${dateStr}T${hourStr}
DTEND:${dateStr}T${hourStr}
SUMMARY:Cita ${c_user} con ${record.scanned_a_last_name} ${record.scanned_a_name}
DESCRIPTION:${escapeICSText(record.appointment.description)}
LOCATION:${escapeICSText(record.appointment.location)}
END:VEVENT
END:VCALENDAR`;

    const fileName = `cita_${record.scanned_a_last_name}_${record.scanned_a_name}_con_${c_user}.ics`;
    const blob = new Blob([icsContent], { type: "text/calendar" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = fileName;
    link.click();
    link.remove();
    URL.revokeObjectURL(link.href);

    await Swal.fire({
        theme: "dark",
        title: "<strong>ÉXITO</strong>",
        text: `Cita descargada. Para guardar en calendario, haga click en el archivo y seleccione el Calendario Disponible de su preferencia`,
        icon: "success"
    });
}

async function updateAppointmentStatus(radio, record) {
    if (!canEditRecords) {
        await Swal.fire({
            theme: "dark",
            title: "<strong>AVISO</strong>",
            text: "Evento Finalizado. Sólo puedes consultar y exportar contactos.",
            icon: "info"
        });
        radio.checked = false;
        return false;
    }
    if (!record.appointment) {
        await Swal.fire({
            theme: "dark",
            title: "<strong>CUIDADO</strong>",
            text: "No hay cita agendada. Acción no permitida",
            icon: "warning"
        });
        radio.checked = false;
        return false;
    }

    if (!hasAppointmentTimeReached(record.appointment)) {
        await Swal.fire({
            theme: "dark",
            title: "<strong>CUIDADO</strong>",
            text: "La fecha y hora de la cita no se ha cumplido. No se actualizó el estado",
            icon: "warning"
        });
        radio.checked = false;
        return false;
    }

    const isCompleted = radio.value === "completed";

    const updatePayload = {
        appointment_id: record.appointment ? record.appointment.appointment_id : 0,
        status: isCompleted
    };

    const response = await fetch("/update-appointment-status", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updatePayload)
    });

    const responseData = await response.json().catch(() => ({}));

    if (!response.ok) {
        await Swal.fire({
            theme: "dark",
            title: "<strong>ERROR</strong>",
            text: "No se pudo actualizar el estado de la cita",
            icon: "error"
        });
        radio.checked = false;
        return false;
    }

    record.appointment.status = isCompleted;

    const apptStatusText = document.getElementById(`appointmentStatus${record.e_scan_id}`);
    const [statusText, statusTextClass] = changeApptDisplayedStatus(record.appointment);
    apptStatusText.querySelector('span').textContent = statusText;
    apptStatusText.className = statusTextClass;

    await Swal.fire({
        theme: "dark",
        title: "<strong>ÉXITO</strong>",
        text: responseData.message || "Estado de la cita actualizado",
        icon: "success"
    });

    return true;
}

function hasAppointmentTimeReached(appointment) {
    const now = new Date();

    const [year, month, day] = appointment.date.split("-").map(Number);
    const apptDate = new Date(year, month - 1, day);
    const [hours, minutes] = appointment.hour.split(":").map(Number);
    apptDate.setHours(hours, minutes, 0, 0);

    return now >= apptDate;
}

function isAppointmentExpired(appointment) {
    const now = new Date();

    const [year, month, day] = appointment.date.split("-").map(Number);
    const apptDate = new Date(year, month - 1, day);
    const [hours, minutes] = appointment.hour.split(":").map(Number);
    apptDate.setHours(hours, minutes, 0, 0);

    const apptDeadline = new Date(apptDate.getTime() + 2 * 60 * 60 * 1000);

    return now >= apptDeadline;
}

function changeApptDisplayedStatus(appointment) {
    var statusText, statusContainerClass;

    const completedRadio = document.getElementById(`appointmentCompletedRadio${appointment.e_scan_id}`);
    const noCompletedRadio = document.getElementById(`appointmentNoCompletedRadio${appointment.e_scan_id}`);

    completedRadio.checked = false;
    noCompletedRadio.checked = false;

    if (appointment.status) {
        completedRadio.checked = true;
        statusText = "Cita Completada";
        statusContainerClass = "appt-badge appt-badge--completed";
    } else {
        if (hasAppointmentTimeReached(appointment)) {
            if (appointment.status === false || isAppointmentExpired(appointment)) {
                statusText = "Cita no Completada";
                statusContainerClass = "appt-badge appt-badge--not-completed";
                noCompletedRadio.checked = true;
            } else {
                statusText = "Cita en Curso";
                statusContainerClass = "appt-badge appt-badge--in-progress";
            }

        } else {
            statusText = "Cita Pendiente";
            statusContainerClass = "appt-badge appt-badge--pending";
        }
    }
    return [statusText, statusContainerClass];
}

function escapeICSText(text) {
    return (text || "")
        .replace(/\\/g, "\\\\")
        .replace(/;/g, "\\;")
        .replace(/,/g, "\\,")
        .replace(/\n/g, "\\n");
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", loadRecords);
} else {
    loadRecords();
}
