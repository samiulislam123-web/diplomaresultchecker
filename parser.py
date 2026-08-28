import hashlib, re
from pathlib import Path
import pdfplumber

ROLL_RE = re.compile(r"\b(?:roll(?:\s*no)?|roll\s*number)\s*[:#-]?\s*(\d{4,12})\b", re.I)
REG_RE = re.compile(r"\b(?:registration|reg(?:istration)?\.?\s*no)\s*[:#-]?\s*([0-9-]{5,20})\b", re.I)
GPA_RE = re.compile(r"\b(?:gpa|cgpa)\s*[:=-]?\s*(4(?:\.0{1,2})?|[0-3](?:\.\d{1,2})?)\b", re.I)
SEM_RE = re.compile(r"\b(?:semester|sem)\s*[:#-]?\s*(1|2|3|4|5|6|7|8)(?:st|nd|rd|th)?\b", re.I)
YEAR_RE = re.compile(r"\b(?:20\d{2})\b")
STATUS_RE = re.compile(r"\b(PASS|PASSED|FAIL|FAILED|REFERRED|REF|PROMOTED|COMPLETED)\b", re.I)
REF_RE = re.compile(r"(?:referred\s*(?:subject(?:s)?|code(?:s)?)?|ref(?:\.|erred)?\s*subject(?:s)?)[\s:=-]*([0-9, /-]{2,100})", re.I)

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def clean(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()

def parse_pdf_bytes(data: bytes, filename: str, default_probidhan: str | None = None, default_year: int | None = None):
    records=[]
    with pdfplumber.open(__import__('io').BytesIO(data)) as pdf:
        for page_no, page in enumerate(pdf.pages, 1):
            text=page.extract_text() or ""
            lines=[clean(x) for x in text.splitlines() if clean(x)]
            for i,line in enumerate(lines):
                rm=ROLL_RE.search(line)
                if not rm:
                    continue
                roll=rm.group(1)
                window=" ".join(lines[max(0,i-2):min(len(lines),i+4)])
                reg=REG_RE.search(window)
                gm=GPA_RE.search(window)
                sm=SEM_RE.search(window)
                ym=YEAR_RE.search(window)
                status=STATUS_RE.search(window)
                ref=REF_RE.search(window)
                prob=default_probidhan
                pm=re.search(r"(?:probidhan|regulation)\s*[:#-]?\s*(2010|2016|2022)", window, re.I)
                if pm: prob=pm.group(1)
                if not prob: continue
                gpa=float(gm.group(1)) if gm else None
                sem=int(sm.group(1)) if sm else None
                year=int(ym.group(0)) if ym else default_year
                if sem is None:
                    # If the PDF is a semester-specific publication, semester can be supplied by filename.
                    fm=re.search(r"(?:sem|semester)[_-]?(1|2|3|4|5|6|7|8)", filename, re.I)
                    sem=int(fm.group(1)) if fm else None
                records.append({
                    "probidhan": prob, "roll": roll,
                    "registration": reg.group(1) if reg else None,
                    "name": None,
                    "exam_year": year, "semester": sem, "gpa": gpa,
                    "status": status.group(1).upper() if status else None,
                    "referred_subjects": ref.group(1).strip() if ref else None,
                    "page": page_no,
                })
    # Keep only usable rows and de-duplicate exact identities within one import.
    out=[]; seen=set()
    for r in records:
        key=(r["probidhan"],r["roll"],r["exam_year"],r["semester"])
        if r["semester"] is None or key in seen: continue
        seen.add(key); out.append(r)
    return out
