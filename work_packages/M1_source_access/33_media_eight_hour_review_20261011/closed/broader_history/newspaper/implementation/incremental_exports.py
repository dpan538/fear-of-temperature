"""Measured future metadata writes; retained exports remain charged once."""
import pathlib,json,io,csv,fcntl,os
import elt
READ_BUFFER_PEAK=0
def pending_write_peak(payload_bytes):
    # UTF-8 serialization/temp file plus final file; existing retained files are
    # already included in elt.resource(). No full old export/store re-reserve.
    return READ_BUFFER_PEAK+2*payload_bytes+65536
def read_peak(own):
    global READ_BUFFER_PEAK
    bodies=own/'bodies'
    body_bytes=sum(p.stat().st_size for p in bodies.iterdir() if p.is_file()) if bodies.exists() else 0
    meta_bytes=sum((own/n).stat().st_size for n in ['BASELINE_METADATA.csv','LOAD_LOG.jsonl','ARCHIVE_ISSUE_STATE.json'] if (own/n).exists())
    requests=[json.loads(x) for x in (own/'REQUESTS.jsonl').read_text().splitlines() if x] if (own/'REQUESTS.jsonl').exists() else []
    raw_peak=max((r.get('raw_bytes',0) or 0 for r in requests),default=0)
    READ_BUFFER_PEAK=3*body_bytes+3*meta_bytes+3*raw_peak+65536
    return READ_BUFFER_PEAK
def write(path,data):
    assert path.parent==elt.OWN and path.name not in ['EXECUTION_SCOPE.json']
    with elt.LOCK.open('a+b') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        capacity=elt.preflight(pending_write_peak(len(data)))
        temp=path.with_name(path.name+'.export-pending')
        temp.write_bytes(data);temp.replace(path)
    elt.append('INCREMENTAL_EXPORT_RECEIPTS.jsonl',dict(at_utc=elt.utc(),file=path.name,payload_bytes=len(data),actual_retained_bytes_charged_by_resource=True,unperformed_write_peak_bytes=pending_write_peak(len(data)),read_buffer_peak_bytes=READ_BUFFER_PEAK,full_prior_export_reserved_again=False,capacity=capacity))
def save(name,obj):
    write(elt.OWN/name,(json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode())
def csvwrite(name,rows,fields=None):
    rows=list(rows);fields=fields or list(dict.fromkeys(k for r in rows for k in r))
    buffer=io.StringIO(newline='');writer=csv.DictWriter(buffer,fieldnames=fields);writer.writeheader()
    writer.writerows({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in r.items()} for r in rows)
    write(elt.OWN/name,buffer.getvalue().encode())
def remaining_unmaterialised_bytes(expected,materialised):return max(0,expected-materialised)
