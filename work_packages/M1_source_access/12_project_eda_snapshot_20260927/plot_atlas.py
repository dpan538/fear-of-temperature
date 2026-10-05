"""Render eight English project EDA figures from the frozen data/*.csv inputs."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/eda_mplconfig")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch, Rectangle
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA, OUT, QA = HERE / "data", HERE / "figures", HERE / "qa"
GOV, MEDIA, PUBLIC = "#6E4D9B", "#357AA8", "#258F86"
INK, MUTED, LIGHT, WARM = "#1F2D3A", "#637485", "#E8EDF0", "#C67738"
ROLE = {"government": GOV, "media": MEDIA, "public": PUBLIC}
plt.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["DejaVu Sans"], "font.size": 9, "axes.titlesize": 11,
                     "axes.labelsize": 9, "xtick.labelsize": 8, "ytick.labelsize": 8,
                     "svg.fonttype": "none", "pdf.fonttype": 42, "axes.spines.top": False,
                     "axes.spines.right": False, "savefig.facecolor": "white"})
plt.rcParams["font.family"] = "sans-serif"


def load(n): return pd.read_csv(DATA / f"figure_{n:02d}_{['inventory','months','annual','footprint','text_shape','paris','review','topology'][n-1]}.csv")


def canvas(n, title, subtitle, footer, h=7.2):
    fig = plt.figure(figsize=(13.4, h), facecolor="white")
    fig.text(.055, .94, f"{n:02d}  {title}", fontsize=16, weight="bold", color=INK)
    fig.text(.055, .901, subtitle, fontsize=9, color=MUTED)
    fig.text(.055, .032, footer, fontsize=7.3, color=MUTED)
    return fig


def save(fig, n):
    OUT.mkdir(exist_ok=True); QA.mkdir(exist_ok=True)
    name = f"figure_{n:02d}"
    if n in (3, 4):
        sys.path.insert(0, "/Users/jarlgiovanni/.codex/skills/nature-figure/scripts")
        from audit_panel_alignment import require_matplotlib_panel_alignment
        fig.canvas.draw()
        require_matplotlib_panel_alignment(fig, json_out=QA / f"{name}_alignment.json",
                                           panel_ids=["a", "b"], row_groups=[{"id": "main-row", "panels": ["a", "b"]}])
    fig.savefig(OUT / f"{name}.png", dpi=320)
    fig.savefig(OUT / f"{name}.pdf")
    fig.savefig(OUT / f"{name}.svg")
    plt.close(fig)


def fig1():
    d = load(1)
    pilot = pd.read_csv(DATA / "figure_01_pilots.csv")
    f = canvas(1, "A large dated inventory narrows at the text stage", "Independent parents or EU Works; points show three documented acquisition stages.",
               "Source-specific checkpoints on 27 Sep 2026 UTC. Guardian URLs and petition IDs are separate pilot units; no cross-source total.")
    a = f.add_axes([.23,.35,.70,.47]); a.set_xscale("log")
    for i, x in d.iterrows():
        y = 3-i; c = GOV if x.source in ("UK","EU") else "#8069AD"
        a.plot([x.readable_text,x.dated],[y,y],color=c,lw=3,alpha=.42)
        for val,mark,fill in [(x.dated,"o","white"),(x.saved_original,"s","white"),(x.readable_text,"o",c)]:
            a.scatter(val,y,marker=mark,s=72,facecolor=fill,edgecolor=c,zorder=3,lw=1.6)
        a.text(x.dated*1.14,y,f"{x.dated:,} dated",va="center",fontsize=8,color=INK)
        a.text(x.readable_text/1.17,y-.19,f"{x.readable_text:,} text",ha="right",fontsize=7.5,color=c)
    a.set_xlim(2,7e5);a.set_ylim(-.7,3.6);a.set_yticks(range(4));a.set_yticklabels(["AU · original parents","EU · Works","US · selected parents","UK · independent parents"])
    a.set_xlabel("Independent parents / Works (log scale)")
    a.legend([Line2D([0],[0],marker="o",color="none",markerfacecolor="white",markeredgecolor=GOV),Line2D([0],[0],marker="s",color="none",markerfacecolor="white",markeredgecolor=GOV),Line2D([0],[0],marker="o",color="none",markerfacecolor=GOV,markeredgecolor=GOV)],
             ["Dated","Saved original","Nonempty stored text"],frameon=False,loc="lower right",fontsize=8)
    f.text(.055,.235,"Separate pilot inventory",color=INK,weight="bold",fontsize=9)
    for i,x in pilot.iterrows():
        f.text(.055,.193-i*.04,f"{x.source}: {x['count']:,} {x.unit}s  ·  {x.qualification}",fontsize=8.5,color=MEDIA if i==0 else PUBLIC)
    save(f,1)


def fig2():
    d=load(2); order=["UK","EU","US","AU","Pooled government","Media pilot","Public pilot"]
    months=sorted(d.month.unique()); codes={"unaudited or absent":0,"metadata only":1,"readable":2,"readable pilot":3,"confirmed query zero":4}
    z=np.array([[codes[d[(d.source==s)&(d.month==m)].status.iloc[0]] for m in months] for s in order])
    f=canvas(2,"Government text touches every study month","465 monthly bins, January 1988–September 2026; pilot channels remain partial.",
             "Presence of stored text, not climate relevance. September 2026 is partial; gray is unaudited or absent, not verified zero.")
    a=f.add_axes([.17,.28,.78,.51]);cm=ListedColormap(["#DCE2E6","#D9B58A",GOV,MEDIA,WARM])
    z[(z==3)&(np.arange(z.shape[0])[:,None]==6)]=5
    cm=ListedColormap(["#DCE2E6","#D9B58A",GOV,MEDIA,WARM,PUBLIC])
    a.imshow(z,aspect="auto",interpolation="none",cmap=cm,vmin=0,vmax=5)
    a.set_yticks(range(7));a.set_yticklabels(order);a.set_xticks([0,84,168,252,336,420,464]);a.set_xticklabels([months[i] for i in [0,84,168,252,336,420,464]])
    a.axvline(months.index("2015-04")-.5,color=WARM,lw=1.5,ls="--")
    a.axvline(months.index("2015-05")+.5,color=WARM,lw=1.5,ls="--")
    a.text(months.index("2015-04")+11,-1.0,"2015 bridge",color=WARM,fontsize=8,ha="left")
    a.set_xlim(-.5,464.5);a.set_ylim(6.5,-1.3)
    for i,(label,c) in enumerate([("Unaudited / absent", "#DCE2E6"),("Dated, no text", "#D9B58A"),("Government text",GOV),("Media body pilot",MEDIA),("Query-zero",WARM),("Published query hit",PUBLIC)]):
        f.add_artist(Rectangle((.17+i*.128,.17),.012,.018,transform=f.transFigure,color=c,clip_on=False))
        f.text(.184+i*.128,.169,label,fontsize=7.1,color=INK)
    save(f,2)


def fig3():
    d=load(3);f=canvas(3,"UK written answers dominate the annual record","Annual dated independent parents / EU Works; separated scales retain source identity.",
                      "UK counts from read-only DB; US/EU from 10:53 UTC ledger; US 125 bridge originals added to readable status only. 2026 is partial.")
    a=f.add_axes([.08,.29,.55,.49]);b=f.add_axes([.72,.29,.22,.49])
    uk=d[d.source=="UK"]; genres=[("ministerial_written_answer","Written answers",GOV),("ministerial_written_statement","Written statements","#A589C6"),("policy_paper","Policy papers","#D5C5E1")]
    for genre,label,c in genres:
        q=uk[uk.genre==genre];a.plot(q.year,q["count"],color=c,lw=2,label=label)
    a.set_ylabel("UK parents / year");a.set_xlabel("Publication year");a.grid(axis="y",color=LIGHT)
    for j,(_,label,c) in enumerate(genres): f.text(.08+j*.14,.814,"━ " + label,color=c,fontsize=8)
    others=d[d.source.isin(["US","EU"])]
    for source,c in [("EU","#866BAF"),("US","#4D5664")]:
        q=others[others.source==source];b.plot(q.year,q["count"],label=source,color=c,lw=2)
    b.set_yscale("log");b.set_ylim(1,1e5);b.set_xlabel("Publication year");b.set_ylabel("Selected parents / Works (log)");b.grid(axis="y",color=LIGHT);b.legend(frameon=False,fontsize=8)
    total=uk.groupby("genre")["count"].sum(); share=total.get("ministerial_written_answer",0)/total.sum()
    f.text(.08,.175,f"{share:.1%}",fontsize=28,weight="bold",color=GOV)
    f.text(.205,.185,"of dated UK parents are written answers",fontsize=10,color=INK)
    f.add_artist(Rectangle((.08,.145),.52*share,.013,transform=f.transFigure,facecolor=GOV,edgecolor="none"))
    f.add_artist(Rectangle((.08+.52*share,.145),.52*(1-share),.013,transform=f.transFigure,facecolor="#C0A9D6",edgecolor="none"))
    f.text(.08,.115,"Source regime and retrieval depth differ; heights are inventory counts, not comparable expression rates.",fontsize=8,color=MUTED)
    save(f,3)


def fig4():
    d=load(4);f=canvas(4,"The pooled timeline has an uneven issuer footprint","Matrix marks documented source roles; incremental months measure contribution to government text coverage.",
                       "Issuer/provenance scope is not the location of affected people. UK-based Guardian and petition pilots have no population coverage claim.")
    a=f.add_axes([.11,.32,.52,.46]); b=f.add_axes([.70,.32,.22,.46]); scopes=d.issuer_scope.tolist()
    a.set_xlim(0,3);a.set_ylim(5.5,-.5);a.set_xticks([.5,1.5,2.5]);a.set_xticklabels(["Government","Media","Public"]);a.set_yticks(range(6));a.set_yticklabels(scopes)
    for i,x in d.iterrows():
        col={"Government":0,"Media pilot":1,"Public pilot":2}[x.role]
        color=GOV if col==0 else MEDIA if col==1 else PUBLIC
        a.add_patch(Rectangle((col+.12,i-.35),.76,.7,color=color,alpha=.18,ec=color,lw=1.2))
        a.text(col+.5,i,"verified\nsource" if col==0 else "pilot",ha="center",va="center",color=color,fontsize=8)
    a.set_xticks(np.arange(4),minor=True);a.grid(which="minor",axis="x",color=LIGHT);a.tick_params(length=0)
    q=d.iloc[:4];b.barh(np.arange(4),q.incremental_government_months,color=[GOV,"#9777BA","#B19ACA","#C9B8D9"])
    b.set_yticks(range(4));b.set_yticklabels(q.issuer_scope);b.invert_yaxis();b.set_xlim(0,490);b.set_xlabel("New text months after prior sources")
    for i,v in enumerate(q.incremental_government_months):b.text(v+7,i,f"{int(v)}",va="center",fontsize=8)
    f.text(.11,.17,"Locator: UK state institutions · EU Commission (supranational) · US federal agencies · verified AU originals",fontsize=8.6,color=INK)
    save(f,4)


def fig5():
    d=load(5);fm=pd.read_csv(DATA/"figure_05_format.csv");st=pd.read_csv(DATA/"figure_05_status.csv")
    f=canvas(5,"Text length is sharply genre dependent","Parent-level extracted characters; horizontal whiskers show P10–P90, thick bar P25–P75, point median.",
             "UK historical quality snapshot; US EPA bridge 125 parents. PDF segments are layout blocks, not independent documents or semantic units.")
    a=f.add_axes([.28,.40,.65,.39]);series=[("ministerial_written_answer","UK written answers",GOV),("ministerial_written_statement","UK statements","#9C7ABF"),("policy_document","UK policy documents","#C0A9D6"),("US EPA bridge","US EPA bridge","#596777")]
    for i,(s,label,c) in enumerate(series):
        q=d[d.series==s]; v={x["quantile"]:float(x.value) for _,x in q.iterrows()}
        y=3-i;a.plot([v["p10"],v["p90"]],[y,y],color=c,lw=2)
        a.plot([v["p25"],v["p75"]],[y,y],color=c,lw=9,solid_capstyle="butt")
        a.scatter(v["p50"],y,s=50,facecolor="white",edgecolor=c,lw=2,zorder=3)
        a.text(v["p90"]*1.17,y,f"median {v['p50']:,.0f} · n={int(q.record_count.iloc[0]):,}",va="center",fontsize=7.5,color=INK)
    a.set_xscale("log");a.set_xlim(100,2e6);a.set_yticks(range(4));a.set_yticklabels([x[1] for x in series][::-1]);a.set_xlabel("Extracted characters per independent parent (log scale)")
    f.text(.08,.305,"Format audit: UK extraction shape",fontsize=9,weight="bold",color=INK)
    for i,x in fm.iterrows():
        f.text(.08+i*.215,.255,f"{x['format']}  {x.extracted_objects:,}/{x.objects:,} objects",fontsize=8,color=INK)
        f.text(.08+i*.215,.218,f"median block {x.median_segment_characters} chars",fontsize=7.5,color=MUTED)
    uk=st[st.snapshot=="UK quality snapshot"].set_index("status").objects_or_items
    eu=st[st.snapshot!="UK quality snapshot"].set_index("status").objects_or_items
    f.text(.08,.14,f"UK status: OCR needed {uk['needs_ocr']}  ·  unsupported {uk['unsupported_format']}  ·  extraction failed {uk['extraction_failed']} objects",fontsize=8,color=WARM)
    f.text(.08,.108,f"EU status: OCR review {eu['ocr_review_candidate']}  ·  scan OCR pending {eu['scan_ocr_pending']} staged Items",fontsize=8,color=WARM)
    save(f,5)


def fig6():
    d=load(6);months=sorted(d.month.unique());f=canvas(6,"Paris is a source-feasibility window, not a panel yet","49 months centered on December 2015; each glyph records the highest verified evidence stage for that role-month.",
                                                    "Dated → readable → reviewed climate topic → denominator-ready. No complete monthly three-role climate or fear measure is established.")
    a=f.add_axes([.12,.38,.81,.39]);roles=["government","media","public"]
    for ri,role in enumerate(roles):
        q=d[d.role==role].set_index("month")
        for j,m in enumerate(months):
            x=q.loc[m]; state=x.coverage_state
            if role=="government": level=2
            elif state=="not_collected_or_audited": level=0
            elif state=="verified_zero_within_published_keyword_query": level=1
            else: level=2
            y=2-ri
            if level==0: a.scatter(j,y,marker="x",s=15,color="#B4BEC6")
            else:
                a.add_patch(Rectangle((j-.42,y-.31),.84,.62,facecolor=ROLE[role],alpha=.15 if level==1 else .65,edgecolor=ROLE[role],lw=.5))
                if pd.notna(x.pilot_reviewed_parent_count) and x.pilot_reviewed_parent_count>0:
                    a.scatter(j,y,marker="D",s=11,color=INK,zorder=3)
        
    a.set_xlim(-.6,48.6);a.set_ylim(-.7,2.6);a.set_yticks([2,1,0]);a.set_yticklabels(["Government","Media","Public"])
    a.set_xticks([0,6,12,18,24,30,36,42,48]);a.set_xticklabels([months[i] for i in [0,6,12,18,24,30,36,42,48]]);a.axvline(24,color=WARM,ls="--",lw=1.3)
    f.text(.12,.285,"49/49",fontsize=20,color=GOV,weight="bold");f.text(.195,.289,"government months with stored text",fontsize=9,color=INK)
    f.text(.12,.22,"Guardian Dec: 396 dated candidate URLs, 4 checked current bodies. Published petition q=climate opened: Nov 0 · Dec 8 · Jan 5.",fontsize=8.4,color=INK)
    f.text(.12,.15,"Diamond = diagnostic parent review in month; pale cell = dated query result without positive published hit; cross = unaudited.",fontsize=8,color=MUTED)
    save(f,6)


def fig7():
    d=load(7);f=canvas(7,"Reviewed parents cover topic and risk; fear remains a later interpretation","48 deliberately selected diagnostic parents: 23 government, 4 media, 21 petition.",
                     "Filled cell = manual parent label present. Counts are not corpus prevalence; zero explicit-fear labels cannot exclude a source.",h=8)
    a=f.add_axes([.39,.17,.42,.66]);d["role_order"]=d.role.map({"government":0,"media":1,"public":2});d=d.sort_values(["role_order","stratum"]).reset_index(drop=True)
    cols=["climate_topic","anticipated_harm","explicit_fear"]
    for i,x in d.iterrows():
        for j,c in enumerate(cols):
            face=ROLE[x.role] if int(x[c]) else "white"
            a.add_patch(Rectangle((j-.41,i-.41),.82,.82,facecolor=face,edgecolor=LIGHT,lw=.5))
    a.set_xlim(-.55,2.55);a.set_ylim(47.6,-.6);a.set_xticks(range(3));a.set_xticklabels(["Climate topic","Anticipated harm","Explicit fear"]);a.xaxis.tick_top();a.set_yticks([])
    for y,label,c in [(0,"Government · 23",GOV),(23,"Media · 4",MEDIA),(27,"Petition · 21",PUBLIC)]:
        a.axhline(y-.5,color=c,lw=1.5);a.text(-1.37,y+max(1,({0:23,23:4,27:21}[y])/2)-1,label,ha="right",va="center",fontsize=9,color=c)
    for (role,stratum),grp in d.groupby(["role","stratum"],sort=False):
        start=int(grp.index.min());end=int(grp.index.max())
        a.axhline(start-.5,color=LIGHT,lw=.7)
        label={"supplementary_exact_title":"exact-title supplement","title_candidate":"title candidate","hash_control":"hash control","closed":"published / closed"}.get(stratum,stratum)
        a.text(-.66,(start+end)/2,label+f" · {len(grp)}",ha="right",va="center",fontsize=7,color=MUTED)
    counts=d.groupby("role")[cols].sum()
    for j,col in enumerate(cols):f.text(.43+j*.146,.105,f"{int(d[col].sum())}/48",ha="center",fontsize=10,color=INK,weight="bold")
    f.text(.055,.86,"DIAGNOSTIC SAMPLE ONLY",color=WARM,weight="bold",fontsize=9)
    save(f,7)


def fig8():
    d=load(8);f=canvas(8,"Traceable links stop before attribution","Three real pilot parents show observed provenance and the next passage-level interpretation step.",
                     "Solid = source-supported relation; dashed/hollow = proposed review. No causal link is inferred from shared date or topic.")
    a=f.add_axes([.055,.23,.89,.60]);a.set_xlim(0,10);a.set_ylim(-.5,3.5);a.axis("off")
    heads=["Source","Parent ID","Version / field","Observed date + topic","Proposed reading"]
    xs=[.6,2.6,4.75,6.9,9.0]
    for x,h in zip(xs,heads):a.text(x,3.1,h,ha="center",fontsize=9,color=INK,weight="bold")
    for i,x in d.iterrows():
        y=2.45-i*1.05;c=ROLE[x.role]
        vals=[x.role.title(),str(x.parent_id).split("/")[-1][:21],str(x.version_or_hash).split("|")[0][:19],str(x.date)[:10]+"\nclimate topic", "speaker · target\nresponsibility / fear?"]
        for k,(xx,v) in enumerate(zip(xs,vals)):
            a.add_patch(Rectangle((xx-.9,y-.31),1.8,.62,facecolor="white" if k==4 else c+"20",edgecolor=c if k<4 else MUTED,lw=1.2,ls="--" if k==4 else "-"))
            a.text(xx,y,v,ha="center",va="center",fontsize=7.5,color=INK)
            if k<4:
                a.add_patch(FancyArrowPatch((xx+.91,y),(xs[k+1]-.92,y),arrowstyle="-|>",mutation_scale=10,lw=1.3,color=c if k<3 else MUTED,linestyle="--" if k==3 else "-"))
        a.text(4.75,y-.42,str(x.locator)[:56],ha="center",fontsize=6.6,color=MUTED)
    f.text(.055,.13,"Version / field IDs and complete parent IDs are retained in figure_08_topology.csv; Guardian body text is not reproduced.",fontsize=8,color=MUTED)
    save(f,8)


FIGS={1:fig1,2:fig2,3:fig3,4:fig4,5:fig5,6:fig6,7:fig7,8:fig8}


def contact_sheet():
    from PIL import Image
    f=plt.figure(figsize=(16,9),facecolor="white")
    f.text(.025,.965,"Project EDA atlas · acquisition and readiness · 27 September 2026",fontsize=17,weight="bold",color=INK)
    for n in range(1,9):
        im=Image.open(OUT/f"figure_{n:02d}.png")
        a=f.add_axes([.025+((n-1)%2)*.49,.73-((n-1)//2)*.228,.465,.202]);a.imshow(im);a.axis("off")
    f.savefig(OUT/"contact_sheet.png",dpi=320);f.savefig(OUT/"contact_sheet.pdf");plt.close(f)


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("figure",nargs="?",type=int);x=p.parse_args()
    if x.figure: FIGS[x.figure]()
    else:
        for fn in FIGS.values():fn()
        contact_sheet()
