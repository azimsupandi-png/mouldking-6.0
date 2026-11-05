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
        check('no script errors', not errs, errs)
        b.close()
    print('All tests passed' if not fails else '%d failed' % len(fails))
    sys.exit(1 if fails else 0)

if __name__ == '__main__':
    main()
