const { createClient } = window.supabase;

const client = createClient(
    SUPABASE_URL,
    SUPABASE_PUBLISHABLE_KEY
);

const bucket_name = BUCKET_NAME;
