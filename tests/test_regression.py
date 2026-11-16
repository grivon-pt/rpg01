"""Регрессия после спринта 1: всё, что было до леса, работает как раньше.
Новая игра, старое сохранение, бой со слаймами (тапами), автобой, инвентарь, магазин Бориса, кузнец,
диалоги и задания деревни, переход луг→лес→луг с сохранением и перезагрузкой, смерть в лесу,
базовый проход на компьютере 1280×720 (мышь и клавиатура).

Запуск: timeout 150 python3 -u -I tests/test_regression.py
"""
import sys, os, time, json, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qa_common import *

R = Report('Регрессия: деревня, луг, бой, сохранения, компьютер')


def safe(key):
    def deco(fn):
        def run(*a):
            try:
                fn(*a)
            except Exception as e:
                R.check(key, False, 'исключение: ' + repr(e)[:200]); traceback.print_exc(limit=2)
        return run
    return deco


def reset(g, mp='meadow', x=10, y=10):
    g.ev(f"if(combat){{for(const e of enemies)e.hp=0;endCombat(false)}};P.dead=0;P.grace=1e9;if(curMap!=='{mp}')setMap('{mp}');enemies.length=0;MAPS[curMap].enemies=enemies;spawnT=999;texts.length=0;placeHero({x},{y});snapCam();0")


def hero_turn(g, t=8):
    return g.wait("combat&&combat.active===P&&!busy", t)


@safe('Новая игра: создание героя')
def new_game(pw, srv, errs):
    g = Game(pw, srv.url, errs=errs)
    start = g.ev("[!!document.getElementById('bnew'),!document.getElementById('bcont')]")
    g.pg.click('#bnew'); time.sleep(.2)
    g.pg.click('#ppre button[data-p="war"]'); g.pg.click('#pstats button[data-m="cha"]'); g.pg.click('#pstats button[data-k="agi"]')
    st = g.ev("[P.st.str,P.st.cha,P.st.agi,P.pts]")
    g.pg.click('#pgo'); time.sleep(.3)
    s = g.ev("[running,curMap,P.gx,P.gy,P.lvl,P.coins,P.bag.map(b=>b.id+'×'+b.qty).join(),P.eq.melee,enemies.length,P.hp===D.maxHp(),!!localStorage.getItem(SAVE_KEY)]")
    sv = g.ev("JSON.parse(localStorage.getItem(SAVE_KEY)).map")
    R.check('Новая игра: создание героя', start == [True, True] and st == [9, 2, 7, 0] and s == [True, 'meadow', 10, 10, 1, 0, 'arrows×20,pot_hp×2,pot_mp×1', 'sword_wood', 9, True, True] and sv == 'meadow',
            f'набор «Воин» −О +Л: {st}; после «В путь!» {s}; в сохранении map={sv}')
    g.close()


@safe('Старое сохранение (ключ teplyruchey_save_v3, без map)')
def old_save(pw, srv, errs):
    s = make_old_save(pw, "P.lvl=3;P.xp=4;P.coins=55;P.st.str=8;P.perks=['heavy'];addItem('goo',3,true);P.eq.armor='leather';P.q={slimes:{s:'done',n:5},goo:{s:'active',n:0}};P.up={sword_wood:1};CAT.follow=true;P.q.cat={s:'active',n:0};placeHero(25,12)")
    g = Game(pw, srv.url, errs=errs)
    g.ev("s=>{localStorage.setItem('teplyruchey_save_v3',s)}", s); g.pg.reload(); g.pg.wait_for_function('typeof P!=="undefined"')
    btn = g.ev("$('bcont')&&$('bcont').textContent")
    g.pg.click('#bcont'); time.sleep(.4)
    a = g.ev("[curMap,P.gx,P.gy,P.lvl,P.xp,P.coins,P.st.str,P.perks.join(),bagCount('goo'),P.eq.armor,qState('slimes'),qState('goo'),P.up.sword_wood,CAT.follow,trackerText()]")
    g.fast(True, 2); time.sleep(1.5); g.fast(False)
    saved = json.loads(g.ev("localStorage.getItem(SAVE_KEY)"))
    R.check('Старое сохранение (ключ teplyruchey_save_v3, без map)',
            btn == 'Продолжить · ур. 3' and a[:14] == ['meadow', 25, 12, 3, 4, 55, 8, 'heavy', 3, 'leather', 'done', 'active', 1, True] and saved.get('map') == 'meadow',
            f'кнопка «{btn}»; загружено {a}; после автосохранения map={saved.get("map")}')
    g.close()


@safe('Бой со слаймами на лугу тапами')
def slime_fight(pw, srv, errs):
    g = Game(pw, srv.url, errs=errs); g.new_game()
    g.ev("P.st.str=8;P.st.agi=8;P.eq.melee='sword_iron';P.hp=D.maxHp();P.q.slimes={s:'active',n:0};0")
    reset(g, 'meadow', 30, 11)
    g.ev("const s=makeFoe('green',33,11);s.wander=99;enemies.push(s);auto=false;localStorage.setItem('teplyruchey_auto','0');0")
    time.sleep(.3)
    g.tap_cell(33, 11)  # тап по слайму вне боя — напасть
    started = g.wait("!!combat", 3); hero_turn(g)
    hits = 0; turns = 0; seen_tip = False; ap_line = None
    while g.ev("!!combat") and turns < 8:
        if not hero_turn(g, 8): break
        turns += 1
        pos = g.ev("(()=>{const e=enemies.find(e=>e.hp>0);return e?[e.gx,e.gy]:null})()")
        if not pos: break
        g.tap_cell(*pos); time.sleep(.25)
        lab = g.ev("preview&&[preview.kind,preview.chance,preview.cost,preview.ok]")
        seen_tip = seen_tip or (lab and lab[0] == 'melee')
        ok_btn = g.ev("getComputedStyle($('bOK')).display")
        g.tap_cell(*pos); time.sleep(1.4)  # второй тап — сделать
        hits += 1
        if g.ev("combat&&combat.active===P&&!busy"):
            r = g.pg.locator('#bE').bounding_box(); g.pg.touchscreen.tap(r['x'] + r['width'] / 2, r['y'] + r['height'] / 2)
    g.wait("!combat", 6)
    res = g.ev("[!!combat,P.q.slimes.n,enemies.filter(e=>e.hp>0).length,P.dead]")
    R.check('Бой со слаймами на лугу тапами', started and seen_tip and res[0] is False and res[1] == 1 and res[3] <= 0,
            f'бой начался тапом={started}; подсказка удара (шанс, ОД) появилась={seen_tip}, кнопка ✓ {ok_btn}; ходов героя {turns}; итог [бой,счётчик задания,живых слаймов,смерть]={res}')
    # автобой
    reset(g, 'meadow', 30, 11)
    g.ev("for(const[x,y]of[[33,11],[34,12]]){const s=makeFoe('blue',x,y);s.wander=99;enemies.push(s)}P.hp=D.maxHp();addItem('pot_hp',2,true);auto=false;0")
    time.sleep(.2)
    r = g.pg.locator('#bAuto').bounding_box(); g.pg.touchscreen.tap(r['x'] + r['width'] / 2, r['y'] + r['height'] / 2)
    g.ev("P.grace=0;0")
    g.fast(True, 3)
    g.wait("!!combat", 4); done = g.wait("!combat&&!enemies.some(e=>e.hp>0)", 40); g.fast(False)
    a = g.ev("[auto,enemies.filter(e=>e.hp>0).length,P.dead<=0,curMap]")
    R.check('Автобой против слаймов', done and a == [True, 0, True, 'meadow'], f'кнопка «авто» включила автобой={a[0]}, живых слаймов {a[1]}, герой жив={a[2]}')
    g.ev("toggleAuto();0")
    g.close()


@safe('Инвентарь')
def inventory(pw, srv, errs):
    g = Game(pw, srv.url, errs=errs); g.new_game()
    g.ev("addItem('sword_iron',1,true);addItem('leather',1,true);addItem('amulet_luck',1,true);P.hp=10;0")
    r = g.pg.locator('#bI').bounding_box(); g.pg.touchscreen.tap(r['x'] + r['width'] / 2, r['y'] + r['height'] / 2); time.sleep(.3)
    opened = g.ev("panel.classList.contains('open')&&pmode==='inv'")
    def click(attr, item):
        return g.ev(f"[...document.querySelectorAll('#pinv [{attr}]')].some(b=>{{const i=+b.dataset.{attr[5:]};if(P.bag[i]&&P.bag[i].id==='{item}'){{b.click();return true}}return false}})")
    click('data-eq', 'sword_iron'); click('data-eq', 'leather'); click('data-eq', 'amulet_luck')
    eq = g.ev("[P.eq.melee,P.eq.armor,P.eq.trinket,bagCount('sword_wood'),bagCount('jacket'),stv('luck')]")
    hp0 = g.ev("P.hp"); click('data-use', 'pot_hp'); hp1 = g.ev("P.hp")
    g.ev("[...document.querySelectorAll('#pinv [data-un]')].find(b=>b.dataset.un==='trinket').click();0")
    w0 = g.ev("bagWeight()"); click('data-drop', 'jacket'); w1 = g.ev("bagWeight()")
    g.ev("togglePanel(false);0"); time.sleep(.3)
    g.ev("placeHero(P.gx+3,P.gy);0"); time.sleep(.6)
    back = g.ev("[bagCount('jacket'),items.some(i=>i.id==='jacket')]")
    R.check('Инвентарь', opened and eq == ['sword_iron', 'leather', 'amulet_luck', 1, 1, 6] and hp1 > hp0 and w1 < w0 and g.ev("P.eq.trinket") is None,
            f'открыт кнопкой={opened}; надето {eq}; зелье ХП {hp0}→{hp1}; вес после «Выбросить» {w0}→{w1}; куртка на земле/в сумке {back}')
    g.close()


@safe('Диалоги в деревне (тап по жителю — подходит и говорит)')
def village(pw, srv, errs):
    g = Game(pw, srv.url, errs=errs); g.new_game()
    names = {}
    for n in ('efim', 'boris', 'gordey', 'mira', 'anya'):
        reset(g, 'meadow', 11, 12)
        pos = g.ev(f"(()=>{{const n=NPCS.find(n=>n.id==='{n}');return[n.gx,n.gy]}})()")
        g.tap_cell(pos[0], pos[1], dy=-8)
        g.wait("!!dlgNpc", 6)
        names[n] = g.ev("$('dname').textContent")
        g.ev("closeDlg();0")
    ok = names == {'efim': 'Ефим · староста', 'boris': 'Борис · торговец', 'gordey': 'Гордей · кузнец', 'mira': 'Мира · травница', 'anya': 'Аня'}
    R.check('Диалоги в деревне (тап по жителю — подходит и говорит)', ok, f'{names}')
    # магазин Бориса
    reset(g, 'meadow', 7, 9)
    g.ev("P.coins=200;P.st.cha=5;talk(NPCS[1]);0"); g.opt('Покажи товар'); time.sleep(.2)
    shop = g.ev("[pmode,panel.querySelector('.hd b').textContent]")
    c0 = g.ev("P.coins"); pr = g.ev("buyPrice('sword_iron','boris')")
    g.ev("document.querySelector('#pinv [data-buy=\"sword_iron\"]').click();0")
    c1 = g.ev("P.coins"); got = g.ev("bagCount('sword_iron')")
    g.ev("addItem('goo',3,true);0"); g.ev("renderShop();0")
    sp = g.ev("sellPrice('goo')")
    g.ev("[...document.querySelectorAll('#pinv [data-sellall]')].find(b=>P.bag[+b.dataset.sellall].id==='goo').click();0")
    c2 = g.ev("P.coins")
    g.ev("togglePanel(false);0")
    R.check('Магазин Бориса: купить и продать', shop == ['shop', 'Лавка Бориса'] and c0 - c1 == pr and got == 1 and c2 - c1 == 3 * sp,
            f'лавка {shop}; железный меч за {pr} (монет {c0}→{c1}); 3 слизи проданы за {c2-c1} ({sp}×3)')
    # кузнец
    reset(g, 'meadow', 17, 9)
    g.ev("P.coins=100;addItem('goo',4,true);P.eq.melee='sword_iron';P.st.str=5;talk(NPCS[2]);0")
    o = [x[0] for x in g.dlg()[1]]
    g.opt('Улучшить оружие'); t = g.dlg()[0]
    up = g.ev("[P.up.sword_iron,P.coins,bagCount('goo'),getIt('sword_iron').dmg]")
    g.ev("closeDlg();0")
    R.check('Кузнец Гордей улучшает оружие', up[0] == 1 and up[1] == 70 and up[3] == [9, 13] and t.startswith('Готово!'),
            f'пункты {o[:3]}; после улучшения {up}')
    # задания деревни
    reset(g, 'meadow', 17, 17)
    g.ev("P.coins=0;P.lvl=99;P.q={};P.flags={};talk(NPCS[0]);0"); g.opt('Есть для меня работа'); g.opt('Берусь'); g.ev("closeDlg();0")
    q1 = g.ev("[qState('slimes'),trackerText()]")
    g.ev("P.q.slimes.n=5;0"); mk = g.ev("npcMark(NPCS[0])")
    g.ev("talk(NPCS[0]);0"); g.opt('выполнено'); g.opt('Рад помочь'); g.ev("closeDlg();0")
    q2 = g.ev("[qState('slimes'),P.coins,npcMark(NPCS[0])]")
    reset(g, 'meadow', 7, 16)
    g.ev("talk(NPCS[3]);0"); g.opt('Тебе нужна помощь'); g.opt('Принесу'); g.ev("addItem('goo',5,true);closeDlg();window._g0=bagCount('goo');0")
    g.ev("talk(NPCS[3]);0"); g.opt('выполнено'); g.ev("closeDlg();0")
    q3 = g.ev("[qState('goo'),window._g0-bagCount('goo')]")
    reset(g, 'meadow', 9, 8)
    g.ev("talk(NPCS[4]);0"); g.opt('Что случилось'); g.opt('Конечно найду'); g.ev("closeDlg();0")
    cat_txt = g.ev("QUESTS.cat.d")
    g.ev("CAT.follow=true;0"); g.ev("talk(NPCS[4]);0"); g.opt('выполнено'); g.ev("closeDlg();0")
    q4 = g.ev("[qState('cat'),bagCount('amulet_luck'),CAT.home]")
    R.check('Задания деревни: «Слаймы на лугу», «Слизь для зелий», «Где Пушок?»',
            q1 == ['active', '• Слаймы на лугу 0/5'] and mk == '?' and q2 == ['done', 30, '!'] and q3 == ['done', 5] and q4 == ['done', 1, True],
            f'слаймы {q1}, знак «{mk}», сдано {q2}; слизь [состояние, забрано] {q3}; Пушок {q4}')
    g.close()


@safe('Луг → лес → луг с сохранением и перезагрузкой')
def meadow_forest(pw, srv, errs):
    g = Game(pw, srv.url, errs=errs); g.new_game()
    reset(g, 'meadow', 46, 11)
    g.ev("populate();0")
    m_before = g.ev("enemies.map(e=>e.type+e.gx+','+e.gy).sort().join(' ')")
    g.tap_cell(47, 11); g.wait("curMap==='forest'&&!busy", 4)
    s1 = g.ev("JSON.parse(localStorage.getItem(SAVE_KEY))")
    f_before = g.ev("enemies.filter(e=>!e.boss).length")
    g.pg.reload(); g.pg.wait_for_function('typeof P!=="undefined"'); g.pg.click('#bcont'); time.sleep(.4)
    a = g.ev("[curMap,P.gx,P.gy]")
    g.ev("P.grace=1e9;placeHero(1,14);0"); g.tap_cell(0, 14); g.wait("curMap==='meadow'&&!busy", 4)
    b = g.ev("[curMap,P.gx,P.gy,JSON.parse(localStorage.getItem(SAVE_KEY)).map]")
    g.pg.reload(); g.pg.wait_for_function('typeof P!=="undefined"'); g.pg.click('#bcont'); time.sleep(.4)
    c = g.ev("[curMap,P.gx,P.gy]")
    # без перезагрузки враги луга сохраняются за картой
    reset(g, 'meadow', 46, 11); g.ev("populate();0"); m1 = g.ev("enemies.map(e=>e.type+e.gx+','+e.gy).sort().join(' ')")
    g.tap_cell(47, 11); g.wait("curMap==='forest'&&!busy", 4); g.ev("placeHero(1,14);0"); g.tap_cell(0, 14); g.wait("curMap==='meadow'&&!busy", 4)
    m2 = g.ev("enemies.map(e=>e.type+e.gx+','+e.gy).sort().join(' ')")
    R.check('Луг → лес → луг с сохранением и перезагрузкой',
            [s1['map'], s1['gx'], s1['gy']] == ['forest', 2, 14] and a == ['forest', 2, 14] and b == ['meadow', 45, 11, 'meadow'] and c == ['meadow', 45, 11] and m1 == m2 and f_before == 4,
            f'сохранено после перехода {[s1["map"], s1["gx"], s1["gy"]]}; после перезагрузки {a}; обратно {b}; перезагрузка {c}; слаймы луга после захода в лес те же={m1 == m2}')
    # смерть в лесу
    reset(g, 'forest', 10, 20)
    g.ev("P.coins=41;const m=makeFoe('mushling',10,21);m.wander=99;enemies.push(m);P.grace=0;startCombat(true,m);0")
    hero_turn(g)
    g.ev("P.hp=1;hurtHero(enemies.find(e=>e.type==='mushling'),99);0")
    tired = g.wait("P.dead>0", 2)
    g.wait("P.dead<=0&&curMap==='meadow'", 6); time.sleep(.3)
    d = g.ev("[curMap,P.gx,P.gy,P.coins,P.hp===D.maxHp(),!!combat,JSON.parse(localStorage.getItem(SAVE_KEY)).map]")
    R.check('Смерть в лесу → костёр на лугу, −25% монет, сохранение на лугу', tired and d == ['meadow', 10, 10, 31, True, False, 'meadow'], f'{d}')
    g.close()


@safe('Компьютер 1280×720: мышь и клавиатура')
def desktop(pw, srv, errs):
    g = Game(pw, srv.url, ctx_opts=DESKTOP, errs=errs)
    help_ = g.ev("$('help').innerText")
    g.pg.click('#bnew'); g.pg.click('#pgo'); time.sleep(.3)
    hint = g.ev("hintT>0")
    # клик мышью — идти
    reset(g, 'meadow', 12, 10)
    g.click_cell(15, 10); g.wait("!P.mv&&P.gx===15", 4)
    a = g.ev("[P.gx,P.gy]")
    # WASD
    g.pg.keyboard.press('d'); time.sleep(.5); g.pg.keyboard.press('s'); time.sleep(.5)
    b = g.ev("[P.gx,P.gy]")
    # I / P / C
    g.pg.keyboard.press('i'); time.sleep(.2); inv = g.ev("panel.classList.contains('open')&&pmode"); g.pg.keyboard.press('Escape'); time.sleep(.1)
    g.pg.keyboard.press('p'); time.sleep(.2); qs = g.ev("pmode"); g.pg.keyboard.press('Escape'); time.sleep(.1)
    g.pg.keyboard.press('c'); time.sleep(.2); he = g.ev("pmode"); g.pg.keyboard.press('Escape'); time.sleep(.1)
    # переход в лес: клик по выходу; обратно — клавишами
    reset(g, 'meadow', 44, 10); g.click_cell(47, 10)
    fw = g.wait("curMap==='forest'&&!busy", 6)
    g.ev("P.grace=1e9;0")
    g.pg.keyboard.press('a'); time.sleep(.5); g.pg.keyboard.press('a'); time.sleep(.3)
    back = g.wait("curMap==='meadow'&&!busy", 4)
    # бой мышью: наведение — подсказка, клик — удар; пробел — конец хода
    reset(g, 'forest', 10, 20)
    g.ev("P.st.str=9;P.eq.melee='sword_iron';const m=makeFoe('mushling',11,20);m.wander=99;m.atk=1;enemies.push(m);auto=false;0")
    g.click_cell(11, 20); hero_turn(g)
    x, y = g.cell_client(11, 20); g.pg.mouse.move(x, y - 3); g.pg.mouse.move(x, y); time.sleep(.2)
    pv = g.ev("preview&&[preview.kind,preview.chance,preview.cost]")
    ap0 = g.ev("P.ap"); g.pg.mouse.click(x, y); time.sleep(1.2); ap1 = g.ev("P.ap")
    g.pg.keyboard.press('Space'); time.sleep(.3)
    ended = g.ev("!combat||combat.active!==P")
    g.shot('/tmp/qa_work/desktop_fight.png')
    g.pg.keyboard.press('q'); time.sleep(.1); q = g.ev("auto"); g.pg.keyboard.press('q')
    btn = g.ev("['bA','bB','bM','bAuto','bE','bI','bQ','bC'].map(id=>{const r=$(id).getBoundingClientRect();return Math.round(Math.min(r.width,r.height))})")
    g.ev("for(const e of enemies)e.hp=0;endCombat(true);0")
    ok = a == [15, 10] and b == [16, 11] and inv == 'inv' and qs == 'quests' and he == 'hero' and fw and back and pv and pv[0] == 'melee' and ap0 - ap1 >= 3 and ended and q is True
    R.check('Компьютер 1280×720: мышь и клавиатура', ok,
            f'клик — идти {a}, WASD {b}; I/P/C → {inv}/{qs}/{he}; клик по выходу → лес={fw}, клавишами обратно={back}; наведение {pv}, клик ОД {ap0}→{ap1}, пробел — конец хода={ended}; Q — автобой={q}; размеры кнопок {btn}')
    words = 'слайм' in help_ and 'слайм' in g.ev("'Клик по жителю — поговорить, по клетке — идти, по слайму — бой.'")
    R.check('Подсказки на старте упоминают только слаймов (в лесу враги другие)', 'part' if words else True,
            f'текст помощи: «{help_[:90]}…»; подсказка внизу экрана тоже «по слайму — бой»')
    g.close()


def main(pw, srv, errs):
    t0 = time.time()
    for f in (new_game, old_save, slime_fight, inventory, village, meadow_forest, desktop):
        f(pw, srv, errs)
    R.check('Ошибок в консоли нет', not errs, str(errs[:3]))
    R.summary(); print(f'время {time.time()-t0:.0f} с')


if __name__ == '__main__':
    run(main)
