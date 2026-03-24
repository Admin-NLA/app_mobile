import isEqual from 'https://cdn.jsdelivr.net/npm/lodash-es@4.17.21/isEqual.js';

const generalTable = document.getElementById("generalTable");
const generalTable1 = document.getElementById("generalTable1");
const attendeesTable = document.getElementById("attendeesTable");
const dailyTable = document.getElementById("dailyTable");

const searchInput = document.getElementById("searchInput");
const statsSelector = document.getElementById("statsSelector");

const tableMap = {
    generalStats: [generalTable, generalTable1],
    attendeeStats: [attendeesTable],
    dailyStats: [dailyTable]
};

var lastStats = {};

statsSelector.addEventListener('change', updateData);

document.getElementById("selector").addEventListener('change', function () {
    Object.values(tableMap).forEach(li => li.forEach(tbl => tbl.style.display = 'none'));

    if (this.value && tableMap[this.value]) {
        for (let i = 0; i < tableMap[this.value].length; i++) {
            tableMap[this.value][i].style.display = 'table';
        }

        if (this.value === "attendeeStats") {
            searchInput.disabled = false;
        } else {
            searchInput.disabled = true;
        }
    }
});

searchInput.addEventListener('keyup', function () {
    const filter = this.value.toLowerCase();
    const rows = document.querySelectorAll('#attendeesTable tbody tr');

    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        row.classList.toggle('hide', !text.includes(filter));
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

                var stats = data.stats;

                if (!isEqual(data.stats, lastStats)) {
                    var attendees = stats.attendees_scan_stats;

                    attendeesTable.querySelector("tbody").innerHTML = "";

                    //stats_p.innerHTML = JSON.stringify(data)
                    for (let nAttendee = 0; nAttendee < attendees.length; nAttendee++) {
                        const newRow = attendeesTable.tBodies[0].insertRow();
                        const idCell = newRow.insertCell(0);
                        const agentCell = newRow.insertCell(1);
                        const lastnameCell = newRow.insertCell(2);
                        const nameCell = newRow.insertCell(3);
                        const companyCell = newRow.insertCell(4);
                        const typeCell = newRow.insertCell(5);
                        const scholarshipCell = newRow.insertCell(6);
                        const day1Cell = newRow.insertCell(7);
                        const day2Cell = newRow.insertCell(8);
                        const day3Cell = newRow.insertCell(9);
                        const day4Cell = newRow.insertCell(10);

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
                        const dayCell = newRow.insertCell(0);
                        const generalCell = newRow.insertCell(1);
                        const coursesCell = newRow.insertCell(2);
                        const sessionsCell = newRow.insertCell(3);
                        const eTotalCell = newRow.insertCell(4);
                        const totalCell = newRow.insertCell(5);
                        const scholarshipsCell = newRow.insertCell(6);

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
            }

        });
}
setInterval(updateData, 60000 * 15);