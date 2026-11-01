import {useEffect, useState} from "react";

// drop the bearer token older builds stored here; the session is now an httpOnly cookie
localStorage.removeItem("token");

// small UI values (e.g. whether we're signed in) kept in localStorage
export function useStored<T>(key: string, init: T) {
    const [v, set] = useState<T>(() => JSON.parse(localStorage.getItem(key) ?? "null") ?? init);
    useEffect(() => localStorage.setItem(key, JSON.stringify(v)), [key, v]);
    return [v, set] as const;
}
