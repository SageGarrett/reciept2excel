let excelDragCounter = 0;

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
    const overlay = document.getElementById("excelLoadingOverlay");
    const placeholder = document.getElementById("excelPlaceholder");
    placeholder.style.display = "none";
    overlay.classList.remove("hidden");

    try {
        const path = `${sessionId}/excel/existing.xlsx`;

        const result = await client.storage
            .from(bucket_name)
            .upload(path, file, {
                upsert: true
            });

        if (result.error) {
            throw result.error;
        }

        renderExcelFile(file);
    } catch (error) {
        console.error("Excel upload error:", error);
        if (document.getElementById("excelFileList").innerHTML === "") {
            placeholder.style.display = "flex";
        }
    } finally {
        overlay.classList.add("hidden");
    }
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
    const overlay = document.getElementById("excelLoadingOverlay");
    overlay.classList.remove("hidden");

    try {
        const { error } = await client.storage
            .from(bucket_name)
            .remove([`${sessionId}/excel/existing.xlsx`]);

        if (error) {
            console.error(error);
            return;
        }

        document.getElementById("excelFileList").innerHTML = "";
        document.getElementById("excelPlaceholder").style.display = "flex";

        const excelInput = document.getElementById("excelInput");
        if (excelInput) excelInput.value = "";
    } catch (error) {
        console.error("Excel remove error:", error);
    } finally {
        overlay.classList.add("hidden");
    }
}
