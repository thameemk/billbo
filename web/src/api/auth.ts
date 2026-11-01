import {get, post} from "./client.ts";

export const register = (display_name: string, email: string, password: string) =>
    post("/users", {display_name, email, password});
// sets the session cookie
export const login = (email: string, password: string) => post<void>("/auth/login", {email, password});
export const logout = () => post("/auth/logout", {});

export type User = { id: string; display_name: string | null; email: string };
export const me = () => get<User>("/users/me");
