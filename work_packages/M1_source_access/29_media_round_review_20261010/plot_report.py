"""PNG report from closed, traceable metadata aggregates; no sampling or semantic filtering."""
from pathlib import Path
import json, sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager, colors, ticker
sys.path.insert(0, '/Users/jarlgiovanni/.codex/skills/nature-figure/scripts')
from audit_panel_alignment import require_matplotlib_panel_alignment

OUT=Path(__file__).resolve().parent; T=OUT/'tables'; F=OUT/'figures'; Q=OUT/'qa'
font_manager.fontManager.addfont('/Library/Fonts/Arial Unicode.ttf')
plt.rcParams.update({'font.family':'Arial Unicode MS','font.size':11,'axes.titlesize':13,'axes.labelsize':11,'axes.spines.top':False,'axes.spines.right':False,'axes.unicode_minus':False,'pdf.fonttype':42,'svg.fonttype':'none','figure.facecolor':'white','axes.facecolor':'white','savefig.facecolor':'white'})
BLUE='#306899'; TEAL='#198A85'; ORANGE='#C57A35'; GRAY='#9CA9B4'; DARK='#263445'; PALE='#EDF2F5'
palette=['#306899','#198A85','#C57A35','#8C79A9','#7E9D55','#C17483','#748C9E','#B49A66','#6F758B','#8CB7B7']
A=json.loads((OUT/'analysis.json').read_text())
pool=pd.read_csv(T/'monthly_before_after.csv'); src=pd.read_csv(T/'source_comparison.csv'); sm=pd.read_csv(T/'source_month.csv'); par=pd.read_csv(T/'parent_comparison.csv'); detail=pd.read_csv(T/'newspaper_month_details.csv')
months=pd.period_range('1988-01','2026-09',freq='M').astype(str)
labels={'camden_new_journal':'Camden New Journal','devonport_flagstaff':'Devonport Flagstaff','falls_church_news_press':'Falls Church News-Press','financial_mirror':'Financial Mirror','galway_advertiser':'Galway Advertiser','green_left':'Green Left','indaily':'InDaily','montpelier_bridge':'Montpelier Bridge','northern_rivers_times':'Northern Rivers Times','otago_daily_times':'Otago Daily Times','se_sustainability':'SE · Sustainability','se_earthscience':'SE · Earth Science','python_discourse':'Python Discourse','osm_discourse':'OSM Discourse','straight_dope':'Straight Dope','bluesky':'Bluesky','mastodon_ie':'Mastodon · IE','mastodon_uk':'Mastodon · UK','mastodon_au':'Mastodon · AU','mastodon_us':'Mastodon · US','aussie_zone':'Aussie.zone','lemmy_nz':'Lemmy.nz','feddit_org':'Feddit.org','midwest_social':'Midwest.social'}
parentlabels={'new_journal_enterprises':'New Journal Enterprises','devonport_publishing':'Devonport Publishing','falls_church_news_press':'Falls Church News-Press','financial_mirror_limited':'Financial Mirror Ltd','galway_advertiser_public_web':'Galway public web','green_left':'Green Left','indaily':'InDaily','capital_region_community_media':'Capital Region Community Media','northern_rivers_regional_media':'Northern Rivers Regional Media','otago_daily_times':'Otago Daily Times','Unmapped / applicability unresolved':'未映射 / 适用性未决','stack_exchange':'Stack Exchange','bluesky':'Bluesky','mastodon':'Mastodon','discourse':'Discourse','lemmy':'Lemmy'}
def title(fig, name, sub):
    fig.text(.055,.965,name,fontsize=21,color=DARK,va='top')
    fig.text(.055,.965-34/(fig.get_figheight()*72),sub,fontsize=11,color='#566675',va='top')
def footer(fig, text):
    fig.text(.055,.035,text,fontsize=10,color='#566675',va='bottom',linespacing=1.5)
def save(fig,name,exclude=()):
    fig.canvas.draw()
    require_matplotlib_panel_alignment(fig,json_out=Q/(name+'.alignment.json'),exclude_axes=exclude,strict=True)
    fig.savefig(F/(name+'.png'),dpi=300)
    fig.savefig(Q/(name+'.pdf'))
    fig.savefig(Q/(name+'.svg'))
    plt.close(fig)
def table(ax, columns, rows, widths=None, fontsize=11):
    ax.set_axis_off(); ax.set_xlim(0,1);ax.set_ylim(0,1)
    widths=np.array(widths if widths else [1]*len(columns),float);widths/=widths.sum();x=np.r_[0,np.cumsum(widths)]
    h=1/(len(rows)+1)
    for i,row in enumerate([columns]+rows):
        y=1-(i+1)*h
        ax.add_patch(plt.Rectangle((0,y),1,h,facecolor=DARK if i==0 else ('#F0F4F7' if i%2 else 'white'),edgecolor='none'))
        for j,v in enumerate(row):
            ax.text(x[j]+.012,y+h/2,str(v),ha='left',va='center',fontsize=fontsize,color='white' if i==0 else DARK,linespacing=1.35)
def series(stream, column='after'):
    return pool[pool.stream==stream].set_index('month')[column].reindex(months)

# 1. Definition-aware results table.
fig,ax=plt.subplots(figsize=(15,7));fig.subplots_adjust(left=.055,right=.955,bottom=.22,top=.85)
title(fig,'本轮成果：采集量大幅增长，时间与来源缺口仍在','九小时固定任务 · 2026-10-09 21:34 → 10-10 06:34 AEST · 已完成收尾')
rows=[['Newspaper 完整文章','9,538','16,138','+6,600（69.2%）'],['Social 保留正文身份','42,488','239,402','+196,914（463.5%）'],['Social 可用日期独立正文','42,478','239,392','9 条日期未决；另 1 条非独立正文'],['Newspaper 有记录月份','380 / 465','401 / 465','+21；仍有 64 个月无记录'],['Social 有记录月份','165 / 465','201 / 465','+36；全日历未观察 ≠ 适用期缺失'],['贡献正文的采集来源','报刊 9 / 社交 14','报刊 10 / 社交 14','报刊新增 Galway；社交主要深化既有来源'],['独立保存的校园出版物','9,249','9,249','单独子框架；不冒充原生社交帖子'],['归档恢复率 / 代表性','未建立','仍未建立','历史全集与适用期分母仍有未知']]
table(ax,['指标 / 计数单位','本轮前','本轮后','变化与解释边界'],rows,[3.0,1.8,1.8,4.8],11)
footer(fig,'固定发表区间：1988-01-01—2026-09-21；2026 年 9 月仅截至 21 日。\n“有记录”仅表示至少一条合格文本，不是质量分数、完整档案或采集停止条件。')
save(fig,'01_round_results')

# 2. All 465 month bins shown, with separate within-stream logarithmic scales.
fig,axes=plt.subplots(1,2,figsize=(15,13));fig.subplots_adjust(left=.08,right=.91,bottom=.105,top=.875,wspace=.30)
title(fig,'Coverage：逐月查看已有文本与未观察区间','颜色表示当月数量（各自对数刻度）；0 单独显示。逐年逐月完整展示，不以两篇为合格线。')
cbaxes=[]
for ax,stream,cmap,total in zip(axes,['newspaper','social'],['Blues','GnBu'],[16138,239392]):
    arr=np.full((39,12),np.nan)
    for m,v in series(stream).items():arr[int(m[:4])-1988,int(m[-2:])-1]=v
    cm=plt.get_cmap(cmap).copy();cm.set_under('#DADFE5');cm.set_bad('#8D99A5')
    im=ax.imshow(np.where(arr==0,.1,arr),aspect='auto',cmap=cm,norm=colors.LogNorm(vmin=1,vmax=np.nanmax(arr)))
    ax.set_xticks(range(12),range(1,13));ax.set_yticks(range(39),range(1988,2027));ax.tick_params(axis='y',labelsize=9)
    ax.set_title(('Newspaper · 401 / 465 月' if stream=='newspaper' else 'Social · 201 / 465 月')+f'\n正文 n = {total:,}',loc='left')
    ax.set_xlabel('发表月份');ax.set_ylabel('发表年份')
    ax.set_xticks(np.arange(-.5,12,1),minor=True);ax.set_yticks(np.arange(-.5,39,1),minor=True);ax.grid(which='minor',color='white',linewidth=.4);ax.tick_params(which='minor',length=0)
    ax.text(8,38,'*',ha='center',va='center',color='white',fontsize=12)
    bbox=ax.get_position();cax=fig.add_axes([bbox.x1+.01,bbox.y0,.012,bbox.height]);fig.colorbar(im,cax=cax,label='当月正文数');cbaxes.append(cax)
footer(fig,'浅灰：未观察到合格文本；深灰：超出固定区间；* 2026-09 为部分月。Social 的成立前 / 未知历史范围需按来源另判，浅灰不等于没有公众表达。\nNewspaper 最长连续空白仍为 1988-01—1991-01（37 个月）。计数不等于完整恢复率。')
save(fig,'02_monthly_coverage',cbaxes)

# 3. Distribution and source composition explain the 2026 concentration.
fig,axes=plt.subplots(2,2,figsize=(16,10));fig.subplots_adjust(left=.08,right=.965,bottom=.13,top=.85,hspace=.55,wspace=.23)
title(fig,'Distribution：增量改善部分历史区间，近期来源偏重仍明显','上：全日历月度数量；下：2026 年逐月来源构成。零值全部保留，未做平滑或削峰。')
for col,stream,colr in [(0,'newspaper',BLUE),(1,'social',TEAL)]:
    ax=axes[0,col];before=series(stream,'before');after=series(stream)
    ax.plot(range(465),after,color=colr,lw=1.1,label='本轮后');ax.plot(range(465),before,color=GRAY,lw=.9,label='本轮前')
    ax.set_yscale('symlog',linthresh=1);ax.set_ylabel('正文 / 月（symlog）');ax.set_xticks([0,84,204,324,456],['1988','1995','2005','2015','2026']);ax.legend(loc='upper left',fontsize=10)
    ax.set_title(('a  Newspaper' if col==0 else 'b  Social')+' · 完整日历',loc='left')
    ax=axes[1,col];g=sm[(sm.stream==stream)&sm.month.str.startswith('2026')].pivot_table(index='month',columns='source_id',values='bodies',aggfunc='sum',fill_value=0).reindex([f'2026-{i:02}' for i in range(1,10)],fill_value=0)
    ranked=g.sum().sort_values(ascending=False).index; keep=list(ranked[:4]); g2=g[keep].copy()
    if len(ranked)>4:g2['其他来源']=g.drop(columns=keep).sum(axis=1)
    bottom=np.zeros(9)
    for i,k in enumerate(g2):ax.bar(np.arange(9),g2[k],bottom=bottom,width=.74,color=palette[i],label=labels.get(k,k));bottom+=g2[k].values
    ax.set_xticks(range(9),['1','2','3','4','5','6','7','8','9*']);ax.set_xlabel('2026 年发表月份');ax.set_ylabel('正文数');ax.legend(loc='upper left',fontsize=8.5,ncol=1)
    ax.set_ylim(0,max(bottom)*1.65)
    ax.set_title(('c  Newspaper · 2026 占全部 5.2%' if col==0 else 'd  Social · 2026 占全部 58.1%'),loc='left')
footer(fig,'Social：2026 占比 59.6% → 58.1%；部分 9 月占比 24.0% → 13.2%。这表示采集构成变化，不是公众表达强度变化。\nNewspaper 的 2026 来源由主要依靠 Flagstaff 扩展到 Northern Rivers Times，但当前仍全部来自 AU 两个来源。* 9 月不完整。')
save(fig,'03_distribution_and_2026')

# 4. Do not merge incompatible parent dimensions into a single count.
fig,axes=plt.subplots(2,2,figsize=(16,11));fig.subplots_adjust(left=.24,right=.97,bottom=.12,top=.85,wspace=.62,hspace=.5)
title(fig,'Parent source：父层级必须分开统计','左上是报刊采集来源族；其他面板分别为社交平台网络、软件和服务器实例。共有软件不代表共有所有者。')
for ax,stream,dimension,caption in [(axes[0,0],'newspaper','acquisition_family','a  Newspaper · 10 个有正文来源族'),(axes[0,1],'social','platform_network','b  Social · 平台网络关系'),(axes[1,0],'social','software_family','c  Social · 共享软件关系'),(axes[1,1],'social','instance','d  Social · 实例 / 服务器关系')]:
    g=par[(par.stream==stream)&(par.dimension==dimension)].sort_values('after')
    labs=[parentlabels.get(v,v.replace('_',' ')) for v in g.parent]
    ax.barh(range(len(g)),g['share']*100,color=[GRAY if v.startswith('Unmapped') else (BLUE if stream=='newspaper' else TEAL) for v in g.parent],height=.6)
    ax.set_yticks(range(len(g)),labs,fontsize=8.5);ax.set_xlabel('占本流全部可用日期正文（%）');ax.set_xlim(0,max(g['share'])*125+3)
    for i,v in enumerate(g['share']):ax.text(v*100+.6,i,f'{v:.1%}',va='center',fontsize=9)
    ax.set_title(caption,loc='left',fontsize=12)
footer(fig,'分母：Newspaper 16,138；Social 239,392。不同关系维度不可相加；“未映射”同时保留未知 / 尚未判断适用性。\n报刊来源族是登记的采集关系，未升级为已验证的历史出版所有权；当前规范化 publisher_organization 映射仍未完成。仅辅助解释，不影响抓取。')
save(fig,'04_parent_source_dimensions')

# 5. Per-source coverage table with observed rather than fabricated archive denominators.
fig,axes=plt.subplots(1,2,figsize=(18,10));fig.subplots_adjust(left=.04,right=.97,bottom=.14,top=.845,wspace=.06)
title(fig,'来源分析表：本轮加深了哪些来源、哪些时间段？','月份为至少有一条合格文本的不同发表月；起止为已采样本范围，不是来源成立时间或完整档案范围。')
for ax,stream,head in zip(axes,['newspaper','social'],['Newspaper','Social']):
    g=src[src.stream==stream].sort_values('after_bodies',ascending=False)
    rows=[[labels.get(x.source_id,x.source_id),f'{x.after_bodies:,}',f'+{x.added_bodies:,}',f'{x.before_months}→{x.after_months}',f'{x.first_observed_month}\n{x.last_observed_month}'] for x in g.itertuples()]
    table(ax,[head,'正文数','本轮增量','有记录月','观察起止'],rows,[3.65,1.25,1.4,1.15,1.35],9.5)
footer(fig,'Social 14 个贡献来源保持不变；Mastodon 四实例合计 87,566 条，全部落在 2026 年近期。OSM 已覆盖 199 个不同月份，是此次历史时间拓展的重要来源。\n完整恢复率仍未知：原生页面 / 已见 ID 清单不是天然的完整历史分母。地理标签为来源机会分层，不推断社交作者国籍。')
save(fig,'05_source_coverage_tables')

# 6. Density distribution and within-month breadth diagnose persistent sparse cells.
fig,axes=plt.subplots(2,2,figsize=(15,10));fig.subplots_adjust(left=.08,right=.97,bottom=.13,top=.85,wspace=.25,hspace=.47)
title(fig,'覆盖深度：少量记录和单一来源月份仍需显式呈现','以下指标只描述已观察语料，不构成最低质量门槛、配额、来源优先级或停止条件。')
bins=[-1,0,1,2,9,49,float('inf')]; names=['0','1','2','3–9','10–49','50+']
for col,stream in enumerate(['newspaper','social']):
    ax=axes[0,col]
    for j,c in enumerate(['before','after']):
        counts=pd.cut(series(stream,c),bins,labels=names).value_counts(sort=False).reindex(names)
        rect=ax.bar(np.arange(6)+(j-.5)*.35,counts,width=.34,color=GRAY if j==0 else (BLUE if col==0 else TEAL),label='本轮前' if j==0 else '本轮后')
        ax.bar_label(rect,padding=3,fontsize=9)
    ax.set_ylim(0,350);ax.set_xticks(range(6),names);ax.set_ylabel('月份数 / 465');ax.set_xlabel('每月正文数');ax.legend(fontsize=10);ax.set_title(('a  Newspaper' if col==0 else 'b  Social')+' · 月度数量分布',loc='left')
    ax=axes[1,col];g=sm[(sm.stream==stream)&(sm.bodies>0)].groupby('month').source_id.nunique().reindex(months,fill_value=0)
    ax.plot(range(465),g,color=BLUE if col==0 else TEAL,lw=1.3);ax.fill_between(range(465),g,color=BLUE if col==0 else TEAL,alpha=.10)
    ax.set_xticks([0,84,204,324,456],['1988','1995','2005','2015','2026']);ax.set_ylim(0,15);ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True));ax.set_ylabel('当月贡献采集来源数');ax.set_title(('c  Newspaper' if col==0 else 'd  Social')+' · 月内来源构成',loc='left')
footer(fig,'Newspaper：恰好两篇的月份 157 → 152；247 / 401 个有记录月份仅由一个采集来源贡献。数量扩张尚未消除稀疏结构。\n来源数不代表独立作者数或独立所有者数；旧“两篇”指标仅作历史诊断，其评估权重为零。')
save(fig,'06_coverage_depth')

# 7. Explicit structural states and remaining uncertainty.
fig,ax=plt.subplots(figsize=(16,9));fig.subplots_adjust(left=.055,right=.965,bottom=.18,top=.85)
title(fig,'质量与复杂性分析表：保留噪声，区分计数层级','数据完整性检查通过，并不代表日期解释、来源独立性或社会代表性全部解决。')
rows=[['Newspaper 待处理记录','76','正文边界、访问、日期等问题保持显式；未删除原始证据'],['Newspaper 完全文本重合候选','94 组 / 198 个 ID','候选不是已证实同一作品；保留 ID、版本与转载关系'],['Social 类型化原生实体','268,343','含正文、上下文、包装、墓碑等；不可全算独立发言'],['Social 实体版本 / 关系边','275,580 / 505,508','版本和回复 / 引用关系不增加独立正文数'],['Social 附件元数据','91,409','附件记录不等于已下载媒体文件或新正文'],['Social 原生单位中无正文的包装','8,212 repost；385 context','按 native_unit 分类；与版本状态表的口径不同'],['Social 本轮关系端点未解析','107,335 / 417,417（25.7%）','仅本轮导出的关系边；不等于全库关系的未解析比例'],['Social 日期映射未决','9','6 条 Bluesky + 3 条 Stack Exchange；从可用日期视图分开'],['Social 作者角色未知','239,181 / 239,402（99.91%）','可访问不等于普通公众；不得从平台或服务器推断作者角色'],['正文 / raw 映射与数据库完整性','两路最终检查通过','重用旧验收，只核验新增批次；不是言论真实性认证'],['运行异常与可追溯限制','间距、元数据 stop、计时延迟','OlivePress 延迟偏短已修复；协调 H+5 实际迟到约 2 小时']]
table(ax,['检查对象','当前结果','如何解释 / 后续处理'],rows,[3.4,4.0,7.3],10.5)
footer(fig,'“零跨实体 publication_key 重复”仅说明当前已建立的键未重叠，不能证明全语料已去重。社交跨实例同源、迁移与版本关系仍需证据映射。\n所有数量来自最终元数据，未重扫正文；未执行气候相关性、情绪或 fear 标签，也未按噪声、长度或主题筛除。')
save(fig,'07_quality_and_native_complexity')

# 8. Concrete next-round priorities, independent of collection score or fixed time quota.
fig,ax=plt.subplots(figsize=(16,9));fig.subplots_adjust(left=.055,right=.965,bottom=.20,top=.85)
title(fig,'下一轮：让新增采集同时改善历史证据与可解释性','按具体缺口、可行来源和原生游标安排工作；继续增量 ELT，保留真实峰值与噪声。以下为计划，尚未启动新任务。')
rows=[['报刊早期历史','1988-01—1991-01 仍为 37 月空白','优先准备有明确该时期范围的合法文字档案路线；记录访问 / OCR / PDF 限制'],['报刊稀疏月份','152 月恰好两篇；247 月仅单来源','沿可用原生索引持续回填；分别呈现历史缺口与既有来源增量，不设达到数即停'],['报刊地域 / 来源','新增 82.0% 来自两家 US 来源','保留这批产出；按未解决 UK / EU / NZ 路线问题推进，不强制地域数量相等'],['社交历史分页','Mastodon 四实例仅观察到 2026 年近期','从已保存 max_id / cursor 向旧记录推进；延续论坛、Q&A 和上下文采集'],['社交来源框架','14 个贡献来源未增加；角色 99.91% 未知','增加有证据的来源框架、原生账户角色元数据；未知保留，不据此拒收'],['身份 / 日期 / 父关系','9 个日期未决；所有权映射尚不充分','保存可复查的迁移、转载、跨实例 URI 和时间关系；不做未经证实的硬合并'],['湖仓增量落地','SQLite 当前单写入流程已完成大批量采集','完善原始对象清单、操作日志、提交后元数据与分析快照；服务端数据库迁移另行验证'],['协调与收尾','H+5 触发延迟；一次上下文换窗','监测“预定时刻与实际触发”偏差；限制重复状态输出，使用紧凑交接与原截止']]
table(ax,['工作面','当前证据','下一步动作'],rows,[2.05,4.5,8.4],10.5)
footer(fig,'资源：最终共享快照约 5.99 / 30 GB；social 终端导出前约 3.95 / 8 GB（两者观测时点不同）。下一轮仍需实时完整操作容量检查。\n新轮次需独立固定时限；本轮已到期，不自动续期。父来源统计和覆盖权重仅用于解释；时间不按固定百分比分配。')
save(fig,'08_next_round_plan')

# 9. Applicable periods are not the same as the full calendar denominator.
fig,axes=plt.subplots(1,2,figsize=(17,9));fig.subplots_adjust(left=.15,right=.965,bottom=.21,top=.83,wspace=.32)
title(fig,'Coverage 分母边界：没有记录不只有一种原因','Social 区分可用日期、适用但未观察、历史未知与结构不适用；Newspaper 保留地域机会层的真实差异。')
era=pd.read_csv(T/'social_era_states.csv');social_ids=list(src[src.stream=='social'].sort_values('after_bodies').source_id)
order=['observed_usable_dated_body','applicable_unobserved','historical_scope_unknown','source_access_blocked_or_unresolved','structurally_inapplicable_under_documented_platform_or_site_lower_bound']
names=['已有日期正文','适用但未观察','历史范围未知','访问受限 / 未决','结构不适用']
cs=[TEAL,ORANGE,'#B7CBD9','#9B8BAA','#DEE2E6'];ax=axes[0];left=np.zeros(len(social_ids))
for state,name,color in zip(order,names,cs):
    vals=era[era.state==state].set_index('source_id').months.reindex(social_ids,fill_value=0).to_numpy()
    ax.barh(range(len(social_ids)),vals,left=left,color=color,height=.7,label=name);left+=vals
assert (left==465).all()
ax.set_yticks(range(len(social_ids)),[labels[x] for x in social_ids],fontsize=9);ax.set_xlim(0,465);ax.set_xticks([0,100,200,300,400,465]);ax.set_xlabel('完整研究日历的 465 个月');ax.set_title('a  Social · 14 个已贡献来源的期间状态',loc='left',fontsize=12)
handles,labs=ax.get_legend_handles_labels();fig.legend(handles,labs,loc='lower left',bbox_to_anchor=(.15,.10),ncol=5,fontsize=9,frameon=False)
r=pd.read_csv(T/'newspaper_region.csv');rows=[[x.region.replace('EU/Europe excluding UK','EU / Europe (excl. UK)'),f'{x.articles:,}',f'{x.observed_months} / 465',str(x.zero_months)] for x in r.itertuples()]
table(axes[1],['报刊机会分层','文章数','有记录月','无记录月'],rows,[3.25,1.2,1.5,1.2],10)
axes[1].set_title('b  Newspaper · 地域机会分层',loc='left',fontsize=12)
footer(fig,'Social 图仅展示已贡献正文的 14 个来源，完整机会登记含 32 个条目；这些状态来自当前登记，未知不强行算成缺失或不适用。\n结构不适用取已记录的平台 / 站点下界，不等于证明该来源历史已全部恢复。地域机会标签不推断作者国籍，不要求各国数量相等。')
save(fig,'09_coverage_denominator_limits')
print('Rendered nine PNG figures and internal QA PDFs.')
