"""Общие помощники для автотестов «Тёплого Ручья» (Playwright, Python).

Запуск тестов: timeout 150 python3 -u -I tests/<файл>.py
Сервер поднимается сам на 127.0.0.1 (порт подбирается свободный).
"""
import os, socket, subprocess, sys, time, json
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PHONE = dict(viewport={'width': 844, 'height': 390}, device_scale_factor=2, has_touch=True, is_mobile=True)
DESKTOP = dict(viewport={'width': 1280, 'height': 720}, device_scale_factor=1, has_touch=False, is_mobile=False)


def free_port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); p = s.getsockname()[1]; s.close(); return p


class Server:
    def __init__(self, root=ROOT):
        self.port = free_port()
        self.p = subprocess.Popen([sys.executable, '-m', 'http.server', str(self.port), '--bind', '127.0.0.1'],
                                  cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(50):
            try:
                socket.create_connection(('127.0.0.1', self.port), .2).close(); break
            except OSError:
                time.sleep(.1)
        self.url = f'http://127.0.0.1:{self.port}/index.html'

    def stop(self):
        self.p.terminate()


class Report:
    """Собирает PASS/FAIL/PART по пунктам и печатает их сразу."""
    def __init__(self, title):
        self.title = title; self.rows = []
        print('=' * 70); print(title); print('=' * 70)

    def check(self, key, ok, note=''):
        st = 'PASS' if ok is True else ('PART' if ok == 'part' else 'FAIL')
        self.rows.append((key, st, note))
        print(f'{st:4}  {key}  {note}', flush=True)
        return ok is True

    def summary(self):
        n = {s: sum(1 for r in self.rows if r[1] == s) for s in ('PASS', 'PART', 'FAIL')}
        print('-' * 70)
        print(f"ИТОГ: PASS {n['PASS']}, PART {n['PART']}, FAIL {n['FAIL']} из {len(self.rows)}")
        return n


class Game:
    def __init__(self, pw, url, ctx_opts=PHONE, errs=None):
        self.b = pw.chromium.launch()
        self.ctx = self.b.new_context(**ctx_opts)
        self.pg = self.ctx.new_page(); self.pg.set_default_timeout(8000)
        self.errs = errs if errs is not None else []
        self.pg.on('pageerror', lambda e: self.errs.append('pageerror: ' + str(e)))
        self.pg.on('console', lambda m: self.errs.append('console: ' + m.text) if m.type == 'error' else None)
        self.url = url
        self.pg.goto(url)
        self.pg.wait_for_function('typeof P!=="undefined"')

    def ev(self, js, arg=None):
        return self.pg.evaluate(js) if arg is None else self.pg.evaluate(js, arg)

    def close(self):
        self.b.close()

    # --- состояния ---
    def new_game(self, preset=None):
        self.pg.click('#bnew')
        if preset: self.pg.click(f'#ppre button[data-p="{preset}"]')
        self.pg.click('#pgo'); time.sleep(.3)
        self.ev("hintT=0;0")

    def reload_continue(self):
        self.pg.reload(); self.pg.wait_for_function('typeof P!=="undefined"')
        self.pg.click('#bcont'); time.sleep(.5)

    def fast(self, on=True, k=1):
        """Ускоряет игровое время: лишние вызовы update(.05) каждые 4 мс."""
        if on:
            self.ev(f"(()=>{{clearInterval(window._qaFast);window._qaFast=setInterval(()=>{{if(running&&!paused)for(let i=0;i<{k};i++)update(.05)}},4);return 0}})()")
        else:
            self.ev("clearInterval(window._qaFast);0")

    def wait(self, js, t=10.0, step=.05):
        end = time.time() + t
        while time.time() < end:
            if self.ev(js): return True
            time.sleep(step)
        return False

    def cell_client(self, gx, gy, dy=-5):
        """Экранные (CSS) координаты центра клетки (чуть выше — туда, где спрайт)."""
        self.pg.evaluate("new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(()=>r(0))))")
        return self.ev(f"(()=>{{const k=cv.width/innerWidth,p=cellPx({gx},{gy});return[(p.x-CX)*S/k,(p.y+({dy})-CY)*S/k]}})()")

    def tap_cell(self, gx, gy, dy=-5):
        x, y = self.cell_client(gx, gy, dy)
        self.pg.touchscreen.tap(x, y)
        return x, y

    def click_cell(self, gx, gy, dy=-5):
        x, y = self.cell_client(gx, gy, dy)
        self.pg.mouse.click(x, y)
        return x, y

    def walk_to(self, x, y, t=15):
        ok = self.ev(f"(()=>{{const p=findPath(P.gx,P.gy,(a,b)=>a==={x}&&b==={y},(a,b)=>!!unitAt(a,b,P));if(p)setPath(P,p,.05);return !!p}})()")
        if not ok: return False
        return self.wait("!P.mv&&!busy&&!P.path.length", t)

    def texts(self):
        return self.ev("texts.map(t=>t.s).join(' | ')")

    def shot(self, path):
        self.pg.screenshot(path=path)

    def dlg(self):
        return self.ev("[$('dtext').textContent,[...document.querySelectorAll('#dopts button')].map(b=>[b.textContent,b.disabled])]")

    def opt(self, sub):
        ok = self.ev("s=>{const b=[...document.querySelectorAll('#dopts button')].find(b=>b.textContent.includes(s));if(!b||b.disabled)return false;b.click();return true}", sub)
        time.sleep(.1); return ok

    def strong_hero(self):
        """«Эталон 4-го уровня» из дизайна 3.1."""
        self.ev("P.lvl=4;P.st={str:7,per:6,end:7,cha:5,int:6,agi:7,luck:5};P.eq.melee='sword_iron';P.up={sword_iron:1};P.eq.armor='leather';P.perks=[];P.hp=D.maxHp();P.mp=D.maxMp();0")


def run(main):
    srv = Server(); errs = []
    try:
        with sync_playwright() as pw:
            main(pw, srv, errs)
    finally:
        srv.stop()


OLD_COMMIT = '26c64bc'  # последняя сборка до спринта 1 (только дизайн-документ)


def old_build_dir():
    """Кладёт index.html сборки до спринта во временную папку (для старых сохранений и сравнения луга)."""
    import tempfile
    d = tempfile.mkdtemp(prefix='qa_old_')
    html = subprocess.check_output(['git', 'show', OLD_COMMIT + ':index.html'], cwd=ROOT)
    open(os.path.join(d, 'index.html'), 'wb').write(html)
    return d


def make_old_save(pw, js_setup="0"):
    """Новая игра в старой сборке → строка сохранения без поля map."""
    srv = Server(old_build_dir())
    try:
        g = Game(pw, srv.url)
        g.new_game()
        g.ev(js_setup + ";save();0")
        s = g.ev("localStorage.getItem('teplyruchey_save_v3')")
        g.close()
        return s
    finally:
        srv.stop()
