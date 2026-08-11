const eventSelector = document.getElementById("eventSelector");
const activeEventLabel = document.getElementById("activeEventLabel");
const companyFilter = document.getElementById("companyFilter");
const searchInput = document.getElementById("searchInput");
const allContactsBody = document.getElementById("allContactsBody");
const exportAllBtn = document.getElementById("exportAllBtn");

let allRecords = [];
let selectedEventId = "";

function renderRows() {
    const selectedCompany = companyFilter.value;
    const searchTerm = searchInput.value.trim().toLowerCase();

    const filtered = allRecords.filter((record) => {
        const matchesCompany = !selectedCompany || record.empresa_expositora === selectedCompany;

        const haystack = [
            record.scanned_a_name,
            record.scanned_a_last_name,
            record.scanned_a_email,
            record.scanned_a_company,
            record.empresa_expositora,
        ].join(" ").toLowerCase();

        const matchesSearch = !searchTerm || haystack.includes(searchTerm);

        return matchesCompany && matchesSearch;
    });

    allContactsBody.innerHTML = "";

    filtered.forEach((record) => {
        const row = allContactsBody.insertRow();
        row.insertCell().textContent = record.empresa_expositora || "N/A";
        row.insertCell().textContent = `${record.scanned_a_last_name || ""} ${record.scanned_a_name || ""}`.trim();
        row.insertCell().textContent = record.scanned_a_email || "N/A";
        row.insertCell().textContent = record.scanned_a_phone || "N/A";
        row.insertCell().textContent = record.scanned_a_company || "N/A";
        row.insertCell().textContent = record.scanned_by_rep_name || record.scanned_by_login || "N/A";
        row.insertCell().textContent = record.day || "N/A";
        row.insertCell().textContent = record.appointment_status || "Sin Cita";
    });
}

function populateCompanyFilter() {
    const companies = [...new Set(allRecords.map((r) => r.empresa_expositora).filter(Boolean))].sort();

    companyFilter.innerHTML = '<option value="">Todas las Empresas Expositoras</option>';
    companies.forEach((company) => {
        const option = document.createElement("option");
        option.value = company;
        option.textContent = company;
        companyFilter.appendChild(option);
    });
}

function loadContactsForEvent(eventId) {
    if (!eventId) {
        allRecords = [];
        allContactsBody.innerHTML = "";
        activeEventLabel.textContent = "Selecciona una sede para ver sus contactos.";
        exportAllBtn.disabled = true;
        return;
    }

    fetch(`/admin/contacts/list?event_id=${encodeURIComponent(eventId)}`)
        .then((response) => response.json())
        .then((data) => {
            if (data.event) {
                activeEventLabel.innerHTML = `<strong>${data.event.total_records} Contactos</strong> para: <strong>${data.event.location} ${data.event.year}</strong> (todas las marcas)`;
                exportAllBtn.disabled = data.event.total_records === 0;
            } else {
                activeEventLabel.textContent = "No se encontró esa sede.";
                exportAllBtn.disabled = true;
            }
            allRecords = data.records || [];
            populateCompanyFilter();
            renderRows();
        });
}

eventSelector.addEventListener("change", () => {
    selectedEventId = eventSelector.value;
    loadContactsForEvent(selectedEventId);
});

companyFilter.addEventListener("change", renderRows);
searchInput.addEventListener("input", renderRows);

exportAllBtn.addEventListener("click", () => {
    if (!selectedEventId) return;
    window.location.href = `/admin/contacts/export?event_id=${encodeURIComponent(selectedEventId)}`;
});