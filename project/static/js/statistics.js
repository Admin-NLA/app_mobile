import isEqual from 'https://cdn.jsdelivr.net/npm/lodash-es@4.17.21/isEqual.js';

const generalTable = document.getElementById("generalTable");
const generalTable1 = document.getElementById("generalTable1");
const attendeesTable = document.getElementById("attendeesTable");
const exhibitorsTable = document.getElementById("exhibitorsTable")
const dailyTable = document.getElementById("dailyTable");
const exhibitorGeneralTable = document.getElementById("exhibitorGeneralTable")
const exhibitorScansTable = document.getElementById("exhibitorScansTable");

const searchInput = document.getElementById("searchInput");
const statsSelector = document.getElementById("statsSelector");

const tableMap = {
    generalStats: [generalTable, generalTable1],
    attendeeStats: [attendeesTable],
    dailyStats: [dailyTable],
    exhibitorStats: [exhibitorGeneralTable, exhibitorsTable],
    exhibitorScansStats: [exhibitorScansTable]
};

let lastStats = {};
let lastExhibitorScansStats = {};

statsSelector.addEventListener('change', updateData);

document.getElementById("selector").addEventListener('change', function () {
    Object.values(tableMap).forEach(li => li.forEach(tbl => tbl.style.display = 'none'));

    if (this.value && tableMap[this.value]) {
        for (let i = 0; i < tableMap[this.value].length; i++) {
            tableMap[this.value][i].style.display = 'table';
        }

        if (this.value === "attendeeStats" || this.value === "exhibitorStats") {
            searchInput.disabled = false;
        } else {
            searchInput.disabled = true;
        }
    }
});

searchInput.addEventListener('keyup', function () {
    const filter = this.value.toLowerCase();

    const searchableTables = [attendeesTable, exhibitorsTable].filter(tbl => tbl.style.display !== 'none');

    searchableTables.forEach(tbl => {
        const rows = tbl.querySelectorAll('tbody tr');
        rows.forEach(row => {
            const text = row.textContent.toLowerCase();
            row.classList.toggle('hide', !text.includes(filter));
        });
    });
});

function isEmpty(obj) {
    if (obj && typeof obj === 'object' && !Array.isArray(obj)) {

        return Object.keys(obj).length === 0;
    }
    throw new TypeError("Expected a plain object")
}

function updateData() {
    var selection = statsSelector.value;

    fetch('/statistics', {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ selected_option: selection })
    })
        .then(response => response.json())
        .then(data => {
            if (!isEmpty(data)) {

                let stats = data.stats;
                let exhibitorScansStats = data.exhibitors_scans;

                if (!isEqual(stats, lastStats)) {
                    var attendees = stats.attendees_scan_stats;
                    var exhibitors = stats.exhibitor_scan_stats;

                    attendeesTable.querySelector("tbody").innerHTML = "";
                    for (let nAttendee = 0; nAttendee < attendees.length; nAttendee++) {
                        const newRow = attendeesTable.tBodies[0].insertRow();
                        const idCell = newRow.insertCell();
                        const agentCell = newRow.insertCell();
                        const lastnameCell = newRow.insertCell();
                        const nameCell = newRow.insertCell();
                        const companyCell = newRow.insertCell();
                        const typeCell = newRow.insertCell();
                        const scholarshipCell = newRow.insertCell();
                        const day1Cell = newRow.insertCell();
                        const day2Cell = newRow.insertCell();
                        const day3Cell = newRow.insertCell();
                        const day4Cell = newRow.insertCell();

                        idCell.textContent = attendees[nAttendee].ID;
                        agentCell.textContent = attendees[nAttendee].Agente;
                        lastnameCell.textContent = attendees[nAttendee]["Apellido(s)"];
                        nameCell.textContent = attendees[nAttendee]["Nombre(s)"];
                        companyCell.textContent = attendees[nAttendee].Empresa;
                        typeCell.textContent = attendees[nAttendee]["Tipo de Asistente"];
                        scholarshipCell.textContent = attendees[nAttendee].Beca;
                        day1Cell.textContent = attendees[nAttendee]["Día 1"];
                        day2Cell.textContent = attendees[nAttendee]["Día 2"];
                        day3Cell.textContent = attendees[nAttendee]["Día 3"];
                        day4Cell.textContent = attendees[nAttendee]["Día 4"];

                    }

                    const exGeneralRow = exhibitorGeneralTable.tBodies[0].rows[0];
                    exGeneralRow.cells[0].textContent = stats.total_exhibitors;
                    exGeneralRow.cells[1].textContent = stats.daily_exhibitor_stats.day_3.actual;
                    exGeneralRow.cells[2].textContent = stats.daily_exhibitor_stats.day_4.actual;

                    exhibitorsTable.querySelector("tbody").innerHTML = "";
                    for (let nExhibitor = 0; nExhibitor < exhibitors.length; nExhibitor++) {
                        const newRow = exhibitorsTable.tBodies[0].insertRow();
                        const idCell = newRow.insertCell();
                        const lastnameCell = newRow.insertCell();
                        const nameCell = newRow.insertCell();
                        const companyCell = newRow.insertCell();
                        const typeCell = newRow.insertCell();
                        const day3Cell = newRow.insertCell();
                        const day4Cell = newRow.insertCell();

                        idCell.textContent = exhibitors[nExhibitor].ID;
                        lastnameCell.textContent = exhibitors[nExhibitor]["Apellido(s)"];
                        nameCell.textContent = exhibitors[nExhibitor]["Nombre(s)"];
                        companyCell.textContent = exhibitors[nExhibitor].Empresa;
                        typeCell.textContent = exhibitors[nExhibitor].Tipo;
                        day3Cell.textContent = exhibitors[nExhibitor]["Día 3"];
                        day4Cell.textContent = exhibitors[nExhibitor]["Día 4"];

                    }

                    const generalRow = generalTable.tBodies[0].rows[0];
                    generalRow.cells[0].textContent = stats.total_attendees;
                    generalRow.cells[1].textContent = stats.type_stats.general;
                    generalRow.cells[2].textContent = stats.type_stats.sessions;
                    generalRow.cells[3].textContent = stats.type_stats.courses;
                    generalRow.cells[4].textContent = stats.scholarship_stats.total_scholarship_holders;
                    generalRow.cells[5].textContent = stats.scholarship_stats.general_scholarship_holders;
                    generalRow.cells[6].textContent = stats.scholarship_stats.sessions_scholarship_holders;
                    generalRow.cells[7].textContent = stats.scholarship_stats.courses_scholarship_holders;

                    const generalRow1 = generalTable1.tBodies[0].rows[0];
                    generalRow1.cells[0].textContent = stats.total_scanned_attendees;
                    generalRow1.cells[1].textContent = stats.scanned_scholarship_holders.total;
                    generalRow1.cells[2].textContent = stats.scanned_attendees_by_type.general;
                    generalRow1.cells[3].textContent = stats.scanned_attendees_by_type.sessions;
                    generalRow1.cells[4].textContent = stats.scanned_attendees_by_type.courses;
                    generalRow1.cells[5].textContent = stats.scanned_scholarship_holders.general;
                    generalRow1.cells[6].textContent = stats.scanned_scholarship_holders.sessions;
                    generalRow1.cells[7].textContent = stats.scanned_scholarship_holders.courses;

                    dailyTable.querySelector("tbody").innerHTML = "";

                    for (let day = 1; day <= 4; day++) {
                        const newRow = dailyTable.tBodies[0].insertRow();
                        const dayCell = newRow.insertCell();
                        const generalCell = newRow.insertCell();
                        const coursesCell = newRow.insertCell();
                        const sessionsCell = newRow.insertCell();
                        const eTotalCell = newRow.insertCell();
                        const totalCell = newRow.insertCell();
                        const scholarshipsCell = newRow.insertCell();

                        dayCell.textContent = `Día ${day}`;
                        generalCell.textContent = stats.daily_attendee_type_scans[`day_${day}`].general;
                        coursesCell.textContent = stats.daily_attendee_type_scans[`day_${day}`].courses;
                        sessionsCell.textContent = stats.daily_attendee_type_scans[`day_${day}`].sessions;
                        eTotalCell.textContent = stats.daily_stats[`day_${day}`].expected;
                        totalCell.textContent = stats.daily_stats[`day_${day}`].actual.length;
                        scholarshipsCell.textContent = stats.daily_scanned_sh[`day_${day}`];
                    }
                    lastStats = stats;
                }

                if (!isEqual(exhibitorScansStats, lastExhibitorScansStats)) {
                    exhibitorScansTable.querySelector("tbody").innerHTML = "";
                    for (let nExhibitorCompany = 0; nExhibitorCompany < exhibitorScansStats.length; nExhibitorCompany++) {
                        const newRow = exhibitorScansTable.tBodies[0].insertRow();
                        const idCell = newRow.insertCell();
                        const companyCell = newRow.insertCell();
                        const apptCountCell = newRow.insertCell();
                        const completedApptCountCell = newRow.insertCell();

                        idCell.textContent = nExhibitorCompany + 1;
                        companyCell.textContent = exhibitorScansStats[nExhibitorCompany].company;
                        apptCountCell.textContent = exhibitorScansStats[nExhibitorCompany].appt_count;
                        completedApptCountCell.textContent = exhibitorScansStats[nExhibitorCompany].completed_appt_count;
                    }
                    lastExhibitorScansStats = exhibitorScansStats;
                }
            }
        });
}

setInterval(updateData, 60000 * 15);