import {CssBaseline, Snackbar, ThemeProvider} from "@mui/material";
import {useEffect, useState} from "react";
import * as auth from "./api/auth.ts";
import {setUnauthorizedHandler} from "./api/client.ts";
import * as tagsApi from "./api/tags.ts";
import * as expensesApi from "./api/expenses.ts";
import * as groupsApi from "./api/groups.ts";
import {adjustTotals, type Expense, type Group, type Tag} from "./lib/money.ts";
import {AppShell} from "./components/AppShell.tsx";
import {AuthPage} from "./features/auth/AuthPage.tsx";
import {GroupSidebar} from "./features/groups/GroupSidebar.tsx";
import {NameDialog} from "./features/groups/NameDialog.tsx";
import {GroupDialog} from "./features/groups/GroupDialog.tsx";
import {ProfilePage} from "./features/profile/ProfilePage.tsx";
import {GroupPage} from "./features/groups/GroupPage.tsx";
import {useStored} from "./lib/storage.ts";
import {usePaged} from "./lib/usePaged.ts";
import {theme} from "./theme.ts";

export default function App() {
    // only whether we think a session exists; the token itself is an httpOnly cookie
    const [signedIn, setSignedIn] = useStored("signedIn", false);
    useEffect(() => setUnauthorizedHandler(() => setSignedIn(false)), [setSignedIn]);
    return (
        <ThemeProvider theme={theme}>
            <CssBaseline/>
            {signedIn ? <Main onLogout={() => {
                auth.logout().catch(() => {
                });
                setSignedIn(false);
            }}/> : <AuthPage onLogin={() => setSignedIn(true)}/>}
        </ThemeProvider>
    );
}

function Main({onLogout}: { onLogout: () => void }) {
    const [open, setOpen] = useState<string | null>(null);
    const [profile, setProfile] = useState(false);
    const [creating, setCreating] = useState(false);
    const [groupDialog, setGroupDialog] = useState<Group | null>(null);
    const [tagDialog, setTagDialog] = useState<{ tag?: Tag } | null>(null);
    const [query, setQuery] = useState("");
    const [tag, setTag] = useState<string | null>(null); // tag view: expenses with this tag across groups
    const [toast, setToast] = useState("");
    const groups = usePaged((c) => groupsApi.listGroups(c), "groups");
    const expenses = usePaged((c) => expensesApi.listExpenses(open ?? undefined, query, tag ?? undefined, c), `${open ?? "all"}|${tag}|${query}`);
    const [tags, setTags] = useState<Tag[]>([]); // the user's existing tags, offered as suggestions
    useEffect(() => {
        tagsApi.listTags().then(setTags, () => {
        });
    }, []);
    const addTags = (e: Expense) => setTags((ts) => {
        const have = new Set(ts.map((t) => t.id));
        return [...ts, ...e.tags.filter((t) => !have.has(t.id))].sort((a, b) => a.name.localeCompare(b.name));
    });
    const g = groups.items.find((x) => x.id === open);
    const tagNames = tags.map((t) => t.name);
    const fail = (e: unknown) => setToast((e as Error).message);
    // keep the group totals current without refetching
    const adjustGroup = (id: string, from: number, to: number, count = 0) =>
        groups.setItems((xs) => xs.map((x) => (x.id === id ? adjustTotals(x, from, to, count) : x)));

    return (
        <>
            <AppShell
                title={profile ? "Profile" : g ? g.name : tag ? `#${tags.find((t) => t.id === tag)?.name ?? ""}` : "All expenses"}
                onBack={profile ? () => setProfile(false) : undefined}
                sidebar={<GroupSidebar groups={groups.items} selected={open} tags={tags} selectedTag={tag} paging={groups} onAdd={() => setCreating(true)}
                                       onEditGroup={setGroupDialog} onAddTag={() => setTagDialog({})} onEditTag={(t) => setTagDialog({tag: t})}
                                       onSelect={(id, t) => {
                                           setOpen(id);
                                           setTag(t ?? null);
                                           setProfile(false);
                                       }}/>}
                onProfile={profile ? undefined : () => setProfile(true)}
            >
                {profile ? (
                    <ProfilePage groups={groups.items}
                                 onLogout={() => {
                                     onLogout();
                                     setOpen(null);
                                     setProfile(false);
                                 }}/>
                ) : (
                    <GroupPage g={g} onQuery={setQuery} expenses={expenses.items} paging={expenses} tags={tagNames}
                               onAdd={(d) => expensesApi.createExpense(d).then((e) => {
                                   addTags(e);
                                   adjustGroup(e.groupId, 0, e.cents, 1);
                                   expenses.setItems((xs) => [e, ...xs]);
                                   setToast("Expense added");
                               })}
                               onEdit={(id, d) => expensesApi.updateExpense(id, d).then((e) => {
                                   addTags(e);
                                   adjustGroup(e.groupId, expenses.items.find((x) => x.id === id)?.cents ?? e.cents, e.cents);
                                   expenses.setItems((xs) => xs.map((x) => (x.id === id ? {...e, group: x.group} : x)));
                                   setToast("Expense updated");
                               })}
                               onDelete={(id) => expensesApi.deleteExpense(id).then(() => {
                                   const gone = expenses.items.find((e) => e.id === id);
                                   if (gone) adjustGroup(gone.groupId, gone.cents, 0, -1);
                                   expenses.setItems((xs) => xs.filter((e) => e.id !== id));
                                   setToast("Expense deleted");
                               }, fail)}/>
                )}
            </AppShell>
            {groupDialog && <GroupDialog group={groupDialog} onClose={() => setGroupDialog(null)}
                                          onDelete={async () => {
                                              await groupsApi.deleteGroup(groupDialog.id);
                                              groups.setItems((xs) => xs.filter((x) => x.id !== groupDialog.id));
                                              expenses.setItems((xs) => xs.filter((x) => x.groupId !== groupDialog.id));
                                              if (open === groupDialog.id) setOpen(null);
                                              setGroupDialog(null);
                                              setToast("Group deleted");
                                          }} onSave={async (d) => {
                const saved = await groupsApi.updateGroup(groupDialog.id, d);
                groups.setItems((xs) => xs.map((x) => (x.id === saved.id ? {...x, name: saved.name, currency: saved.currency} : x)));
                // rows in the all-expenses view carry their group's name and currency
                expenses.setItems((xs) => xs.map((x) => (x.groupId === saved.id && x.group ? {...x, group: {name: saved.name, currency: saved.currency}} : x)));
                setGroupDialog(null);
            }}/>}
            {tagDialog && <NameDialog title={tagDialog.tag ? "Edit tag" : "New tag"} label="Tag name" name={tagDialog.tag?.name} maxLength={30}
                                      onClose={() => setTagDialog(null)}
                                      onDelete={tagDialog.tag ? async () => {
                                          const id = tagDialog.tag!.id;
                                          await tagsApi.deleteTag(id);
                                          setTags((ts) => ts.filter((x) => x.id !== id));
                                          expenses.setItems((xs) => xs.map((x) => ({...x, tags: x.tags.filter((y) => y.id !== id)})));
                                          if (tag === id) setTag(null);
                                          setTagDialog(null);
                                          setToast("Tag deleted");
                                      } : undefined}
                                      onSave={async (name) => {
                const t = tagDialog.tag;
                const saved = t ? await tagsApi.updateTag(t.id, name) : await tagsApi.createTag(name);
                setTags((ts) => [...ts.filter((x) => x.id !== saved.id), saved].sort((a, b) => a.name.localeCompare(b.name)));
                // listed expenses still carry the old name
                expenses.setItems((xs) => xs.map((x) => ({...x, tags: x.tags.map((y) => (y.id === saved.id ? saved : y))})));
                setTagDialog(null);
            }}/>}
            {creating && <GroupDialog onClose={() => setCreating(false)} onSave={async (d) => {
                const gr = await groupsApi.createGroup(d.name, d.currency);
                groups.setItems((xs) => [gr, ...xs]);
                setOpen(gr.id);
                setTag(null);
                setProfile(false);
                setCreating(false);
            }}/>}
            <Snackbar open={!!toast} autoHideDuration={3000} onClose={() => setToast("")} message={toast}/>
        </>
    );
}
