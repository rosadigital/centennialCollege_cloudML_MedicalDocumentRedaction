const API_BASE = "http://127.0.0.1:8000";

const form = document.getElementById("redactionForm");
const fileInput = document.getElementById("fileInput");
const documentType = document.getElementById("documentType");
const submitterId = document.getElementById("submitterId");

const originalPreview = document.getElementById("originalPreview");
const redactedPreview = document.getElementById("redactedPreview");
const resultJson = document.getElementById("resultJson");
const messageBox = document.getElementById("messageBox");
const apiStatus = document.getElementById("apiStatus");
const downloadBtn = document.getElementById("downloadBtn");
const clearBtn = document.getElementById("clearBtn");
const checkHealthBtn = document.getElementById("checkHealthBtn");

let currentDownloadUrl = null;
let currentDownloadName = "redacted_output";

function setMessage(message, type = "") {
  messageBox.textContent = message;
  messageBox.className = "message-box";
  if (type) {
    messageBox.classList.add(type);
  }
}

function formatBytes(bytes) {
  if (!bytes && bytes !== 0) return "Unknown";
  if (bytes === 0) return "0 Bytes";
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(2)} ${sizes[i]}`;
}

function clearElementContent(el) {
  while (el.firstChild) {
    el.removeChild(el.firstChild);
  }
}

function resetDownload() {
  if (currentDownloadUrl) {
    URL.revokeObjectURL(currentDownloadUrl);
    currentDownloadUrl = null;
  }
  downloadBtn.disabled = true;
}

function getFileExtension(fileName) {
  const parts = fileName.split(".");
  return parts.length > 1 ? parts.pop().toLowerCase() : "";
}

function showOriginalPreview(file) {
  clearElementContent(originalPreview);

  if (!file) {
    originalPreview.innerHTML = '<p class="muted">No file selected yet.</p>';
    return;
  }

  const ext = getFileExtension(file.name);
  const meta = document.createElement("div");
  meta.className = "file-meta";
  meta.innerHTML = `
    <p><strong>Name:</strong> ${file.name}</p>
    <p><strong>Type:</strong> ${file.type || ext || "Unknown"}</p>
    <p><strong>Size:</strong> ${formatBytes(file.size)}</p>
  `;

  if (file.type.startsWith("image/")) {
    const img = document.createElement("img");
    img.src = URL.createObjectURL(file);
    img.alt = "Original uploaded document";
    originalPreview.appendChild(img);
    originalPreview.appendChild(meta);
  } else if (ext === "pdf") {
    const iframe = document.createElement("iframe");
    iframe.src = URL.createObjectURL(file);
    originalPreview.appendChild(iframe);
    originalPreview.appendChild(meta);
  } else if (ext === "txt") {
    const reader = new FileReader();
    reader.onload = function (e) {
      const pre = document.createElement("pre");
      pre.className = "json-box";
      pre.textContent = e.target.result;
      clearElementContent(originalPreview);
      originalPreview.appendChild(pre);
      originalPreview.appendChild(meta);
    };
    reader.readAsText(file);
  } else {
    originalPreview.appendChild(meta);
  }
}

function base64ToBlob(base64String, mimeType = "application/octet-stream") {
  const byteCharacters = atob(base64String);
  const byteNumbers = new Array(byteCharacters.length);

  for (let i = 0; i < byteCharacters.length; i++) {
    byteNumbers[i] = byteCharacters.charCodeAt(i);
  }

  const byteArray = new Uint8Array(byteNumbers);
  return new Blob([byteArray], { type: mimeType });
}

function inferOutputMimeType(originalFileName, selectedDocumentType) {
  if (selectedDocumentType === "pdf") {
    return "application/pdf";
  }

  if (selectedDocumentType === "image") {
    const ext = getFileExtension(originalFileName);
    if (ext === "png") return "image/png";
    return "image/jpeg";
  }

  if (selectedDocumentType === "text") {
    return "text/plain";
  }

  const ext = getFileExtension(originalFileName);

  if (["png", "jpg", "jpeg"].includes(ext)) {
    return ext === "png" ? "image/png" : "image/jpeg";
  }

  if (ext === "pdf") {
    return "application/pdf";
  }

  if (ext === "txt") {
    return "text/plain";
  }

  return "application/octet-stream";
}

function showRedactedPreview(blob, originalFileName, selectedDocumentType) {
  clearElementContent(redactedPreview);

  const mimeType = blob.type;
  const ext = getFileExtension(originalFileName);

  if (mimeType.startsWith("image/") || selectedDocumentType === "image") {
    const img = document.createElement("img");
    img.src = currentDownloadUrl;
    img.alt = "Redacted output preview";
    redactedPreview.appendChild(img);
    return;
  }

  if (mimeType === "application/pdf" || selectedDocumentType === "pdf") {
    const iframe = document.createElement("iframe");
    iframe.src = currentDownloadUrl;
    redactedPreview.appendChild(iframe);
    return;
  }

  if (mimeType === "text/plain" || selectedDocumentType === "text" || ext === "txt") {
    blob.text().then((text) => {
      const pre = document.createElement("pre");
      pre.className = "json-box";
      pre.textContent = text;
      redactedPreview.appendChild(pre);
    });
    return;
  }

  redactedPreview.innerHTML =
    '<p class="muted">Preview not available for this file type. Use the download button.</p>';
}

async function checkHealth() {
  try {
    apiStatus.textContent = "API: Checking...";
    const response = await fetch(`${API_BASE}/health`);

    if (!response.ok) {
      throw new Error(`Health check failed with status ${response.status}`);
    }

    apiStatus.textContent = "API: Connected";
    setMessage("API health check successful.", "success");
  } catch (error) {
    apiStatus.textContent = "API: Unavailable";
    setMessage(`Cannot connect to backend: ${error.message}`, "error");
  }
}

fileInput.addEventListener("change", () => {
  const file = fileInput.files[0];
  showOriginalPreview(file);
});

checkHealthBtn.addEventListener("click", checkHealth);

clearBtn.addEventListener("click", () => {
  form.reset();
  showOriginalPreview(null);
  redactedPreview.innerHTML = '<p class="muted">Processed result will appear here.</p>';
  resultJson.textContent = "No result yet.";
  setMessage("Ready.");
  resetDownload();
});

downloadBtn.addEventListener("click", () => {
  if (!currentDownloadUrl) return;

  const link = document.createElement("a");
  link.href = currentDownloadUrl;
  link.download = currentDownloadName;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const file = fileInput.files[0];
  const selectedDocumentType = documentType.value;

  if (!file) {
    setMessage("Please select a file first.", "error");
    return;
  }

  if (!selectedDocumentType) {
    setMessage("Please select a document type.", "error");
    return;
  }

  resetDownload();
  resultJson.textContent = "Processing...";
  redactedPreview.innerHTML = '<p class="muted">Processing document...</p>';
  setMessage("Uploading and processing document...", "loading");

  const formData = new FormData();
  formData.append("file", file);
  formData.append("document_type", selectedDocumentType);

  if (submitterId.value.trim()) {
    formData.append("submitter_id", submitterId.value.trim());
  }

  try {
    const response = await fetch(`${API_BASE}/api/v1/process/sync`, {
      method: "POST",
      body: formData
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail ? JSON.stringify(data.detail) : "Processing failed.");
    }

    resultJson.textContent = JSON.stringify(data.result, null, 2);
    
    const entities = data.result.entities || [];
    const piiList = document.getElementById("piiList");

    if (entities.length === 0) {
      piiList.innerHTML = "<p>No sensitive information detected.</p>";
    } else {
      let html = "<ul>";
      entities.forEach(e => {
        html += `
          <li>
            <strong>${e.type}</strong> 
            (confidence: ${Math.round(e.confidence * 100)}%)
          </li>
    `   ;
    });
    html += "</ul>";
    piiList.innerHTML = html;
  }
    
    

    if (!data.redacted_base64) {
      setMessage("Processing finished, but no redacted file was returned.", "error");
      redactedPreview.innerHTML = '<p class="muted">No preview available.</p>';
      return;
    }

    const mimeType = inferOutputMimeType(file.name, selectedDocumentType);
    const outputBlob = base64ToBlob(data.redacted_base64, mimeType);

    currentDownloadUrl = URL.createObjectURL(outputBlob);

    const ext = getFileExtension(file.name) || "bin";
    currentDownloadName = `redacted_output.${ext}`;

    downloadBtn.disabled = false;
    showRedactedPreview(outputBlob, file.name, selectedDocumentType);
    setMessage("Document processed successfully.", "success");
  } catch (error) {
    resultJson.textContent = "No result yet.";
    redactedPreview.innerHTML = '<p class="muted">Processing failed.</p>';
    setMessage(`Error: ${error.message}`, "error");
  }
});

checkHealth();
