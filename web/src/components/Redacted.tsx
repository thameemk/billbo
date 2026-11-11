import {Box} from "@mui/material";
import {useState, type ReactNode} from "react";

// Blurred until clicked; click again to hide.
export function Redacted({children}: { children: ReactNode }) {
    const [show, setShow] = useState(false);
    return <Box component="span" onClick={() => setShow((s) => !s)} sx={{cursor: "pointer", filter: show ? "none" : "blur(8px)", userSelect: show ? "auto" : "none"}}>{children}</Box>;
}
