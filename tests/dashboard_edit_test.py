"""Landscape dashboard editing: drag, tap-to-select toolbar, resize. Run: python3 tests/dashboard_edit_test.py"""
from playwright.sync_api import sync_playwright
import os, sys
u = 'file://' + os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app/src/main/assets/index.html')) + '?mk6test'
fails = []
def chk(n, c):
    print(('PASS ' if c else 'FAIL ') + n)
    if not c: fails.append(n)
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={'width': 820, 'height': 380}); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.route('http*://**/*', lambda r: r.abort())
    pg.goto(u, wait_until='domcontentloaded'); pg.wait_for_timeout(1200)
    try: pg.click('#gSkip', timeout=1500)
    except Exception: pass
    pg.evaluate("""()=>{const t=__t;t.C.layout='board';t.C.dash=true;document.querySelector('#cols').classList.add('board');t.S.connected=true;
      t.C.board=t.cleanBoard([{k:'s',c:0,w:1},{k:'s',c:1,w:1},{k:'b',c:2,w:1}]);t.save();t.syncBoard()}""")
    pg.click('#dbEdit'); pg.wait_for_timeout(300)
    G = lambda: pg.evaluate("__t.C.board.map(o=>o.g)")
    chk('no toolbar buttons before selecting', pg.evaluate("[...document.querySelectorAll('.bdw-ed button')].length") == 0)
    def drag(i, dx, dy):
        e = pg.query_selector_all('.dw')[i].bounding_box(); x = e['x'] + e['width']/2; y = e['y'] + e['height']/2
        pg.mouse.move(x, y); pg.mouse.down(); pg.mouse.move(x+dx, y+dy, steps=12); pg.mouse.up(); pg.wait_for_timeout(200)
    g0 = G(); drag(0, 40, 120); g1 = G()
    chk('drag from the middle moves the widget', g1[0] != g0[0])
    chk('diagonal drag against a neighbour slides instead of snapping back', g1[0][1] > g0[0][1])
    chk('dragged widget is selected and shows its toolbar', pg.evaluate("document.querySelectorAll('.dw.sel .bdw-ed button').length") > 0)
    h = pg.query_selector_all('.dw-rs')[1].bounding_box(); x = h['x']+h['width']*.7; y = h['y']+h['height']*.7
    pg.mouse.move(x, y); pg.mouse.down(); pg.mouse.move(x+30, y+25, steps=8); pg.mouse.up(); pg.wait_for_timeout(200)
    chk('resize handle resizes', G()[1][3] > g1[1][3])
    # a tap that selects must not click the toolbar button that appears under the finger
    pg.click('#dbEdit'); pg.click('#dbEdit'); pg.wait_for_timeout(300)
    pg.evaluate("window.__c=0;__t.C.board.forEach(o=>{})")
    e = pg.query_selector_all('.dw')[2].bounding_box()
    n0 = pg.evaluate("__t.C.board.length")
    pg.mouse.move(e['x']+e['width']-12, e['y']+12); pg.mouse.down(); pg.mouse.up(); pg.wait_for_timeout(120)
    pg.mouse.down(); pg.mouse.up(); pg.wait_for_timeout(100)
    chk('tap on future button spot does not trigger it', pg.evaluate("__t.C.board.length")==n0)
    for tp, n in (('mon', 5), ('four', 6)):
        pg.click('#dbEdit') if not pg.evaluate("__t.C.dash&&document.querySelector('#dbTpl')&&!document.querySelector('#dbTpl').hidden") else None
        pg.wait_for_timeout(200)
        pg.click('#dbTpl'); pg.wait_for_timeout(200)
        pg.click('[data-tpl=%s]' % tp); pg.wait_for_timeout(500)
        g = pg.evaluate("__t.C.board.map(o=>o.g)")
        ov = any(a is not b and a[0] < b[0]+b[2] and b[0] < a[0]+a[2] and a[1] < b[1]+b[3] and b[1] < a[1]+a[3] for a in g for b in g)
        chk('template %s: %d widgets, no overlap' % (tp, n), len(g) == n and not ov)
    # no colour option on any widget
    pg.evaluate("""()=>{const t=__t;t.C.board=t.cleanBoard([{k:'t',c:0,y:'led',p:80,w:1,g:[0,0,16,6],hc:'#2f6bff',col:3}]);t.save();t.syncBoard()}""")
    pg.wait_for_timeout(300)
    e = pg.query_selector_all('.dw')[0].bounding_box()
    pg.mouse.click(e['x'] + 6, e['y'] + 6); pg.wait_for_timeout(300)
    chk('no Colour button on widgets', pg.evaluate("!document.querySelector('.dw button[aria-label=Colour]')"))
    chk('stored colours are dropped', pg.evaluate("!__t.C.board[0].hc&&!__t.C.board[0].col"))
    # Tidy: scrambled widgets are packed with no overlap and the same sizes
    pg.evaluate("""()=>{const t=__t;t.C.board=t.cleanBoard([{k:'n',c:0,w:1},{k:'n',c:1,w:1},{k:'n',c:2,w:1}]);t.save();t.syncBoard()}""")
    pg.wait_for_timeout(300)
    pg.evaluate("""()=>{const t=__t;t.C.board[0].g=[30,2,10,12];t.C.board[1].g=[4,0,10,12];t.C.board[2].g=[18,3,10,12];t.syncBoard()}""")
    pg.click('#dbTidy'); pg.wait_for_timeout(300)
    tg = pg.evaluate("__t.C.board.map(o=>o.g)")
    chk('tidy aligns a messy row: same top, no gaps, same sizes', sorted(g[0] for g in tg) == [0, 10, 20] and all(g[1] == 0 and g[2] == 10 and g[3] == 12 for g in tg))
    chk('no script errors', not errs)
    b.close()
sys.exit(1 if fails else 0)
