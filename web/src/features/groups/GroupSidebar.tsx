import AddIcon from "@mui/icons-material/Add";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";
import FolderOutlinedIcon from "@mui/icons-material/FolderOutlined";
import LabelOutlinedIcon from "@mui/icons-material/LabelOutlined";
import ReceiptLongIcon from "@mui/icons-material/ReceiptLong";
import {
    Button,
    IconButton,
    ListItem,
    List,
    ListItemButton,
    ListItemIcon,
    ListItemText,
    ListSubheader,
    Typography
} from "@mui/material";
import {InfiniteScroll} from "../../components/InfiniteScroll.tsx";
import type {Group, Tag} from "../../lib/money.ts";
import {colorOf} from "../../lib/util.ts";

const item = {mx: 1, borderRadius: 2, "&.Mui-selected": {bgcolor: "action.selected"}};

// selected = group id, or null for "All expenses"
export function GroupSidebar({groups, selected, tags, selectedTag, onSelect, onAdd, onAddTag, onEditTag, onEditGroup, paging}: {
    groups: Group[]; selected: string | null; tags: Tag[]; selectedTag: string | null;
    onSelect: (id: string | null, tag?: string) => void; onAdd: () => void;
    onAddTag: () => void; onEditTag: (t: Tag) => void; onEditGroup: (g: Group) => void;
    paging: { loadMore: () => void; retry: () => void; hasMore: boolean; loading: boolean; error: string };
}) {
    return (
        <>
            <Typography variant="h6" fontWeight={700} sx={{px: 2.5, pt: 2.5, pb: 1}}>Billbo</Typography>
            <List dense sx={{py: 1}}>
                <ListItemButton sx={item} selected={selected === null && selectedTag === null} onClick={() => onSelect(null)}>
                    <ListItemIcon sx={{minWidth: 36, color: "text.primary"}}><ReceiptLongIcon fontSize="small"/></ListItemIcon>
                    <ListItemText primary="All expenses" slotProps={{primary: {fontWeight: 500}}}/>
                </ListItemButton>
                <ListSubheader disableSticky sx={{display: "flex", alignItems: "center", justifyContent: "space-between", bgcolor: "transparent", mt: 1, lineHeight: "36px", fontSize: 12, letterSpacing: 1}}>
                    GROUPS
                    <Button size="small" startIcon={<AddIcon/>} onClick={onAdd}>add</Button>
                </ListSubheader>
                {groups.map((gr) => (
                    <ListItem key={gr.id} disablePadding sx={{"&:hover .edit, & .edit:focus-visible": {opacity: 1}}}
                              secondaryAction={<IconButton className="edit" size="small" edge="end" aria-label={`Edit ${gr.name}`}
                                                           sx={{mr: 1, "@media (hover: hover)": {opacity: 0}}}
                                                           onClick={() => onEditGroup(gr)}><EditOutlinedIcon fontSize="small"/></IconButton>}>
                        <ListItemButton sx={item} selected={selected === gr.id && selectedTag === null} onClick={() => onSelect(gr.id)}>
                            <ListItemIcon sx={{minWidth: 36, color: colorOf(gr.id)}}><FolderOutlinedIcon fontSize="small"/></ListItemIcon>
                            <ListItemText primary={gr.name} slotProps={{primary: {noWrap: true}}}/>
                        </ListItemButton>
                    </ListItem>
                ))}
                {groups.length === 0 && !paging.loading && !paging.error &&
                    <Typography variant="caption" color="text.secondary" sx={{px: 2.5}}>No groups yet</Typography>}
                <ListSubheader disableSticky sx={{display: "flex", alignItems: "center", justifyContent: "space-between", bgcolor: "transparent", mt: 1, lineHeight: "36px", fontSize: 12, letterSpacing: 1}}>
                    TAGS
                    <Button size="small" startIcon={<AddIcon/>} onClick={onAddTag}>add</Button>
                </ListSubheader>
                {tags.map((t) => (
                    <ListItem key={t.id} disablePadding sx={{"&:hover .edit, & .edit:focus-visible": {opacity: 1}}}
                              secondaryAction={<IconButton className="edit" size="small" edge="end" aria-label={`Edit ${t.name}`}
                                                           sx={{mr: 1, "@media (hover: hover)": {opacity: 0}}}
                                                           onClick={() => onEditTag(t)}><EditOutlinedIcon fontSize="small"/></IconButton>}>
                        <ListItemButton sx={item} selected={selectedTag === t.id} onClick={() => onSelect(null, t.id)}>
                            <ListItemIcon sx={{minWidth: 36, color: colorOf(t.id)}}><LabelOutlinedIcon fontSize="small"/></ListItemIcon>
                            <ListItemText primary={t.name} slotProps={{primary: {noWrap: true}}}/>
                        </ListItemButton>
                    </ListItem>
                ))}
            </List>
            <InfiniteScroll onMore={paging.loadMore} onRetry={paging.retry} hasMore={paging.hasMore} loading={paging.loading} count={groups.length} error={paging.error}/>
        </>
    );
}
