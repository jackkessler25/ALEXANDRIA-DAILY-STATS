"""
Alexandria Daily Report Generator
Queries Sigma, builds the HTML file, commits it to GitHub Pages.
Runs nightly via GitHub Actions.
"""

import os
import requests
from datetime import date, datetime

SIGMA_CLIENT_ID     = os.environ["SIGMA_CLIENT_ID"]
SIGMA_CLIENT_SECRET = os.environ["SIGMA_CLIENT_SECRET"]
SIGMA_WORKBOOK_ID   = "eeebb906-d875-432c-946d-77c7a121dfd7"
SIGMA_ELEMENT_ID    = "QmmzkyOvk3"

TARGET_REPS = [
    "LANDIN NEILL", "COLIN NEDBLAKE", "COLTON CURTIS", "DYLAN TAYLOR",
    "KRIS ROBERSON", "AUGUST JONES", "EDUARDO ARREDONDO", "JASON BRYANT",
    "MEKHI JUNIEL", "WADE SCHEMENAUER", "LANDON RHODES", "GUSTAVO ORTIZ",
    "BARACK TURNER", "NICOLE HARRISON", "TALAN WENDEL", "BLAINE TURPIN",
    "CADEN REESE", "JADEN CALHOUN", "RYAN ROBERSON", "TANNER PETILLO",
]

def get_sigma_token():
    r = requests.post(
        "https://aws-api.sigmacomputing.com/v2/auth/token",
        json={"grant_type":"client_credentials",
              "client_id":SIGMA_CLIENT_ID,
              "client_secret":SIGMA_CLIENT_SECRET},
    )
    r.raise_for_status()
    return r.json()["access_token"]

def query_sigma(token, today_str):
    names = ",".join(f"'{n}'" for n in TARGET_REPS)
    sql = f"""
        SELECT
            "inode-7qH2dUry7n8DhtjgReE6GP/REP_NAME"                    AS rep,
            SUM("inode-7qH2dUry7n8DhtjgReE6GP/SOLD")                   AS sales,
            SUM("inode-7qH2dUry7n8DhtjgReE6GP/SOLD_CONTRACT_VALUE")    AS cv,
            SUM("inode-7qH2dUry7n8DhtjgReE6GP/ACTUAL_CONTRACT_VALUE")  AS serv,
            SUM("inode-7qH2dUry7n8DhtjgReE6GP/KNOCKS")                 AS knocks,
            SUM("inode-7qH2dUry7n8DhtjgReE6GP/TOTAL_DECISION_MAKERS")  AS dms,
            MIN("inode-7qH2dUry7n8DhtjgReE6GP/FIRST_KNOCK_SECONDS")    AS fk,
            MAX("inode-7qH2dUry7n8DhtjgReE6GP/LAST_KNOCK_SECONDS")     AS lk
        FROM "workbook"."{SIGMA_ELEMENT_ID}"
        WHERE CAST("inode-7qH2dUry7n8DhtjgReE6GP/DATE" AS date) = '{today_str}'
          AND "inode-7qH2dUry7n8DhtjgReE6GP/PARENT_NAME" = 'JACK KESSLER'
          AND "inode-7qH2dUry7n8DhtjgReE6GP/REP_NAME" IN ({names})
        GROUP BY 1
        ORDER BY 2 DESC, 3 DESC
    """
    r = requests.post(
        f"https://aws-api.sigmacomputing.com/v2/workbooks/{SIGMA_WORKBOOK_ID}/query",
        headers={"Authorization":f"Bearer {token}","Content-Type":"application/json"},
        json={"sql":sql},
    )
    r.raise_for_status()
    data = r.json()
    col  = {c:i for i,c in enumerate(data["columns"])}

    returned = {}
    for row in data["rows"]:
        returned[row[col["rep"]]] = {
            "name":   row[col["rep"]].title(),
            "sales":  row[col["sales"]]  or 0,
            "cv":     row[col["cv"]]     or 0,
            "serv":   row[col["serv"]]   or 0,
            "knocks": row[col["knocks"]] or 0,
            "dms":    row[col["dms"]]    or 0,
            "fk":     row[col["fk"]],
            "lk":     row[col["lk"]],
        }

    # Fill in any reps with no activity today
    reps = []
    for name in TARGET_REPS:
        if name in returned:
            reps.append(returned[name])
        else:
            reps.append({"name":name.title(),"sales":0,"cv":0,"serv":0,
                         "knocks":0,"dms":0,"fk":None,"lk":None})
    return reps

def build_html(reps, today_str):
    d        = datetime.strptime(today_str, "%Y-%m-%d")
    day_long = d.strftime("%A, %B %-d · %Y")

    total_sales  = sum(r["sales"]  for r in reps)
    total_cv     = sum(r["cv"]     for r in reps)
    total_serv   = sum(r["serv"]   for r in reps)
    total_knocks = sum(r["knocks"] for r in reps)

    # Build JS reps array
    def js_val(v):
        return "null" if v is None else str(v)

    js_reps = "[\n" + ",\n".join(
        f'  {{name:{repr(r["name"])},sales:{r["sales"]},cv:{r["cv"]},'
        f'serv:{r["serv"]},knocks:{r["knocks"]},dms:{r["dms"]},'
        f'fk:{js_val(r["fk"])},lk:{js_val(r["lk"])}}}'
        for r in reps
    ) + "\n]"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ALEXANDRIA · {today_str}</title>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0;}}
body{{background:#0f1117;color:#e8eaf0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;min-height:100vh;padding:2rem;}}
.header{{display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:1.5rem;border-bottom:2px solid #2a2d3a;padding-bottom:1rem;}}
.header-name{{font-size:32px;font-weight:800;color:#fff;letter-spacing:-.5px;}}
.header-date{{font-size:18px;color:#8b90a0;font-weight:500;}}
.summary-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:1.5rem;}}
.metric{{background:#1a1d27;border:1px solid #2a2d3a;border-radius:12px;padding:16px 20px;}}
.metric-label{{font-size:11px;font-weight:700;color:#6b7080;text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px;}}
.metric-val{{font-size:36px;font-weight:800;color:#fff;line-height:1;}}
.sort-row{{display:flex;gap:8px;margin-bottom:16px;align-items:center;flex-wrap:wrap;}}
.sort-label{{font-size:11px;font-weight:700;color:#5a5f70;text-transform:uppercase;letter-spacing:.07em;margin-right:2px;}}
.sort-btn{{font-size:12px;font-weight:600;padding:6px 14px;border-radius:7px;border:1.5px solid #2a2d3a;background:transparent;color:#8b90a0;cursor:pointer;transition:all .1s;display:flex;align-items:center;gap:5px;}}
.sort-btn:hover{{background:#1a1d27;color:#e8eaf0;}}
.sort-btn.active-asc{{background:#1a2a3a;color:#60aaff;border-color:#3060a0;}}
.sort-btn.active-desc{{background:#2a1a3a;color:#c080ff;border-color:#7040b0;}}
.tbl-wrap{{border:1.5px solid #2a2d3a;border-radius:14px;overflow-x:auto;-webkit-overflow-scrolling:touch;}}
table{{width:100%;min-width:700px;border-collapse:collapse;font-size:16px;}}
thead{{background:#181b25;}}
th{{font-size:11px;font-weight:700;color:#5a5f70;text-transform:uppercase;letter-spacing:.08em;padding:12px 16px;border-bottom:1.5px solid #2a2d3a;text-align:left;white-space:nowrap;}}
th.r{{text-align:right;}}
td{{padding:13px 16px;border-bottom:1px solid #1e2130;font-size:16px;white-space:nowrap;}}
td.r{{text-align:right;font-variant-numeric:tabular-nums;}}
tbody tr:last-child td{{border-bottom:none;}}
tbody tr:hover td{{background:#181b25;}}
.rep-name{{font-weight:600;font-size:16px;color:#e8eaf0;}}
.dim td{{color:#4a4f60;}}
.dim .rep-name{{color:#6b7080;font-weight:500;}}
.s-badge{{display:inline-block;padding:4px 12px;border-radius:7px;font-size:15px;font-weight:800;min-width:36px;text-align:center;}}
.s6{{background:#2e9900;color:#0a1f00;}}.s5{{background:#38b000;color:#0a1f00;}}
.s4{{background:#4caf20;color:#0d2500;}}.s3{{background:#78c840;color:#1a3d00;}}
.s2{{background:#a0d870;color:#2a5000;}}.s1{{background:#3a3d4a;color:#a8aab8;}}
.serv-pos{{color:#5ecc88;font-weight:600;}}
.fk-early{{color:#4ecb82;font-weight:700;}}
.lk-late{{color:#e05252;font-weight:700;}}
@media(max-width:600px){{
  body{{padding:1rem;}}
  .header-name{{font-size:24px;}}.header-date{{font-size:14px;}}
  .metric-val{{font-size:26px;}}.metric{{padding:12px 14px;}}
  th{{padding:10px 12px;}}td{{padding:11px 12px;font-size:14px;}}
  .rep-name{{font-size:14px;}}.s-badge{{font-size:13px;padding:3px 8px;}}
}}
</style>
</head>
<body>
<div class="header">
  <span class="header-name">ALEXANDRIA</span>
  <span class="header-date">{day_long}</span>
</div>
<div class="summary-grid">
  <div class="metric"><div class="metric-label">Sales</div><div class="metric-val">{total_sales}</div></div>
  <div class="metric"><div class="metric-label">Sold CV</div><div class="metric-val">${total_cv:,}</div></div>
  <div class="metric"><div class="metric-label">Serviced CV</div><div class="metric-val">${total_serv:,}</div></div>
  <div class="metric"><div class="metric-label">Knocks</div><div class="metric-val">{total_knocks:,}</div></div>
</div>
<div class="sort-row">
  <span class="sort-label">Sort by:</span>
  <button class="sort-btn" id="btn-sales"  onclick="cycleSort('sales')"><span>Sales</span><span id="arr-sales">↕</span></button>
  <button class="sort-btn" id="btn-knocks" onclick="cycleSort('knocks')"><span>Knocks</span><span id="arr-knocks">↕</span></button>
  <button class="sort-btn" id="btn-dms"    onclick="cycleSort('dms')"><span>DMs</span><span id="arr-dms">↕</span></button>
</div>
<div class="tbl-wrap">
  <table>
    <thead>
      <tr>
        <th style="width:24%">Rep</th>
        <th class="r" style="width:8%">Sales</th>
        <th class="r" style="width:12%">Sold CV</th>
        <th class="r" style="width:12%">Serv. CV</th>
        <th class="r" style="width:9%">Knocks</th>
        <th class="r" style="width:7%">DMs</th>
        <th class="r" style="width:12%">First knock</th>
        <th class="r" style="width:12%">Last knock</th>
      </tr>
    </thead>
    <tbody id="tbody"></tbody>
  </table>
</div>
<script>
function secToTime(s){{if(!s)return'—';const h=Math.floor(s/3600),m=Math.floor((s%3600)/60),ap=h>=12?'PM':'AM',h12=h>12?h-12:h===0?12:h;return h12+':'+String(m).padStart(2,'0')+' '+ap;}}
let sortState={{field:'sales',dir:'desc'}};
function cycleSort(field){{
  if(sortState.field===field){{sortState.dir=sortState.dir==='desc'?'asc':'desc';}}
  else{{sortState.field=field;sortState.dir='desc';}}
  updateSortButtons();render();
}}
function updateSortButtons(){{
  ['sales','knocks','dms'].forEach(f=>{{
    const btn=document.getElementById('btn-'+f),arr=document.getElementById('arr-'+f);
    btn.className='sort-btn';
    if(sortState.field===f){{
      if(sortState.dir==='desc'){{btn.classList.add('active-desc');arr.textContent=' ↓ Most';}}
      else{{btn.classList.add('active-asc');arr.textContent=' ↑ Least';}}
    }}else{{arr.textContent='↕';}}
  }});
}}
const reps={js_reps};
function render(){{
  const f=sortState.field,d=sortState.dir==='desc'?-1:1;
  const sorted=[...reps].sort((a,b)=>d*(a[f]-b[f])||(b.sales-a.sales)||b.cv-a.cv);
  document.getElementById('tbody').innerHTML=sorted.map(r=>{{
    const dim=r.sales===0&&r.serv===0?'dim':'';
    const sc=r.sales>=6?'s6':r.sales>=5?'s5':r.sales>=4?'s4':r.sales>=3?'s3':r.sales>=2?'s2':r.sales===1?'s1':'';
    const sb=r.sales>0?`<span class="s-badge ${{sc}}">${{r.sales}}</span>`:`<span style="color:#4a4f60">0</span>`;
    const sv=r.serv>0?`<span class="serv-pos">$${{r.serv.toLocaleString()}}</span>`:`<span style="color:#4a4f60">—</span>`;
    const fkc=r.fk&&r.fk<=38700?'fk-early':'',lkc=r.lk&&r.lk>=75600?'lk-late':'';
    const kS=sortState.field==='knocks'?'font-weight:700;color:#c8cad8':'';
    const dS=sortState.field==='dms'?'font-weight:700;color:#c8cad8':'';
    return`<tr class="${{dim}}">
      <td class="rep-name">${{r.name}}</td>
      <td class="r">${{sb}}</td>
      <td class="r">${{r.cv?'$'+r.cv.toLocaleString():`<span style="color:#4a4f60">—</span>`}}</td>
      <td class="r">${{sv}}</td>
      <td class="r" style="${{kS}}">${{r.knocks||`<span style="color:#4a4f60">—</span>`}}</td>
      <td class="r" style="${{dS}}">${{r.dms||`<span style="color:#4a4f60">—</span>`}}</td>
      <td class="r ${{fkc}}">${{secToTime(r.fk)}}</td>
      <td class="r ${{lkc}}">${{secToTime(r.lk)}}</td>
    </tr>`;
  }}).join('');
}}
updateSortButtons();render();
</script>
</body>
</html>"""

def main():
    today = date.today().isoformat()
    print(f"Generating Alexandria report for {today}...")
    token = get_sigma_token()
    reps  = query_sigma(token, today)
    html  = build_html(reps, today)
    with open("index.html", "w") as f:
        f.write(html)
    print("index.html written successfully.")

if __name__ == "__main__":
    main()
