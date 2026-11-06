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
        ev("__t.S.connected=true;__t.C.ch[0].kind='slider';__t.C.ch[0].stp=10;__t.C.ch[0].mag=0;__t.C.ch[0].lo=-100;__t.C.ch[0].hi=100;__t.rt.t[0]=0")
        tap = "(s)=>{const b=document.querySelector(s);b.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true,pointerId:7}));b.dispatchEvent(new PointerEvent('pointerup',{bubbles:true,pointerId:7}))}"
        pg.evaluate(tap, '.stp.inc'); pg.wait_for_timeout(100)
        a10 = ev("__t.rt.t[0]")
        pg.evaluate(tap, '.stp.dec'); pg.evaluate(tap, '.stp.dec'); pg.wait_for_timeout(100)
        b10 = ev("__t.rt.t[0]")
        check('step size: arrows move by the chosen step (10)', a10 == 10 and b10 == -10, (a10, b10))
        ev("document.querySelector('.pre .btn[data-v=\"50\"]').click()"); pg.wait_for_timeout(100)
        pr = ev("[__t.rt.t[0], document.querySelector('.pre .btn[data-v=\"50\"]').classList.contains('on')]")
        check('preset chip sets the value and highlights', pr == [50, True], pr)
        ev("__t.C.ch[0].lo=-40;__t.C.ch[0].hi=60")
        ev("document.querySelector('.pre .btn[data-v=\"-100\"]').click()"); lo = ev("__t.rt.t[0]")
        ev("document.querySelector('.pre .btn[data-v=\"100\"]').click()"); hi = ev("__t.rt.t[0]")
        check('slider limits clamp the requested value', lo == -40 and hi == 60, (lo, hi))
        ev("__t.C.ch[0].lo=-100;__t.C.ch[0].hi=100;__t.C.ch[0].mag=6")
        near = ev("""(()=>{const r=document.querySelector('.track input.pwr');r.value=4;r.dispatchEvent(new Event('input',{bubbles:true}));return [__t.rt.t[0],+r.value]})()""")
        far = ev("""(()=>{const r=document.querySelector('.track input.pwr');r.value=20;r.dispatchEvent(new Event('input',{bubbles:true}));return __t.rt.t[0]})()""")
        check('magnet: values close to 0 snap to 0, others pass', near == [0, 0] and far == 20, (near, far))
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
        # slider limit controls are real inputs that drive the config
        ev("document.querySelector('#lStd').click()"); pg.wait_for_timeout(200)
        lim = ev("""(()=>{const e=document.querySelector('.adv input.lo');e.value=-40;e.dispatchEvent(new Event('input',{bubbles:true}));
          const h=document.querySelector('.adv input.hi');h.value=60;h.dispatchEvent(new Event('input',{bubbles:true}));
          return [e.tagName,__t.C.ch[0].lo,__t.C.ch[0].hi]})()""")
        check('slider min/max controls are range inputs and change the limits', lim == ['INPUT', -40, 60], lim)
        # Slider maximum limits only the slider: a dial selector still reaches its full output
        pg2, errs2 = W.boot(b, {'width': 900, 'height': 500}, True, [{'k': 'rs', 'w': 1, 'p': 100, 'ns': 6, 's': 0, 'rt': 0.3}])
        pg2.evaluate("__t.C.ch[0].kind='slider';__t.C.ch[0].hi=60;__t.C.ch[0].lo=-60;__t.rt.t[0]=0")
        kb = pg2.locator('.dialk').first.bounding_box()
        pg2.mouse.move(kb['x'] + kb['width'] / 2, kb['y'] + kb['height'] / 2); pg2.mouse.down(); pg2.wait_for_timeout(1100); pg2.mouse.up(); pg2.wait_for_timeout(1500)
        sel = pg2.evaluate("__t.rt.t[0]")
        check('selector output is not capped by the slider maximum', sel == 100, sel)
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

        # ---- cab widgets: work mode, Power Max, auto-stop timer, service alerts, response, cab monitor ----
        pg4, errs4 = W.boot(b, {'width': 1000, 'height': 447}, True, [
            {'k': 'wm', 'w': 1}, {'k': 'pm', 'w': 1, 'h': 1, 'cd': 2}, {'k': 'ct', 'w': 1}, {'k': 'as', 'w': 1},
            {'k': 'rp', 'w': 1}, {'k': 'cm', 'w': 2}, {'k': 's', 'c': 0, 'w': 1}])
        e4 = pg4.evaluate
        card = lambda name: pg4.locator('.bdw', has_text=name).first
        e4("__t.C.limit=100;__t.C.speed='fast';__t.C.ramp=60;__t.rt.t[0]=100;__t.paintBoard()"); pg4.wait_for_timeout(300)
        base = e4("__t.goalOf(0)")
        for q, cap in ((0, 30), (1, 40), (2, 70), (3, 100)):
            card('Work mode').locator('.wmb').nth(q).click(); pg4.wait_for_timeout(150)
            g = e4("__t.goalOf(0)")
            check('work mode %s: real click caps the output to %d%% of full' % ('IFGH'[q], cap), abs(g - base * cap / 100) < 1.01, (g, base))
        card('Work mode').locator('.wmb').nth(0).click(); pg4.wait_for_timeout(150)
        e4("__t.C.board=__t.C.board.filter(o=>o.k!=='wm');__t.save();__t.syncBoard()"); pg4.wait_for_timeout(300)
        check('work mode: removing the widget removes the cap', abs(e4("__t.goalOf(0)") - base) < 0.01, e4("__t.goalOf(0)"))
        e4("__t.C.board.unshift({k:'wm',w:1});__t.S.wm=3;__t.save();__t.syncBoard()"); pg4.wait_for_timeout(300)
        # work mode caps are editable and clamped by the sanitizer
        cl = e4("__t.cleanBoard([{k:'wm',w:1,cp:[20,50,200]},{k:'pm',w:1,h:999,cd:-4},{k:'ct',w:1},{k:'as',w:1},{k:'rp',w:1},{k:'cm',w:1}])")
        check('cab widgets: sanitizer keeps all six and clamps odd values', [o['k'] for o in cl] == ['wm','pm','ct','as','rp','cm'] and cl[0]['cp'] == [20, 50, 70] and cl[1]['h'] == 10 and cl[1]['cd'] == 3, cl)
        e4("__t.wsEdit(__t.C.board.find(o=>o.k==='wm'))"); pg4.wait_for_timeout(200)
        pg4.locator('#gEdit .wsf').first.locator('.wsc button[data-v="20"]').click()
        pg4.locator('#gEdit .gact button', has_text='Save').click(); pg4.wait_for_timeout(300)
        check('work mode: setting mode I to 20% is saved and shown on the button', e4("__t.C.board.find(o=>o.k==='wm').cp")[0] == 20 and '20%' in card('Work mode').locator('.wmb').nth(0).inner_text(), e4("__t.C.board.find(o=>o.k==='wm').cp"))
        card('Work mode').locator('.wmb').nth(0).click(); pg4.wait_for_timeout(150)
        check('work mode: new cap applies', abs(e4("__t.goalOf(0)") - base * .2) < 1.01, e4("__t.goalOf(0)"))
        # Power Max: hold, overrides the cap and the power limit, ends by itself, then cools down
        e4("__t.C.limit=50"); card('Work mode').locator('.wmb').nth(3).click(); pg4.wait_for_timeout(150)
        normal = e4("__t.goalOf(0)")
        bb = card('Power Max').locator('.qbtn').bounding_box()
        pg4.mouse.move(bb['x'] + bb['width'] / 2, bb['y'] + bb['height'] / 2); pg4.mouse.down(); pg4.wait_for_timeout(200)
        boosted = e4("__t.goalOf(0)"); on1 = e4("__t.PM.on")
        pg4.wait_for_timeout(1100)
        ended = not e4("__t.PM.on")
        pg4.mouse.up(); pg4.wait_for_timeout(150)
        check('Power Max: holding lifts the 50% limit, then ends by itself after the longest hold', on1 and boosted > normal * 1.9 and ended, (normal, boosted, on1, ended))
        pg4.mouse.down(); pg4.wait_for_timeout(200)
        during_cd = e4("__t.PM.on"); pg4.mouse.up(); pg4.wait_for_timeout(100)
        check('Power Max: refused during the cool-down', not during_cd, during_cd)
        pg4.wait_for_timeout(2200)
        pg4.mouse.down(); pg4.wait_for_timeout(200); again = e4("__t.PM.on"); pg4.mouse.up(); pg4.wait_for_timeout(200)
        check('Power Max: works again after the cool-down, and releasing stops it at once', again and not e4("__t.PM.on") and abs(e4("__t.goalOf(0)") - normal) < .01, (again, e4("__t.PM.on")))
        e4("__t.C.limit=100")
        # Response: Fast reaches the goal at once, Soft climbs slower than Normal
        def climb(q):
            e4("__t.rt.t[0]=0;__t.rt.o[0]=0"); pg4.wait_for_timeout(400)
            card('Response').locator('.wmb').nth(q).click()
            e4("__t.C.ramp=80;__t.rt.t[0]=100"); pg4.wait_for_timeout(250)
            return e4("[__t.rt.o[0],__t.goalOf(0)]")
        so, no, fa = climb(0), climb(1), climb(2)
        check('response: Fast arrives at the goal, Soft is slower than Normal', fa[0] == fa[1] and so[0] < no[0] < no[1], (so, no, fa))
        e4("__t.C.board=__t.C.board.filter(o=>o.k!=='rp');__t.save();__t.syncBoard()"); pg4.wait_for_timeout(200)
        e4("__t.S.rsp=2;__t.rt.t[0]=0;__t.rt.o[0]=0"); pg4.wait_for_timeout(300); e4("__t.C.ramp=80;__t.rt.t[0]=100"); pg4.wait_for_timeout(250)
        check('response: without the widget the setting is ignored (normal ramp)', e4("__t.rt.o[0]") < e4("__t.goalOf(0)"), e4("[__t.rt.o[0],__t.goalOf(0)]"))
        e4("__t.S.rsp=1;__t.C.board.splice(4,0,{k:'rp',w:1});__t.C.ramp=60;__t.save();__t.syncBoard()"); pg4.wait_for_timeout(300)
        # Auto-stop timer: counts down while a motor runs, a tap resets it, the gear changes the Safety setting
        e4("__t.C.safety.idle=10;__t.rt.t[0]=50;__t.paintBoard()"); pg4.wait_for_timeout(2300)
        t_before = card('Auto-stop timer').locator('.sesst b').inner_text()
        card('Auto-stop timer').locator('.sesst').click(); pg4.wait_for_timeout(250)
        t_after = card('Auto-stop timer').locator('.sesst b').inner_text()
        check('auto-stop timer: counts down while running, a tap resets it', t_before in ('0:07', '0:08') and t_after in ('0:09', '0:10'), (t_before, t_after))
        e4("__t.rt.t[0]=0"); pg4.wait_for_timeout(400)
        check('auto-stop timer: shows Ready when nothing runs', card('Auto-stop timer').locator('.sesst b').inner_text() == 'Ready', card('Auto-stop timer').locator('.sesst b').inner_text())
        e4("__t.wsEdit(__t.C.board.find(o=>o.k==='ct'))"); pg4.wait_for_timeout(200)
        pg4.locator('#gEdit .wsc button[data-v="30"]').click(); pg4.locator('#gEdit .gact button', has_text='Save').click(); pg4.wait_for_timeout(300)
        check('auto-stop timer: gear sets the Safety idle time', e4("__t.C.safety.idle") == 30 and e4("document.querySelector('#sfIdle').value") == '30', e4("__t.C.safety.idle"))
        # Service alerts
        rows = lambda: pg4.evaluate("[...document.querySelectorAll('.asr')].map(r=>r.className)")
        e4("__t.S.connected=true;__t.S.estop=false;__t.paintBoard()"); pg4.wait_for_timeout(250)
        ok_rows = rows()
        e4("__t.S.estop=true;__t.S.connected=false;__t.paintBoard()"); pg4.wait_for_timeout(250)
        bad_rows = rows()
        check('service alerts: green when fine, amber link and red e-stop when not', ok_rows == ['asr l0'] * 4 and bad_rows[0] == 'asr l1' and bad_rows[1] == 'asr l2', (ok_rows, bad_rows))
        e4("__t.S.estop=false;__t.S.connected=true")
        # Cab monitor
        e4("__t.C.ramp=0;__t.C.limit=100;__t.rt.t[0]=60"); pg4.wait_for_timeout(500)
        cmv = e4("(()=>{const c=document.querySelector('.cmsvg');return [c.querySelector('text').textContent,[...c.querySelectorAll('text')].map(t=>t.textContent).join('|'),__t.rt.o[0]]})()")
        check('cab monitor: shows mode, load percent, bars and auto-stop state', ('MODE H' in cmv[1] or 'MODE ' in cmv[1]) and (str(round(cmv[2])) + '%') in cmv[1] and 'Auto-stop' in cmv[1], cmv)
        card('Work mode').locator('.wmb').nth(1).click(); pg4.wait_for_timeout(300)
        check('cab monitor: follows the work mode button', 'MODE F' in e4("document.querySelector('.cmsvg').textContent"), e4("document.querySelector('.cmsvg').textContent"))
        # fits: no card is clipped or overlaps at the phone landscape size
        ov = e4("(()=>{const a=[...document.querySelectorAll('.bdw')],bad=[];a.forEach(w=>{const r=w.getBoundingClientRect();if(w.scrollHeight>w.clientHeight+2||w.scrollWidth>w.clientWidth+2) bad.push(w.textContent.slice(0,14))});return bad})()")
        check('cab widgets: nothing is clipped inside its card at 1000x447', not ov, ov)
        check('no script errors (cab widgets)', not errs4, errs4)
        check('no script errors', not errs, errs)
        b.close()
    print('All tests passed' if not fails else '%d failed' % len(fails))
    sys.exit(1 if fails else 0)

if __name__ == '__main__':
    main()
