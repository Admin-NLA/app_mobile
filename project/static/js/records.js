const recordsTable = document.getElementById("recordsTable");
const activeEventLabel = document.getElementById("activeEventLabel");
let records;
let eventName;
let c_user;
const notesChangedMap = {}

function toggleExportButton(activeEvent){
    const div =  document.getElementById("topDiv");
    const exportButton = document.getElementById("exportBtn");

    if (activeEvent) {
        if (!exportButton) {
            const btn = document.createElement("button");
            btn.id= "exportBtn";
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
        activeEventLabel.innerHTML = `<strong>${eventData.total_records} Registros</strong> para: <strong>${eventName}</strong> <span class="small">(${eventData.start_date} – ${eventData.end_date})</span>`;
        //document.getElementById("exportBtn").disabled = false;
        toggleExportButton(true);
    } else {
        activeEventLabel.textContent = "No hay evento activo para la fecha de hoy.";
        //document.getElementById("exportBtn").disabled = true;
        toggleExportButton(false);
    }
}

function renderRecords() {
    const theadRow = recordsTable ? recordsTable.querySelector("thead tr") : null;
    const tbody = recordsTable ? recordsTable.querySelector("tbody") : null;
    if (!theadRow || !tbody) return;

    tbody.innerHTML = "";

    if (window.innerWidth > 768) theadRow.insertCell();

    (records || []).forEach((record) => {
        const row = tbody.insertRow();
        row.classList.add("align-middle");

        const expandCell = row.insertCell();
        const fullNameCell = row.insertCell();
        const emailCell = row.insertCell();

        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "btn btn-sm btn-outline-primary";
        btn.textContent = "+";
        expandCell.appendChild(btn);

        fullNameCell.textContent = record.name;
        emailCell.textContent = record.email || "N/A";

        let detailsColSpan = 3;

        const scheduleBtn = document.createElement("button");
        scheduleBtn.type = "button";
        scheduleBtn.id = `scheduleBtn${record.e_scan_id}`;
        scheduleBtn.className = "btn btn-sm btn-dark";

        scheduleBtn.textContent = record.appointment ? "Ver Cita" : "Agendar Cita";

        if (window.innerWidth > 768) {
            const scheduleCell = row.insertCell();
            scheduleCell.appendChild(scheduleBtn);
            detailsColSpan = 4;
        }

        const detailsRow = tbody.insertRow();
        detailsRow.classList.add("d-none");
        const detailsCell = detailsRow.insertCell();
        detailsCell.colSpan = detailsColSpan;
        detailsCell.innerHTML = `
            <div class="container-fluid d-flex flex-column flex-md-row text-start">
                <div class="container d-flex flex-column justify-content-center mb-3 fs-5">
                    <span><strong>Nombre:</strong> ${record.name}</span>
                    <span><strong>Día:</strong> ${record.day}</span>
                    <span><strong>Teléfono:</strong> ${record.phone || "N/A"}</span>
                    <span><strong>Empresa:</strong> ${record.company || "N/A"}</span>
                    <span class="d-flex flex-column flex-md-row mt-4"><strong class="me-sm-2 mb-1 mb-sm-0">Estado de la Cita:</strong> <span id="appointmentStatus${record.e_scan_id}"></span></span>
                    <span>
                        <input class="form-check-input" type="checkbox" id="appointmentCheck${record.e_scan_id}" disabled>
                        <label class="form-check-label" for="appointmentCheck${record.e_scan_id}">Marcar Cita como Completada</label>
                    </span>
                </div>
                <div class="container d-flex flex-column justify-content-center mb-3">
                    <span class="mb-3"><strong>Notas:</strong></span> 
                    <textarea class="form-control border-dark" rows="8" id="notesText${record.e_scan_id}">${record.notes || ""}</textarea>
                </div>
            </div>
            <div class="container-fluid d-flex flex-column flex-md-row text-start">
                <div class="container d-flex flex-column justify-content-center mb-3 order-2 order-md-1" id="scheduleContainer${record.e_scan_id}">
                </div>
                <div class="container d-flex flex-column justify-content-center mb-3 order-1 order-md-2">
                    <button disabled class="btn btn-sm btn-dark" id="saveBtn${record.e_scan_id}" onclick="updateNotes(${record.e_scan_id}, document.getElementById('notesText${record.e_scan_id}').value)">Guardar</button>
                </div>
            </div>
        `;

        if (window.innerWidth < 768) {
            document.getElementById(`scheduleContainer${record.e_scan_id}`).appendChild(scheduleBtn);
        }

        const notesTA =  document.getElementById(`notesText${record.e_scan_id}`);
        const saveBtn =  document.getElementById(`saveBtn${record.e_scan_id}`);

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
            const isHidden = detailsRow.classList.contains("d-none");
            detailsRow.classList.toggle("d-none", !isHidden);
            btn.textContent = isHidden ? "−" : "+";
        });
        
        const apptStatusText = document.getElementById(`appointmentStatus${record.e_scan_id}`);
        const apptCheck = document.getElementById(`appointmentCheck${record.e_scan_id}`);
        let statusCheckState, statusText, statusTextClass;

        scheduleBtn.addEventListener("click", async () => {
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
                showDenyButton: true,
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
                const { date, hour, description } = scheduleResult.value;

                const schedulePayload = {
                    e_scan_id: record.e_scan_id,
                    appointment_id: record.appointment ? record.appointment.appointment_id : 0, 
                    date: date,
                    hour: hour,
                    description: description
                };

                const response = await fetch("/add_or_update_appointment", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(schedulePayload)
                });
                const responseData = await response.json().catch(() => ({}));

                if(!response.ok) {
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

                [statusCheckState, statusText, statusTextClass] = changeApptDisplayedStatus(record.appointment);
                apptStatusText.innerHTML = statusText;
                apptStatusText.className = statusTextClass;
                apptCheck.checked = statusCheckState;

                await Swal.fire({
                    theme: "dark",
                    title: "<strong>ÉXITO</strong>",
                    text: responseData.message || "Cita guardada",
                    icon: "success"
                });

            } else if(scheduleResult.isDenied) {
                downloadAndShareAppointment(record);
            }
        });

        if (!record.appointment) {
            statusText = "Cita no Agendada";
            statusTextClass = "text-muted";
        } else {
            apptCheck.disabled = false;
            [statusCheckState, statusText, statusTextClass] = changeApptDisplayedStatus(record.appointment);
            apptCheck.checked = statusCheckState;
        }

        apptStatusText.innerHTML = statusText;
        apptStatusText.className = statusTextClass;

        apptCheck.addEventListener("change", function () {
            updateAppointmentStatus(this, record);
        });
    });
}

async function updateNotes(e_scan_id, notes) {
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

    if(!response.ok || !updateData.success) {
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

    document.getElementById(`saveBtn${e_scan_id}`).disabled = true;
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
            updateEventLabel(data.event);
            records = data.records;
            renderRecords();
        });
}

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
                const err = await response.json().catch(() =>  ({}));

                await Swal.fire({
                    theme: "dark",
                    title: "<strong>ERROR</strong>",
                    text:  err.error || "Ocurrió un error al exportar",
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
                text:  "Descarga fallida" + err.message,
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
SUMMARY:Cita ${c_user} con ${record.name}
DESCRIPTION:${escapeICSText(record.appointment.description)}
LOCATION:${escapeICSText(record.appointment.location)}
END:VEVENT
END:VCALENDAR`;

    const fileName = `cita_${record.name}_con_${c_user}.ics`;
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

async function updateAppointmentStatus(checkbox, record) {
    if (!record.appointment) {
        await Swal.fire({
            theme: "dark",
            title: "<strong>CUIDADO</strong>",
            text: "No hay cita agendada. Acción no permitida",
            icon: "warning"
        });
        return;
    }

    if(isAppointmentActive(record.appointment)) {
        await Swal.fire({
            theme: "dark",
            title: "<strong>CUIDADO</strong>",
            text: "La fecha y hora de la cita no se ha cumplido. No se actualizó el estado",
            icon: "warning"
        });
        checkbox.checked = !checkbox.checked;
        return;
    }

    const isChecked = checkbox.checked;

    const updatePayload = {
        appointment_id: record.appointment ? record.appointment.appointment_id : 0,
        status: isChecked
    };

    const response = await fetch("/update-appointment-status", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updatePayload)
    });

    const responseData = await response.json().catch(() => ({}));

    if(!response.ok) {
        await Swal.fire({
            theme: "dark",
            title: "<strong>ERROR</strong>",
            text: "No se pudo actualizar el estado de la cita",
            icon: "error"
        });
        checkbox.checked = !checkbox.checked;
        return;
    }

    const apptStatusText = document.getElementById(`appointmentStatus${record.e_scan_id}`);
    const [statusCheckState, statusText, statusTextClass] = changeApptDisplayedStatus(record.appointment);
    apptStatusText.innerText = statusText;
    apptStatusText.className = statusTextClass;

    await Swal.fire({
        theme: "dark",
        title: "<strong>ÉXITO</strong>",
        text: responseData.message || "Estado de la cita actualizado",
        icon: "success"
    });

    record.appointment.status = isChecked;

}

function isAppointmentActive(appointment) {
    const today = new Date();

    const [year, month, day] = appointment.date.split("-").map(Number);
    const apptDate = new Date(year, month-1, day);
    const [hours, minutes] = appointment.hour.split(":").map(Number);
    apptDate.setHours(hours,minutes,0,0);

    return today < apptDate;
}

function changeApptDisplayedStatus(appointment) {
    var statusCheckState,statusText, statusTextClass;
    if (appointment.status) {
        statusCheckState = true;
        statusText = "Cita Completada";
        statusTextClass = "text-success";
    } else {
        statusCheckState = false;
        if (isAppointmentActive(appointment)) {
            statusText = "Cita Pendiente";
            statusTextClass = "text-warning";
        } else {
            statusText = "Cita no Completada";
            statusTextClass = "text-danger";
        }
    }
    return [statusCheckState, statusText, statusTextClass];
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