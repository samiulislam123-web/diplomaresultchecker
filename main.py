import json, os, secrets
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from .config import settings
from .db import Base, engine, get_db
from .models import ResultRecord
from .parser import parse_pdf_bytes, sha256_bytes

BASE_DIR = Path(__file__).resolve().parents[1]
FRONTEND_INDEX = BASE_DIR.parent / "frontend" / "index.html"
Base.metadata.create_all(bind=engine)

app=FastAPI(title="BTEB Result Search API", version="1.0.0")
origins=[x.strip() for x in settings.cors_origins.split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins or ["*"], allow_credentials=False, allow_methods=["GET","POST","DELETE"], allow_headers=["*"])

def require_admin(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401,"Admin authentication required")
    token=authorization[7:]
    if not secrets.compare_digest(token, settings.admin_token):
        raise HTTPException(403,"Invalid admin token")

@app.get("/health")
def health(): return {"ok":True,"service":"bteb-result-search-api"}

@app.get("/api/result")
def result(probidhan: str=Query(...), roll: str=Query(...), db: Session=Depends(get_db)):
    probidhan=probidhan.strip(); roll=roll.strip()
    rows=db.scalars(select(ResultRecord).where(ResultRecord.probidhan==probidhan, ResultRecord.roll==roll).order_by(ResultRecord.exam_year.asc(), ResultRecord.semester.asc())).all()
    if not rows:
        return {"found":False,"message":"Result not found"}
    latest=rows[-1]
    semester_gpa={str(r.semester): r.gpa for r in rows if r.semester is not None and r.gpa is not None}
    refs={str(r.semester):r.referred_subjects for r in rows if r.semester is not None and r.referred_subjects}
    return {"found":True,"result":{
        "roll":roll,"name":latest.name,"registration":latest.registration,
        "probidhan":probidhan,"exam_year":latest.exam_year,
        "semester_gpa":semester_gpa,"referred_subjects":refs,
        "status":latest.status,"source":latest.source_url or latest.source_file
    }}

@app.post("/api/admin/import-pdf", dependencies=[Depends(require_admin)])
async def import_pdf(file: UploadFile=File(...), probidhan: str|None=Query(default=None), exam_year: int|None=Query(default=None), source_url: str|None=Query(default=None), db: Session=Depends(get_db)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400,"Only PDF files are accepted")
    data=await file.read()
    if len(data)>settings.max_upload_mb*1024*1024: raise HTTPException(413,"File too large")
    rows=parse_pdf_bytes(data,file.filename,probidhan,exam_year)
    if not rows: raise HTTPException(422,"No usable roll/GPA/semester rows found. Check PDF format or supply probidhan/exam_year.")
    h=sha256_bytes(data); created=updated=0
    for r in rows:
        existing=db.scalar(select(ResultRecord).where(ResultRecord.probidhan==r['probidhan'],ResultRecord.roll==r['roll'],ResultRecord.exam_year==r['exam_year'],ResultRecord.semester==r['semester']))
        payload=dict(r); payload.pop('page',None); payload['source_file']=file.filename; payload['source_hash']=h; payload['source_url']=source_url
        if existing:
            for k,v in payload.items(): setattr(existing,k,v)
            updated+=1
        else:
            db.add(ResultRecord(**payload)); created+=1
    db.commit()
    return {"ok":True,"file":file.filename,"sha256":h,"parsed":len(rows),"created":created,"updated":updated}

@app.post("/api/admin/import-json", dependencies=[Depends(require_admin)])
def import_json(payload: dict, db: Session=Depends(get_db)):
    rows=payload.get("records")
    if not isinstance(rows,list): raise HTTPException(400,"records array required")
    created=updated=0
    for r in rows:
        required=[r.get('probidhan'),r.get('roll'),r.get('exam_year'),r.get('semester')]
        if any(x is None for x in required): continue
        existing=db.scalar(select(ResultRecord).where(ResultRecord.probidhan==str(r['probidhan']),ResultRecord.roll==str(r['roll']),ResultRecord.exam_year==int(r['exam_year']),ResultRecord.semester==int(r['semester'])))
        vals={k:r.get(k) for k in ['probidhan','roll','registration','name','exam_year','semester','gpa','status','referred_subjects','source_url','source_file','source_hash']}
        if existing:
            for k,v in vals.items(): setattr(existing,k,v)
            updated+=1
        else: db.add(ResultRecord(**vals)); created+=1
    db.commit(); return {"ok":True,"created":created,"updated":updated}

@app.get("/api/admin/stats", dependencies=[Depends(require_admin)])
def stats(db: Session=Depends(get_db)):
    return {"records":db.scalar(select(func.count()).select_from(ResultRecord)) or 0,"rolls":db.scalar(select(func.count(func.distinct(ResultRecord.roll)))) or 0}

@app.delete("/api/admin/results/{probidhan}/{roll}", dependencies=[Depends(require_admin)])
def delete_result(probidhan: str, roll: str, db: Session=Depends(get_db)):
    n=db.query(ResultRecord).filter(ResultRecord.probidhan==probidhan,ResultRecord.roll==roll).delete(synchronize_session=False); db.commit(); return {"ok":True,"deleted":n}

@app.get("/", include_in_schema=False)
def home():
    if not FRONTEND_INDEX.exists():
        raise HTTPException(500, "Frontend index.html is missing")
    return FileResponse(FRONTEND_INDEX)
