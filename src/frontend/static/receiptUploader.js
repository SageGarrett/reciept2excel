let receiptDragCounter = 0;
window.uploadedFiles = [];

function initReceiptUploader() {
    const dropZone = document.getElementById("dropZone");
    const fileInput = document.getElementById("fileInput");

    if (!dropZone || !fileInput) return;

    dropZone.addEventListener("click", () => {
        fileInput.click();
    });

    fileInput.addEventListener("change", async () => {
        await uploadFiles(fileInput.files);
    });

    dropZone.addEventListener("dragenter", onReceiptDragEnter);
    dropZone.addEventListener("dragover", onReceiptDragOver);
    dropZone.addEventListener("dragleave", onReceiptDragLeave);
    dropZone.addEventListener("drop", onReceiptDrop);
}

function onReceiptDragEnter(e) {
    e.preventDefault();
    receiptDragCounter++;

    document
        .getElementById("dropZone")
        .classList.add("dragging");
}

function onReceiptDragOver(e) {
    e.preventDefault();
}

function onReceiptDragLeave(e) {
    e.preventDefault();
    receiptDragCounter--;

    if (receiptDragCounter <= 0) {
        receiptDragCounter = 0;

        document
            .getElementById("dropZone")
            .classList.remove("dragging");
    }
}

async function onReceiptDrop(e) {
    e.preventDefault();

    receiptDragCounter = 0;

    document
        .getElementById("dropZone")
        .classList.remove("dragging");

    await uploadFiles(e.dataTransfer.files);
}

async function uploadFiles(files) {
    const status = document.getElementById("status");
    const placeholder = document.getElementById("placeholder");

    if (files.length > 0) {
        placeholder.style.display = "none";
    }
    if (!files || files.length === 0) {
        console.log("no files");
        placeholder.style.display = "flex";
        return;
    }

    const overlay = document.getElementById("loadingOverlay");
    overlay.classList.remove("hidden");
    status.textContent = "";

    try {
        for (const file of files) {
            console.log(`Uploading receipt: ${file.name}, size: ${file.size}, type: ${file.type}`);
            const ext = file.name.split(".").pop();
            const storageName = `${crypto.randomUUID()}.${ext}`;
            const path = `${sessionId}/receipts/${storageName}`;

            const result = await client.storage
                .from(bucket_name)
                .upload(path, file);

            if (result.error) {
                throw result.error;
            }

            // Only add to array after successful upload
            window.uploadedFiles.push({
                originalName: file.name,
                storagePath: path,
                file: file
            });
        }
        await syncMetadata();

        renderFileList(window.uploadedFiles);
        overlay.classList.add("hidden");
    } catch (err) {
        console.error("upload error:", err);
        status.textContent = `アップロード失敗: ${err.message || JSON.stringify(err)}`;
        overlay.classList.add("hidden");
    }
}

async function syncMetadata() {
    const metadata = {};
    for (const file of window.uploadedFiles) {
        metadata[file.storagePath] = file.originalName;
    }

    const blob = new Blob(
        [JSON.stringify(metadata)],
        { type: "application/json" }
    );

    const result = await client.storage
        .from(bucket_name)
        .upload(
            `${sessionId}/metadata.json`,
            blob,
            { upsert: true }
        );

    if (result.error) {
        console.error("metadata sync error:", result.error);
        throw result.error;
    }
}

function renderFileList(files) {
    const fileList = document.getElementById("fileList");
    fileList.innerHTML = "";

    for (const file of files) {
        const item = document.createElement("div");
        item.className = "file-item";

        item.innerHTML = `
            <span class="file-name">${file.originalName}</span>
            <button class="remove-btn">×</button>
        `;

        const button = item.querySelector(".remove-btn");
        button.addEventListener("click", async (e) => {
            e.stopPropagation();
            await removeFile(file);
        });

        fileList.appendChild(item);
    }
}

async function removeFile(fileObj) {
    const { error } = await client.storage
        .from(bucket_name)
        .remove([fileObj.storagePath]);

    if (error) {
        console.error(error);
        return;
    }

    window.uploadedFiles = window.uploadedFiles.filter(
        f => f.storagePath !== fileObj.storagePath
    );

    try {
        await syncMetadata();
    } catch (err) {
        console.error("failed to sync metadata after remove:", err);
    }

    renderFileList(window.uploadedFiles);

    if (window.uploadedFiles.length === 0) {
        document.getElementById("placeholder").style.display = "flex";
    }

    const fileInput = document.getElementById("fileInput");
    if (fileInput) fileInput.value = "";
}
