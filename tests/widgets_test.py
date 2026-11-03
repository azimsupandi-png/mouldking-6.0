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
    {'k': 'h', 'c': 1, 'w': 2},
    {'k': 'j', 'c': 0, 'd': 1, 'm': 'axis', 'w': 1},
    {'k': 'd', 'c': 0, 'd': 1, 'e': 2, 'f': 3, 'm': 'axis', 'w': 2},
    {'k': 'm', 't': [{'c': 0, 'r': 100}, {'c': 1, 'r': -50}], 'w': 1, 'hold': True},
    {'k': 'l', 'c': 4, 'w': 1},
    {'k': 't', 'c': 2, 'y': 'led', 'p': 80, 'w': 1},
    {'k': 'b', 'c': 3, 'w': 1, 'p': 80},
    {'k': 'u', 'c': 0, 'w': 1, 'p': 50},
    {'k': 'g', 'c': 1, 'w': 1},
    {'k': 'c', 'c': 2, 'w': 1},
    {'k': 'n', 'c': 3, 'w': 1},
    {'k': 'k', 'c': 0, 'w': 1},
]
GROUP_B = [
    {'k': 'a', 'c': 0, 'w': 1, 's': 10},
    {'k': 'y', 'c': 1, 'w': 1, 'p': 75, 'd': 2},
    {'k': 'v', 'c': 2, 'w': 1, 'p': 50, 'd': 0.5},
    {'k': 'o', 'c': 0, 'w': 1},
    {'k': 'x', 'w': 1, 'sc': {'0': 30, '1': -40}},
    {'k': 'z', 'w': 1, 'a': 15},
    {'k': 'e', 'w': 1},
    {'k': 'r', 'w': 1},
    {'k': 'p', 'w': 1},
    {'k': 'q', 'c': 'sqT', 'w': 1},
    {'k': 'w', 'c': 2, 'd': 3, 'w': 1, 'p': 80},
    {'k': 'f', 'c': 0, 'w': 1},
    {'k': 'i', 'c': 1, 'w': 1},
]
GROUPS = {'A': GROUP_A, 'B': GROUP_B}
EXPECT_SETTINGS = ['s', 'h', 'm', 'c', 'n', 'g', 'b', 'l', 'u', 't', 'y', 'v', 'a', 'z', 'q', 'w']

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
        ev("""(()=>{const r=document.querySelector('.cruise input');r.value=40;r.dispatchEvent(new Event('input',{bubbles:true}))})()""")
        check(L + 'cruise sets C', T(2) == 40, T(2))
        ev("document.querySelector('.cklock').click()")
        check(L + 'cruise lock disables its slider', ev("document.querySelector('.cruise input').disabled"))
        ev("document.querySelector('.cklock').click()")
        ev("""(()=>{const k=document.querySelector('.dialk'),r=k.getBoundingClientRect();
          k.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true,pointerId:2,clientX:r.right-4,clientY:r.top+r.height/2}))})()""")
        check(L + 'dial right edge is positive', T(3) > 40, T(3))
        ev("__t.rt.t[3]=0")
        ev("""(()=>{const b=document.querySelector('.nudge .tgd[data-d="1"]');
          b.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true,pointerId:3}));
          b.dispatchEvent(new PointerEvent('pointerup',{bubbles:true,pointerId:3}))})()""")
        check(L + 'nudge pushes A', T(0) == 50, T(0))
        pg.wait_for_timeout(450)
        check(L + 'nudge returns A to 0', T(0) == 0, T(0))
        ev("""(()=>{const b=document.querySelector('.turbo');['pointerdown','pointerup'].forEach(n=>b.dispatchEvent(new PointerEvent(n,{bubbles:true,pointerId:4})))})()""")
        check(L + 'turbo returns to previous value on release', T(3) == 0, T(3))
        # joystick drives B, slider on the same channel follows
        cx, cy, w = ev("(()=>{const r=document.querySelector('.pad').getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2,r.width]})()")
        pg.mouse.move(cx, cy); pg.mouse.down(); pg.mouse.move(cx + 0.9 * w / 2, cy, steps=5); pg.wait_for_timeout(250)
        check(L + 'joystick right drives B', T(1) > 80, T(1))
        pg.mouse.up(); pg.wait_for_timeout(250)
        check(L + 'joystick returns to 0 on release', T(1) == 0, T(1))
    else:
        ev("[...document.querySelectorAll('.sesst')].find(e=>e.textContent.startsWith('APPLY')).click()")
        check(L + 'scene applies A=30,B=-40', T(0) == 30 and T(1) == -40, (T(0), T(1)))
        ev("__t.rt.t[0]=0;__t.rt.t[1]=0")
        ev("[...document.querySelectorAll('.tgdir')].find(r=>r.querySelector('[data-d=\"0\"]')).querySelector('[data-d=\"1\"]').click()")
        pg.wait_for_timeout(300)
        check(L + 'ramp starts moving B', T(1) != 0, T(1))
        ev("[...document.querySelectorAll('.tgdir')].find(r=>r.querySelector('[data-d=\"0\"]')).querySelector('[data-d=\"0\"]').click()")
        check(L + 'ramp stop returns B to 0', T(1) == 0, T(1))
        ev("__t.rt.t[0]=60")
        pg.wait_for_timeout(300)
        check(L + 'position counter integrates', ev("[...document.querySelectorAll('.sesst')].some(e=>/[+\u2212]0\\.[1-9]/.test(e.textContent))"))
        ev("__t.rt.t[0]=0")
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
    if group == 'B':
        ev("__t.rt.t[0]=60;__t.rt.t[1]=-40"); pg.wait_for_timeout(350)
        arc = ev("document.querySelector('.bdw .mtr text[font-size=\"28\"]').textContent")
        check(L + 'arc meter shows +60', arc == '+60', arc)
        lit = ev("[...document.querySelectorAll('.mtr')][1].querySelectorAll('rect').length")
        check(L + 'LED meter drawn (20 segments)', lit >= 20, lit)
        led = ev("[...document.querySelectorAll('.mtr text')].map(t=>t.textContent).filter(t=>/\\u221240%/.test(t)).length")
        check(L + 'LED meter shows -40%', led == 1, led)
        ev("__t.rt.t[1]=0;__t.rt.t[0]=0")
    if group == 'A':
        ev("__t.rt.t[0]=70"); pg.wait_for_timeout(500)
        pts = ev("document.querySelector('.mtr polyline').getAttribute('points').split(' ').length")
        cy = ev("+document.querySelector('.mtr circle').getAttribute('cy')")
        check(L + 'scope draws 100 points', pts == 100, pts)
        check(L + 'scope dot follows output (+70 -> y=28)', abs(cy - 28) < 0.6, cy)
        ev("__t.rt.t[0]=0")
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
