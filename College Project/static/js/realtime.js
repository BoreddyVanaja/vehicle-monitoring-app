const apiUrl = "http://127.0.0.1:5000/get-vehicles"
const socket = io();

const tableElement = document.getElementById("vehicleTable");
tableElement.innerHTML = "";

async function populateTable() {
    try {
        response = await fetch(apiUrl)
        data = await response.json()
        data.forEach(row => {
            const vehicle_number = row["vehicle_number"]
            tableElement.innerHTML += `
            <tr>
                <td>${row["vehicle_number"]}</td>
                <td id=${vehicle_number}_weight>${row["weight"]}</td>
                <td id=${vehicle_number}_status>${row["status"]}</td>
                <td id=${vehicle_number}_timestamp>${row["timestamp"]}</td>
            </tr>
            `;
        })
    } catch (error) {
        console.log("Error fetching data:", error);
    }
}

populateTable();

socket.on('update', (data) => {
    const vehicle_number = data["vehicle_number"]
    console.log("Received:", data);
    document.getElementById(`${vehicle_number}_weight`).innerText = data.weight;
    document.getElementById(`${vehicle_number}_status`).innerText = data.status;
    document.getElementById(`${vehicle_number}_timestamp`).innerText = data.timestamp;
});