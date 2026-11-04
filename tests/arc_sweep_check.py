import sys
from playwright.sync_api import sync_playwright
u='file:///home/claude/mouldking-6.0/app/src/main/assets/index.html?mk6test'
JS="""([w,h,nch])=>{const t=__t;t.C.board=t.cleanBoard([{k:'f',c:0,w:1,g:[0,0,w,h]}]);t.save();t.syncBoard();t.rt.t[0]=100;t.paintBoard();
 const svg=document.querySelector('svg.mtr');if(!svg) return 'nosvg';
 const R=e=>{const r=e.getBoundingClientRect();return [r.left,r.top,r.right,r.bottom]};
 const box=R(svg), tx=[...svg.querySelectorAll('text')].filter(e=>e.textContent.trim()), segs=[...svg.querySelectorAll('path')].map(R), dots=[...svg.querySelectorAll('circle')].map(R);
 const items=tx.filter(e=>e.getAttribute('display')!=='none').map(e=>['T:'+e.textContent,R(e)]);
 const ov=(a,b)=>a[0]<b[2]-.5&&b[0]<a[2]-.5&&a[1]<b[3]-.5&&b[1]<a[3]-.5;
 const bad=[];
 for(let i=0;i<items.length;i++){for(let j=i+1;j<items.length;j++) if(!(items[i][0]=='T:+100'&&items[j][0]=='T:%')&&ov(items[i][1],items[j][1])) bad.push(items[i][0]+'x'+items[j][0]);
   dots.forEach(d=>{if(ov(items[i][1],d)) bad.push(items[i][0]+'xdot')});
   segs.forEach((s,q)=>{if((s[2]-s[0])>0&&ov(items[i][1],s)) bad.push(items[i][0]+'xseg'+q)});
   const b=items[i][1];if(b[0]<box[0]-1||b[2]>box[2]+1||b[1]<box[1]-1||b[3]>box[3]+1) bad.push(items[i][0]+' outside')}
 dots.forEach(d=>{if(d[3]>box[3]+1) bad.push('dot outside')});
 segs.forEach(s=>{if(s[3]>box[3]+1||s[0]<box[0]-1||s[2]>box[2]+1) bad.push('seg outside')});
 return [...new Set(bad)].join(',')}"""
def run(vp,dash,sizes,label):
    with sync_playwright() as p:
        b=p.chromium.launch(); pg=b.new_page(viewport=vp); pg.route('http*://**/*',lambda r:r.abort())
        pg.goto(u,wait_until='domcontentloaded'); pg.wait_for_timeout(1200)
        try: pg.click('#gSkip',timeout=1500)
        except: pass
        pg.evaluate("()=>{const t=__t;t.C.layout='board';t.C.dash=%s;document.querySelector('#cols').classList.add('board');t.S.connected=true}"%('true' if dash else 'false'))
        fails=0
        for w,h in sizes:
            r=pg.evaluate(JS,[w,h,1]); pg.wait_for_timeout(120)
            r=pg.evaluate("()=>{const svg=document.querySelector('svg.mtr');return 1}") and pg.evaluate(JS,[w,h,1])
            if r: fails+=1;print(label,w,h,r)
        print(label,'sizes',len(sizes),'fails',fails)
        b.close()
sizes=[(w,h) for w in range(10,41,2) for h in range(8,25,2)]
run({'width':1000,'height':450},True,sizes,'land')
