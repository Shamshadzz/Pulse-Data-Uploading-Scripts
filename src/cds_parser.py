import re
from typing import Dict, List, Any, Tuple

CDS_ENUM_RE = re.compile(r"type\s+(?P<name>[A-Za-z0-9_]+)\s*:\s*String\s*enum\s*\{(?P<body>[^}]*)\}", re.DOTALL)
CDS_ENTITY_RE = re.compile(r"entity\s+(?P<name>[A-Za-z0-9_]+)\s*\{(?P<body>.*?)\}", re.DOTALL)
CDS_UNIQUE_RE = re.compile(r"@assert\.unique\s*:\s*\{(?P<body>[^}]*)\}", re.DOTALL)

FIELD_LINE_RE = re.compile(
    r"^(?P<key>\s*key\s+)?(?P<name>[A-Z0-9_]+)\s*:\s*(?P<type>[A-Za-z0-9_() ,]+?);",
    re.MULTILINE,
)
ASSOC_LINE_RE = re.compile(
    r"^\s*(?P<name>[A-Z0-9_]+)\s*:\s*Association\s+to\s+(?P<target>[A-Z0-9_]+)",
    re.MULTILINE,
)
COMMENT_LINE_RE = re.compile(r"^\s*//\s*(?P<text>.*)$", re.MULTILINE)

C_STYLE_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)


def _parse_unique(body: str) -> List[Dict[str, Any]]:
    # Example: unique_uom: [CODE], another_one: [A, B]
    parts = [p.strip() for p in body.split(',') if p.strip()]
    constraints: List[Dict[str, Any]] = []
    # Re-join tokens into name:[cols] pairs
    buf = []
    acc = ""
    for p in parts:
        acc = acc + ("," if acc else "") + p
        if "]" in p:
            buf.append(acc)
            acc = ""
    if acc:
        buf.append(acc)
    for pair in buf:
        if ':' not in pair:
            continue
        name, cols = pair.split(':', 1)
        name = name.strip()
        cols = cols.strip()
        m = re.match(r"\[(.*?)\]", cols)
        if not m:
            continue
        col_list = [c.strip() for c in m.group(1).split(',') if c.strip()]
        constraints.append({"name": name, "columns": col_list})
    return constraints


def parse_cds(content: str) -> Dict[str, Any]:
    # Strip C-style comments to avoid confusing field parsing
    content_nc = C_STYLE_COMMENT_RE.sub("", content)

    enums: Dict[str, List[str]] = {}
    for m in CDS_ENUM_RE.finditer(content_nc):
        name = m.group('name')
        body = m.group('body')
        values = [v.strip() for v in body.replace('\n', ' ').split(';') if v.strip()]
        enums[name] = values

    # Map entity name to its unique constraints captured immediately before it
    uniques_by_entity: Dict[str, List[Dict[str, Any]]] = {}
    # Collect segments with positions to map annotations to next entity
    annotations: List[Tuple[int, List[Dict[str, Any]]]] = []
    for m in CDS_UNIQUE_RE.finditer(content_nc):
        constraints = _parse_unique(m.group('body'))
        annotations.append((m.end(), constraints))

    # Build entity structures
    entities: Dict[str, Dict[str, Any]] = {}
    for ent in CDS_ENTITY_RE.finditer(content_nc):
        name = ent.group('name')
        body = ent.group('body')
        # Find nearest unique annotation right before this entity block
        unique_list: List[Dict[str, Any]] = []
        start_idx = ent.start()
        for pos, cons in annotations:
            if pos <= start_idx:
                unique_list = cons
            else:
                break

        fields: List[Dict[str, Any]] = []
        associations: List[Dict[str, Any]] = []

        # Collect comments as notes
        notes = [m.group('text').strip() for m in COMMENT_LINE_RE.finditer(body)]

        for fm in FIELD_LINE_RE.finditer(body):
            fname = fm.group('name').strip()
            ftype = fm.group('type').strip()
            is_key = fm.group('key') is not None
            # Skip association lines which are handled separately
            if 'Association' in ftype:
                continue
            fields.append({
                'name': fname,
                'type': ftype,
                'key': bool(is_key)
            })
        for am in ASSOC_LINE_RE.finditer(body):
            aname = am.group('name').strip()
            atarget = am.group('target').strip()
            associations.append({
                'name': aname,
                'target': atarget
            })

        entities[name] = {
            'fields': fields,
            'associations': associations,
            'uniqueConstraints': unique_list,
            'notes': notes,
        }

    return {'enums': enums, 'entities': entities}


def build_dependencies(parsed: Dict[str, Any]) -> Dict[str, List[str]]:
    deps: Dict[str, List[str]] = {}
    ents = parsed['entities']
    for ename, edef in ents.items():
        targets: List[str] = []
        # From associations
        for assoc in edef.get('associations', []):
            t = assoc.get('target')
            if t and t != ename and t not in targets:
                targets.append(t)
        # From *_ID heuristic
        for f in edef.get('fields', []):
            fname = f['name']
            if fname.endswith('_ID') and f.get('type','').upper().startswith('UUID'):
                base = fname[:-3]
                # Try to match association with same base
                matched = None
                for assoc in edef.get('associations', []):
                    if assoc['name'] == base:
                        matched = assoc['target']
                        break
                if matched:
                    if matched != ename and matched not in targets:
                        targets.append(matched)
        deps[ename] = targets
    return deps


def topo_sort(deps: Dict[str, List[str]]) -> List[str]:
    # Kahn's algorithm
    nodes = set(deps.keys()) | {d for v in deps.values() for d in v}
    incoming = {n: set() for n in nodes}
    outgoing = {n: set() for n in nodes}
    for n, vs in deps.items():
        for v in vs:
            incoming[n].add(v)
            outgoing[v].add(n)
    order: List[str] = []
    S = [n for n in nodes if not incoming[n]]
    S.sort()
    while S:
        n = S.pop(0)
        order.append(n)
        for m in list(outgoing[n]):
            outgoing[n].remove(m)
            incoming[m].remove(n)
            if not incoming[m]:
                S.append(m)
                S.sort()
    # Append any remaining nodes (cycles) at end, stable order
    remaining = [n for n in nodes if n not in order]
    order.extend(sorted(remaining))
    return order
