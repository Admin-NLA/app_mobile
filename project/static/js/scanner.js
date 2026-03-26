const scanner = new Html5Qrcode("camera-container");
const message = document.getElementById("msg");
const zoomSlider = document.getElementById("zoomControl");
let track;
let c_user;

const config = {fps: 30,qrbox: document.getElementById("camera-container").offsetWidth};
let isScanning = false;
let pollingInterval = null;

function extractLastNameAndName(text) {
    const parts = text.slice(2).split(";");
    return [
      parts[0]?.trim() || "",
      parts[1]?.trim() || ""
    ];
}

function processExhibitorScanInfo(data) {
    const attendee = {
      scanned_a_last_name: "",
      scanned_a_name: "",
      scanned_a_phone: "",
      scanned_a_email: "",
      scanned_a_company: "",
      notes: ""
    };
    
    const lines = data.split("\r\n");

    if(lines[0] != "BEGIN:VCARD") return null;
  
    for (let line of lines) {
      line = line.trim();
  
      if (line.startsWith("N:")) {
        const [lastName, name] = extractLastNameAndName(line);
        attendee.scanned_a_last_name = lastName;
        attendee.scanned_a_name = name;
  
      } else if (line.startsWith("TEL;TYPE=CELL:")) {
        attendee.scanned_a_phone = line.replace("TEL;TYPE=CELL:", "").trim();
  
      } else if (line.startsWith("EMAIL;TYPE=INTERNET:")) {
        attendee.scanned_a_email = line.replace("EMAIL;TYPE=INTERNET:", "").trim();
  
      } else if (line.startsWith("ORG:")) {
        attendee.scanned_a_company = line.replace("ORG:", "").trim();
      }
    }
  
    return attendee;
}

function escapeHtml(str = '') {
  const map = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  };

  return String(str).replace(/[&<>"']/g, match => map[match]);
}

async function onQrScanned(decodedText, decodedResult) {
    await track.stop();
    await scanner.stop();

    if(pollingInterval) {
        clearInterval(pollingInterval);
    }
    let response;
    const endpoint = window.location.pathname;
    
    if (endpoint === "/scanner") {
        response = await fetch("/scan", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({qr_data: decodedText})
        }); 
        if (!response.ok) {
            await Swal.fire({
                    theme: "dark",
                    title: "<strong>ERROR</strong>",
                    text: "Error al enviar escaneo",
                    icon: "error",
                });
                return;
        }

        const { scan_id } = await response.json();

        pollingInterval = setInterval(() => {
            checkScanStatus(scan_id);
        }, 1000);

    } else if (endpoint === "/exhibitor-scanner") {
        let attendee;
        try {

            attendee = processExhibitorScanInfo(decodedText);

            if (!attendee) {
                await Swal.fire({
                    theme: "dark",
                    title: "<strong>ERROR</strong>",
                    text: "No se pudo procesar el escaneo",
                    icon: "error",
                });
                return;
            }

            const firstResult = await Swal.fire({
                theme: "dark",
                title: "Contacto Escaneado",
                html: `
                        <div>
                            <p><strong>Nombre:</strong> ${escapeHtml(attendee.scanned_a_name)} ${escapeHtml(attendee.scanned_a_last_name)}</p>
                            <p><strong>Empresa:</strong> ${escapeHtml(attendee.scanned_a_company)}</p>
                            <p><strong>Teléfono:</strong> ${escapeHtml(attendee.scanned_a_phone)}</p>
                            <p><strong>Email:</strong> ${escapeHtml(attendee.scanned_a_email)}</p>
                        </div>
                    `,
                showCancelButton: true,
                confirmButtonColor: "#4caf50",
                confirmButtonText: "Guardar Contacto",
                cancelButtonText: "Cancelar",
            });

            if (firstResult.isConfirmed) {

                const response = await fetch("/exhibitor-scan", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(attendee)
                });

                const data = await response.json().catch(() => ({}));

                if (!response.ok || !data.result) {
                    await Swal.fire({
                        theme: "dark",
                        title: "<strong>ERROR</strong>",
                        text: data.message || "No se pudo Guardar el Contacto",
                        icon: "error"
                    });
                    return;
                }

                c_user = data.current_user;

                if (data.status === "repeated") {
                    showContactAlert(false, data.record);
                } else {
                    showContactAlert(true, data.record);
                }
            }
        } catch (err) {
            await Swal.fire({
                theme: "dark",
                title: "<strong>ERROR</strong>",
                text: "Ocurrió un error",
                icon: "error",
            });
            scanner.start({ facingMode: { exact: "environment" } }, config, onQrScanned);
        }
    }
}

async function checkScanStatus(scanId) {
    const response = await fetch(`/scan-status/${scanId}`);
    const data = await response.json();

    if (data.status === "pending") {
        return;
    }

    clearInterval(pollingInterval);

    if(!data.result){
        Swal.fire({
            theme: "dark",
            title: "<strong>ERROR</strong>",
            text: data.message,
            icon: "error",
        });
    } else {
        if(data.status === "repeated"){
            Swal.fire({
                theme: "dark",
                title: "<strong>REPETIDO</strong>",
                text: data.message,
                icon: "warning",
            });
        } else {
            Swal.fire({
                theme: "dark",
                title: "<strong>ÉXITO</strong>",
                text: data.message,
                icon: "success",
            });
        }
    }
    
    scanner.start({facingMode: {exact: "environment"}}, config, onQrScanned);
}

document.getElementById("start-scan").onclick = async () => {
    if (isScanning) return;

    isScanning = true;

    message.style.color = "#000";
    message.textContent = "Escaneando...";

    try {

        const devices = await Html5Qrcode.getCameras();
        if (devices && devices.length) {

            await scanner.start({facingMode: {exact: "environment"}}, config, onQrScanned);

            const stream = await navigator.mediaDevices.getUserMedia({video: {facingMode: "environment"}});
            track = stream.getVideoTracks()[0];

            const capabilities = track.getCapabilities();
            if (capabilities.zoom) {
                zoomSlider.disabled = false;
                zoomSlider.min = capabilities.zoom.min;
                zoomSlider.max = capabilities.zoom.max;
                zoomSlider.step = capabilities.zoom.step || 0.2;
                
                track.applyConstraints({advanced: [{zoom: parseFloat(zoomSlider.value)}]})
                    .catch(err => Swal.fire({
                        theme: "dark",
                        title: "<strong>ERROR</strong>",
                        text: "Error de zoom: " + err,
                        icon: "error",
                    }));

                zoomSlider.addEventListener("input", () => {
                    track.applyConstraints({advanced: [{zoom: parseFloat(zoomSlider.value)}]})
                        .catch(err => Swal.fire({
                            theme: "dark",
                            title: "<strong>ERROR</strong>",
                            text: "Error de zoom: " + err,
                            icon: "error",
                        }));
                });
            } else {
                document.getElementById("zoomControl").style.display = "none";
            }
        }

    } catch (error) {
        Swal.fire({
            theme: "dark",
            title: "<strong>ERROR</strong>",
            text: "Ocurrió un error al escanear",
            icon: "error",
        });
        message.style.color = "#cc0000";
        message.textContent = "Ocurrió un error";
        isScanning = false; 
        if(track) {
            await track.stop();
        }
        if(scanner) {
            await scanner.stop();
        }
    }
};

document.getElementById("stop-scan").onclick = async () => {
    if (!isScanning) return;
    await track.stop();
    await scanner.stop();
    isScanning = false;
    zoomSlider.disabled = true;
    message.style.color = "#000";
    message.textContent = "Escáner detenido";
};

document.addEventListener('visibilitychange', async () => {
    if(document.visibilityState !== 'visible') {
        if(isScanning) {
            await track.stop();
            await scanner.stop();
            zoomSlider.disabled = true;
            message.style.color = "#000";
            message.textContent = "Escáner detenido";
        }
    } else {
        if(isScanning) {
            await scanner.start({facingMode: {exact: "environment"}}, config, onQrScanned);
            if(track) {
                await track.start();
            }
        }
        
    }
});

async function showContactAlert(isNewContact, record) {
    await Swal.fire({
        theme: "dark",
        title: `<strong>${isNewContact ? "Contacto Nuevo" : "Contacto ya Registrado"}</strong>`,
        html: `
            <div>
                <p><strong>Nombre:</strong> ${escapeHtml(record.scanned_a_name)} ${escapeHtml(record.scanned_a_last_name)}</p>
                <p><strong>Empresa:</strong> ${escapeHtml(record.scanned_a_company)}</p>
                <p><strong>Teléfono:</strong> ${escapeHtml(record.scanned_a_phone)}</p>
                <p><strong>Email:</strong> ${escapeHtml(record.scanned_a_email)}</p>
            </div>
        `,
        icon: isNewContact ? "success" : "info",
        showCancelButton: true,
        showDenyButton: true,
        confirmButtonText: isNewContact ? "Añadir Notas" : "Actualizar Notas",
        denyButtonText: record.appointment ? "Ver Cita" : "Agendar Cita",
        cancelButtonText: "Cancelar",
        confirmButtonColor:"#3a3ca4"
    }).then((result) => {
        if (result.isConfirmed) {
            showNotesAlert(isNewContact, record);
        } else if (result.isDenied) {
            showScheduleAlert(isNewContact, record)
        } else if (result.isDismissed) {
            scanner.start({ facingMode: { exact: "environment" } }, config, onQrScanned);
        }
    });

}

async function showNotesAlert(isNewContact, record) {
    const notesResult = await Swal.fire({
        theme: "dark",
        title: `<strong>${isNewContact ? "Añadir Notas" : "Actualizar Notas"}</strong>`,
        input: 'textarea',
        inputValue: record.notes,
        inputPlaceholder: "Escribe tus notas...",
        showCancelButton: true,
        confirmButtonText: isNewContact ? "Guardar Notas" : "Actualizar Notas",
        cancelButtonText: "Cancelar",
        confirmButtonColor: "#4caf50",
    });
    if (notesResult.isConfirmed) {
        const notesPayload = {
            e_scan_id: record.e_scan_id,
            notes: notesResult.value || ''
        };

        const response = await fetch("/update-exhibitor-record-notes", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(notesPayload)
        });
        const responseData = await response.json().catch(() => ({}));

        record.notes = notesResult.value;

        if(!response.ok || !responseData.success) {
            await Swal.fire({
                theme: "dark",
                title: "<strong>ERROR</strong>",
                text: responseData.message || "No se pudieron guardar las notas",
                icon: "error"
            });
            showNotesAlert(isNewContact, record);
        }

        await Swal.fire({
            theme: "dark",
            title: "<strong>ÉXITO</strong>",
            text: responseData.message || "Notas guardadas",
            icon: "success"
        }).then(() => showContactAlert(isNewContact, record));

    } else {
        showContactAlert(isNewContact, record);
    }
}

async function showScheduleAlert(isNewContact, record) {
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
        denyButtonText: "Descargar y Compartir",
        confirmButtonColor: "#4caf50",
        cancelButtonText: "Cancelar",
        preDeny: () => {
            if (!record.appointment) {
                Swal.showValidationMessage("No hay cita guardada");
                return;
            }
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
            showScheduleAlert(isNewContact, record);
        }

        record.appointment = responseData.appointment;

        await Swal.fire({
            theme: "dark",
            title: "<strong>ÉXITO</strong>",
            text: responseData.message || "Cita guardada",
            icon: "success"
        }).then(() => showScheduleAlert(isNewContact, record));

    } else if(scheduleResult.isDismissed) {
        showContactAlert(isNewContact, record);
    } else if (scheduleResult.isDenied) {
        const btn = document.createElement("button");
        btn.style.display = "none";
        document.body.appendChild(btn);
        btn.addEventListener("click", () => {
            downloadAndShareAppt(isNewContact,record);
            btn.remove();
        });
        btn.click();
    }
    
}

function escapeICSText(text) {
  return (text || "")
    .replace(/\\/g, "\\\\")
    .replace(/;/g, "\\;")
    .replace(/,/g, "\\,")
    .replace(/\n/g, "\\n");
}


async function downloadAndShareAppt(isNewContact, record) {
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
SUMMARY:Cita con ${record.name}
DESCRIPTION:${escapeICSText(record.appointment.description)}
LOCATION:${escapeICSText(record.appointment.location)}
END:VEVENT
END:VCALENDAR`;

    const blob = new Blob([icsContent], { type: "text/calendar" });
    const file = new File([blob], `cita_${record.name}_con_${c_user}.ics`, { type: "application/octet-stream" });

    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `cita_${record.name}_con_${c_user}.ics`;
    link.click();
    link.remove();

    URL.revokeObjectURL(link.href);

    alert(JSON.stringify({
        canShare: navigator.canShare ? navigator.canShare({ files: [file] }) : null,
        secure: window.isSecureContext
    }));

    if (navigator.share && navigator.canShare && navigator.canShare({ files: [file] })) {
        await navigator.share({
            title: "Cita",
            text: `Cita ${c_user} con ${record.name}\nFecha: ${record.appointment.date}\nHora: ${record.appointment.hour}\nLugar:${record.appointment.location}`,
            files: [file]
        }).catch(async err => {
            console.error("Error al compartir:", err);
            await Swal.fire({
                theme: "dark",
                title: "<strong>ERROR</strong>",
                text: `No se compartió la cita`,
                icon: "error"
            });
        });
    } else {
        await Swal.fire({
            theme: "dark",
            title: "<strong>ADVERTENCIA</strong>",
            text: "No es posible compartir la cita. Seleccione manualmente el archivo descargado para compartir en el canal de su preferencia",
            icon: "warning"
        });
    }
    showScheduleAlert(isNewContact, record);
}