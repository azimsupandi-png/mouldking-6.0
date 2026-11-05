#!/usr/bin/env python3
"""Regression test for every board widget in MK6 Console.

Run:  python3 tests/widgets_test.py
Needs: python3, playwright with chromium (pip install playwright; playwright install chromium).
It loads app/src/main/assets/index.html in headless Chromium (network blocked) and
exercises each widget kind in the landscape dashboard and in the portrait board.
Exit code 0 = all passed.
"""
import os, sys, json
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
URL = 'file://' + os.path.join(HERE, '..', 'app', 'src', 'main', 'assets', 'index.html') + '?mk6test'

# One sample of every widget kind (channels A..F = 0..5). The board holds at most 16 widgets,
# so the kinds are split over two boards (GROUPS) that are tested one after the other.
GROUP_A = [
    {'k': 's', 'c': 0, 'w': 1, 'hold': True},
    {'k': 'j', 'c': 0, 'd': 1, 'm': 'axis', 'w': 1},
    {'k': 'd', 'c': 0, 'd': 1, 'e': 2, 'f': 3, 'm': 'axis', 'w': 2},
    {'k': 'm', 't': [{'c': 0, 'r': 100}, {'c': 1, 'r': -50}], 'w': 1, 'hold': True},
    {'k': 'l', 'c': 4, 'w': 1},
    {'k': 't', 'c': 2, 'y': 'led', 'p': 80, 'w': 1},
    {'k': 'b', 'c': 3, 'w': 1, 'p': 80},
    {'k': 'g', 'c': 1, 'w': 1},
    {'k': 'n', 'c': 3, 'w': 1},
    {'k': 'k', 'c': 0, 'w': 1},
    {'k': 'st', 'c': 4, 'w': 1},
    {'k': 'lv', 'c': 5, 'w': 1},
]
GROUP_B = [
    {'k': 'a', 'c': 0, 'w': 1, 's': 10},
    {'k': 'y', 'c': 1, 'w': 1, 'p': 75, 'd': 2, 'sc': 1},
    {'k': 'z', 'w': 1, 'a': 15},
    {'k': 'e', 'w': 1},
    {'k': 'w', 'c': 2, 'd': 3, 'w': 1, 'p': 80},
    {'k': 'f', 'c': 0, 'w': 1},
    {'k': 'i', 'c': 1, 'w': 1},
    {'k': 'rs', 'w': 1, 'p': 100, 'ns': 6, 's': 0, 'rt': 0},
    {'k': 'dp', 'c': 3, 'd': 4, 'w': 1, 'm': 'tank', 'p': 70, 'rt': 0},
]
GROUPS = {'A': GROUP_A, 'B': GROUP_B}
EXPECT_SETTINGS = ['s', 'm', 'n', 'g', 'b', 'l', 't', 'y', 'a', 'z', 'w', 'k', 'f', 'i', 'rs', 'st', 'lv', 'dp']

fails = []
def check(name, cond, extra=''):
    print(('PASS ' if cond else 'FAIL ') + name + ((' ' + str(extra)) if (extra != '' and not cond) else ''))
    if not cond: fails.append(name)

def boot(b, vp, dash, samples):
    pg = b.new_page(viewport=vp)
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.route('http*://**/*', lambda r: r.abort())
    pg.goto(URL, wait_until='domcontentloaded'); pg.wait_for_timeout(1200)
    try: pg.click('#gSkip', timeout=1500)
    except Exception: pass
    pg.evaluate("""([dash,samples])=>{const t=__t;t.C.layout='board';t.C.dash=dash;
      if(dash) document.querySelector('#cols').classList.add('board');
      t.C.seq.push({id:'sqT',name:'Demo',loop:false,reps:1,speed:1,delay:0,steps:[{ch:[],dur:1}]});
      t.C.board=t.cleanBoard(samples);t.S.connected=true;t.save();t.syncBoard()}""", [dash, samples])
    pg.wait_for_timeout(700)
    return pg, errs

def run_layout(b, label, vp, dash, samples):
    pg, errs = boot(b, vp, dash, samples)
    n_expected = len(samples)
    n_board = pg.evaluate("__t.C.board.length")
    check(label + ': cleanBoard keeps all %d widgets' % n_expected, n_board == n_expected, n_board)
    n_dom = pg.evaluate("document.querySelectorAll('.bdw').length")
    check(label + ': every widget rendered', n_dom == n_expected, n_dom)
    check(label + ': no script errors on render', not errs, errs)

    # settings dialog: open, change nothing, save, widget count unchanged (edit mode)
    kinds = [o['k'] for o in samples]
    for k in [k for k in EXPECT_SETTINGS if k in kinds]:
        ok = pg.evaluate("""(k)=>{const t=__t,it=t.C.board.find(o=>o.k===k);if(!it||!t.WSPEC[k]) return false;
          t.wsEdit(it);const ov=document.getElementById('gEdit');if(!ov) return false;
          const sv=[...ov.querySelectorAll('button')].find(b=>b.getAttribute('aria-pressed')==='true'&&b.textContent==='Save');
          if(!sv) return false;sv.click();return !document.getElementById('gEdit')}""", k)
        check(label + ': settings popup ' + k, ok)
    check(label + ': settings keep widget count', pg.evaluate("document.querySelectorAll('.bdw').length") == n_expected)

    # persistence: reload from storage keeps the board
    before = pg.evaluate("JSON.stringify(__t.C.board.map(o=>o.k))")
    pg.reload(wait_until='domcontentloaded'); pg.wait_for_timeout(1000)
    try: pg.click('#gSkip', timeout=1000)
    except Exception: pass
    after = pg.evaluate("JSON.stringify(__t.C.board.map(o=>o.k))")
    check(label + ': board survives reload', before == after, (before, after))
    pg.close()

def run_behaviour(b, group):
    pg, errs = boot(b, {'width': 900, 'height': 400}, True, GROUPS[group])
    ev = lambda js: pg.evaluate(js)
    T = lambda i: ev("__t.rt.t[%d]" % i)
    ev("__t.S.connected=true")
    L = 'behaviour ' + group + ': '
    if group == 'A':
        ev("document.querySelector('.gear .tgd[data-g=\"4\"]').click()"); pg.wait_for_timeout(150)
        check(L + 'gear 3 sends 100 to B', T(1) == 100, T(1))
        ev("document.querySelector('.gear .tgd[data-g=\"1\"]').click()"); pg.wait_for_timeout(150)
        check(L + 'gear N stops B', T(1) == 0, T(1))
        # dial: relative drag only. sweep(a0,a1) turns a finger round the knob from angle a0 to a1 (degrees, 0 = top).
        sweep = lambda a0, a1, pid=2: ev("""(()=>{const k=document.querySelector('.dialk'),r=k.getBoundingClientRect(),cx=r.left+r.width/2,cy=r.top+r.height/2,R=r.width/2*.8,a0=%s,a1=%s,n=Math.max(2,Math.ceil(Math.abs(a1-a0)/10));
          const P=a=>({clientX:cx+R*Math.sin(a*Math.PI/180),clientY:cy-R*Math.cos(a*Math.PI/180)});
          k.dispatchEvent(new PointerEvent('pointerdown',Object.assign({bubbles:true,pointerId:%d},P(a0))));
          for(let i=1;i<=n;i++) k.dispatchEvent(new PointerEvent('pointermove',Object.assign({bubbles:true,pointerId:%d},P(a0+(a1-a0)*i/n))));
          k.dispatchEvent(new PointerEvent('pointerup',Object.assign({bubbles:true,pointerId:%d},P(a1))))})()""" % (a0, a1, pid, pid, pid))
        sweep(90, 90); pg.wait_for_timeout(100)
        check(L + 'dial: touching the right edge does not jump', T(3) == 0, T(3))
        sweep(0, 100); pg.wait_for_timeout(100)
        check(L + 'dial: dragging round raises the value from 0', 60 <= T(3) <= 80, T(3))
        sweep(-20, 40); pg.wait_for_timeout(100)
        check(L + 'dial: touching elsewhere continues from the current value', 90 <= T(3) <= 100, T(3))
        sweep(150, 200); pg.wait_for_timeout(100)
        check(L + 'dial: stops at 100, does not wrap round to the other end', T(3) == 100, T(3))
        sweep(180, 100); pg.wait_for_timeout(100)
        check(L + 'dial: turning back lowers it from 100', 0 < T(3) < 100, T(3))
        sweep(0, -250); pg.wait_for_timeout(100)
        check(L + 'dial: stops at -100 the other way', T(3) == -100, T(3))
        ev("__t.rt.t[3]=0")
        hold = lambda: ev("""(()=>{const k=document.querySelector('.dialk'),r=k.getBoundingClientRect(),x=r.left+r.width/2,y=r.top+r.height/2;
          k.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true,pointerId:5,clientX:x,clientY:y}));
          return new Promise(res=>setTimeout(()=>{k.dispatchEvent(new PointerEvent('pointerup',{bubbles:true,pointerId:5,clientX:x,clientY:y}));res(1)},1200))})()""")
        ev("__t.C.board.find(o=>o.k==='n').rt=0;__t.syncBoard()"); pg.wait_for_timeout(300)
        hold(); i0 = T(3); hold(); i1 = T(3)
        check(L + 'dial ramp time 0 switches instantly', i0 == 50 and i1 == 0, (i0, i1))
        ev("delete __t.C.board.find(o=>o.k==='n').rt;__t.syncBoard()"); pg.wait_for_timeout(300)
        ev("""(()=>{const k=document.querySelector('.dialk'),r=k.getBoundingClientRect();window.__hc=[];
          k.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true,pointerId:11,clientX:r.left+r.width/2,clientY:r.top+r.height/2}));
          window.__hc.push(k.classList.contains('holding'));
          k.dispatchEvent(new PointerEvent('pointerup',{bubbles:true,pointerId:11,clientX:r.left+r.width/2,clientY:r.top+r.height/2}));
          window.__hc.push(k.classList.contains('holding'))})()""")
        hc = ev("window.__hc")
        check(L + 'dial shows a hold cue while pressed and clears it on release', hc == [True, False], hc)
        ev("__t.rt.t[3]=0")
        hold(); pg.wait_for_timeout(1000); vm = T(3); pg.wait_for_timeout(2400); v0 = T(3)
        check(L + 'dial on ramps up over 3 s (no jump)', 0 < vm < 50, vm)
        hold(); pg.wait_for_timeout(3400); v1 = T(3)
        hold(); pg.wait_for_timeout(3400)
        check(L + 'dial long press: on, off, on again', v0 == 50 and v1 == 0 and T(3) == 50, (v0, v1, T(3)))
        ev("__t.rt.t[3]=0;__t.C.board.find(o=>o.k==='n').ow=1;__t.C.board.find(o=>o.k==='n').th=1;__t.syncBoard()"); pg.wait_for_timeout(300)
        drag_to = lambda dx: sweep(-135, 135, 7) if dx > 0 else sweep(135, -135, 7)
        drag_to(1); pg.wait_for_timeout(300); ow1 = T(3)
        lit = ev("[...document.querySelectorAll('.dialbox svg path')].filter(p=>p.getAttribute('fill').startsWith('#')).length")
        col = ev("(()=>{const l=[...document.querySelectorAll('.dialbox svg path')].filter(p=>p.getAttribute('fill').startsWith('#'));return l.length?l[0].getAttribute('fill'):''})()")
        drag_to(-1); pg.wait_for_timeout(300); ow0 = T(3)
        check(L + 'dial forward-only: turn forward = high, turn back = low, never negative', 70 <= ow1 <= 100 and 0 <= ow0 <= 30, (ow1, ow0))
        check(L + 'dial forward-only LED ring lights from the start', lit >= 15, lit)
        check(L + 'dial colour theme applies', col.lower() == '#378add', col)
        swp = lambda dx, tgt: ev("""(()=>{const k=document.querySelector('.dialk'),e=%s,r=e.getBoundingClientRect(),y=r.top+14;
          e.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true,pointerId:9,clientX:r.left+r.width/2,clientY:y}));
          e.dispatchEvent(new PointerEvent('pointerup',{bubbles:true,pointerId:9,clientX:r.left+r.width/2+(%s),clientY:y+2}))})()""" % (tgt, dx))
        dc = lambda: ev("__t.C.board.find(o=>o.k==='n').c")
        card = "k.closest('.bdw')"
        c0 = dc(); swp(-90, card); pg.wait_for_timeout(250)
        check(L + 'dial: swipe does nothing while the option is off', dc() == c0 and ev("document.querySelectorAll('.dialdots').length") == 0, dc())
        ev("__t.C.board.find(o=>o.k==='n').sw=1;__t.syncBoard()"); pg.wait_for_timeout(300)
        check(L + 'dial: swipe option shows channel dots', ev("document.querySelectorAll('.dialdots i').length") >= 2)
        swp(-90, card); pg.wait_for_timeout(250); c1 = dc()
        swp(90, card); pg.wait_for_timeout(250); c2 = dc()
        check(L + 'dial: swipe left moves to the next channel, right comes back', c1 != c0 and c2 == c0, (c0, c1, c2))
        c0 = dc(); swp(-90, "document.querySelector('.dialk')"); pg.wait_for_timeout(250)
        check(L + 'dial: swiping on the knob turns it, it does not change channel', dc() == c0, dc())
        ev("delete __t.C.board.find(o=>o.k==='n').sw;__t.syncBoard()"); pg.wait_for_timeout(300)
        ev("(()=>{const o=__t.C.board.find(o=>o.k==='n');delete o.ow;delete o.th;__t.syncBoard()})()"); pg.wait_for_timeout(300)
        ev("__t.rt.t[3]=0")
        ev("__t.rt.t[3]=0")
        ev("""(()=>{const b=document.querySelector('.turbo');['pointerdown','pointerup'].forEach(n=>b.dispatchEvent(new PointerEvent(n,{bubbles:true,pointerId:4})))})()""")
        check(L + 'turbo returns to previous value on release', T(3) == 0, T(3))
        # joystick drives B, slider on the same channel follows
        cx, cy, w = ev("(()=>{const r=document.querySelector('.pad').getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2,r.width]})()")
        pg.mouse.move(cx, cy); pg.mouse.down(); pg.mouse.move(cx + 0.9 * w / 2, cy, steps=5); pg.wait_for_timeout(250)
        check(L + 'joystick right drives B', T(1) > 80, T(1))
        pg.mouse.up(); pg.wait_for_timeout(250)
        check(L + 'joystick returns to 0 on release', T(1) == 0, T(1))
    else:
        ev("__t.rt.t[0]=0;__t.rt.t[1]=0")
        ev("[...document.querySelectorAll('.tgdir')].find(r=>r.querySelector('[data-d=\"0\"]')).querySelector('[data-d=\"1\"]').click()")
        pg.wait_for_timeout(300)
        check(L + 'ramp starts moving B', T(1) != 0, T(1))
        ev("[...document.querySelectorAll('.tgdir')].find(r=>r.querySelector('[data-d=\"0\"]')).querySelector('[data-d=\"0\"]').click()")
        check(L + 'ramp stop returns B to 0', T(1) == 0, T(1))
        # SPDT switch: left side -> output A only, right side -> output B only
        r = ev("(()=>{const e=document.querySelector('.spsw');e.scrollIntoView();const r=e.getBoundingClientRect();return [r.left,r.top,r.width,r.height]})()")
        pg.mouse.click(r[0] + r[2] * 0.15, r[1] + r[3] / 2); pg.wait_for_timeout(150)
        check(L + 'switch left: C=80, D=0', T(2) == 80 and T(3) == 0, (T(2), T(3)))
        pg.mouse.click(r[0] + r[2] * 0.85, r[1] + r[3] / 2); pg.wait_for_timeout(150)
        check(L + 'switch right: C=0, D=80', T(2) == 0 and T(3) == 80, (T(2), T(3)))
        pg.mouse.click(r[0] + r[2] * 0.85, r[1] + r[3] / 2); pg.wait_for_timeout(150)
        check(L + 'switch right again stays on B (2-position)', T(3) == 80, T(3))
        ev("__t.C.board.find(o=>o.k==='w').mid=1;__t.syncBoard()"); pg.wait_for_timeout(300)
        r = ev("(()=>{const r=document.querySelector('.spsw').getBoundingClientRect();return [r.left,r.top,r.width,r.height]})()")
        pg.mouse.click(r[0] + r[2] * 0.85, r[1] + r[3] / 2); pg.wait_for_timeout(150)
        check(L + 'centre-off: tapping the active side turns both off', T(2) == 0 and T(3) == 0, (T(2), T(3)))
        ev("__t.rt.t[2]=0;__t.rt.t[3]=0")
    if group == 'A':
        tx = lambda: ev("[...document.querySelectorAll('.mtr[data-k=k] text')].map(e=>e.textContent).filter(x=>/^Target/.test(x))")
        vis = lambda: ev("[...document.querySelectorAll('.mtr[data-k=k] line')].some(e=>e.getAttribute('stroke-dasharray')&&e.getAttribute('visibility')==='visible')")
        pg.wait_for_timeout(300)
        check(L + 'scope target line is off by default', not vis(), tx())
        ev("(()=>{const o=__t.C.board.find(o=>o.k==='k');o.tg=1;o.tv=-50;__t.syncBoard()})()"); pg.wait_for_timeout(400)
        check(L + 'scope target line on shows the set value', vis() and any('50' in x for x in tx()), tx())
        ev("(()=>{const o=__t.C.board.find(o=>o.k==='k');delete o.tg;delete o.tv;__t.syncBoard()})()"); pg.wait_for_timeout(300)
    if group == 'A':
        # steering wheel: grab the top marker, turn to the right (90 deg = full lock at 180 total), release springs back
        wheel = lambda pid, ax, ay, bx, by, wait: ev("""(()=>{const k=document.querySelector('.stk'),r=k.getBoundingClientRect(),cx=r.left+r.width/2,cy=r.top+r.height/2,R=r.width/2*.8;
          k.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true,pointerId:%d,clientX:cx+R*%s,clientY:cy+R*%s}));
          k.dispatchEvent(new PointerEvent('pointermove',{bubbles:true,pointerId:%d,clientX:cx+R*%s,clientY:cy+R*%s}));
          return new Promise(res=>setTimeout(()=>{res(__t.rt.t[4])},%d))})()""" % (pid, ax, ay, pid, bx, by, wait))
        v_r = wheel(21, 0, -1, 1, 0, 50)
        ang = ev("document.querySelector('.stk').style.transform")
        ev("document.querySelector('.stk').dispatchEvent(new PointerEvent('pointerup',{bubbles:true,pointerId:21}))")
        pg.wait_for_timeout(700)
        check(L + 'wheel: turn right sends about +100 and the wheel rotates', v_r >= 90 and 'rotate' in ang, (v_r, ang))
        check(L + 'wheel: springs back to 0 on release', T(4) == 0, T(4))
        v_l = wheel(22, 0, -1, -1, 0, 50)
        ev("document.querySelector('.stk').dispatchEvent(new PointerEvent('pointerup',{bubbles:true,pointerId:22}))")
        pg.wait_for_timeout(700)
        check(L + 'wheel: turn left sends about -100', v_l <= -90, v_l)
        # gear lever: tap positions top (3), N and bottom (R)
        lever = lambda i: ev("""(()=>{const t=document.querySelector('.lvt'),r=t.getBoundingClientRect(),y=r.top+r.height*(8+%d/4*84)/100,x=r.left+r.width*.6;
          t.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true,pointerId:31,clientX:x,clientY:y}));
          t.dispatchEvent(new PointerEvent('pointerup',{bubbles:true,pointerId:31,clientX:x,clientY:y}))})()""" % i)
        lever(0); pg.wait_for_timeout(300); g3 = T(5)
        lever(2); pg.wait_for_timeout(300); g1 = T(5)
        lever(3); pg.wait_for_timeout(300); gn = T(5)
        lever(4); pg.wait_for_timeout(300); gr = T(5)
        check(L + 'lever: 3, 1, N, R send 100, 35, 0, -50', (g3, g1, gn, gr) == (100, 35, 0, -50), (g3, g1, gn, gr))
        lab = ev("[...document.querySelectorAll('.lvd b')].map(b=>b.textContent).join('')")
        check(L + 'lever: labels top to bottom 3 2 1 N R', lab == '321NR', lab)
        ev("__t.rt.t[4]=0;__t.rt.t[5]=0")
    if group == 'B':
        rsdrag = lambda ang: ev("""(()=>{const k=document.querySelector('.dialk[aria-valuemax="6"]'),r=k.getBoundingClientRect(),x=r.left+r.width/2,y=r.top+r.height/2,a=%s*Math.PI/180;
          const X=x+Math.sin(a)*r.width/2*.9,Y=y-Math.cos(a)*r.width/2*.9;
          k.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true,pointerId:9,clientX:x,clientY:y}));
          k.dispatchEvent(new PointerEvent('pointermove',{bubbles:true,pointerId:9,clientX:X,clientY:Y}));
          k.dispatchEvent(new PointerEvent('pointerup',{bubbles:true,pointerId:9,clientX:X,clientY:Y}))})()""" % ang)
        rshold = lambda: ev("""(()=>{const k=document.querySelector('.dialk[aria-valuemax="6"]'),r=k.getBoundingClientRect(),x=r.left+r.width/2,y=r.top+r.height/2;
          k.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true,pointerId:10,clientX:x,clientY:y}));
          return new Promise(res=>setTimeout(()=>{k.dispatchEvent(new PointerEvent('pointerup',{bubbles:true,pointerId:10,clientX:x,clientY:y}));res(1)},1200))})()""")
        rsel = lambda: ev("__t.C.board.find(o=>o.k==='rs').s")
        rsdrag(-27); pg.wait_for_timeout(200)
        check(L + 'selector: drag selects position C without output', rsel() == 2 and T(2) == 0, (rsel(), T(2)))
        rshold(); pg.wait_for_timeout(200)
        check(L + 'selector: long press switches C on', T(2) == 100, T(2))
        dots = ev("[...document.querySelectorAll('.dialbox svg g')].map(g=>g.children[1].getAttribute('fill')+'|'+(+g.children[1].getAttribute('opacity')).toFixed(2))")
        check(L + 'selector: six small red dots, only the active one bright', all(d.startswith('#E24B4A') for d in dots) and sum(1 for d in dots if float(d.split('|')[1]) > .9) == 1 and len(dots) == 6, dots)
        check(L + 'selector: no letters on the dial', ev("document.querySelectorAll('.dialbox svg text').length") == 0)
        rsdrag(130); pg.wait_for_timeout(200)
        check(L + 'selector: changing position switches the old output off', rsel() == 5 and T(2) == 0 and T(5) == 0, (rsel(), T(2), T(5)))
        rshold(); pg.wait_for_timeout(200)
        check(L + 'selector: F on', T(5) == 100, T(5))
        rshold(); pg.wait_for_timeout(200)
        check(L + 'selector: long press again switches off', T(5) == 0, T(5))
        ns2 = ev("(()=>{const o=Object.assign({},__t.C.board.find(o=>o.k==='rs'),{ns:2});return __t.cleanBoard([o])[0].ns})()")
        check(L + 'selector: 2 positions no longer allowed (falls back to 6)', ns2 == 6, ns2)
        ev("__t.rt.t[0]=60;__t.rt.t[1]=-40"); pg.wait_for_timeout(350)
        arc = ev("document.querySelector('.mtr[data-k=f] .mv').textContent")
        check(L + 'arc meter shows +60', arc == '+60', arc)
        ev("__t.C.board.find(o=>o.k==='f').ow=1;__t.syncBoard()"); pg.wait_for_timeout(300)
        lit_f = lambda: ev("[...document.querySelector('.mtr[data-k=f]').querySelectorAll('path')].slice(0,24).filter(p=>(p.getAttribute('stroke')||'').startsWith('#')).length")
        pg.wait_for_timeout(300); arc_o = ev("document.querySelector('.mtr[data-k=f] .mv').textContent"); n60 = lit_f()
        ev("__t.rt.t[0]=-40"); pg.wait_for_timeout(350)
        arc_n = ev("document.querySelector('.mtr[data-k=f] .mv').textContent"); n0 = lit_f()
        check(L + 'arc forward-only: 60 shows 60 with about 14 of 24 segments lit', arc_o == '60' and 12 <= n60 <= 16, (arc_o, n60))
        check(L + 'arc forward-only: negative shows 0 and nothing lit', arc_n == '0' and n0 == 0, (arc_n, n0))
        ev("delete __t.C.board.find(o=>o.k==='f').ow;__t.syncBoard();__t.rt.t[0]=60"); pg.wait_for_timeout(350)
        lit = ev("Math.max(...[...document.querySelectorAll('.mtr')].map(s=>s.querySelectorAll('rect').length))")
        check(L + 'LED meter drawn (20 segments)', lit >= 20, lit)
        old_t1 = T(1); ev("__t.C.board.find(o=>o.k==='i').ow=1;__t.syncBoard();__t.rt.t[1]=-30"); pg.wait_for_timeout(400)
        n_neg = ev("[...document.querySelector('.mtr[data-k=i]').querySelectorAll('rect')].slice(0,20).filter(r=>(r.getAttribute('fill')||'').startsWith('#')).length")
        ev("__t.rt.t[1]=50"); pg.wait_for_timeout(400)
        n_50 = ev("[...document.querySelector('.mtr[data-k=i]').querySelectorAll('rect')].slice(0,20).filter(r=>(r.getAttribute('fill')||'').startsWith('#')).length")
        txt_50 = ev("document.querySelector('.mtr[data-k=i] .mv').textContent")
        check(L + 'LED meter forward-only: negative lights nothing, 50 lights half, shows 50%', n_neg == 0 and 9 <= n_50 <= 11 and txt_50 == '50%', (n_neg, n_50, txt_50))
        ev("delete __t.C.board.find(o=>o.k==='i').ow;__t.syncBoard();__t.rt.t[1]=%d" % old_t1); pg.wait_for_timeout(300)
        led = ev("[...document.querySelectorAll('.mtr text')].map(t=>t.textContent).filter(t=>/\\u221240%/.test(t)).length")
        check(L + 'LED meter and ramp scope show -40%', led >= 2, led)
        ev("__t.rt.t[1]=0;__t.rt.t[0]=0")
        ev("__t.C.limit=70;__t.rt.t[0]=100"); pg.wait_for_timeout(350)
        arc = ev("document.querySelector('.mtr[data-k=f] .mv').textContent")
        sub = ev("[...document.querySelectorAll('.mtr[data-k=f] text')].map(t=>t.textContent).join('|')")
        check(L + 'arc meter follows the widget value and shows the hub output as hub 70', arc == '+100' and 'hub 70' in sub, (arc, sub))
        ev("__t.C.board.find(o=>o.k==='f').sh=1;__t.syncBoard()"); pg.wait_for_timeout(350)
        arc = ev("document.querySelector('.mtr[data-k=f] .mv').textContent")
        sub = ev("[...document.querySelectorAll('.mtr[data-k=f] text')].map(t=>t.textContent).join('|')")
        check(L + 'hub-output mode shows +70 of 100', arc == '+70' and 'of 100' in sub, (arc, sub))
        ev("delete __t.C.board.find(o=>o.k==='f').sh;__t.syncBoard()")
        ev("__t.C.limit=100;__t.rt.t[0]=0")
        ev("window.__v=0;navigator.vibrate=function(){window.__v++;return true};__t.rt.t[0]=50"); pg.wait_for_timeout(350)
        v0 = ev("window.__v"); ev("__t.rt.t[0]=90"); pg.wait_for_timeout(350)
        v1 = ev("window.__v"); ev("__t.rt.t[0]=95"); pg.wait_for_timeout(350)
        check(L + 'entering the red zone vibrates once', v1 - v0 >= 1 and ev("window.__v") == v1, (v0, v1))
        ev("__t.rt.t[0]=0")
        c0 = ev("__t.C.board.find(o=>o.k==='i').c")
        ev("""(()=>{const s=document.querySelector('.mtr[data-k=i]'),r=s.getBoundingClientRect();
          s.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true,pointerId:7,clientX:r.right-10,clientY:r.top+20}));
          s.dispatchEvent(new PointerEvent('pointerup',{bubbles:true,pointerId:7,clientX:r.left+10,clientY:r.top+22}))})()""")
        pg.wait_for_timeout(300)
        check(L + 'swipe changes the meter channel', ev("__t.C.board.find(o=>o.k==='i').c") != c0)
        ev("__t.C.board.find(o=>o.k==='f').th=1;__t.syncBoard()"); pg.wait_for_timeout(300)
        ev("__t.rt.t[0]=40"); pg.wait_for_timeout(300)
        col = ev("[...document.querySelectorAll('.mtr[data-k=f] path')].map(p=>p.getAttribute('stroke')).find(c=>c&&c[0]==='#')")
        check(L + 'colour theme applies', col == '#378ADD', col)
        ev("__t.rt.t[0]=0")
    if group == 'A':
        ev("__t.rt.t[0]=70"); pg.wait_for_timeout(500)
        pts = ev("document.querySelector('.mtr polyline').getAttribute('points').split(' ').length")
        cy = ev("+document.querySelector('.mtr circle').getAttribute('cy')")
        check(L + 'scope draws 100 points', pts == 100, pts)
        ly = ev("+document.querySelector('.mtr polyline').getAttribute('points').split(' ').pop().split(',')[1]")
        zy = ev("+document.querySelector('.mtr line[stroke-width=\"1.5\"]').getAttribute('y1')")
        check(L + 'scope dot follows output (above zero line, on the trace)', cy < zy and abs(cy - ly) < 0.6, (cy, ly, zy))
        ev("__t.rt.t[0]=0"); pg.wait_for_timeout(1300)
        btns = "document.querySelector('.mtr-ctl').querySelectorAll('button')"
        check(L + 'scope has 5 control buttons', ev(btns + ".length") == 5)
        sz = ev("[...document.querySelectorAll('.mtr-ctl svg')].slice(0,5).map(s=>s.getBoundingClientRect().width+'x'+s.getBoundingClientRect().height)")
        check(L + 'all control symbols have the same size', len(set(sz)) == 1, sz)
        ev(btns + "[0].click()"); pg.wait_for_timeout(250)
        lab = ev("[...document.querySelector('.mtr').querySelectorAll('text')].map(t=>t.textContent).join('|')")
        check(L + 'back button pauses and shows time offset', '\u275a\u275a' in lab, lab)
        pts1 = ev("document.querySelector('.mtr polyline').getAttribute('points')"); pg.wait_for_timeout(400)
        pts2 = ev("document.querySelector('.mtr polyline').getAttribute('points')")
        check(L + 'paused trace is frozen', pts1 == pts2)
        ev(btns + "[3].click()"); pg.wait_for_timeout(250)
        check(L + 'pause button resumes live', ev("document.querySelector('.mtr-ctl .btn[aria-pressed=true]')") is None)
        ev("__t.rt.t[0]=50"); pg.wait_for_timeout(400); ev(btns + "[2].click()"); pg.wait_for_timeout(50)
        off = ev('''(()=>{const sv=document.querySelector('.mtr'),z=+sv.querySelector('line[stroke-width="1.5"]').getAttribute('y1');return sv.querySelector('polyline').getAttribute('points').split(' ').filter(p=>Math.abs(+p.split(',')[1]-z)>0.5).length})()''')
        check(L + 'stop clears the capture', off <= 2, off)
        ev(btns + "[1].click()"); ev("__t.rt.t[0]=50"); pg.wait_for_timeout(1200)
        lab = ev("[...document.querySelector('.mtr').querySelectorAll('text')].map(t=>t.textContent).join('|')")
        check(L + 'rec shows REC and elapsed time', 'REC' in lab, lab)
        ev(btns + "[2].click()"); pg.wait_for_timeout(300)
        lab = ev("[...document.querySelector('.mtr').querySelectorAll('text')].map(t=>t.textContent).join('|')")
        check(L + 'stop ends the take and keeps it', '\u25a0' in lab and 'REC' not in lab, lab)
        ev(btns + "[2].click()"); pg.wait_for_timeout(300)
        lab = ev("[...document.querySelector('.mtr').querySelectorAll('text')].map(t=>t.textContent).join('|')")
        check(L + 'second stop returns to live', '10 s' in lab, lab)
        ev("__t.rt.t[0]=0")
        ev("__t.rt.t[0]=0")
    if group == 'B':
        # D-pad (tank): hold up = both forward, + left = pivot, release stops
        press = lambda d, pid: ev("document.querySelector('.dpb.%s').dispatchEvent(new PointerEvent('pointerdown',{bubbles:true,pointerId:%d}))" % (d, pid))
        lift = lambda d, pid: ev("document.querySelector('.dpb.%s').dispatchEvent(new PointerEvent('pointerup',{bubbles:true,pointerId:%d}))" % (d, pid))
        press('u', 41); up = (T(3), T(4))
        press('l', 42); pv = (T(3), T(4))
        lift('l', 42); lift('u', 41); st0 = (T(3), T(4))
        check(L + 'dpad tank: up drives both at 70%', up == (70, 70), up)
        check(L + 'dpad tank: up + left pivots (left 0, right 70)', pv == (0, 70), pv)
        check(L + 'dpad: release stops both', st0 == (0, 0), st0)
        press('d', 43); dn = (T(3), T(4)); lift('d', 43)
        check(L + 'dpad tank: down reverses both', dn == (-70, -70), dn)
        ev("(()=>{const o=__t.C.board.find(o=>o.k==='dp');o.m='car';__t.syncBoard()})()"); pg.wait_for_timeout(300)
        press('u', 44); c1 = (T(3), T(4)); press('r', 45); c2 = (T(3), T(4)); lift('r', 45); lift('u', 44)
        check(L + 'dpad car: up drives, right steers', c1 == (70, 0) and c2 == (70, 70), (c1, c2))
        ev("(()=>{const o=__t.C.board.find(o=>o.k==='dp');o.tg=1;o.m='tank';__t.syncBoard()})()"); pg.wait_for_timeout(300)
        press('u', 46); lift('u', 46); t1 = (T(3), T(4))
        press('u', 47); lift('u', 47); t2 = (T(3), T(4))
        check(L + 'dpad tap-to-toggle: on then off', t1 == (70, 70) and t2 == (0, 0), (t1, t2))
        ev("(()=>{const o=__t.C.board.find(o=>o.k==='dp');delete o.tg;o.rt=1;__t.syncBoard()})()"); pg.wait_for_timeout(300)
        press('u', 48); pg.wait_for_timeout(300); mid = T(3)
        lift('u', 48); pg.wait_for_timeout(1300)
        check(L + 'dpad ramp: partway after 0.3 s, back to 0 after release', 0 < mid < 70 and T(3) == 0, (mid, T(3)))
        # gamepad -> dial selector: LB/RB move, A toggles on/off
        ev("""(()=>{window.__fp={connected:true,id:'test pad',axes:[0,0,0,0],buttons:Array.from({length:17},()=>({pressed:false,value:0}))};
          navigator.getGamepads=()=>[window.__fp];__t.C.pad.on=true;__t.C.pad.map={4:'rp',5:'rn',0:'rg'};__t.save()})()""")
        pg.wait_for_timeout(200)
        tap = lambda i: (ev("window.__fp.buttons[%d].pressed=true" % i), pg.wait_for_timeout(120), ev("window.__fp.buttons[%d].pressed=false" % i), pg.wait_for_timeout(120))
        ev("__t.C.board.find(o=>o.k==='rs').s=0;__t.syncBoard()"); pg.wait_for_timeout(300)
        tap(5); tap(5); s2 = rsel()
        tap(4); s1 = rsel()
        check(L + 'gamepad: RB, RB, LB moves the dial selector 0 -> 2 -> 1', (s2, s1) == (2, 1), (s2, s1))
        tap(0); on1 = T(1)
        tap(5); moved = (rsel(), T(1), T(2))
        tap(0); tap(0)
        check(L + 'gamepad: A switches the selected output on', on1 == 100, on1)
        check(L + 'gamepad: changing position switches the old output off', moved[0] == 2 and moved[1] == 0, moved)
        ev("__t.C.pad.map={};__t.rt.t[1]=0;__t.rt.t[2]=0")
    check(L + 'no script errors', not errs, errs)
    pg.close()

def main():
    with sync_playwright() as p:
        b = p.chromium.launch()
        for g, smp in GROUPS.items():
            run_layout(b, 'landscape %s' % g, {'width': 900, 'height': 400}, True, smp)
            run_layout(b, 'portrait %s' % g, {'width': 400, 'height': 860}, False, smp)
            run_behaviour(b, g)
        b.close()
    print('\n%d failed' % len(fails) if fails else '\nAll tests passed')
    sys.exit(1 if fails else 0)

if __name__ == '__main__':
    main()
