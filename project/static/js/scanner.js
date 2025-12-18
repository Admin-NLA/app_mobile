const scanner = new Html5Qrcode("camera-container");
const message = document.getElementById("msg");
const zoomSlider = document.getElementById("zoomControl");
let track;

let isScanning = false;

document.getElementById("start-scan").onclick = async () => {
    if (isScanning) return;

    isScanning = true;
    const config = {fps: 30,qrbox: document.getElementById("camera-container").offsetWidth};

    const qrCodeSuccessCallback = (decodedText, decodedResult) => {
        //alert("QR: " + decodedText, decodedResult)
        scanner.stop();
        fetch("/scanner", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({qr_data: decodedText})
        })
        .then(response => response.json())
        .then(data => {
            alert(data.message);
            scanner.start({facingMode: {exact: "environment"}}, config, qrCodeSuccessCallback);
        })
        .catch(error => {
            alert("Error al enviar data" + error)
            scanner.start({facingMode: {exact: "environment"}}, config, qrCodeSuccessCallback);
        });
    };
    message.style.color = "#000";
    message.textContent = "Escaneando...";

    try {

        const devices = await Html5Qrcode.getCameras();
        if (devices && devices.length) {

            await scanner.start({facingMode: {exact: "environment"}}, config, qrCodeSuccessCallback);

            const stream = await navigator.mediaDevices.getUserMedia({video: {facingMode: "environment"}})
            track = stream.getVideoTracks()[0];

            const capabilities = track.getCapabilities();
            if (capabilities.zoom) {
                zoomSlider.disabled = false;
                zoomSlider.min = capabilities.zoom.min;
                zoomSlider.max = capabilities.zoom.max;
                zoomSlider.step = capabilities.zoom.step || 0.2;
                
                track.applyConstraints({advanced: [{zoom: parseFloat(zoomSlider.value)}]})
                        .catch(err => alert("Error de zoom: " + err));

                zoomSlider.addEventListener("input", () => {
                    track.applyConstraints({advanced: [{zoom: parseFloat(zoomSlider.value)}]})
                        .catch(err => alert("Error de zoom: " + err));
                });
            } else {
                document.getElementById("zoomControl").style.display = "none";
            }
        }

    } catch (error) {
        alert(error);
        message.style.color = "#cc0000";
        message.textContent = "Ocurrió un error"
        isScanning = false;
        await track.stop();
        await scanner.stop();
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
        await track.stop();
        await scanner.stop();
    }
});