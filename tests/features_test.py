#!/usr/bin/env python3
"""Regression tests for the dashboard polish features: channel chips, hub-limit ticks, active glow,
paired channels, gyro dead zone, hub-lost banner, board lock and board history.
Run:  python3 tests/features_test.py"""
import os, sys, math
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import widgets_test as W

fails = []
def check(name, ok, info=''):
    print(('PASS ' if ok else 'FAIL ') + name + ('' if ok else ' ' + str(info)))
    if not ok: fails.append(name)

def main():
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg, errs = W.boot(b, {'width': 900, 'height': 400}, True, [
            {'k': 'n', 'c': 0, 'w': 1}, {'k': 'f', 'c': 1, 'w': 1}, {'k': 'i', 'c': 1, 'w': 1},
            {'k': 'st', 'c': 4, 'w': 1, 'gy': 1, 'gz': 8, 'gs': 30}, {'k': 's', 'c': 2, 'w': 1}])
        ev = pg.evaluate
        # chips
        chip = ev("document.querySelector('.bdw-h .bdw-chip')&&document.querySelector('.bdw-h .bdw-chip').textContent")
        nm = ev("document.querySelector('.bdw-h span').textContent")
        check('title: channel letter chip + channel name', chip == 'A' and len(nm) > 1, (chip, nm))
        # hub-limit ticks
        tick = "[...document.querySelectorAll('svg.mtr[data-k=%s] line[stroke=\"#fff\"]')].filter(l=>l.getAttribute('visibility')==='visible').length"
        ev("__t.C.limit=100;__t.paintBoard()"); pg.wait_for_timeout(200)
        t100 = (ev(tick % 'f'), ev(tick % 'i'))
        ev("__t.C.limit=70;__t.paintBoard()"); pg.wait_for_timeout(200)
        t70 = (ev(tick % 'f'), ev(tick % 'i'))
        check('meters: no hub-limit tick at 100%, two ticks at 70%', t100 == (0, 0) and t70 == (2, 2), (t100, t70))
        ev("__t.C.limit=100;__t.paintBoard()")
        # connecting is refused while editing
        ev("__t.S.connected=false;document.querySelector('#dbEdit').disabled=false;document.querySelector('#dbEdit').click()")
        pg.wait_for_timeout(200)
        ev("document.querySelector('#link').click()"); pg.wait_for_timeout(200)
        edit_conn = ev("__t.S.connected")
        ev("document.querySelector('#dbEdit').click()"); pg.wait_for_timeout(200)
        ev("document.querySelector('#link').click()"); pg.wait_for_timeout(200)
        done_conn = ev("__t.S.connected")
        check('connect: refused while editing, allowed after Done', edit_conn is False and done_conn is True, (edit_conn, done_conn))
        ev("document.querySelector('#dbEdit').disabled=false")
        # paired channels
        ev("(()=>{const o=__t.C.board.find(o=>o.k==='n');o.pc=1;o.pi=1;__t.C.board=__t.cleanBoard(__t.C.board);__t.syncBoard()})()")
        kept = ev("(()=>{const o=__t.C.board.find(o=>o.k==='n');return [o.pc,o.pi]})()")
        ev("__t.rt.t[0]=60;__t.paintBoard()"); p1 = ev("__t.rt.t[1]")
        ev("__t.rt.t[0]=0;__t.paintBoard()"); p2 = ev("__t.rt.t[1]")
        check('paired channel: kept by cleanBoard, mirrors opposite, follows to 0', kept == [1, 1] and p1 == -60 and p2 == 0, (kept, p1, p2))
        # gyro dead zone / sensitivity
        def tilt(deg):
            r = math.radians(deg); ev("window.onTilt(%.3f,%.3f,0)" % (-9.8 * math.sin(r), 9.8 * math.cos(r)))
        stk = lambda t: ev("""(()=>{const k=document.querySelector('.stk'),r=k.getBoundingClientRect();
          k.dispatchEvent(new PointerEvent('%s',{bubbles:true,pointerId:55,clientX:r.left+r.width/2,clientY:r.top+r.height*.2}))})()""" % t)
        tilt(0); stk('pointerdown'); pg.wait_for_timeout(300)
        tilt(5); pg.wait_for_timeout(400); small = ev("__t.rt.t[4]")
        tilt(20); pg.wait_for_timeout(400); big = ev("__t.rt.t[4]")
        tilt(-30); pg.wait_for_timeout(400); full = ev("__t.rt.t[4]")
        stk('pointerup'); pg.wait_for_timeout(500)
        check('gyro: 5 deg is inside the 8 deg dead zone, 20 deg steers, 30 deg is full lock',
              small == 0 and abs(big) > 20 and abs(full) >= 95, (small, big, full))
        # settings keep gz/gs
        gz = ev("(()=>{const o=__t.cleanBoard([{k:'st',c:0,gz:5,gs:45},{k:'st',c:1,gz:3}]);return [o[0].gz,o[0].gs,o[1].gz,o[1].gs]})()")
        check('gyro settings survive cleanBoard (3 deg = default)', gz == [5, 45, None, None], gz)
        # hub lost banner
        ev("window.onHubState('ready')"); pg.wait_for_timeout(100)
        a = ev("[document.getElementById('lostBanner').hidden, document.documentElement.classList.contains('nolink')]")
        ev("window.onHubState('error')"); pg.wait_for_timeout(100)
        b2 = ev("[document.getElementById('lostBanner').hidden, document.documentElement.classList.contains('nolink')]")
        ev("window.onHubState('ready')"); pg.wait_for_timeout(100)
        c2 = ev("[document.getElementById('lostBanner').hidden, document.documentElement.classList.contains('nolink')]")
        check('hub lost: banner + dimmed widgets, cleared when the hub is back', a == [True, False] and b2 == [False, True] and c2 == [True, False], (a, b2, c2))
        # lock
        pg.click('#dbLock'); pg.wait_for_timeout(200)
        lk = ev("[window.__lock(), getComputedStyle(document.querySelector('#cols')).pointerEvents, document.getElementById('lockPad').hidden]")
        box = pg.locator('#lockPad').bounding_box()
        pg.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2); pg.mouse.down(); pg.wait_for_timeout(400)
        still = ev("window.__lock()"); pg.mouse.up(); pg.wait_for_timeout(100)
        pg.mouse.down(); pg.wait_for_timeout(1300); pg.mouse.up(); pg.wait_for_timeout(200)
        un = ev("window.__lock()")
        check('lock: board locked, short press keeps it locked, 1 s hold unlocks', lk == [True, 'none', False] and still and not un, (lk, still, un))
        # board history
        for f in ('localStorage.removeItem("mk6.boardsnaps")',):
            ev(f)
        ev("__snap.take()")
        ev("(()=>{__t.C.board.pop();__t.save();__t.syncBoard()})()"); ev("__snap.take()")
        n = ev("__snap.list().length")
        rows = ev("document.querySelectorAll('#snapList .snaprow').length")
        check('board history: keeps copies when the board changes', n == 2 and rows == 2, (n, rows))
        before = ev("__t.C.board.length")
        ev("document.querySelectorAll('#snapList .snaprow button')[1].click()"); pg.wait_for_timeout(200)
        after = ev("__t.C.board.length")
        check('board history: restore brings the older board back', after == before + 1, (before, after))
        # ---- main screen: slider upgrades + joystick axis bars
        ev("document.querySelector('#lStd').click()"); pg.wait_for_timeout(300)
        ev("__t.S.connected=true;__t.C.ch[0].kind='slider';__t.C.ch[0].stp=10;__t.rt.t[0]=0")
        tap = "(s)=>{const b=document.querySelector(s);b.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true,pointerId:7}));b.dispatchEvent(new PointerEvent('pointerup',{bubbles:true,pointerId:7}))}"
        pg.evaluate(tap, '.stp.inc'); pg.wait_for_timeout(100)
        a10 = ev("__t.rt.t[0]")
        pg.evaluate(tap, '.stp.dec'); pg.evaluate(tap, '.stp.dec'); pg.wait_for_timeout(100)
        b10 = ev("__t.rt.t[0]")
        check('step size: arrows move by the chosen step (10)', a10 == 10 and b10 == -10, (a10, b10))
        ev("document.querySelector('.pre .btn[data-v=\"50\"]').click()"); pg.wait_for_timeout(100)
        pr = ev("[__t.rt.t[0], document.querySelector('.pre .btn[data-v=\"50\"]').classList.contains('on')]")
        check('preset chip sets the value and highlights', pr == [50, True], pr)
        gone = ev("[...document.querySelectorAll('.adv label')].map(l=>l.textContent).filter(x=>/Magnet|Slider minimum|Slider maximum/.test(x)).length+document.querySelectorAll('.limz,.adv input.lo,.adv input.hi,.adv input.mag').length")
        check('channel settings: magnet, slider minimum and maximum are gone', gone == 0, gone)
        # axis bars
        ev("document.querySelector('#lJoy').click()"); pg.wait_for_timeout(300)
        pg.locator('.padbox .pad').first.scroll_into_view_if_needed(); pg.wait_for_timeout(200)
        pb = pg.locator('.padbox .pad').first.bounding_box()
        cx, cy = pb['x'] + pb['width'] / 2, pb['y'] + pb['height'] / 2
        pg.mouse.move(cx, cy); pg.mouse.down(); pg.mouse.move(cx + pb['width'] * 0.3, cy - pb['height'] * 0.3, steps=4); pg.wait_for_timeout(150)
        txt = ev("[...document.querySelectorAll('.padbox')[0].querySelectorAll('.axb output')].map(o=>+o.textContent)")
        pg.mouse.up(); pg.wait_for_timeout(150)
        check('axis bars: show drive/steer values, no peak marker', txt[0] > 20 and txt[1] > 20 and not ev("document.querySelector('.abp')"), txt)
        check('no white chasing marker on the slider', ev("!document.querySelector('.track .act')"), '')
        # A dial selector reaches its full output
        pg2, errs2 = W.boot(b, {'width': 900, 'height': 500}, True, [{'k': 'rs', 'w': 1, 'p': 100, 'ns': 6, 's': 0, 'rt': 0.3}])
        pg2.evaluate("__t.C.ch[0].kind='slider';__t.rt.t[0]=0")
        kb = pg2.locator('.dialk').first.bounding_box()
        pg2.mouse.move(kb['x'] + kb['width'] / 2, kb['y'] + kb['height'] / 2); pg2.mouse.down(); pg2.wait_for_timeout(1100); pg2.mouse.up(); pg2.wait_for_timeout(1500)
        sel = pg2.evaluate("__t.rt.t[0]")
        check('selector reaches its full output', sel == 100, sel)
        check('no script errors (selector)', not errs2, errs2)
        # joystick card: swipe to the next pair of channels
        pg3, errs3 = W.boot(b, {'width': 1000, 'height': 447}, True, [{'k': 'j', 'c': 0, 'd': 1, 'm': 'axis', 'w': 2, 'sw': 1}])
        kept = pg3.evaluate("__t.C.board[0].sw")
        dots = pg3.evaluate("document.querySelectorAll('.bdw .dialdots i').length")
        check('joystick swipe: option kept, one dot per pair', kept == 1 and dots >= 2, (kept, dots))
        fitchk = pg3.evaluate("(()=>{const w=document.querySelector('.bdw');const p=w.querySelector('.pad').getBoundingClientRect(),d=w.querySelector('.dialdots').getBoundingClientRect(),c=w.getBoundingClientRect();return [p.bottom<=d.top+1, d.bottom<=c.bottom+1]})()")
        check('joystick swipe: pad leaves room so the dots are not clipped', fitchk == [True, True], fitchk)
        pg3.evaluate("__t.rt.t[0]=40;__t.rt.t[1]=-30")
        hb = pg3.locator('.bdw .bdw-h').first.bounding_box()
        y = hb['y'] + hb['height'] / 2
        pg3.mouse.move(hb['x'] + hb['width'] - 10, y); pg3.mouse.down(); pg3.mouse.move(hb['x'] + 10, y + 2, steps=6); pg3.mouse.up(); pg3.wait_for_timeout(500)
        res = pg3.evaluate("[__t.C.board[0].c,__t.C.board[0].d,__t.rt.t[0],__t.rt.t[1]]")
        check('joystick swipe: left swipe moves to the next pair and zeroes the old one', res == [2, 3, 0, 0], res)
        pb3 = pg3.locator('.bdw .pad').first.bounding_box()
        pg3.mouse.move(pb3['x'] + pb3['width'] - 8, pb3['y'] + pb3['height'] / 2); pg3.mouse.down(); pg3.mouse.move(pb3['x'] + 8, pb3['y'] + pb3['height'] / 2, steps=6); pg3.mouse.up(); pg3.wait_for_timeout(400)
        still = pg3.evaluate("[__t.C.board[0].c,__t.C.board[0].d]")
        check('joystick swipe: dragging on the pad does not change the pair', still == [2, 3], still)
        # three hubs: nine pairs, nine dots, swiping walks through all of them and wraps
        pg3.evaluate("__t.C.hubs=[0,1,2];__t.C.board[0].c=0;__t.C.board[0].d=1;__t.C.board[0].sw=1;__t.save();__t.syncBoard()"); pg3.wait_for_timeout(300)
        n9 = pg3.evaluate("document.querySelectorAll('.bdw .dialdots i').length")
        seen = []
        for _ in range(9):
            hb = pg3.locator('.bdw .bdw-h').first.bounding_box(); y = hb['y'] + hb['height'] / 2
            pg3.mouse.move(hb['x'] + hb['width'] - 10, y); pg3.mouse.down(); pg3.mouse.move(hb['x'] + 10, y + 2, steps=5); pg3.mouse.up(); pg3.wait_for_timeout(350)
            seen.append(pg3.evaluate("[__t.C.board[0].c,__t.C.board[0].d]"))
        check('3 hubs: nine dots, swiping visits every pair once and wraps to the first', n9 == 9 and seen == [[2,3],[4,5],[6,7],[8,9],[10,11],[12,13],[14,15],[16,17],[0,1]], (n9, seen))
        hb = pg3.locator('.bdw .bdw-h').first.bounding_box(); y = hb['y'] + hb['height'] / 2
        pg3.mouse.move(hb['x'] + 10, y); pg3.mouse.down(); pg3.mouse.move(hb['x'] + hb['width'] - 10, y + 2, steps=5); pg3.mouse.up(); pg3.wait_for_timeout(350)
        back = pg3.evaluate("[__t.C.board[0].c,__t.C.board[0].d]")
        fit9 = pg3.evaluate("(()=>{const w=document.querySelector('.bdw'),d=w.querySelector('.dialdots').getBoundingClientRect(),c=w.getBoundingClientRect();return d.left>=c.left&&d.right<=c.right&&d.bottom<=c.bottom+1})()")
        check('3 hubs: right swipe wraps back to the last pair, nine dots fit the card', back == [16, 17] and fit9, (back, fit9))
        pg3.evaluate("__t.C.hubs=[0,-1,-1];__t.C.board[0].c=0;__t.C.board[0].d=1;__t.save();__t.syncBoard()"); pg3.wait_for_timeout(200)
        pg3.evaluate("__t.C.board[0].sw=0;delete __t.C.board[0].sw;__t.syncBoard()"); pg3.wait_for_timeout(300)
        nodots = pg3.evaluate("document.querySelectorAll('.bdw .dialdots i').length")
        check('joystick swipe: off by default, no dots', nodots == 0, nodots)
        check('no script errors (joystick swipe)', not errs3, errs3)

        # ---- LED meter: vertical / horizontal bar ----
        pg5, errs5 = W.boot(b, {'width': 1000, 'height': 447}, True, [{'k': 'i', 'c': 0, 'w': 1}, {'k': 's', 'c': 0, 'w': 1}])
        e5 = pg5.evaluate
        e5("__t.C.limit=100;__t.rt.t[0]=60;__t.paintBoard()"); pg5.wait_for_timeout(400)
        geo = "(()=>{const r=[...document.querySelectorAll('svg.mtr[data-k=i] rect')].filter(x=>x.getAttribute('rx')==='1.5');const g=r.map(x=>[+x.getAttribute('x'),+x.getAttribute('y'),x.getAttribute('fill')]);return g})()"
        v = e5(geo)
        check('LED meter: vertical by default (segments stacked, same x)', len(v) == 20 and len({q[0] for q in v}) == 1 and len({q[1] for q in v}) == 20, v[:2])
        fill = lambda: e5("""(()=>{const s=document.querySelector('svg.mtr[data-k=i]'),R=s.getBoundingClientRect(),b=[...s.querySelectorAll('rect')].filter(r=>r.getAttribute('rx')==='1.5').map(r=>r.getBoundingClientRect());
          const l=Math.min(...b.map(r=>r.left)),r2=Math.max(...b.map(r=>r.right)),tp=Math.min(...b.map(r=>r.top)),bt=Math.max(...b.map(r=>r.bottom));
          const o=s.closest('.bdw').querySelector('.bdw-h output');
          return {w:(r2-l)/R.width,h:(bt-tp)/R.height,val:o?o.textContent:null,col:o?getComputedStyle(o).color:null,white:s.querySelectorAll('text.mv').length,pos:o?o.getBoundingClientRect().right>R.right-30&&o.getBoundingClientRect().bottom<R.top+4:false}})()""")
        fv = fill()
        check('LED meter vertical: no white value inside, small yellow value at top right, bar fills the card', fv['white'] == 0 and fv['val'] == '+60' and fv['col'] == 'rgb(255, 216, 74)' and fv['pos'] and fv['w'] > .6 and fv['h'] > .72, fv)
        e5("__t.wsEdit(__t.C.board.find(o=>o.k==='i'))"); pg5.wait_for_timeout(200)
        has = pg5.locator('#gEdit .wsf', has_text='Bar layout').count()
        pg5.locator('#gEdit .wsf', has_text='Bar layout').locator('.wsc button[data-v="1"]').click()
        pg5.locator('#gEdit .gact button', has_text='Save').click(); pg5.wait_for_timeout(500)
        e5("__t.paintBoard()"); pg5.wait_for_timeout(300)
        h = e5(geo)
        fh = fill()
        check('LED meter horizontal: no white value inside, yellow value up top right, bar fills the width and most of the height', fh['white'] == 0 and fh['val'] == '+60' and fh['pos'] and fh['w'] > .88 and fh['h'] > .45, fh)
        lit = [i for i, q in enumerate(h) if q[2] != 'rgba(150,160,175,.32)']
        check('LED meter: setting "Bar layout" exists and switches to horizontal (one row, left to right)', has == 1 and len(h) == 20 and len({q[1] for q in h}) == 1 and len({q[0] for q in h}) == 20 and e5("__t.C.board[0].hz") == 1, (has, h[:2]))
        check('LED meter horizontal: +60% lights the right side from the centre, none on the left', lit and min(lit) >= 10 and max(lit) == 15, lit)
        e5("__t.rt.t[0]=-30;__t.paintBoard()"); pg5.wait_for_timeout(300)
        h2 = e5(geo); lit2 = [i for i, q in enumerate(h2) if q[2] != 'rgba(150,160,175,.32)']
        check('LED meter horizontal: -30% lights the left side of the centre', lit2 and max(lit2) <= 9 and min(lit2) == 7, lit2)
        g5 = e5("__t.C.board[0].g")
        clip5 = e5("(()=>{const w=document.querySelector('.bdw');return w.scrollHeight>w.clientHeight+2||w.scrollWidth>w.clientWidth+2})()")
        check('LED meter horizontal: card is wide and not clipped', g5 and g5[2] > g5[3] and not clip5, (g5, clip5))
        e5("__t.save();__t.syncBoard()"); pg5.wait_for_timeout(300)
        check('LED meter horizontal: saved layout survives a reload of the board', e5("__t.cleanBoard(JSON.parse(JSON.stringify(__t.C.board)))[0].hz") == 1 and e5("JSON.stringify(__t.cleanBoard(JSON.parse(JSON.stringify(__t.C.board)))[0].g)") == e5("JSON.stringify(__t.C.board[0].g)"))
        check('no script errors (LED meter layout)', not errs5, errs5)

        # horizontal LED bar: value text, bar, scale and pager dots never overlap, at any card height (including with two hubs)
        pg6, errs6 = W.boot(b, {'width': 1000, 'height': 447}, True, [
            {'k': 'i', 'c': 0, 'w': 1, 'hz': 1, 'g': [0, 0, 16, 5]}, {'k': 'i', 'c': 0, 'w': 1, 'hz': 1, 'g': [16, 0, 16, 6]},
            {'k': 'i', 'c': 0, 'w': 1, 'hz': 1, 'g': [0, 6, 16, 7]}, {'k': 'i', 'c': 0, 'w': 1, 'hz': 1, 'ow': 1, 'g': [16, 6, 10, 5]}, {'k': 'i', 'c': 0, 'w': 1, 'hz': 1, 'g': [0, 13, 24, 9]}])
        pg6.evaluate("__t.C.hubs=[0,1,-1];__t.C.limit=100;__t.rt.t[0]=100;__t.save();__t.syncBoard()"); pg6.wait_for_timeout(800)
        bad6 = pg6.evaluate("""(()=>{const out=[];document.querySelectorAll('.bdw').forEach((w,n)=>{
          const s=w.querySelector('svg.mtr'),bx=a=>a.getBoundingClientRect(),R=s.getBoundingClientRect();
          const bar=[...s.querySelectorAll('rect')].filter(r=>r.getAttribute('rx')==='1.5').map(bx);
          const bl=Math.min(...bar.map(r=>r.left)),br=Math.max(...bar.map(r=>r.right)),bt=Math.min(...bar.map(r=>r.top)),bb=Math.max(...bar.map(r=>r.bottom));
          const txt=[...s.querySelectorAll('text')].filter(q=>q.getAttribute('display')!=='none').map(bx),dots=[...s.querySelectorAll('circle')].map(bx);
          const hit=(a)=>a.left<br&&a.right>bl&&a.top<bb-0.5&&a.bottom>bt+0.5;
          if(txt.some(hit)) out.push(n+':text-on-bar');
          if(dots.some(hit)) out.push(n+':dots-on-bar');
          const labs=txt;for(let i=0;i<labs.length;i++)for(let j=i+1;j<labs.length;j++){const a=labs[i],c=labs[j];if(a.left<c.right-1&&c.left<a.right-1&&a.top<c.bottom-1&&c.top<a.bottom-1) out.push(n+':text-overlap')}
          if(txt.concat(dots).some(a=>a.bottom>R.bottom+1||a.top<R.top-1||a.left<R.left-1||a.right>R.right+1)) out.push(n+':outside')});return out})()""")
        check('horizontal LED bar: nothing overlaps or falls outside at any card height', not bad6, bad6)

        # sweep the card height: texts, bar and pager dots never touch, however short the card is
        sw = pg6.evaluate("""(()=>{
          const w=document.querySelector('.bdw:last-child')||document.querySelectorAll('.bdw')[4], box=w.querySelector('.mtr-box'), s=w.querySelector('svg.mtr'), out=[];
          for(let h=26;h<=140;h+=4){
            box.style.cssText='flex:none;height:'+h+'px;position:relative';__t.paintBoard();
            const R=s.getBoundingClientRect(),bx=a=>a.getBoundingClientRect();
            const bar=[...s.querySelectorAll('rect')].filter(r=>r.getAttribute('rx')==='1.5').map(bx);
            const bt=Math.min(...bar.map(r=>r.top)),bb=Math.max(...bar.map(r=>r.bottom)),bl=Math.min(...bar.map(r=>r.left)),br=Math.max(...bar.map(r=>r.right));
            const txt=[...s.querySelectorAll('text')].filter(t=>t.getAttribute('display')!=='none').map(bx),dots=[...s.querySelectorAll('circle')].map(bx);
            const ov=(a,c)=>a.left<c.right-.5&&c.left<a.right-.5&&a.top<c.bottom-.5&&c.top<a.bottom-.5;
            const barR={left:bl,right:br,top:bt,bottom:bb};
            let bad=[];
            if(txt.some(a=>ov(a,barR))) bad.push('text/bar');
            if(dots.some(a=>ov(a,barR))) bad.push('dots/bar');
            if(txt.some(a=>dots.some(d=>ov(a,d)))) bad.push('text/dots');
            for(let i=0;i<txt.length;i++)for(let j=i+1;j<txt.length;j++) if(ov(txt[i],txt[j])) bad.push('text/text');
            if(bad.length) out.push(h+':'+[...new Set(bad)].join(','));
          }return out})()""")
        check('horizontal LED bar: no overlap at any svg height from 26 to 140 px', not sw, sw)
        check('no script errors (horizontal LED bar)', not errs6, errs6)

        # board (non-dashboard) layout: the horizontal LED bar card is half the height of the vertical one
        pg7, errs7 = W.boot(b, {'width': 412, 'height': 900}, False, [
            {'k': 'i', 'c': 0, 'w': 1}, {'k': 'i', 'c': 0, 'w': 1, 'hz': 1}, {'k': 'i', 'c': 0, 'w': 1, 'hz': 1, 'ow': 1}, {'k': 'f', 'c': 0, 'w': 1}])
        pg7.click('#lBoard'); pg7.wait_for_timeout(300)
        pg7.evaluate("__t.rt.t[0]=60;__t.paintBoard()"); pg7.wait_for_timeout(500)
        hh = pg7.evaluate("[...document.querySelectorAll('.bdw')].map(w=>Math.round(w.getBoundingClientRect().height))")
        fit7 = pg7.evaluate("[...document.querySelectorAll('.bdw.hzw')].map(w=>{const s=w.querySelector('svg.mtr').getBoundingClientRect(),b=[...w.querySelectorAll('svg.mtr rect')].filter(r=>r.getAttribute('rx')==='1.5').map(r=>r.getBoundingClientRect());return b.length===20&&Math.min(...b.map(r=>r.top))>=s.top&&Math.max(...b.map(r=>r.bottom))<=s.bottom})")
        check('board layout: horizontal LED bar card is about half the height of the vertical one', hh[0] > 150 and hh[1] <= hh[0] * .58 and hh[2] <= hh[0] * .58 and all(fit7), (hh, fit7))
        check('no script errors (horizontal LED bar size)', not errs7, errs7)

        # ---- Start / stop push button (hub link): long press, vibrate, then the LEDs change one by one ----
        pg8, errs8 = W.boot(b, {'width': 1000, 'height': 447}, True, [{'k': 'ps', 'w': 1, 'g': [0, 0, 9, 12]}, {'k': 's', 'c': 0, 'w': 1, 'g': [9, 0, 12, 4]}])
        e8 = pg8.evaluate
        e8("__t.S.connected=false;__t.hubMsgSet('');window.__vib=[];navigator.vibrate=function(x){window.__vib.push(x);return true};0")
        pg8.wait_for_timeout(1300)
        ring = lambda: e8("[...document.querySelectorAll('.pssvg > path')].map(p=>p.getAttribute('stroke'))")
        cnt = lambda c: sum(1 for x in ring() if x == c)
        check('start/stop: stopped = all 40 LEDs red after they lit up', len(ring()) == 40 and cnt('#E24B4A') == 40, cnt('#E24B4A'))
        bb = pg8.locator('.psb').bounding_box(); cx, cy = bb['x'] + bb['width'] / 2, bb['y'] + bb['height'] / 2
        pg8.mouse.move(cx, cy); pg8.mouse.down(); pg8.wait_for_timeout(250); pg8.mouse.up(); pg8.wait_for_timeout(300)
        check('start/stop: a short press does nothing (no vibration, still red, hub link unchanged)', not e8("__t.S.connected") and e8("window.__vib.length") == 0 and cnt('#E24B4A') == 40, (e8("__t.S.connected"), e8("window.__vib")))
        pg8.mouse.down(); pg8.wait_for_timeout(350)
        before = (e8("window.__vib.length"), cnt('#E24B4A'), e8("__t.S.connected"))
        pg8.wait_for_timeout(250)
        fired = (e8("window.__vib.length"), e8("__t.S.connected"))
        pg8.wait_for_timeout(120)
        mid_g, mid_r = cnt('#1D9E75'), cnt('#E24B4A')
        pg8.wait_for_timeout(1000)
        check('start/stop: nothing changes before the hold time; then it vibrates and the link turns on', before == (0, 40, False) and fired == (1, True), (before, fired))
        check('start/stop: LEDs turn green one by one, replacing red', 0 < mid_g < 40 and mid_g + mid_r == 40 and cnt('#1D9E75') == 40, (mid_g, mid_r, cnt('#1D9E75')))
        pg8.mouse.up(); pg8.wait_for_timeout(200)
        check('start/stop: holding on does not toggle again', e8("__t.S.connected") and e8("window.__vib.length") == 1)
        pg8.mouse.down(); pg8.wait_for_timeout(750); m2 = (cnt('#E24B4A'), cnt('#1D9E75')); pg8.wait_for_timeout(1000); pg8.mouse.up(); pg8.wait_for_timeout(200)
        check('start/stop: a second long press stops the link and the LEDs go back to red one by one', not e8("__t.S.connected") and cnt('#E24B4A') == 40 and e8("window.__vib.length") == 2, (m2, cnt('#E24B4A')))
        e8("__t.S.estop=true;window.__fr=[]"); fr = []
        for _ in range(14):
            pg8.wait_for_timeout(120); fr.append(sorted(set(ring())))
        yel = [f for f in fr if f == ['#ffd84a']]; off = [f for f in fr if f == ['rgba(150,160,175,.32)']]
        check('start/stop: E-Stop makes the whole ring flash yellow', len(yel) >= 2 and len(off) >= 2, fr[:6])
        e8("__t.S.estop=false"); pg8.wait_for_timeout(300)
        check('start/stop: ring returns to its colour when E-Stop is released', sorted(set(ring())) == ['#E24B4A'], sorted(set(ring())))
        e8("__t.hubMsgSet('Permission denied')"); fr2 = []
        for _ in range(10):
            pg8.wait_for_timeout(120); fr2.append(sorted(set(ring())))
        check('start/stop: a hub fault also flashes yellow', any(f == ['#ffd84a'] for f in fr2) and any(f != ['#ffd84a'] for f in fr2), fr2[:4])
        e8("__t.hubMsgSet('')"); pg8.wait_for_timeout(300)
        op = e8("getComputedStyle(document.querySelector('.bdw.psw')).opacity")
        check('start/stop: the button is not dimmed while the hub is off', op == '1', op)
        # hold time setting
        e8("__t.wsEdit(__t.C.board.find(o=>o.k==='ps'))"); pg8.wait_for_timeout(200)
        pg8.locator('#gEdit .wsc button[data-v="1200"]').click(); pg8.locator('#gEdit .gact button', has_text='Save').click(); pg8.wait_for_timeout(300)
        bb = pg8.locator('.psb').bounding_box(); cx, cy = bb['x'] + bb['width'] / 2, bb['y'] + bb['height'] / 2
        pg8.mouse.move(cx, cy); pg8.mouse.down(); pg8.wait_for_timeout(900); short = e8("__t.S.connected"); pg8.wait_for_timeout(500); longp = e8("__t.S.connected"); pg8.mouse.up()
        check('start/stop: hold time 1.2 s is respected', e8("__t.C.board.find(o=>o.k==='ps').hd") == 1200 and not short and longp, (short, longp))
        cl = e8("__t.cleanBoard([{k:'ps',w:1,hd:77},{k:'ps',w:1,hd:800}])")
        check('start/stop: sanitizer keeps a valid hold time and resets odd ones', cl[0]['hd'] == 500 and cl[1]['hd'] == 800, cl)
        clip8 = e8("(()=>{const w=document.querySelector('.bdw.psw');const s=w.querySelector('.pssvg').getBoundingClientRect(),r=w.getBoundingClientRect();return s.bottom>r.bottom+1||s.right>r.right+1||s.left<r.left-1})()")
        check('start/stop: nothing clipped inside the card', not clip8, clip8)
        check('no script errors (start/stop button)', not errs8, errs8)
        check('no script errors', not errs, errs)
        b.close()
    print('All tests passed' if not fails else '%d failed' % len(fails))
    sys.exit(1 if fails else 0)

if __name__ == '__main__':
    main()
