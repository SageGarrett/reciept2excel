async function uploadFiles() {
    const fileInput = document.getElementById("fileInput");
    const status = document.getElementById("status");

    const files = fileInput.files;

    if (!files.length) {
        status.innerText = "ファイルを選択してください";
        return;
    }

    status.innerText = "アップロード中...";

    for (const file of files) {
        const safeName = file.name.replace(/[^\w.-]/g, "_");
        const filePath = `uploads/${sessionId}/${Date.now()}_${safeName}`;

        try {
            console.log("upload start");
            console.log(SUPABASE_URL);
            console.log(filePath);
            const response = await fetch(
                `${SUPABASE_URL}/storage/v1/object/receipt_files/${filePath}`,
                {
                    method: "POST",
                    headers: {
                        apikey: SUPABASE_PUBLISHABLE_KEY,
                        Authorization: `Bearer ${SUPABASE_PUBLISHABLE_KEY}`,
                        "Content-Type": file.type,
                        "x-upsert": "false",
                    },
                    body: file,
                }
            );

            if (!response.ok) {
                const errorText = await response.text();
                status.innerText = `失敗: ${errorText}`;
                return;
            }
        } catch (error) {
            console.error("UPLOAD ERROR:", error);
            status.innerText = String(error);
            console.log("apikey=", SUPABASE_PUBLISHABLE_KEY);
            return
        }
    }

    status.innerText = `${files.length}件アップロード完了`;
}