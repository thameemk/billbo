import {del, get, patch, post} from "./client.ts";
import type {Tag} from "../lib/money.ts";

export const listTags = () => get<Tag[]>("/tags");

export const createTag = (name: string) => post<Tag>("/tags", {name});

export const updateTag = (id: string, name: string) => patch<Tag>(`/tags/${id}`, {name});

export const deleteTag = (id: string) => del(`/tags/${id}`);
