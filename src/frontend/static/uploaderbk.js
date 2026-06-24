const { createClient } = window.supabase;

const client = createClient(
    SUPABASE_URL,
    SUPABASE_PUBLISHABLE_KEY
);

let dragCounter = 0;
let uploadedFiles = [];

document.addEventListener("DOMContentLoaded", () => {
    const dropZone = document.getElementById("dropZone");
    const fileInput = document.getElementById("fileInput");


    // クリックでファイル選択
    dropZone.addEventListener("click", () => {
        console.log("dropZone clicked");
        fileInput.click();
    });

    // ファイル選択後アップロード
    fileInput.addEventListener("change", async () => {
        const files = fileInput.files;

        await uploadFiles(files);
    });

    // ドラッグ開始
    dropZone.addEventListener("dragenter", (e) => {
        e.preventDefault();
        receiptDragCounter++;
        dropZone.classList.add("dragging");
    });

    // ドラッグ中
    dropZone.addEventListener("dragover", (e) => {
        e.preventDefault();
    });

    // ドラッグ離脱
    dropZone.addEventListener("dragleave", (e) => {
        e.preventDefault();
        receiptDragCounter--;

        if (receiptDragCounter <= 0) {
            receiptDragCounter = 0;
            dropZone.classList.remove("dragging");
        }
    });

    // ドロップ
    dropZone.addEventListener("drop", async (e) => {
        e.preventDefault();

        receiptDragCounter = 0;
        dropZone.classList.remove("dragging");

        const files = e.dataTransfer.files;

        await uploadFiles(files);
    });
    // 選択ファイル削除
    button.addEventListener("click", async (e) => {
        e.stopPropagation();
        await removeFile(file);
    });
});

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

    try {
        for (const file of files) {
            const ext = file.name.split(".").pop();
            const storageName = `${crypto.randomUUID()}.${ext}`;
            const path = `uploads/${sessionId}/${storageName}`;
            uploadedFiles.push({
                originalName: file.name,
                storagePath: path,
                file: file
            });

            const result = await client.storage
                .from("receipt_files")
                .upload(path, file);

            if (result.error) {
                throw result.error;
            }
        }
        renderFileList(uploadedFiles);
        overlay.classList.add("hidden");
    } catch (err) {
        console.error("upload error:", err);
        status.textContent = "アップロード失敗";
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
        .from("receipt_files")
        .remove([fileObj.storagePath]);

    if (error) {
        console.error(error);
        return;
    }

    uploadedFiles = uploadedFiles.filter(
        f => f.storagePath !== fileObj.storagePath
    );

    renderFileList(uploadedFiles);

    if (uploadedFiles.length === 0) {
        document.getElementById("placeholder").style.display = "flex";
    }
}