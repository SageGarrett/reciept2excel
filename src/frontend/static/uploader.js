const { createClient } = window.supabase;

const client = createClient(
    SUPABASE_URL,
    SUPABASE_PUBLISHABLE_KEY
);

const bucket_name = BUCKET_NAME

let excelDragCounter = 0;
let receiptDragCounter = 0;
let uploadedFiles = [];

function init() {
    initExcelUploader();
    initReceiptUploader();
}

document.addEventListener("DOMContentLoaded", init);

function initExcelUploader() {
    const excelDropZone = document.getElementById("excelDropZone");
    const excelInput = document.getElementById("excelInput");

    if (!excelDropZone || !excelInput) return;

    excelDropZone.addEventListener("click", () => {
        excelInput.click();
    });

    excelInput.addEventListener("change", async () => {
        const file = excelInput.files[0];
        if (!file) return;

        await uploadExcel(file);
    });

    excelDropZone.addEventListener("dragenter", onExcelDragEnter);
    excelDropZone.addEventListener("dragover", onExcelDragOver);
    excelDropZone.addEventListener("dragleave", onExcelDragLeave);
    excelDropZone.addEventListener("drop", onExcelDrop);

}

function onExcelDragEnter(e) {
    e.preventDefault();
    excelDragCounter++;

    document
        .getElementById("excelDropZone")
        .classList.add("dragging");
}

function onExcelDragOver(e) {
    e.preventDefault();
}

function onExcelDragLeave(e) {
    e.preventDefault();
    excelDragCounter--;

    if (excelDragCounter <= 0) {
        excelDragCounter = 0;

        document
            .getElementById("excelDropZone")
            .classList.remove("dragging");
    }
}

async function onExcelDrop(e) {
    e.preventDefault();

    excelDragCounter = 0;

    document
        .getElementById("excelDropZone")
        .classList.remove("dragging");

    const file = e.dataTransfer.files[0];
    if (!file) return;

    await uploadExcel(file);
}

async function uploadExcel(file) {
    const path = `${sessionId}/excel/existing.xlsx`;

    const result = await client.storage
        .from(bucket_name)
        .upload(path, file, {
            upsert: true
        });

    if (result.error) {
        console.error(result.error);
        return;
    }

    renderExcelFile(file);
}

function renderExcelFile(file) {
    const list = document.getElementById("excelFileList");
    const placeholder = document.getElementById("excelPlaceholder");

    placeholder.style.display = "none";

    list.innerHTML = `
        <div class="excel-file-item">
            <span>${file.name}</span>
            <button class="remove-btn">×</button>
        </div>
    `;

    const button = list.querySelector(".remove-btn");
    button.addEventListener("click", async (e) => {
        e.stopPropagation();
        await removeExcel();
    });
}

async function removeExcel() {
    await client.storage
        .from(bucket_name)
        .remove([`${sessionId}/excel/existing.xlsx`]);


    document.getElementById("excelFileList").innerHTML = "";
    document.getElementById("excelPlaceholder").style.display = "flex";

    // clear the file input so re-selecting the same file will fire change
    const excelInput = document.getElementById("excelInput");
    if (excelInput) excelInput.value = "";
}

function initReceiptUploader() {
    const dropZone = document.getElementById("dropZone");
    const fileInput = document.getElementById("fileInput");


    if (!dropZone || !fileInput) return;

    // クリックでファイル選択
    dropZone.addEventListener("click", () => {
        fileInput.click();
    });

    // ファイル選択後アップロード
    fileInput.addEventListener("change", async () => {
        await uploadFiles(fileInput.files);
    });

    // ドラッグ開始
    dropZone.addEventListener("dragenter", onReceiptDragEnter);;
    // ドラッグ中
    dropZone.addEventListener("dragover", onReceiptDragOver);
    // ドラッグ離脱
    dropZone.addEventListener("dragleave", onReceiptDragLeave);
    // ドロップ
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

    try {
        for (const file of files) {
            const ext = file.name.split(".").pop();
            const storageName = `${crypto.randomUUID()}.${ext}`;
            const path = `${sessionId}/receipts/${storageName}`;
            uploadedFiles.push({
                originalName: file.name,
                storagePath: path,
                file: file
            });

            const result = await client.storage
                .from(bucket_name)
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
        .from(bucket_name)
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

    const fileInput = document.getElementById("fileInput");
    if (fileInput) fileInput.value = "";
}