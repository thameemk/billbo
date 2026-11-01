const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1";

// Called when a request gets a 401 (session expired or revoked).
let onUnauthorized = () => {};
export const setUnauthorizedHandler = (fn: () => void) => {
    onUnauthorized = fn;
};

// FastAPI sends `detail` as a string, or for 422 as a list of {msg}; show it as plain text.
function message(detail: unknown): string {
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail))
        return detail.map((d) => String(d?.msg ?? d).replace(/^Value error, /, "")).join("; ");
    return "Request failed";
}

// the session lives in an httpOnly cookie the browser attaches; scripts never see it
async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
    const res = await fetch(BASE + path, {
        method,
        credentials: "include",
        headers: {"Content-Type": "application/json"},
        body: body === undefined ? undefined : JSON.stringify(body),
    }).catch(() => {
        throw new Error("Can't reach the server");
    });
    if (res.status === 401) onUnauthorized();
    if (!res.ok) throw new Error(message((await res.json().catch(() => null))?.detail));
    return res.status === 204 ? (undefined as T) : res.json();
}

export const post = <T>(path: string, body: unknown) => request<T>("POST", path, body);
export const put = <T>(path: string, body: unknown) => request<T>("PUT", path, body);
export const patch = <T>(path: string, body: unknown) => request<T>("PATCH", path, body);
export const get = <T>(path: string) => request<T>("GET", path);
export const del = (path: string) => request<void>("DELETE", path);

export type Page<T> = { items: T[]; next_cursor: string | null };

// query string without the undefined values
export const qs = (params: Record<string, string | undefined>) =>
    new URLSearchParams(Object.entries(params).filter((e): e is [string, string] => e[1] !== undefined)).toString();
