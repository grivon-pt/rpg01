"""Спринт 1 «Шепчущий лес»: критерии готовности 1–22 и 31–42 (раздел 8 дизайна).
Критерии босса 23–30 — в test_sprint1_stump.py.

Запуск: timeout 150 python3 -u -I tests/test_sprint1_forest.py
Телефон 844×390 (dpr 2, touch). Каждый пункт печатает PASS / PART / FAIL.
"""
import sys, os, time, json, re, subprocess, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qa_common import *

R = Report('Спринт 1 «Шепчущий лес» — переходы, карта, враги, задание, предметы')

DESIGN = open(os.path.join(ROOT, 'docs/design/sprint1-forest.md'), encoding='utf-8').read()
REF = DESIGN.split('```\n    0123456789')[1].split('```')[0].strip('\n').split('\n')[1:]
REF = [row[4:] for row in REF]


def safe(key):
    def deco(fn):
        def run(*a):
            try:
                fn(*a)
            except Exception as e:
                R.check(key, False, 'исключение: ' + repr(e)[:200])
                traceback.print_exc(limit=2)
        return run
    return deco


def reset(g, mp='meadow', x=10, y=10):
    """Чистое состояние: без боя, без врагов, с передышкой, герой на клетке."""
    g.ev(f"if(combat){{for(const e of enemies)e.hp=0;endCombat(false)}};P.dead=0;P.grace=1e9;if(curMap!=='{mp}')setMap('{mp}');enemies.length=0;MAPS[curMap].enemies=enemies;spawnT=999;texts.length=0;placeHero({x},{y});snapCam();0")


def to_forest(g, x=10, y=14):
    reset(g, 'forest', x, y)


def clear_foes(g):
    g.ev("enemies.length=0;spawnT=999;0")


def hero_turn(g, t=8):
    return g.wait("combat&&combat.active===P&&!busy", t)


# ---------------------------------------------------------------- переходы и карта
@safe('1. Выход и табличка на лугу, остальной луг не изменился')
def c1(pw, srv, errs):
    g = Game(pw, srv.url, errs=errs); g.new_game()
    tiles = g.ev("[[46,10],[47,10],[46,11],[47,11]].map(([x,y])=>at(x,y)===PATH).every(Boolean)&&at(44,9)===SIGN")
    reset(g, 'meadow', 42, 10)
    g.tap_cell(44, 9, dy=-8); time.sleep(.2)
    sign = 'Шепчущий лес →' in g.texts()
    new = g.ev("""(()=>{const M=MAPS.meadow;return{t:Array.from(M.tiles),ch:chests.filter(c=>c.map==='meadow').map(c=>[c.x,c.y]),
        cat:[CAT.gx,CAT.gy],npc:NPCS.map(n=>[n.id,n.gx,n.gy])}})()""")
    g.close()
    osrv = Server(old_build_dir())
    try:
        o = Game(pw, osrv.url); o.new_game()
        old = o.ev("({t:Array.from(map),ch:chests.map(c=>[c.x,c.y]),cat:[CAT.gx,CAT.gy],npc:NPCS.map(n=>[n.id,n.gx,n.gy])})")
        o.close()
    finally:
        osrv.stop()
    changed = [(i % 48, i // 48) for i, (a, b) in enumerate(zip(new['t'], old['t'])) if a != b]
    allowed = {(46, 10), (47, 10), (46, 11), (47, 11), (44, 9)}
    same = set(changed) <= allowed and new['ch'] == old['ch'] and new['cat'] == old['cat'] and new['npc'] == old['npc']
    R.check('1. Выход и табличка на лугу, остальной луг не изменился', tiles and sign and same,
            f'тайлы выхода={tiles}, тап по табличке={sign}, изменённые клетки={sorted(changed)}, сундуки/кот/жители те же={same}')


@safe('2. Луг (47,10)→лес (2,13), (47,11)→(2,14), затемнение, баннер')
def c2_3_4(pw, srv, errs):
    g = Game(pw, srv.url, errs=errs); g.new_game()
    g.ev("P.grace=999;placeHero(46,10);snapCam();0"); time.sleep(.3)
    g.tap_cell(47, 10)
    sawfade = g.wait("!!fade", 3)
    g.wait("curMap==='forest'&&!fade&&!busy", 4)
    a = g.ev("[curMap,P.gx,P.gy,P.dir,banner&&banner.s]")
    g.ev("setMap('meadow');P.grace=999;placeHero(46,11);snapCam();0"); time.sleep(.3)
    g.tap_cell(47, 11); g.wait("curMap==='forest'&&!fade&&!busy", 4)
    b = g.ev("[curMap,P.gx,P.gy]")
    R.check('2. Луг (47,10)→лес (2,13), (47,11)→(2,14), затемнение, баннер',
            sawfade and a[:3] == ['forest', 2, 13] and a[4] == 'Шепчущий лес' and b == ['forest', 2, 14] and a[3] == 'right',
            f'затемнение={sawfade}, с (47,10): {a}, с (47,11): {b}')
    # 3. обратно
    g.ev("P.grace=999;placeHero(1,13);snapCam();0"); time.sleep(.3)
    g.tap_cell(0, 13); g.wait("curMap==='meadow'&&!fade&&!busy", 4)
    c = g.ev("[curMap,P.gx,P.gy,P.dir,banner&&banner.s]")
    g.ev("setMap('forest');P.grace=999;placeHero(1,14);snapCam();0"); time.sleep(.3)
    g.tap_cell(0, 14); g.wait("curMap==='meadow'&&!fade&&!busy", 4)
    d = g.ev("[curMap,P.gx,P.gy]")
    R.check('3. Лес (0,13)→луг (45,10), (0,14)→(45,11), баннер',
            c[:3] == ['meadow', 45, 10] and c[4] == 'Луг у Тёплого Ручья' and d == ['meadow', 45, 11] and c[3] == 'left',
            f'с (0,13): {c}, с (0,14): {d}')
    # 4. тап по далёкой клетке выхода
    clear_foes(g); g.ev("P.grace=999;placeHero(39,11);snapCam();0"); time.sleep(.4)
    g.tap_cell(47, 11)
    ok = g.wait("curMap==='forest'&&!fade&&!busy", 8)
    e = g.ev("[curMap,P.gx,P.gy]")
    R.check('4. Тап по далёкой клетке выхода → герой доходит и переходит', ok and e == ['forest', 2, 14], f'итог: {e}')
    g.close()


@safe('5. В бою выход не переносит, «Сначала закончи бой»')
def c5(pw, srv, errs):
    g = Game(pw, srv.url, errs=errs); g.new_game()
    clear_foes(g)
    g.ev("placeHero(45,10);snapCam();const s=makeFoe('green',42,12);s.ac=-200;enemies.push(s);P.grace=0;texts.length=0;startCombat(true,s);0")
    hero_turn(g)
    g.ev("(()=>{const pv=makePreview(47,10);execute(pv);return 0})()")
    time.sleep(1.2)
    a = g.ev("[curMap,P.gx,P.gy,!!combat]"); t = g.texts()
    msg = 'Сначала закончи бой' in t
    g.ev("for(const e of enemies)e.hp=0;endCombat(true);0"); time.sleep(1.0)
    stay = g.ev("curMap")
    g.tap_cell(47, 10)  # тап по этой же клетке — переход
    g.wait("curMap==='forest'&&!busy", 4)
    after = g.ev("curMap")
    R.check('5. В бою выход не переносит, «Сначала закончи бой»',
            a[:3] == ['meadow', 47, 10] and msg and stay == 'meadow' and after == 'forest',
            f'в бою: {a}, надпись={msg}; после боя стоит на выходе: {stay}; тап по клетке: {after}')
    g.close()


@safe('6. Враги не встают на выходы и не появляются ближе 3 клеток')
def c6(pw, srv, errs):
    g = Game(pw, srv.url, errs=errs); g.new_game()
    g.ev("""(()=>{window.QSP=[];for(const f of['spawnSlime','spawnForestFoe']){const o=window[f];
      window[f]=function(){const n=enemies.length;const r=o.apply(this,arguments);if(enemies.length>n){const e=enemies[enemies.length-1];QSP.push([curMap,e.gx,e.gy])}return r}}return 0})()""")
    bad = set(); cnt = 0
    for mp, hero in (('meadow', (30, 20)), ('forest', (12, 18)), ('meadow', (40, 12)), ('forest', (6, 13))):
        g.ev(f"if(curMap!=='{mp}')setMap('{mp}');enemies.length=0;P.grace=1e9;placeHero({hero[0]},{hero[1]});snapCam();populate();spawnT=0;0")
        g.fast(True, 4)
        for _ in range(30):
            time.sleep(.1)
            on = g.ev("enemies.filter(e=>e.hp>0&&exitAt(e.gx,e.gy)).map(e=>[e.gx,e.gy])")
            for c in on: bad.add(('стоит на выходе', mp, tuple(c)))
        g.fast(False)
    sp = g.ev("QSP")
    near = g.ev("QSP.filter(([m,x,y])=>MAPS[m].exits.some(e=>Math.max(Math.abs(e.x-x),Math.abs(e.y-y))<=3))")
    for c in near: bad.add(('появился рядом', tuple(c)))
    R.check('6. Враги не встают на выходы и не появляются ближе 3 клеток', not bad and len(sp) > 20,
            f'появлений проверено: {len(sp)}, нарушений: {sorted(bad)[:5]}')
    g.close()


@safe('7. Передышка 1,5 с после перехода, безопасная опушка x≤4')
def c7(pw, srv, errs):
    g = Game(pw, srv.url, errs=errs); g.new_game()
    clear_foes(g)
    g.ev("setMap('forest');enemies.length=0;spawnT=999;P.grace=999;placeHero(1,13);snapCam();0"); time.sleep(.2)
    g.ev("switchMap(MAPS.forest.exits[0]);0")
    g.wait("curMap==='meadow'&&!busy", 3)
    g.ev("enemies.length=0;spawnT=999;const s=makeFoe('green',43,10);s.wander=99;enemies.push(s);0")
    t0 = time.time(); started = None
    while time.time() - t0 < 3.5:
        if g.ev("!!combat"): started = time.time() - t0; break
        time.sleep(.05)
    # реальное время передышки, считая с конца перехода
    grace_ok = started is not None and started >= 1.0
    reset(g, 'forest', 4, 13)
    # опушка леса
    g.ev("setMap('forest');enemies.length=0;spawnT=999;placeHero(4,13);snapCam();P.grace=0;const m=makeFoe('mushling',6,13);m.wander=99;enemies.push(m);0")
    time.sleep(2.0)
    safe_ok = not g.ev("!!combat")
    g.ev("placeHero(5,14);0"); time.sleep(1.0)
    starts_out = g.ev("!!combat")
    R.check('7. Передышка 1,5 с после перехода, безопасная опушка x≤4', grace_ok and safe_ok and starts_out,
            f'бой со слаймом в 2 клетках начался через {started and round(started,2)} с после конца затемнения; на x=4 боя нет={safe_ok}; на x=5 бой начался={starts_out}')
    g.close()


@safe('8. Раскладка леса совпадает с эталоном 2.5')
def c8_9_10(pw, srv, errs):
    g = Game(pw, srv.url, errs=errs); g.new_game()
    lay = g.ev("""(()=>{const M=MAPS.forest,ch={0:'_',1:'=',2:'~',3:'T',5:'*',7:'.',8:'f',9:'m',10:'o',11:'H',12:'S'};const out=[];
      for(let y=0;y<28;y++){let s='';for(let x=0;x<40;x++)s+=ch[M.tiles[y*40+x]]||'?';out.push(s)}return out})()""")
    diff = []
    for y, (a, b) in enumerate(zip(lay, REF)):
        for x, (ca, cb) in enumerate(zip(a, b)):
            cb = {'1': '_', '2': '_', 'X': '_', 'g': '_'}.get(cb, cb)
            if cb in 'AB': continue
            if ca != cb: diff.append((x, y, ca, cb))
    to_forest(g, 2, 13)
    keys = {'кольцо 1': (8, 6), 'кольцо 2': (25, 5), 'сундук Л1': (28, 6), 'сундук Л2': (8, 22), 'мостик': (19, 13),
            'вход в логово': (27, 21), 'пень': (33, 21), 'гриб (30,19)': (30, 19), 'гриб (35,23)': (35, 23)}
    reach = g.ev("""k=>{const out={};for(const n in k){const[x,y]=k[n];out[n]=!!findPath(2,13,(a,b)=>Math.max(Math.abs(a-x),Math.abs(b-y))<=1,()=>false)}return out}""", keys)
    chests_ok = g.ev("JSON.stringify(chests.filter(c=>c.map==='forest').map(c=>[c.x,c.y]))") == '[[28,6],[8,22]]'
    # ручей сверху донизу, переправа только по мостику
    creek = g.ev("(()=>{for(let y=2;y<=25;y++){let w=0;for(let x=0;x<40;x++)if(at(x,y)===WATER||at(x,y)===BRIDGE)w++;if(w<2)return false}return true})()")
    only_bridge = g.ev("""(()=>{const s=[11,11,11,11];const c=[[18,13],[19,13],[18,14],[19,14]];c.forEach(([x,y])=>set(x,y,WATER));
       const p=findPath(2,13,(a,b)=>a===26&&b===13,()=>false);c.forEach(([x,y])=>set(x,y,BRIDGE));return !p})()""")
    # в логово можно попасть только через проход (27,21)
    ring = g.ev("(()=>{const t=at(27,21);set(27,21,TREE);const p=findPath(2,13,(a,b)=>dE(a,b,LAIR)<1,()=>false);set(27,21,t);return p?1:0})()")
    R.check('8. Раскладка леса совпадает с эталоном 2.5', not diff and all(reach.values()) and chests_ok and creek and only_bridge and ring == 0,
            f'отличий от эталона: {len(diff)} {diff[:4]}, ключевые точки достижимы: {all(reach.values())}, сундуки на месте: {chests_ok}, ручей: {creek}, переправа только мостик: {only_bridge}, в логово можно пройти мимо прохода (27,21): {bool(ring)}')
    # 9. тайлы
    w = g.ev("[MOSS,FERN,MUSH,STUMP,BRIDGE,SIGN].map(t=>{const c=[...Array(28*40).keys()].find(i=>MAPS.forest.tiles[i]===t);const x=c%40,y=c/40|0;return[walkable(x,y),seeThrough(x,y)]})")
    expect = [[True, True], [True, True], [True, True], [False, True], [True, True], [False, True]]
    # огонёк через пенёк: находим пенёк с проходимыми клетками по бокам
    los_stump = g.ev("""(()=>{for(let y=1;y<27;y++)for(let x=1;x<39;x++)if(at(x,y)===STUMP)for(const[dx,dy]of[[1,0],[0,1],[1,1],[1,-1]])if(walkable(x-dx,y-dy)&&walkable(x+dx,y+dy))return los(x-dx,y-dy,x+dx,y+dy);return null})()""")
    los_sign = g.ev("los(2,11,2,13)")
    # различимость: средний цвет тайла в предрисовке
    cols = g.ev("""(()=>{const g=MAPS.forest.cv.getContext('2d');const res={};const names={7:'мох',8:'папоротник',9:'грибы',10:'пенёк',11:'мостик',12:'табличка'};
      for(const t of[7,8,9,10,11,12]){const i=[...Array(28*40).keys()].find(i=>MAPS.forest.tiles[i]===t&&!GLADES.some(g=>dE(i%40,i/40|0,g)<1));const x=i%40,y=i/40|0;
        const d=g.getImageData(x*16,y*16,16,16).data;const hist={};for(let k=0;k<d.length;k+=4){const h=d[k]+','+d[k+1]+','+d[k+2];hist[h]=(hist[h]||0)+1}
        res[names[t]]=hist}return res})()""")
    def dist(a, b):
        keys_ = set(a) | set(b); return sum(abs(a.get(k, 0) - b.get(k, 0)) for k in keys_) / 2
    names = list(cols); worst = min(dist(cols[a], cols[b]) for i, a in enumerate(names) for b in names[i + 1:])
    g.ev("setMap('forest');placeHero(17,13);snapCam();0"); time.sleep(.3); g.shot('/tmp/qa_work/forest_tiles.png')
    R.check('9. Новые тайлы различимы; пенёк и табличка непроходимы, мостик проходим, сквозь пенёк/табличку видно',
            w == expect and los_stump and los_sign and worst >= 12,
            f'проходимость/видимость {w}, огонёк через пенёк={los_stump}, через табличку={los_sign}, мин. различие тайлов {worst:.0f} пикс. из 256')
    # 10. палитра
    lum = g.ev("""(()=>{const L=(id,t,pred)=>{const M=MAPS[id],g=M.cv.getContext('2d');let s=0,n=0;
        for(let i=0;i<M.w*M.h&&n<40;i++){const x=i%M.w,y=i/M.w|0;if(M.tiles[i]!==t||!pred(x,y))continue;const d=g.getImageData(x*16,y*16,16,16).data;
          for(let k=0;k<d.length;k+=4)s+=.2126*d[k]+.7152*d[k+1]+.0722*d[k+2];n++}return n?s/n/256:0};
       const any=()=>true,notExit=(x,y)=>!MAPS.forest.exits.concat(MAPS.meadow.exits).some(e=>e.x===x&&e.y===y);
       return{treeM:L('meadow',TREE,any),treeF:L('forest',TREE,any),pathM:L('meadow',PATH,(x,y)=>x>14&&x<40),pathF:L('forest',PATH,(x,y)=>x>2),
         glade:L('forest',GRASS,(x,y)=>GLADES.some(g=>dE(x,y,g)<1)),moss:L('forest',MOSS,any)}})()""")
    R.check('10. Лесная палитра темнее луговой, поляны светлее мха',
            lum['treeF'] < lum['treeM'] * .9 and lum['pathF'] < lum['pathM'] * .9 and lum['glade'] > lum['moss'] * 1.1,
            'яркость: деревья луг/лес {treeM:.0f}/{treeF:.0f}, тропа {pathM:.0f}/{pathF:.0f}, поляна/мох {glade:.0f}/{moss:.0f}'.format(**lum))
    g.close()


# ---------------------------------------------------------------- сохранение
@safe('11. Сохранение в лесу → «Продолжить» в лес на ту же клетку')
def c11_13(pw, srv, errs):
    g = Game(pw, srv.url, errs=errs); g.new_game()
    reset(g, 'meadow', 46, 10); g.tap_cell(47, 10)
    g.wait("curMap==='forest'&&!busy", 4)
    g.ev("enemies.length=0;MAPS.forest.enemies=enemies;spawnT=0;P.grace=1e9;0")
    g.walk_to(10, 14)
    time.sleep(9)  # автосохранение по таймеру появления врагов (8 с в лесу)
    saved = g.ev("(()=>{const s=JSON.parse(localStorage.getItem(SAVE_KEY));return[s.map,s.gx,s.gy]})()")
    g.reload_continue()
    a = g.ev("[curMap,P.gx,P.gy,running]")
    R.check('11. Сохранение в лесу → «Продолжить» в лес на ту же клетку', saved == ['forest', 10, 14] and a == ['forest', 10, 14, True],
            f'в сохранении {saved}, после загрузки {a}')
    # непроходимая клетка из сохранения → точка появления леса
    g.ev("(()=>{const s=JSON.parse(localStorage.getItem(SAVE_KEY));s.gx=0;s.gy=0;localStorage.setItem(SAVE_KEY,JSON.stringify(s));return 0})()")
    g.reload_continue()
    bad_cell = g.ev("[curMap,P.gx,P.gy]")
    R.check('11б. Клетка из сохранения непроходима → появление на (2,13)', bad_cell == ['forest', 2, 13], f'{bad_cell}')
    # 13. поражение в лесу
    reset(g, 'forest', 10, 20)
    g.ev("P.coins=100;const m=makeFoe('mushling',10,21);m.wander=99;enemies.push(m);startCombat(true,m);0")
    hero_turn(g)
    g.ev("P.hp=1;hurtHero(enemies[0],50);0")
    g.wait("P.dead<=0&&!combat", 6)
    time.sleep(.3)
    d = g.ev("[curMap,P.gx,P.gy,P.coins,P.hp===D.maxHp(),banner&&banner.s]")
    R.check('13. Поражение в лесу → костёр на лугу, −25% монет', d[:5] == ['meadow', 10, 10, 75, True], f'{d}')
    g.close()


@safe('12. Старое сохранение без map грузится на луг, сундуки сохранены')
def c12(pw, srv, errs):
    s = make_old_save(pw, "chests[1].open=true;chests[1].loot=[];chests[3].loot=[['ring_agi',1]];P.coins=77;placeHero(30,11)")
    has_map = 'map' in json.loads(s)
    g = Game(pw, srv.url, errs=errs)
    g.ev("s=>{localStorage.setItem('teplyruchey_save_v3',s)}", s); g.reload_continue()
    a = g.ev("[curMap,P.gx,P.gy,P.coins,chests[1].open,chests[1].loot.length,chests[3].loot.map(l=>l[0]).join(),chests[6].open,chests[6].loot.length,chests[7].loot.length,running]")
    R.check('12. Старое сохранение без map грузится на луг, сундуки сохранены', (not has_map) and a == ['meadow', 30, 11, 77, True, 0, 'ring_agi', False, 2, 3, True],
            f'поле map в старом сохранении: {has_map}; загружено [карта,x,y,монеты,сундук1 открыт,лут1,лут3,Л1 открыт,Л1 лут,Л2 лут]={a[:-1]}')
    g.close()


@safe('14. Кот Пушок переходит вместе с героем; не идущий остаётся на лугу')
def c14_15(pw, srv, errs):
    g = Game(pw, srv.url, errs=errs); g.new_game()
    home = g.ev("(()=>{placeCat();return[CAT.gx,CAT.gy]})()")
    reset(g, 'meadow', 46, 10); g.ev("P.q.cat={s:'active',n:0};CAT.follow=true;CAT.x=P.x-12;CAT.y=P.y;0")
    g.tap_cell(47, 10); g.wait("curMap==='forest'&&!busy", 4); time.sleep(.5)
    a = g.ev("[Math.round(Math.hypot(CAT.x-P.x,CAT.y-P.y)),CAT.gx,CAT.gy]")
    g.ev("placeHero(1,13);0"); g.tap_cell(0, 13); g.wait("curMap==='meadow'&&!busy", 4); time.sleep(.5)
    b = g.ev("Math.round(Math.hypot(CAT.x-P.x,CAT.y-P.y))")
    g.ev("CAT.follow=false;placeCat();P.grace=999;placeHero(46,11);snapCam();0"); g.tap_cell(47, 11)
    g.wait("curMap==='forest'&&!busy", 4); time.sleep(.3)
    drawn_in_forest = g.ev("curMap==='meadow'||CAT.follow")
    g.ev("placeHero(1,14);0"); g.tap_cell(0, 14); g.wait("curMap==='meadow'&&!busy", 4)
    c = g.ev("[CAT.gx,CAT.gy]")
    R.check('14. Кот Пушок переходит вместе с героем; не идущий остаётся на лугу',
            a[0] <= 20 and b <= 20 and not drawn_in_forest and c == home and max(abs(c[0]-41), abs(c[1]-13)) <= 1,
            f'идущий кот: в лесу в {a[0]} px от героя, на лугу {b} px; не идущий рисуется в лесу={drawn_in_forest}, на лугу на {c} (место кота до спринта {home})')
    # 15
    to_forest(g, 2, 13)
    r = g.ev("""(()=>{const out=[];for(const n of NPCS){const t=at(n.gx,n.gy);const tw=![WATER,TREE,HOUSE,STUMP,SIGN].includes(t);
        out.push([n.id,npcAt(n.gx,n.gy)===null||npcAt(n.gx,n.gy)===undefined,walkable(n.gx,n.gy)===tw])}
      const ft=at(10,8),fw=![WATER,TREE,HOUSE,STUMP,SIGN].includes(ft);out.push(['костёр',true,walkable(10,8)===fw]);return out})()""")
    ok = all(x[1] and x[2] for x in r)
    marks_code = 'if(curMap===\'meadow\')for(const n of NPCS){const m=npcMark(n)' in open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
    R.check('15. Жители, костёр и «!»/«?» только на лугу; в лесу их клетки проходимы', ok and marks_code, f'{r}; знаки рисуются только на лугу: {marks_code}')
    g.close()


# ---------------------------------------------------------------- враги
@safe('16. В лесу 4 врага при входе, со временем до 6, только грибовики/шишкари')
def c16(pw, srv, errs):
    g = Game(pw, srv.url, errs=errs); g.new_game()
    g.ev("setMap('meadow');populate();P.grace=1e9;placeHero(46,10);snapCam();0"); g.tap_cell(47, 10); g.wait("curMap==='forest'&&!busy", 4)
    first = g.ev("enemies.filter(e=>!e.boss).map(e=>[e.type,e.gx,e.gy])")
    g.ev("P.grace=1e9;placeHero(3,13);0")
    g.fast(True, 4); g.wait("enemies.filter(e=>!e.boss&&!e.still).length>=6", 20); time.sleep(2); g.fast(False)
    later = g.ev("enemies.filter(e=>!e.boss).map(e=>[e.type,e.gx,e.gy])")
    rule = g.ev("""l=>l.every(([t,x,y])=>x>=8&&at(x,y)!==PATH&&dE(x,y,LAIR)>=1.8)""", first)
    types = {t for t, _, _ in first + later}
    ratio = g.ev("(()=>{const keep=enemies.slice();let m=0,n=0;placeHero(3,13);for(let i=0;i<400;i++){enemies.length=0;spawnForestFoe();if(enemies[0]){n++;if(enemies[0].type==='mushling')m++}}enemies.splice(0,enemies.length,...keep);return Math.round(m/n*100)})()")
    R.check('16. В лесу 4 врага при входе, со временем до 6, только грибовики/шишкари',
            len(first) == 4 and len(later) == 6 and types <= {'mushling', 'cone'} and rule and 45 <= ratio <= 65,
            f'при входе {len(first)}, потом {len(later)}, типы {types}, правила появления соблюдены={rule}; грибовиков среди 400 появлений {ratio}% (дизайн 55%)')
    g.close()


@safe('17. Грибовик: ХП 48, удар 3 ОД, «Сонная спора» раз в 3 хода, −2 ОД')
def c17(pw, srv, errs):
    g = Game(pw, srv.url, errs=errs); g.new_game(); g.strong_hero()
    to_forest(g, 10, 20)
    g.ev("""(()=>{window.QM=[];const sa=window.sporeAttack,ea=window.enemyAttack;
      window.sporeAttack=function(e){QM.push('S');return sa.apply(this,arguments)};window.enemyAttack=function(e){QM.push('A'+e.ap);return ea.apply(this,arguments)};
      const m=makeFoe('mushling',10,21);m.acc=300;m.atk=1;enemies.push(m);P.grace=0;auto=false;P.hp=9999;startCombat(true,m);return 0})()""")
    hp = g.ev("enemies[0].max")
    turns = []; aps = []; zev = False
    for i in range(6):
        hero_turn(g)
        aps.append(g.ev("P.ap"))
        if i == 1: zev = 'Зевота… −2 ОД' in g.ev("texts.map(t=>t.s).join('|')+'|'+(window._z||'')")
        g.ev("QM.length=0;endHeroTurn();0")
        g.wait("combat&&combat.active!==P", 3); hero_turn(g)
        turns.append(''.join(x[0] for x in g.ev("QM")))
        # проверяем надпись сразу после споры
        if turns[-1].startswith('S'): zev = zev or g.ev("texts.some(t=>t.s==='Зевота… −2 ОД')")
    g.fast(False)
    max_ap = g.ev("D.maxAp()")
    spore_turns = [i for i, t in enumerate(turns) if 'S' in t]
    gaps_ok = all(b - a >= 3 for a, b in zip(spore_turns, spore_turns[1:]))
    # после хода со спорой у героя на 2 ОД меньше
    drowsy_ok = all(aps[i + 1] == max_ap - 2 for i in spore_turns if i + 1 < len(aps))
    att_ok = all(t in ('S', 'AA') for t in turns)
    R.check('17. Грибовик: ХП 48, удар 3 ОД, «Сонная спора» раз в 3 хода, −2 ОД',
            hp == 48 and gaps_ok and drowsy_ok and att_ok and zev and bool(spore_turns),
            f'ХП {hp}; ходы грибовика {turns} (S — спора, A — удар 3 ОД); ОД героя по ходам {aps} при максимуме {max_ap}; «Зевота… −2 ОД» видна={zev}')
    g.ev("endCombat(true);0"); g.close()


@safe('18. Шишкарь: бросок при видимости ≤5, отход до 2 шагов, вплотную не подходит')
def c18(pw, srv, errs):
    g = Game(pw, srv.url, errs=errs); g.new_game(); g.strong_hero()
    to_forest(g, 10, 20)
    g.ev("""(()=>{window.QC={thr:[],adj:0,bolt:0,steps:[]};const ct=window.coneThrow;
      window.coneThrow=function(e){QC.thr.push([distE(P,e),los(e.gx,e.gy,P.gx,P.gy)]);return ct.apply(this,arguments)};
      setInterval(()=>{if(bolts.some(b=>b.kind==='cone'))QC.bolt++},20);return 0})()""")
    res = []
    # а) герой вплотную: отход
    g.ev("const c=makeFoe('cone',11,20);c.seq=1;enemies.push(c);P.grace=0;P.hp=9999;auto=false;startCombat(true,c);0")
    for i in range(4):
        hero_turn(g)
        # герой подходит вплотную, если может
        g.ev("(()=>{const c=enemies.find(e=>e.type==='cone');if(!c)return 0;if(distE(P,c)>1){const p=findPath(P.gx,P.gy,(a,b)=>cheb(a,b,c.gx,c.gy)<=1&&!unitAt(a,b,P),(a,b)=>!!unitAt(a,b,P));if(p&&p.length<=P.ap){P.ap-=p.length;const t=p[p.length-1];placeHero(t[0],t[1])}}QC.d0=distE(P,c);return 0})()")
        d0 = g.ev("QC.d0")
        g.ev("QC.mid=[];endHeroTurn();0")
        # следим за ходом шишкаря: ни одного шага вплотную, кроме исходного положения
        mind = 99
        t0 = time.time()
        while time.time() - t0 < 4 and not g.ev("combat&&combat.active===P&&!busy"):
            dd = g.ev("(()=>{const c=enemies.find(e=>e.type==='cone');return c?distE(P,c):99})()"); mind = min(mind, dd); time.sleep(.03)
        d1, corner = g.ev("(()=>{const c=enemies.find(e=>e.type==='cone');return c?[distE(P,c),!retreatCell(c)]:[99,0]})()")
        res.append((d0, d1, 'загнан в угол' if (d1 <= 1 and corner) else ''))
    g.ev("endCombat(true);0")
    retreat_ok = all(d1 >= 2 or why for d0, d1, why in res)
    # в) издалека шишкарь подходит на бросок, но не вплотную
    g.ev("(()=>{for(const e of enemies)e.hp=0;endCombat(true);enemies.length=0;placeHero(8,21);const c=makeFoe('cone',13,21);c.seq=99;c.wander=99;enemies.push(c);P.grace=0;startCombat(false,c);return 0})()")
    near = 99
    for i in range(3):
        t0 = time.time()
        while time.time() - t0 < 4 and not g.ev("combat&&combat.active===P&&!busy"):
            near = min(near, g.ev("(()=>{const c=enemies.find(e=>e.type==='cone');return c?distE(P,c):99})()")); time.sleep(.03)
        g.ev("P.hp=9999;endHeroTurn();0"); time.sleep(.1)
    g.ev("for(const e of enemies)e.hp=0;endCombat(true);0")
    retreat_ok = retreat_ok and near >= 2
    # б) без прямой видимости бросков нет
    clear_foes(g)
    thr = g.ev("QC.thr")
    vis_ok = all(d <= 5 and l for d, l in thr) and len(thr) > 0
    bolt = g.ev("QC.bolt") > 0
    R.check('18. Шишкарь: бросок при видимости ≤5, отход до 2 шагов, вплотную не подходит',
            retreat_ok and vis_ok and bolt,
            f'дистанция до/после хода шишкаря {res}; издалека подошёл не ближе {near}; броски (дистанция, видимость) {thr}; шишка видна в полёте={bolt}')
    g.close()


@safe('19. Полоска очерёдности: значки, «Ходит грибовик/шишкарь/корешок/Древний пень»')
def c19_20(pw, srv, errs):
    g = Game(pw, srv.url, errs=errs); g.new_game(); g.strong_hero()
    to_forest(g, 29, 21); clear_foes(g)
    g.ev("""(()=>{window.QN=new Set();setInterval(()=>{if(combat&&combat.active&&combat.active!==P)QN.add('Ходит '+combat.active.name)},20);
      populate();enemies.splice(0,enemies.length,...enemies.filter(e=>e.boss));const s=stumpOf();
      const m=makeFoe('mushling',28,20),c=makeFoe('cone',27,21),r=makeFoe('root',30,22);r.inCombat=false;enemies.push(m,c,r);
      for(const e of enemies){e.atk=1}P.hp=9999;P.grace=0;auto=false;startCombat(true,s);return 0})()""")
    hero_turn(g)
    chances = g.ev("(()=>{const m=enemies.find(e=>e.type==='mushling'),s=stumpOf();mode='melee';return[hitMelee(m),hitMelee(s),makePreview(m.gx,m.gy).chance,makePreview(s.gx,s.gy).chance,hitBow(m)]})()")
    g.shot('/tmp/qa_work/order_bar.png')
    icons = g.ev("combat.order.map(u=>u===P?'hero':u.type)")
    for _ in range(2):
        hero_turn(g); g.ev("endHeroTurn();0"); time.sleep(.2)
    hero_turn(g, 12)
    names = g.ev("[...QN]")
    g.ev("endCombat(true);0")
    need = {'Ходит грибовик', 'Ходит шишкарь', 'Ходит корешок', 'Ходит Древний пень'}
    R.check('19. Полоска очерёдности: значки, «Ходит грибовик/шишкарь/корешок/Древний пень»', need <= set(names) and {'mushling', 'cone', 'root', 'stump'} <= set(icons),
            f'в очереди {icons}; надписи {sorted(names)} (скриншот /tmp/qa_work/order_bar.png)')
    R.check('20. Шанс в подсказке по формуле (эталон: грибовик 66%, пень 62%)', chances[0] == 66 and chances[1] == 62 and chances[2] == 66 and chances[3] == 62,
            f'меч по грибовику {chances[0]}% (подсказка {chances[2]}%), по пню {chances[1]}% (подсказка {chances[3]}%)')
    g.close()


@safe('21. Добыча лесных врагов, монеты и опыт; слизи нет')
def c21_22(pw, srv, errs):
    g = Game(pw, srv.url, errs=errs); g.new_game()
    to_forest(g, 10, 20)
    stat = g.ev("""(()=>{P.lvl=99;const out={};for(const t of['mushling','cone','green','blue']){let it={},coins=0,xp=0,N=600;
      for(let i=0;i<N;i++){items.length=0;const x0=P.xp;const e=makeFoe(t,10,21);defeatFoe(e);xp+=P.xp-x0;
        for(const i_ of items){if(i_.kind==='coin')coins++;else{const k=i_.kind==='item'?i_.id:i_.kind;it[k]=(it[k]||0)+1}}P.xp=0}
      for(const k in it)it[k]=Math.round(it[k]/N*100);out[t]={items:it,coins:+(coins/N).toFixed(2),cm:+(D.coinMul()*(FOES[t].coin+.4)).toFixed(2),xpEach:Math.round(FOES[t].xp*D.xpMul()),xp:Math.round(xp/N)}}
      items.length=0;return out})()""")
    m, c = stat['mushling'], stat['cone']
    ok = (25 <= m['items'].get('forest_mush', 0) <= 45 and 'goo' not in m['items'] and 'goo' not in c['items'] and 35 <= c['items'].get('arrows', 0) <= 55
          and abs(m['coins'] - m['cm']) < .4 and abs(c['coins'] - c['cm']) < .4 and m['xp'] == m['xpEach'] and c['xp'] == c['xpEach'] and FOES_OK(g))
    R.check('21. Добыча лесных врагов, монеты и опыт; слизи нет', ok,
            f"грибовик: {m}; шишкарь: {c}")
    # 22. слаймы
    g.ev("setMap('meadow');0")
    q = g.ev("""(()=>{P.q={slimes:{s:'active',n:0},blues:{s:'active',n:0}};const s=FOES.green,b=FOES.blue;
       defeatFoe(makeFoe('green',30,12));defeatFoe(makeFoe('blue',30,12));items.length=0;
       const bl=makeFoe('blue',30,12),gr=makeFoe('green',30,12);
       return[P.q.slimes.n,P.q.blues.n,[s.hp,s.atk,s.acc,s.maxAp,s.ac,s.xp],[b.hp,b.atk,b.acc,b.maxAp,b.ac,b.xp],hitEnemy(bl)-hitEnemy(gr),bl.blue,gr.blue]})()""")
    g_ = stat['green']; b_ = stat['blue']
    ok22 = q[0] == 2 and q[1] == 1 and q[2] == [22, 6, 0, 5, 5, 5] and q[3] == [38, 9, 8, 6, 10, 8] and q[4] == 8 and 40 <= g_['items'].get('goo', 0) <= 60
    R.check('22. Слаймы как раньше: ХП/урон/КБ, синие +8 точности, счётчики заданий, слизь', ok22,
            f'счётчики слаймы/синие {q[0]}/{q[1]}, зелёный {q[2]}, синий {q[3]}, разница точности {q[4]}, слизь со слайма {g_["items"].get("goo")}%')
    g.close()


def FOES_OK(g):
    f = g.ev("FOES")
    return (f['mushling']['hp'] == 48 and f['mushling']['xp'] == 12 and f['mushling']['coin'] == 3 and f['cone']['hp'] == 30 and f['cone']['xp'] == 10
            and f['cone']['coin'] == 3 and f['cone']['range'] == 5 and f['stump']['xp'] == 70 and f['stump']['coin'] == 20)


# ---------------------------------------------------------------- задание и диалоги
@safe('31. «Что слышно в округе?» и «!» только после «Синей напасти»')
def c31_36(pw, srv, errs):
    g = Game(pw, srv.url, errs=errs); g.new_game()
    reset(g, 'meadow', 17, 17)
    g.ev("P.lvl=99;P.st.per=5;P.st.cha=5;P.st.int=6;P.q={slimes:{s:'done',n:5},blues:{s:'active',n:3}};P.grace=999;placeHero(17,17);snapCam();0")
    mark_ready = g.ev("npcMark(NPCS[0])")  # «?» за синих
    g.ev("P.q.blues={s:'active',n:1};0"); mark_before = g.ev("npcMark(NPCS[0])")
    g.ev("talk(NPCS[0]);0"); opts_before = [o[0] for o in g.dlg()[1]]; g.ev("closeDlg();0")
    g.ev("P.q.blues={s:'done',n:3};0"); mark_after = g.ev("npcMark(NPCS[0])")
    g.ev("talk(NPCS[0]);0"); opts_after = [o[0] for o in g.dlg()[1]]
    R.check('31. «Что слышно в округе?» и «!» только после «Синей напасти»',
            'Что слышно в округе?' not in opts_before and mark_before == '' and mark_after == '!' and 'Что слышно в округе?' in opts_after,
            f'до сдачи: пункт={"Что слышно в округе?" in opts_before}, знак «{mark_before}»; после: пункт={"Что слышно в округе?" in opts_after}, знак «{mark_after}»')
    # 32. тексты дословно и проверки параметров
    g.opt('Что слышно')
    t, opts = g.dlg()
    exp_t = 'Беда у нас тихая, но странная. За восточной опушкой, прямо по дороге, начинается Шепчущий лес. Раньше туда грибники ходили, а теперь лес шепчет — по ночам до самой деревни слышно. Говорят, на дальней поляне проснулся Древний пень. Тропы корнями путает, грибовиков на людей науськивает. Разбудил его кто-то… или что-то.'
    exp_o = [['Я схожу и успокою его.', False], ['[Восприятие 6] А что именно шепчет лес?', True], ['[Обаяние 6] Дело непростое. Добавишь за смелость?', True], ['Не сейчас', False]]
    low_ok = t == exp_t and opts == exp_o
    g.opt('Не сейчас'); g.ev("closeDlg();P.eq.trinket='heart_forest';P.st.cha=6;0")  # амулет: +1 Восприятие → 6
    g.ev("talk(NPCS[0]);0"); g.opt('Что слышно'); opts2 = g.dlg()[1]
    amulet_ok = opts2[1] == ['[Восприятие 6] А что именно шепчет лес?', False] and opts2[2][1] is False
    x0 = g.ev("P.xp+P.lvl*1000"); g.opt('шепчет лес'); t3, o3 = g.dlg()
    xp_gain = g.ev("P.xp+P.lvl*1000") - x0; xp_exp = g.ev("Math.round(10*D.xpMul())")
    exp_t3 = 'Ишь, какой чуткий… Я сам раз ходил, прислушался. Шепчет: „грибы… грибы…“. Думаю, пень из грибов силы тянет. Будешь с ним толковать — срывай грибы вокруг него, не давай подкрепиться.'
    t3_ok = t3 == exp_t3 and [o[0] for o in o3] == ['Возьмусь!', 'Подумаю']
    g.opt('Подумаю'); g.opt('Что слышно'); o4 = [o[0] for o in g.dlg()[1]]
    once = not any('шепчет лес' in o for o in o4)
    g.opt('Добавишь'); t5, o5 = g.dlg()
    t5_ok = t5 == 'Ох, торгуешься, как Борис… Ладно. Вернёшься — получишь сверху ещё 30 монет. Слово старосты.' and [o[0] for o in o5] == ['До встречи']
    st = g.ev("[qState('stump'),!!P.flags.efimStumpAdv]")
    g.opt('До встречи')
    # «Я схожу…» отдельно (на копии состояния)
    g.ev("window._q=JSON.stringify([P.q,P.flags]);P.q.stump=undefined;delete P.q.stump;P.flags.efimStumpAdv=0;talk(NPCS[0]);0"); g.opt('Что слышно'); g.opt('Я схожу'); t6 = g.dlg()[0]
    t6_ok = t6 == 'Вот спасибо. Только не обижай старика зря — он лесу хозяин, ему просто спать пора. Иди по дороге на восток, за мостик через ручей, а там на юго-восток, к поляне в кольце деревьев. И грибов набери в дорогу — лесные грибы силы прибавляют.'
    g.opt('До встречи'); g.ev("(()=>{const[a,b]=JSON.parse(window._q);P.q=a;P.flags=b;return 0})()")
    R.check('32. Тексты диалога дословно; [Восприятие 6]/[Обаяние 6] видны всегда, нажимаются при нужном параметре (с амулетом)',
            low_ok and amulet_ok and t3_ok and t5_ok and t6_ok,
            f'реплика и пункты при В5/О5: {low_ok}; с амулетом В6, О6 доступны: {amulet_ok}; ответ на [В6]: {t3_ok}; на [О6]: {t5_ok}; на «Я схожу»: {t6_ok}')
    # 34. журнал и трекер
    tr0 = g.ev("trackerText()")
    g.ev("openPanel('quests');0"); time.sleep(.2); jr = g.ev("$('pinv').innerText"); g.ev("togglePanel(false);0")
    # после исправлений: трекер показывает задание текущей карты (в лесу — «Шёпот в чаще»),
    # иначе первое активное; остальные активные — «+N»
    g.ev("closeDlg();P.q.goo={s:'active',n:0};0"); tr_goo = g.ev("trackerText()")
    reset(g, 'forest', 3, 13); tr_goo_forest = g.ev("trackerText()"); time.sleep(.3)
    g.shot('/tmp/qa_tracker_forest.png')
    reset(g, 'meadow', 17, 17); g.ev("delete P.q.goo;0"); tr_back = g.ev("trackerText()")
    g.ev("P.flags.stumpDown=1;0"); tr1 = g.ev("trackerText()"); mk = g.ev("npcMark(NPCS[0])")
    R.check('34. Задание в журнале и под полосками: «• Шёпот в чаще 0/1» → «✔ … 1/1», над Ефимом «?»; в лесу трекер показывает его, иначе первое активное с «+N»',
            tr0 == '• Шёпот в чаще 0/1' and 'Шёпот в чаще' in jr and tr1 == '✔ Шёпот в чаще 1/1' and mk == '?'
            and tr_goo == '• Слизь для зелий 0/5 +1' and tr_goo_forest == '• Шёпот в чаще 0/1 +1' and tr_back == tr0,
            f'трекер «{tr0}» → «{tr1}», знак «{mk}», в журнале={"Шёпот в чаще" in jr}; '
            f'со «Слизью для зелий»: на лугу «{tr_goo}», в лесу «{tr_goo_forest}» (скриншот /tmp/qa_tracker_forest.png)')
    # 33. награда
    c0, x0 = g.ev("[P.coins,P.xp+P.lvl*1000]")
    b0 = g.ev("[bagCount('pot_hp'),bagCount('forest_mush')]")
    g.ev("closeDlg();talk(NPCS[0]);0"); done_opt = g.opt('Шёпот в чаще» выполнено'); td = g.dlg()[0]
    c1, b1 = g.ev("P.coins"), g.ev("[bagCount('pot_hp'),bagCount('forest_mush')]")
    R.check('33. [Обаяние 6] при сдаче даёт 130 монет вместо 100; [Восприятие 6] +10 опыта (×множитель) один раз',
            done_opt and c1 - c0 == 130 and xp_gain == xp_exp and once and b1[0] - b0[0] == 2 and b1[1] - b0[1] == 2,
            f'монет +{c1-c0}, предметы +зелья {b1[0]-b0[0]} +грибы {b1[1]-b0[1]}; опыт за [В6] +{xp_gain} (ожидалось 10×{g.ev("D.xpMul()"):.2f}={xp_exp}), пункт исчез после выбора={once}')
    done_txt = td == 'Лес снова шепчет только листьями — я ночью сам выходил слушать. Спасибо тебе, путник! Вот, держи награду.'
    # 36. туман [Интеллект 7]
    g.opt('Рад помочь'); o7 = g.dlg()[1]
    fog = [o for o in o7 if 'туман с башни' in o[0]]
    g.ev("P.st.int=7;closeDlg();talk(NPCS[0]);0")
    x1 = g.ev("P.xp+P.lvl*1000"); g.opt('туман с башни'); t8 = g.dlg()[0]; gain = g.ev("P.xp+P.lvl*1000") - x1
    g.opt('Похоже на то'); o9 = [o[0] for o in g.dlg()[1]]
    R.check('36. После сдачи [Интеллект 7] про туман, +20 опыта один раз',
            bool(fog) and fog[0][1] is True and gain == g.ev("Math.round(20*D.xpMul())") and t8.startswith('Туман, говоришь…') and not any('туман с башни' in o for o in o9) and done_txt,
            f'пункт при И6 виден и заблокирован={bool(fog) and fog[0][1]}; опыт +{gain}; повторно нет={not any("туман с башни" in o for o in o9)}; текст сдачи дословно={done_txt}')
    g.ev("closeDlg();0")
    # 35. пень успокоен до взятия
    g.ev("delete P.q.stump;P.flags={stumpDown:1};0")
    g.ev("talk(NPCS[0]);0"); g.opt('Что слышно'); g.opt('Я схожу'); g.opt('До встречи')
    r35 = g.ev("[qState('stump'),qReady('stump'),npcMark(NPCS[0]),trackerText()]")
    R.check('35. Пень успокоен до взятия → задание сразу готово к сдаче', r35[1] is True and r35[2] == '?', f'{r35}')
    g.close()


# ---------------------------------------------------------------- предметы
@safe('37. Лесной гриб: 2 ОД, 25% ХП и 15% маны; у Миры продаётся, Борис покупает за VAL×множитель')
def c37_40(pw, srv, errs):
    g = Game(pw, srv.url, errs=errs); g.new_game(); g.strong_hero()
    to_forest(g, 10, 20)
    g.ev("addItem('forest_mush',3,true);const m=makeFoe('mushling',10,22);m.wander=99;m.atk=1;enemies.push(m);P.grace=0;auto=false;startCombat(true,m);0")
    hero_turn(g)
    g.ev("P.hp=10;P.mp=0;0")
    before = g.ev("[P.ap,P.hp,P.mp,bagCount('forest_mush')]")
    g.ev("openPanel('inv');0"); time.sleep(.2)
    g.ev("[...document.querySelectorAll('#pinv [data-use]')].find(b=>P.bag[+b.dataset.use].id==='forest_mush').click();0"); time.sleep(.2)
    after = g.ev("[P.ap,P.hp,P.mp,bagCount('forest_mush'),Math.round(D.maxHp()*.25),Math.round(D.maxMp()*.15)]")
    # Бой закрываем в одном вызове вместе с уборкой грибовика и передышкой: иначе живой грибовик в 2 клетках
    # при P.grace=0 на следующем кадре снова начинает бой, тот «переезжает» на луг, и Гордей отвечает
    # «Не до разговоров!» (так п. 38 падал примерно в 1 прогоне из 6).
    g.ev("togglePanel(false);for(const e of enemies)e.hp=0;endCombat(true);enemies.length=0;P.grace=1e9;0")
    use_ok = before[0] - after[0] == 2 and after[1] - before[1] == after[4] and after[2] - before[2] == after[5] and after[3] == before[3] - 1
    # магазины
    reset(g, 'meadow', 12, 10); g.ev("P.st.cha=6;P.flags.discount=0;0")
    mira = g.ev("[STOCK.mira.some(s=>s[0]==='forest_mush'),buyPrice('forest_mush','mira'),[1,5,6,10].map(c=>{const o=P.st.cha;P.st.cha=c;const p=buyPrice('forest_mush','mira');P.st.cha=o;return p})]")
    g.ev("openShop('mira');0"); time.sleep(.2); mira_ui = 'Лесной гриб' in g.ev("$('pinv').innerText"); g.ev("togglePanel(false);0")
    g.ev("openShop('boris');0"); time.sleep(.2)
    c0 = g.ev("P.coins"); sp = g.ev("sellPrice('forest_mush')")
    g.ev("[...document.querySelectorAll('#pinv [data-sell]')].find(b=>P.bag[+b.dataset.sell].id==='forest_mush').click();0"); time.sleep(.1)
    sold = g.ev("P.coins") - c0; g.ev("togglePanel(false);0")
    # цену считаем от VAL в игре (после исправлений VAL гриба намеренно 13), а не от константы
    val, mul_s, exp_sell, exp_buy = g.ev("[VAL.forest_mush,sellMul(),Math.max(1,Math.floor(VAL.forest_mush*sellMul())),Math.max(1,Math.round(VAL.forest_mush*buyMul('mira')))]")
    R.check('37. Лесной гриб: 2 ОД, 25% ХП и 15% маны; у Миры продаётся, Борис покупает за VAL×множитель',
            use_ok and mira[0] and mira_ui and sold == exp_sell and mira[1] == exp_buy,
            f'в бою [ОД,ХП,мана,грибы] {before[:4]} → {after[:4]}; у Миры есть={mira[0]}, цена при О6 {mira[1]} (ожидалось {exp_buy}; при О1/5/6/10: {mira[2]}); Борис дал {sold} ({val}×{mul_s:.2f}={exp_sell})')
    # 38. лук и броня
    g.ev("addItem('bow_ash',1,true);addItem('bark_armor',1,true);P.eq.bow='bow_ash';P.eq.armor='bark_armor';P.eq.trinket=null;P.st.per=6;P.up={};0")
    bow = g.ev("[D.bow(),D.bowAp(),D.bowRange(),D.armorAc(),D.def()-Math.floor(stv('end')/2)]")
    g.ev("P.coins=1000;addItem('goo',20,true);talk(NPCS[2]);0")
    pre = g.ev("[!!combat,!!dlgNpc]")  # если бой не закрылся, Гордей не говорит — покажем это в итоге
    ups = [o[0] for o in g.dlg()[1]]
    g.opt('Улучшить лук'); g.opt('Спасибо'); g.opt('Улучшить броню'); g.opt('Спасибо'); g.ev("closeDlg();0")
    up = g.ev("[P.up.bow_ash||0,P.up.bark_armor||0,getIt('bow_ash').dmg,getIt('bark_armor').ac,getIt('bark_armor').def]")
    R.check('38. Ясеневый лук 9–13+В, 4 ОД, дальность 8+⌊В/3⌋; Кора-доспех КБ+7/защ.+3; оба улучшаются у Гордея',
            bow == [[15, 19], 4, 10, 7, 3] and up[:2] == [1, 1] and up[2] == [11, 15] and up[3:] == [8, 4],
            f'лук [урон,ОД,дальность] {bow[:3]} при В6, броня КБ {bow[3]} защита +{bow[4]}; у Гордея {up}'
            + ('' if pre == [False, True] else f'; перед разговором бой={pre[0]}, диалог открыт={pre[1]}'))
    # 39. сердце леса
    g.ev("P.eq.trinket=null;P.st.per=5;P.st.end=5;0")
    h0 = g.ev("[D.maxHp(),stv('per'),stv('end')]")
    g.ev("addItem('heart_forest',1,true);openPanel('inv');0"); time.sleep(.2)
    g.ev("[...document.querySelectorAll('#pinv [data-eq]')].find(b=>P.bag[+b.dataset.eq].id==='heart_forest').click();0"); time.sleep(.1)
    h1 = g.ev("[D.maxHp(),stv('per'),stv('end')]")
    g.ev("openPanel('hero');0"); time.sleep(.2)
    hero_txt = g.ev("[...document.querySelectorAll('#pstats .row')].filter(r=>r.querySelector('.v').style.color).map(r=>r.querySelector('b').textContent+'='+r.querySelector('.v').textContent)")
    g.ev("togglePanel(false);0")
    R.check('39. Сердце леса: +1 Выносливость и Восприятие, видно на экране героя, максимум ХП растёт',
            h1[1] == h0[1] + 1 and h1[2] == h0[2] + 1 and h1[0] > h0[0] and len(hero_txt) == 2,
            f'[макс.ХП,В,Вын] {h0} → {h1}; выделены на экране героя: {hero_txt}')
    # 40. лесные сундуки
    reset(g, 'forest', 27, 7); g.ev("P.bag=[];P.eq={melee:'sword_wood',bow:'bow_short',armor:'jacket',trinket:null};P.st.str=5;0")
    g.tap_cell(28, 6, dy=-6); time.sleep(1.0)
    l1 = g.ev("[bagCount('bow_ash'),bagCount('arrows'),chests[6].open,chests[6].loot.length]")
    g.ev("placeHero(9,21);snapCam();addItem('chain',1,true);addItem('chain',1,true);addItem('goo',30,true);0"); time.sleep(.2)  # почти полная сумка
    w0 = g.ev("[bagWeight(),D.carry()]")
    g.tap_cell(8, 22, dy=-6); time.sleep(1.0)
    l2 = g.ev("[bagCount('bark_armor'),bagCount('forest_mush'),bagCount('pot_mp'),JSON.stringify(chests[7].loot)]")
    R.check('40. Лесные сундуки (28,6), (8,22) открываются, лишнее по весу остаётся',
            l1 == [1, 15, True, 0] and l2[0] == 1 and l2[3] != '[]',
            f'Л1: лук {l1[0]}, стрелы {l1[1]}, пуст={l1[3]==0}; Л2 при весе {w0[0]}/{w0[1]}: получено {l2[:3]}, осталось {l2[3]}')
    g.close()


# ---------------------------------------------------------------- общее
@safe('41. node --check, тесты зелёные, ошибок в консоли нет на обеих картах')
def c41(pw, srv, errs):
    html = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
    js = html.split('<script>')[1].split('</script>')[0]
    p = '/tmp/qa_sprint1_check.js'; open(p, 'w', encoding='utf-8').write(js)
    r = subprocess.run(['node', '--check', p], capture_output=True, text=True)
    R.check('41. node --check, ошибок в консоли нет на обеих картах', r.returncode == 0 and not errs,
            f'node --check: {"ок" if r.returncode == 0 else r.stderr[:200]}; ошибок страницы за прогон: {len(errs)} {errs[:3]}')


@safe('42. Тапы по грибу, табличке, сундуку и клетке выхода срабатывают с первого раза')
def c42(pw, srv, errs):
    g = Game(pw, srv.url, errs=errs); g.new_game()
    res = {}
    # табличка в лесу
    reset(g, 'forest', 4, 13)
    g.tap_cell(2, 12, dy=-8); time.sleep(.15); res['табличка'] = '← Тёплый Ручей' in g.texts()
    # гриб-боровик вне боя: подойти и сорвать
    g.ev("P.flags.stumpDown=1;P.flags.stumpAt=[33,21];placeHero(31,21);snapCam();0"); time.sleep(.3)
    n0 = g.ev("bagCount('forest_mush')"); g.tap_cell(30, 19, dy=-6); g.wait("!P.mv", 3); time.sleep(.3)
    res['гриб'] = g.ev("bagCount('forest_mush')") == n0 + 1
    # сундук
    g.ev("placeHero(26,7);snapCam();0"); time.sleep(.3); g.tap_cell(28, 6, dy=-6); g.wait("!P.mv", 3); time.sleep(.3)
    res['сундук'] = g.ev("chests[6].open")
    # выход (уже проверен в п. 2–4, здесь — с первого тапа)
    g.ev("placeHero(2,14);snapCam();0"); time.sleep(.3); g.tap_cell(0, 14); res['выход'] = g.wait("curMap==='meadow'&&!busy", 4)
    # размер клетки на экране и грибы под кнопками в бою у логова
    cell_css = g.ev("16*S/(cv.width/innerWidth)")
    g.ev("setMap('forest');P.flags.stumpDown=0;for(const m of MAPS.forest.shrooms)m.alive=true;enemies.length=0;populate();enemies.splice(0,enemies.length,...enemies.filter(e=>e.boss));spawnT=999;placeHero(27,21);snapCam();P.grace=0;auto=false;0")
    g.walk_to(28, 21); hero_turn(g); time.sleep(.6)
    under = g.ev("""MAPS.forest.shrooms.filter(m=>m.alive).map(m=>{const k=cv.width/innerWidth,p=cellPx(m.x,m.y);const x=(p.x-CX)*S/k,y=(p.y-6-CY)*S/k;
        const el=document.elementFromPoint(x,y);return[m.x,m.y,el&&el.classList.contains('btn')?el.id:'']}).filter(r=>r[2])""")
    g.shot('/tmp/qa_shroom_under_button.png')
    # игрок тапает по грибу (35,23), который на экране под кнопкой «конец хода»
    tap_res = None
    if under:
        mx, my = under[0][0], under[0][1]
        g.ev("texts.length=0;0"); ap0 = g.ev("P.ap")
        g.tap_cell(mx, my, dy=-6); time.sleep(.3)
        tap_res = g.ev(f"[combat&&combat.active===P,P.ap,MAPS.forest.shrooms.find(m=>m.x==={mx}&&m.y==={my}).alive,!!preview]")
        tap_res = f'тап по грибу ({mx},{my}): ход героя продолжается={tap_res[0]}, ОД {ap0}→{tap_res[1]}, гриб на месте={tap_res[2]}, подсказка «сорвать» появилась={tap_res[3]}'
    g.ev("endCombat(false);0")
    ok = all(res.values()) and cell_css >= 44
    R.check('42. Тапы по грибу, табличке, сундуку и клетке выхода срабатывают с первого раза', 'part' if ok and under else ok,
            f'{res}; клетка {cell_css:.0f} CSS px; в бою у входа в логово под кнопками грибы: {under}; {tap_res}')
    g.close()


def main(pw, srv, errs):
    t0 = time.time()
    for f in (c1, c2_3_4, c5, c6, c7, c8_9_10, c11_13, c12, c14_15, c16, c17, c18, c19_20, c21_22, c31_36, c37_40, c42):
        f(pw, srv, errs)
    c41(pw, srv, errs)
    R.summary(); print(f'время {time.time()-t0:.0f} с')


if __name__ == '__main__':
    run(main)
