// Mirrored from FASTAPI/configfile.json "Allowed_Extensions".
// Duplicated explicitly on the frontend (no backend config endpoint exists yet —
// chosen over exposing one to keep this a frontend-only step). Keep in sync
// with configfile.json if the backend list changes.
export const ALLOWED_EXTENSIONS = ['.docx', '.txt', '.pdf', '.png', '.jpeg', '.jpg']
